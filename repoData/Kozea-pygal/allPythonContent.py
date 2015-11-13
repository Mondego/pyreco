__FILENAME__ = cabaret
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
from cabaret import create_app
import logging
app = create_app()

try:
    from log_colorizer import make_colored_stream_handler
    handler = make_colored_stream_handler()
    app.logger.handlers = []
    app.logger.addHandler(handler)
    import werkzeug
    werkzeug._internal._log('debug', '<-- I am with stupid')
    logging.getLogger('werkzeug').handlers = []
    logging.getLogger('werkzeug').addHandler(handler)

    handler.setLevel(logging.DEBUG)
    app.logger.setLevel(logging.DEBUG)
    logging.getLogger('werkzeug').setLevel(logging.DEBUG)
except:
    pass


try:
    import wsreload
except ImportError:
    app.logger.debug('wsreload not found')
else:
    url = "http://cabaret.l:12221/*"

    def log(httpserver):
        app.logger.debug('WSReloaded after server restart')
    wsreload.monkey_patch_http_server({'url': url}, callback=log)
    app.logger.debug('HTTPServer monkey patched for url %s' % url)

try:
    from wdb.ext import WdbMiddleware, add_w_builtin
except ImportError:
    pass
else:
    add_w_builtin()
    app.wsgi_app = WdbMiddleware(app.wsgi_app, start_disabled=True)

app.run(debug=True, threaded=True, host='0.0.0.0', port=12221)

########NEW FILE########
__FILENAME__ = data
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.

labels = ['AURSAUTRAUIA',
          'dpvluiqhu enuie',
          'su sru a nanan a',
          '09_28_3023_98120398',
          u'éàéç€®ð{æə|&']
series = {
    'Female': [4, 2, 3, 0, 2],
    'Male': [5, 1, 1, 3, 2]
}

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
# This file is part of pygal
from pygal import (
    Bar, Gauge, Pyramid, Funnel, Dot, StackedBar, XY,
    CHARTS_BY_NAME, Config, Line, DateY, Worldmap, Histogram, Box,
    FrenchMap_Departments, FrenchMap_Regions, Pie)
from pygal.style import styles, Style
from pygal.colors import rotate
from pygal.graph.frenchmap import DEPARTMENTS, REGIONS
from random import randint, choice


def get_test_routes(app):
    lnk = lambda v, l=None: {
        'value': v,
        'xlink': 'javascript:alert("Test %s")' % v,
        'label': l}

    @app.route('/test/unsorted')
    def test_unsorted():
        bar = Bar(style=styles['neon'])
        bar.add('A', {'red': 10, 'green': 12, 'blue': 14})
        bar.add('B', {'green': 11, 'blue': 7})
        bar.add('C', {'blue': 7})
        bar.add('D', {})
        bar.add('E', {'blue': 2, 'red': 13})
        bar.x_labels = ('red', 'green', 'blue')
        return bar.render_response()

    @app.route('/test/bar_links')
    def test_bar_links():
        bar = Bar(style=styles['neon'])
        bar.js = ('http://l:2343/svg.jquery.js',
                  'http://l:2343/pygal-tooltips.js')
        bar.add('1234', [
            {'value': 10,
             'label': 'Ten',
             'xlink': 'http://google.com?q=10'},
            {'value': 20,
             'tooltip': 'Twenty',
             'xlink': 'http://google.com?q=20'},
            30,
            {'value': 40,
             'label': 'Forty',
             'xlink': 'http://google.com?q=40'}
        ])

        bar.add('4321', [40, {
            'value': 30,
            'label': 'Thirty',
            'xlink': 'http://google.com?q=30'
        }, 20, 10])
        bar.x_labels = map(str, range(1, 5))
        bar.logarithmic = True
        bar.zero = 1
        return bar.render_response()

    @app.route('/test/xy_links')
    def test_xy_links():
        xy = XY(style=styles['neon'])
        xy.add('1234', [
            {'value': (10, 5),
             'label': 'Ten',
             'xlink': 'http://google.com?q=10'},
            {'value': (20, 20),
             'tooltip': 'Twenty',
             'xlink': 'http://google.com?q=20'},
            (30, 15),
            {'value': (40, -5),
             'label': 'Forty',
             'xlink': 'http://google.com?q=40'}
        ])

        xy.add('4321', [(40, 10), {
            'value': (30, 3),
            'label': 'Thirty',
            'xlink': 'http://google.com?q=30'
        }, (20, 10), (10, 21)])
        xy.x_labels = map(str, range(1, 5))
        return xy.render_response()

    @app.route('/test/long_title')
    def test_long_title():
        bar = Bar()
        bar.add('Looooooooooooooooooooooooooooooooooong', [2, None, 12])
        bar.title = (
            '1 12 123 1234 12345 123456 1234567 12345678 123456789 1234567890 '
            '12345678901 123456789012 1234567890123 12345678901234 '
            '123456789012345 1234567890123456 12345678901234567 '
            '123456789012345678 1234567890123456789 12345678901234567890 '
            '123456789012345 1234567890123456 12345678901234567 '
            '12345678901 123456789012 1234567890123 12345678901234 '
            '1 12 123 1234 12345 123456 1234567 12345678 123456789 1234567890')
        return bar.render_response()

    @app.route('/test/multiline_title')
    def test_multiline_title():
        bar = Bar()
        bar.add('Looooooooooooooooooooooooooooooooooong', [2, None, 12])
        bar.title = (
            'First line \n Second line \n Third line'
        )
        return bar.render_response()

    @app.route('/test/long_labels')
    def test_long_labels():
        bar = Bar()
        bar.add('Long', [2, None, 12])
        bar.title = (
            '1 12 123 1234 12345 123456 1234567 12345678 123456789 1234567890')
        bar.x_labels = 'a' * 100, 'b ' * 50, 'cc ! ' * 20
        bar.x_label_rotation = 45
        return bar.render_response()

    @app.route('/test/none')
    def test_bar_none():
        bar = Bar()
        bar.add('Lol', [2, None, 12])
        return bar.render_response()

    @app.route('/test/gauge')
    def test_gauge():
        gauge = Gauge()

        gauge.range = [-10, 10]
        gauge.add('Need l', [2.3, 5.12])
        gauge.add('No', [99, -99])
        return gauge.render_response()

    @app.route('/test/pyramid')
    def test_pyramid():
        pyramid = Pyramid()

        pyramid.x_labels = ['0-25', '25-45', '45-65', '65+']
        pyramid.add('Man single', [2, 4, 2, 1])
        pyramid.add('Woman single', [10, 6, 1, 1])
        pyramid.add('Man maried', [10, 3, 4, 2])
        pyramid.add('Woman maried', [3, 3, 5, 3])

        return pyramid.render_response()

    @app.route('/test/funnel')
    def test_funnel():
        funnel = Funnel()

        funnel.add('1', [1, 2, 3])
        funnel.add('3', [3, 4, 5])
        funnel.add('6', [6, 5, 4])
        funnel.add('12', [12, 2, 9])

        return funnel.render_response()

    @app.route('/test/dot')
    def test_dot():
        dot = Dot()
        dot.x_labels = map(str, range(4))
        dot.add('a', [1, lnk(3, 'Foo'), 5, 3])
        dot.add('b', [2, 2, 0, 2])
        dot.add('c', [5, 1, 5, lnk(3, 'Bar')])
        dot.add('d', [5, 5, lnk(0, 'Babar'), 3])

        return dot.render_response()

    @app.route('/test/<chart>')
    def test_for(chart):
        graph = CHARTS_BY_NAME[chart]()
        graph.add('1', [1, 3, 12, 3, 4, None, 9])
        graph.add('2', [7, -4, 10, None, 8, 3, 1])
        graph.add('3', [7, -14, -10, None, 8, 3, 1])
        graph.add('4', [7, 4, -10, None, 8, 3, 1])
        graph.x_labels = ('a', 'b', 'c', 'd', 'e', 'f', 'g')
        graph.x_label_rotation = 90
        return graph.render_response()

    @app.route('/test/one/<chart>')
    def test_one_for(chart):
        graph = CHARTS_BY_NAME[chart]()
        graph.add('1', [10])
        graph.x_labels = 'a',
        return graph.render_response()

    @app.route('/test/xytitles/<chart>')
    def test_xy_titles_for(chart):
        graph = CHARTS_BY_NAME[chart]()
        graph.title = 'My global title'
        graph.x_title = 'My X title'
        graph.y_title = 'My Y title'
        graph.add('My number 1 serie', [1, 3, 12])
        graph.add('My number 2 serie', [7, -4, 10])
        graph.add('A', [17, -14, 11], secondary=True)
        graph.x_label_rotation = 25
        graph.legend_at_bottom = not True
        graph.x_labels = (
            'First point', 'Second point', 'Third point')
        return graph.render_response()

    @app.route('/test/no_data/<chart>')
    def test_no_data_for(chart):
        graph = CHARTS_BY_NAME[chart]()
        graph.add('Empty 1', [])
        graph.add('Empty 2', [])
        graph.x_labels = 'empty'
        graph.title = '123456789 ' * 30
        return graph.render_response()

    @app.route('/test/no_data/at_all/<chart>')
    def test_no_data_at_all_for(chart):
        graph = CHARTS_BY_NAME[chart]()
        return graph.render_response()

    @app.route('/test/interpolate/<chart>')
    def test_interpolate_for(chart):
        graph = CHARTS_BY_NAME[chart](interpolate='lagrange',
                                      interpolation_parameters={
                                          'type': 'kochanek_bartels',
                                          'c': 1,
                                          'b': -1,
                                          't': -1})
        graph.add('1', [1, 3, 12, 3, 4])
        graph.add('2', [7, -4, 10, None, 8, 3, 1])
        return graph.render_response()

    @app.route('/test/logarithmic/<chart>')
    def test_logarithmic_for(chart):
        graph = CHARTS_BY_NAME[chart](logarithmic=True)
        if isinstance(graph, CHARTS_BY_NAME['XY']):
            graph.add('xy', [
                (.1, .234), (10, 243), (.001, 2), (1000000, 1231)])
        else:
            graph.add('1', [.1, 10, .01, 10000])
            graph.add('2', [.234, 243, 2, 2379, 1231])
            graph.x_labels = ('a', 'b', 'c', 'd', 'e')
        graph.x_label_rotation = 90
        return graph.render_response()

    @app.route('/test/zero_at_34/<chart>')
    @app.route('/test/zero_at_<int:zero>/<chart>')
    def test_zero_at_34_for(chart, zero=34):
        graph = CHARTS_BY_NAME[chart](fill=True, zero=zero)
        graph.add('1', [100, 34, 12, 43, -48])
        graph.add('2', [73, -14, 10, None, -58, 32, 91])
        return graph.render_response()

    @app.route('/test/negative/<chart>')
    def test_negative_for(chart):
        graph = CHARTS_BY_NAME[chart]()
        graph.add('1', [10, 0, -10])
        return graph.render_response()

    @app.route('/test/bar')
    def test_bar():
        bar = Bar()
        bar.add('1', [1, 2, 3])
        bar.add('2', [4, 5, 6])
        return bar.render_response()

    @app.route('/test/histogram')
    def test_histogram():
        hist = Histogram(style=styles['neon'])
        hist.add('1', [
            (2, 0, 1),
            (4, 1, 3),
            (3, 3.5, 5),
            (1.5, 5, 10)
        ])
        hist.add('2', [(2, 2, 8)])
        return hist.render_response()

    @app.route('/test/ylabels')
    def test_ylabels():
        chart = Line()
        chart.x_labels = 'Red', 'Blue', 'Green'
        chart.y_labels = .0001, .0003, .0004, .00045, .0005
        chart.add('line', [.0002, .0005, .00035])
        return chart.render_response()

    @app.route('/test/secondary/<chart>')
    def test_secondary_for(chart):
        chart = CHARTS_BY_NAME[chart](fill=True)
        chart.title = 'LOL ' * 23
        chart.x_labels = 'abc'
        chart.x_label_rotation = 25
        chart.y_label_rotation = 50
        chart.add('1', [30, 20, -2])
        chart.add(10 * '1b', [-4, 50, 6], secondary=True)
        chart.add(10 * '2b', [3, 30, -1], secondary=True)
        chart.add('2', [8, 21, -0])
        chart.add('3', [1, 2, 3])
        chart.add('3b', [-1, 2, -3], secondary=True)
        return chart.render_response()

    @app.route('/test/secondary_xy')
    def test_secondary_xy():
        chart = XY()
        chart.add(10 * '1', [(30, 5), (20, 12), (25, 4)])
        chart.add(10 * '1b', [(4, 12), (5, 8), (6, 4)], secondary=True)
        chart.add(10 * '2b', [(3, 24), (0, 17), (12, 9)], secondary=True)
        chart.add(10 * '2', [(8, 23), (21, 1), (5, 0)])
        return chart.render_response()

    @app.route('/test/box')
    def test_box():
        chart = Box()
        chart.add('One', [15, 8, 2, -12, 9, 23])
        chart.add('Two', [5, 8, 2, -9, 23, 12])
        chart.add('Three', [8, -2, 12, -5, 9, 3])
        chart.add('Four', [5, 8, 2, -9, -3, 12])
        chart.add('Five', [8, 12, 12, -9, 5, 13])
        chart.x_labels = map(str, range(5))
        return chart.render_response()

    @app.route('/test/stacked')
    def test_stacked():
        stacked = StackedBar()
        stacked.add('1', [1, 2, 3])
        stacked.add('2', [4, 5, 6])
        return stacked.render_response()

    @app.route('/test/show_dots')
    def test_show_dots():
        line = Line(show_dots=False)
        line.add('1', [1, 2, 3])
        line.add('2', [4, 5, 6])
        return line.render_response()

    @app.route('/test/config')
    def test_config():

        class LolConfig(Config):
            js = ['http://l:2343/svg.jquery.js',
                  'http://l:2343/pygal-tooltips.js']

        stacked = StackedBar(LolConfig())
        stacked.add('1', [1, 2, 3])
        stacked.add('2', [4, 5, 6])
        return stacked.render_response()

    @app.route('/test/datey')
    def test_datey():
        from datetime import datetime
        datey = DateY(show_dots=False)
        datey.add('1', [
            (datetime(2011, 12, 21), 10),
            (datetime(2014, 4, 8), 12),
            (datetime(2010, 2, 28), 2)
        ])
        datey.add('2', [(12, 4), (219, 8), (928, 6)])
        datey.x_label_rotation = 25
        return datey.render_response()

    @app.route('/test/worldmap')
    def test_worldmap():
        wmap = Worldmap(style=choice(list(styles.values())))

        wmap.add('1st', [('fr', 100), ('us', 10)])
        wmap.add('2nd', [('jp', 1), ('ru', 7), ('uk', 0)])
        wmap.add('3rd', ['ch', 'cz', 'ca', 'cn'])
        wmap.add('4th', {'br': 12, 'bo': 1, 'bu': 23, 'fr': 34})
        wmap.add('5th', [{
            'value': ('tw', 10),
            'label': 'First label',
            'xlink': 'http://google.com?q=tw'
        }, {
            'value': ('bw', 20),
            'label': 'Second one',
            'xlink': 'http://google.com?q=bw'
        }, {
            'value': ('mw', 40),
            'label': 'Last'
        }])
        wmap.add('6th', [3, 5, 34, 12])
        wmap.title = 'World Map !!'
        return wmap.render_response()

    @app.route('/test/frenchmapdepartments')
    def test_frenchmapdepartments():
        fmap = FrenchMap_Departments(style=choice(list(styles.values())))
        for i in range(10):
            fmap.add('s%d' % i, [
                (choice(list(DEPARTMENTS.keys())), randint(0, 100))
                for _ in range(randint(1, 5))])

        fmap.add('links', [{
            'value': ('69', 10),
            'label': '\o/',
            'xlink': 'http://google.com?q=69'
        }, {
            'value': ('42', 20),
            'label': 'Y',
        }])
        fmap.add('6th', [3, 5, 34, 12])
        fmap.title = 'French map'
        return fmap.render_response()

    @app.route('/test/frenchmapregions')
    def test_frenchmapregions():
        fmap = FrenchMap_Regions(style=choice(list(styles.values())))
        for i in range(10):
            fmap.add('s%d' % i, [
                (choice(list(REGIONS.keys())), randint(0, 100))
                for _ in range(randint(1, 5))])

        fmap.add('links', [{
            'value': ('02', 10),
            'label': '\o/',
            'xlink': 'http://google.com?q=69'
        }, {
            'value': ('72', 20),
            'label': 'Y',
        }])
        fmap.add('6th', [91, 2, 41])
        fmap.title = 'French map'
        return fmap.render_response()

    @app.route('/test/labels')
    def test_labels():
        line = Line()
        line.add('test1', range(100))
        line.x_labels = map(str, range(11))
        return line.render_response()

    @app.route('/test/64colors')
    def test_64_colors():
        colors = [rotate('#ff0000', i * 360 / 64) for i in range(64)]
        pie = Pie(style=Style(colors=colors))
        for i in range(64):
            pie.add(str(i), 1)
        return pie.render_response()

    @app.route('/test/major_dots')
    def test_major_dots():
        line = Line(x_labels_major_count=2, show_only_major_dots=True)
        line.add('test', range(12))
        line.x_labels = [
            'lol', 'lol1', 'lol2', 'lol3', 'lol4', 'lol5',
            'lol6', 'lol7', 'lol8', 'lol9', 'lol10', 'lol11']
        # line.x_labels_major = ['lol3']
        return line.render_response()

    @app.route('/test/x_major_labels/<chart>')
    def test_x_major_labels_for(chart):
        chart = CHARTS_BY_NAME[chart]()
        chart.add('test', range(12))
        chart.x_labels = map(str, range(12))
        chart.x_labels_major_count = 4
        # chart.x_labels_major = ['1', '5', '11', '1.0', '5.0', '11.0']
        return chart.render_response()

    @app.route('/test/y_major_labels/<chart>')
    def test_y_major_labels_for(chart):
        chart = CHARTS_BY_NAME[chart]()
        chart.add('test', zip(*[range(12), range(12)]))
        chart.y_labels = range(12)
        # chart.y_labels_major_count = 4
        chart.y_labels_major = [1.0, 5.0, 11.0]
        return chart.render_response()

    @app.route('/test/stroke_config')
    def test_stroke_config():
        line = Line()
        line.add('test_no_line', range(12), stroke=False)
        line.add('test', reversed(range(12)))
        line.add('test_no_dots', [5] * 12, show_dots=False)
        line.add('test_big_dots', [
            randint(1, 12) for _ in range(12)], dots_size=5)
        line.add('test_fill', [
            randint(1, 3) for _ in range(12)], fill=True)

        line.x_labels = [
            'lol', 'lol1', 'lol2', 'lol3', 'lol4', 'lol5',
            'lol6', 'lol7', 'lol8', 'lol9', 'lol10', 'lol11']
        return line.render_response()

    @app.route('/test/pie_serie_radius')
    def test_pie_serie_radius():
        pie = Pie()
        for i in range(10):
            pie.add(str(i), i, inner_radius=(10 - i) / 10)

        return pie.render_response()

    @app.route('/test/half_pie')
    def test_half_pie():
        pie = Pie(half_pie=True)
        for i in range(10):
            pie.add(str(i), i, inner_radius=.1)

        return pie.render_response()

    @app.route('/test/legend_at_bottom/<chart>')
    def test_legend_at_bottom_for(chart):
        graph = CHARTS_BY_NAME[chart]()
        graph.add('1', [1, 3, 12, 3, 4, None, 9])
        graph.add('2', [7, -4, 10, None, 8, 3, 1])
        graph.add('3', [7, -14, -10, None, 8, 3, 1])
        graph.add('4', [7, 4, -10, None, 8, 3, 1])
        graph.x_labels = ('a', 'b', 'c', 'd', 'e', 'f', 'g')
        graph.legend_at_bottom = True
        return graph.render_response()

    return list(filter(lambda x: x.startswith('test'), locals()))

########NEW FILE########
__FILENAME__ = moulinrouge
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
from moulinrouge import create_app
import logging
app = create_app()

try:
    from log_colorizer import make_colored_stream_handler
    handler = make_colored_stream_handler()
    app.logger.handlers = []
    app.logger.addHandler(handler)
    import werkzeug
    werkzeug._internal._log('debug', '<-- I am with stupid')
    logging.getLogger('werkzeug').handlers = []
    logging.getLogger('werkzeug').addHandler(handler)

    handler.setLevel(logging.DEBUG)
    app.logger.setLevel(logging.DEBUG)
    logging.getLogger('werkzeug').setLevel(logging.DEBUG)
except:
    pass


try:
    import wsreload
except ImportError:
    app.logger.debug('wsreload not found')
else:
    url = "http://moulinrouge.l:21112/*"

    def log(httpserver):
        app.logger.debug('WSReloaded after server restart')
    wsreload.monkey_patch_http_server({'url': url}, callback=log)
    app.logger.debug('HTTPServer monkey patched for url %s' % url)

try:
    from wdb.ext import WdbMiddleware, add_w_builtin
except ImportError:
    pass
else:
    add_w_builtin()
    app.wsgi_app = WdbMiddleware(app.wsgi_app, start_disabled=True)

app.run(debug=True, threaded=True, host='0.0.0.0', port=21112)

########NEW FILE########
__FILENAME__ = perf
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.


from pygal import CHARTS_NAMES, CHARTS_BY_NAME
from pygal.test import adapt
from random import sample

import timeit
import sys


rands = list(zip(
    sample(range(1000), 1000),
    sample(range(1000), 1000)))


def perf(chart_name, length, series):
    chart = CHARTS_BY_NAME.get(chart_name)()
    for i in range(series):
        chart.add('s %d' % i, adapt(chart, rands[:length]))
    return chart


def prt(s):
    sys.stdout.write(s)
    sys.stdout.flush()


if '--profile' in sys.argv:
    import cProfile
    c = perf('Line', 500, 500)
    cProfile.run("c.render()")
    sys.exit(0)

if '--mem' in sys.argv:
    _TWO_20 = float(2 ** 20)
    import os
    import psutil
    import linecache
    pid = os.getpid()
    process = psutil.Process(pid)
    import gc
    gc.set_debug(gc.DEBUG_UNCOLLECTABLE | gc.DEBUG_INSTANCES | gc.DEBUG_OBJECTS)
    def print_mem():
        mem = process.get_memory_info()[0] / _TWO_20
        f = sys._getframe(1)
        line = linecache.getline(f.f_code.co_filename, f.f_lineno - 1).replace('\n', '')
        print('%s:%d \t| %.6f \t| %s' % (
            f.f_code.co_name, f.f_lineno, mem, line))

    c = perf('Line', 100, 500)
    print_mem()
    a = c.render()
    print_mem()
    import objgraph
    objgraph.show_refs([c], filename='sample-graph.png')
    gc.collect()
    print_mem()
    print(gc.garbage)
    print_mem()
    del a
    print_mem()
    del c
    print_mem()

    sys.exit(0)

charts = CHARTS_NAMES if '--all' in sys.argv else 'Line',

for chart in charts:
    prt('%s\n' % chart)
    prt('s\\l\t1\t10\t100')

    for series in (1, 10, 100):
        prt('\n%d\t' % series)
        for length in (1, 10, 100):
            times = []
            time = timeit.timeit(
                "c.render()",
                setup="from __main__ import perf; c = perf('%s', %d, %d)" % (
                    chart, length, series),
                number=10)
            prt('%d\t' % (1000 * time))
    prt('\n')

########NEW FILE########
__FILENAME__ = adapters
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Value adapters to use when a chart doesn't accept all value types

"""
import datetime
from numbers import Number
from pygal.i18n import COUNTRIES


def positive(x):
    if x is None:
        return
    if x < 0:
        return 0
    return x


def not_zero(x):
    if x == 0:
        return
    return x


def none_to_zero(x):
    return x or 0


def date(x):
    # Make int work for date graphs by counting days number from now
    if isinstance(x, Number):
        try:
            d = datetime.date.today() + datetime.timedelta(days=x)
            return datetime.datetime.combine(d, datetime.time(0, 0, 0))
        except OverflowError:
            return None
    return x

########NEW FILE########
__FILENAME__ = colors
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Color utils

"""
from __future__ import division


def normalize_float(f):
    if abs(f - round(f)) < .0000000000001:
        return round(f)
    return f


def rgb_to_hsl(r, g, b):
    r /= 255
    g /= 255
    b /= 255
    max_ = max((r, g, b))
    min_ = min((r, g, b))
    d = max_ - min_

    if not d:
        h = 0
    elif r is max_:
        h = 60 * (g - b) / d
    elif g is max_:
        h = 60 * (b - r) / d + 120
    else:
        h = 60 * (r - g) / d + 240

    l = .5 * (max_ + min_)
    if not d:
        s = 0
    elif l < 0.5:
        s = .5 * d / l
    else:
        s = .5 * d / (1 - l)
    return tuple(map(normalize_float, (h % 360, s * 100, l * 100)))


def hsl_to_rgb(h, s, l):
    h /= 360
    s /= 100
    l /= 100

    m2 = l * (s + 1) if l <= .5 else l + s - l * s
    m1 = 2 * l - m2

    def h_to_rgb(h):
        h = h % 1
        if 6 * h < 1:
            return m1 + 6 * h * (m2 - m1)
        if 2 * h < 1:
            return m2
        if 3 * h < 2:
            return m1 + 6 * (2 / 3 - h) * (m2 - m1)
        return m1
    r, g, b = map(lambda x: round(x * 255),
                  map(h_to_rgb, (h + 1 / 3, h, h - 1 / 3)))

    return r, g, b


def adjust(color, attribute, percent):
    assert color[0] == '#', '#rrggbb and #rgb format are supported'
    color = color[1:]
    assert len(color) in (3, 6), '#rrggbb and #rgb format are supported'
    if len(color) == 3:
        color = [a for b in zip(color, color) for a in b]

    bound = lambda x: max(0, min(100, x))

    def _adjust(hsl):
        hsl = list(hsl)
        if attribute > 0:
            hsl[attribute] = bound(hsl[attribute] + percent)
        else:
            hsl[attribute] += percent

        return hsl
    return '#%02x%02x%02x' % hsl_to_rgb(
        *_adjust(
            rgb_to_hsl(*map(lambda x: int(''.join(x), 16),
                            zip(color[::2], color[1::2])))))


def rotate(color, percent):
    return adjust(color, 0, percent)


def saturate(color, percent):
    return adjust(color, 1, percent)


def desaturate(color, percent):
    return adjust(color, 1, -percent)


def lighten(color, percent):
    return adjust(color, 2, percent)


def darken(color, percent):
    return adjust(color, 2, -percent)

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.

"""
Config module with all options
"""
from copy import deepcopy
from pygal.style import Style, DefaultStyle
from pygal.interpolate import INTERPOLATIONS


class FontSizes(object):
    """Container for font sizes"""

CONFIG_ITEMS = []


class Key(object):

    _categories = []

    def __init__(
            self, default_value, type_, category, doc,
            subdoc="", subtype=None):

        self.value = default_value
        self.type = type_
        self.doc = doc
        self.category = category
        self.subdoc = subdoc
        self.subtype = subtype
        self.name = "Unbound"
        if category not in self._categories:
            self._categories.append(category)

        CONFIG_ITEMS.append(self)

    @property
    def is_boolean(self):
        return self.type == bool

    @property
    def is_numeric(self):
        return self.type in (int, float)

    @property
    def is_string(self):
        return self.type == str

    @property
    def is_dict(self):
        return self.type == dict

    @property
    def is_list(self):
        return self.type == list

    def coerce(self, value):
        if self.type == Style:
            return value
        elif self.type == list:
            return self.type(
                map(
                    self.subtype, map(
                        lambda x: x.strip(), value.split(','))))
        elif self.type == dict:
            rv = {}
            for pair in value.split(','):
                key, val = pair.split(':')
                key = key.strip()
                val = val.strip()
                try:
                    rv[key] = self.subtype(val)
                except:
                    rv[key] = val
            return rv
        return self.type(value)


class MetaConfig(type):
    def __new__(mcs, classname, bases, classdict):
        for k, v in classdict.items():
            if isinstance(v, Key):
                v.name = k
        return type.__new__(mcs, classname, bases, classdict)


class BaseConfig(MetaConfig('ConfigBase', (object,), {})):

    def __init__(self, **kwargs):
        """Can be instanciated with config kwargs"""
        for k in dir(self):
            v = getattr(self, k)
            if (k not in self.__dict__ and not
                    k.startswith('_') and not
                    hasattr(v, '__call__')):
                if isinstance(v, Key):
                    if v.is_list and v.value is not None:
                        v = list(v.value)
                    else:
                        v = v.value
                setattr(self, k, v)
        self._update(kwargs)

    def __call__(self, **kwargs):
        """Can be updated with kwargs"""
        self._update(kwargs)

    def _update(self, kwargs):
        self.__dict__.update(
            dict([(k, v) for (k, v) in kwargs.items()
                  if not k.startswith('_') and k in dir(self)]))

    def font_sizes(self, with_unit=True):
        """Getter for all font size configs"""
        fs = FontSizes()
        for name in dir(self):
            if name.endswith('_font_size'):
                setattr(
                    fs,
                    name.replace('_font_size', ''),
                    ('%dpx' % getattr(self, name))
                    if with_unit else getattr(self, name))
        return fs

    def to_dict(self):
        config = {}
        for attr in dir(self):
            if not attr.startswith('__'):
                value = getattr(self, attr)
                if hasattr(value, 'to_dict'):
                    config[attr] = value.to_dict()
                elif not hasattr(value, '__call__'):
                    config[attr] = value
        return config

    def copy(self):
        return deepcopy(self)


class CommonConfig(BaseConfig):
    stroke = Key(
        True, bool, "Look",
        "Line dots (set it to false to get a scatter plot)")

    show_dots = Key(True, bool, "Look", "Set to false to remove dots")

    show_only_major_dots = Key(
        False, bool, "Look",
        "Set to true to show only major dots according to their majored label")

    dots_size = Key(2.5, float, "Look", "Radius of the dots")

    fill = Key(
        False, bool, "Look", "Fill areas under lines")

    rounded_bars = Key(
        None, int, "Look",
        "Set this to the desired radius in px (for Bar-like charts)")

    inner_radius = Key(
        0, float, "Look", "Piechart inner radius (donut), must be <.9")


class Config(CommonConfig):
    """Class holding config values"""

    style = Key(
        DefaultStyle, Style, "Style", "Style holding values injected in css")

    css = Key(
        ('style.css', 'graph.css'), list, "Style",
        "List of css file",
        "It can be an absolute file path or an external link",
        str)

    # Look #
    title = Key(
        None, str, "Look",
        "Graph title.", "Leave it to None to disable title.")

    x_title = Key(
        None, str, "Look",
        "Graph X-Axis title.", "Leave it to None to disable X-Axis title.")

    y_title = Key(
        None, str, "Look",
        "Graph Y-Axis title.", "Leave it to None to disable Y-Axis title.")

    width = Key(
        800, int, "Look", "Graph width")

    height = Key(
        600, int, "Look", "Graph height")

    show_x_guides = Key(False, bool, "Look",
                        "Set to true to always show x guide lines")

    show_y_guides = Key(True, bool, "Look",
                        "Set to false to hide y guide lines")

    show_legend = Key(
        True, bool, "Look", "Set to false to remove legend")

    legend_at_bottom = Key(
        False, bool, "Look", "Set to true to position legend at bottom")

    legend_box_size = Key(
        12, int, "Look", "Size of legend boxes")

    spacing = Key(
        10, int, "Look",
        "Space between titles/legend/axes")

    margin = Key(
        20, int, "Look",
        "Margin around chart")

    tooltip_border_radius = Key(0, int, "Look", "Tooltip border radius")

    inner_radius = Key(
        0, float, "Look", "Piechart inner radius (donut), must be <.9")

    half_pie = Key(
        False, bool, "Look", "Create a half-pie chart")

    x_labels = Key(
        None, list, "Label",
        "X labels, must have same len than data.",
        "Leave it to None to disable x labels display.",
        str)

    x_labels_major = Key(
        None, list, "Label",
        "X labels that will be marked major.",
        subtype=str)

    x_labels_major_every = Key(
        None, int, "Label",
        "Mark every n-th x label as major.")

    x_labels_major_count = Key(
        None, int, "Label",
        "Mark n evenly distributed labels as major.")

    show_minor_x_labels = Key(
        True, bool, "Label", "Set to false to hide x-labels not marked major")

    y_labels = Key(
        None, list, "Label",
        "You can specify explicit y labels",
        "Must be a list of numbers", float)

    y_labels_major = Key(
        None, list, "Label",
        "Y labels that will be marked major. Default: auto",
        subtype=str)

    y_labels_major_every = Key(
        None, int, "Label",
        "Mark every n-th y label as major.")

    y_labels_major_count = Key(
        None, int, "Label",
        "Mark n evenly distributed y labels as major.")

    show_minor_y_labels = Key(
        True, bool, "Label", "Set to false to hide y-labels not marked major")

    show_y_labels = Key(
        True, bool, "Label", "Set to false to hide y-labels")

    x_label_rotation = Key(
        0, int, "Label", "Specify x labels rotation angles", "in degrees")

    y_label_rotation = Key(
        0, int, "Label", "Specify y labels rotation angles", "in degrees")

    x_label_format = Key(
        "%Y-%m-%d %H:%M:%S.%f", str, "Label",
        "Date format for strftime to display the DateY X labels")

    # Value #
    human_readable = Key(
        False, bool, "Value", "Display values in human readable format",
        "(ie: 12.4M)")

    value_formatter = Key(
        None, type(lambda: 1), "Value",
        "A function to convert numeric value to strings")

    logarithmic = Key(
        False, bool, "Value", "Display values in logarithmic scale")

    interpolate = Key(
        None, str, "Value", "Interpolation",
        "May be %s" % ' or '.join(INTERPOLATIONS))

    interpolation_precision = Key(
        250, int, "Value", "Number of interpolated points between two values")

    interpolation_parameters = Key(
        {}, dict, "Value", "Various parameters for parametric interpolations",
        "ie: For hermite interpolation, you can set the cardinal tension with"
        "{'type': 'cardinal', 'c': .5}", int)

    order_min = Key(
        None, int, "Value", "Minimum order of scale, defaults to None")

    range = Key(
        None, list, "Value", "Explicitly specify min and max of values",
        "(ie: (0, 100))", int)

    include_x_axis = Key(
        False, bool, "Value", "Always include x axis")

    zero = Key(
        0, int, "Value",
        "Set the ordinate zero value",
        "Useful for filling to another base than abscissa")

    # Text #
    no_data_text = Key(
        "No data", str, "Text", "Text to display when no data is given")

    label_font_size = Key(10, int, "Text", "Label font size")

    major_label_font_size = Key(10, int, "Text", "Major label font size")

    value_font_size = Key(8, int, "Text", "Value font size")

    tooltip_font_size = Key(16, int, "Text", "Tooltip font size")

    title_font_size = Key(16, int, "Text", "Title font size")

    legend_font_size = Key(14, int, "Text", "Legend font size")

    no_data_font_size = Key(64, int, "Text", "No data text font size")

    print_values = Key(
        True, bool,
        "Text", "Print values when graph is in non interactive mode")

    print_zeroes = Key(
        False, bool,
        "Text", "Print zeroes when graph is in non interactive mode")

    truncate_legend = Key(
        None, int, "Text",
        "Legend string length truncation threshold", "None = auto")

    truncate_label = Key(
        None, int, "Text",
        "Label string length truncation threshold", "None = auto")

    # Misc #
    js = Key(
        ('http://kozea.github.com/pygal.js/javascripts/svg.jquery.js',
         'http://kozea.github.com/pygal.js/javascripts/pygal-tooltips.js'),
        list, "Misc", "List of js file",
        "It can be a filepath or an external link",
        str)

    disable_xml_declaration = Key(
        False, bool, "Misc",
        "Don't write xml declaration and return str instead of string",
        "usefull for writing output directly in html")

    explicit_size = Key(
        False, bool, "Misc", "Write width and height attributes")

    pretty_print = Key(
        False, bool, "Misc", "Pretty print the svg")

    strict = Key(
        False, bool, "Misc",
        "If True don't try to adapt / filter wrong values")

    no_prefix = Key(
        False, bool, "Misc",
        "Don't prefix css")


class SerieConfig(CommonConfig):
    """Class holding serie config values"""

    secondary = Key(
        False, bool, "Misc",
        "Set it to put the serie in a second axis")

########NEW FILE########
__FILENAME__ = ghost
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Ghost container

It is used to delegate rendering to real objects but keeping config in place

"""

from __future__ import division
import io
import sys
from pygal._compat import u, is_list_like
from pygal.graph import CHARTS_NAMES
from pygal.config import Config, CONFIG_ITEMS
from pygal.util import prepare_values
from pygal.table import Table
from uuid import uuid4


class ChartCollection(object):
    pass


REAL_CHARTS = {}
for NAME in CHARTS_NAMES:
    mod_name = 'pygal.graph.%s' % NAME.lower()
    __import__(mod_name)
    mod = sys.modules[mod_name]
    chart = getattr(mod, NAME)
    if issubclass(chart, ChartCollection):
        for name, chart in chart.__dict__.items():
            if name.startswith('_'):
                continue
            REAL_CHARTS['%s_%s' % (NAME, name)] = chart
    else:
        REAL_CHARTS[NAME] = chart


class Ghost(object):

    def __init__(self, config=None, **kwargs):
        """Init config"""
        name = self.__class__.__name__
        self.cls = REAL_CHARTS[name]
        self.uuid = str(uuid4())
        if config and isinstance(config, type):
            config = config()

        if config:
            config = config.copy()
        else:
            config = Config()

        config(**kwargs)
        self.config = config
        self.raw_series = []
        self.raw_series2 = []
        self.xml_filters = []

    def add(self, title, values, **kwargs):
        """Add a serie to this graph"""
        if not is_list_like(values) and not isinstance(values, dict):
            values = [values]
        if kwargs.get('secondary', False):
            self.raw_series2.append((title, values, kwargs))
        else:
            self.raw_series.append((title, values, kwargs))

    def add_xml_filter(self, callback):
        self.xml_filters.append(callback)

    def make_series(self, series):
        return prepare_values(series, self.config, self.cls)

    def make_instance(self, overrides=None):
        for conf_key in CONFIG_ITEMS:
            if conf_key.is_list:
                if getattr(self, conf_key.name, None):
                    setattr(self, conf_key.name,
                            list(getattr(self, conf_key.name)))

        self.config(**self.__dict__)
        self.config.__dict__.update(overrides or {})
        series = self.make_series(self.raw_series)
        secondary_series = self.make_series(self.raw_series2)
        self._last__inst = self.cls(
            self.config, series, secondary_series, self.uuid,
            self.xml_filters)
        return self._last__inst

    # Rendering
    def render(self, is_unicode=False, **kwargs):
        return (self
                .make_instance(overrides=kwargs)
                .render(is_unicode=is_unicode))

    def render_tree(self):
        return self.make_instance().render_tree()

    def render_table(self, **kwargs):
        real_cls, self.cls = self.cls, Table
        rv = self.make_instance().render(**kwargs)
        self.cls = real_cls
        return rv

    def render_pyquery(self):
        """Render the graph, and return a pyquery wrapped tree"""
        from pyquery import PyQuery as pq
        return pq(self.render_tree())

    def render_in_browser(self):
        """Render the graph, open it in your browser with black magic"""
        from lxml.html import open_in_browser
        open_in_browser(self.render_tree(), encoding='utf-8')

    def render_response(self):
        """Render the graph, and return a Flask response"""
        from flask import Response
        return Response(self.render(), mimetype='image/svg+xml')

    def render_to_file(self, filename):
        """Render the graph, and write it to filename"""
        with io.open(filename, 'w', encoding='utf-8') as f:
            f.write(self.render(is_unicode=True))

    def render_to_png(self, filename=None, dpi=72):
        """Render the graph, convert it to png and write it to filename"""
        import cairosvg
        return cairosvg.svg2png(
            bytestring=self.render(), write_to=filename, dpi=dpi)

    def render_sparktext(self, relative_to=None):
        """Make a mini text sparkline from chart"""
        bars = u('▁▂▃▄▅▆▇█')
        if len(self.raw_series) == 0:
            return u('')
        values = list(self.raw_series[0][1])
        if len(values) == 0:
            return u('')

        chart = u('')
        values = list(map(lambda x: max(x, 0), values))

        vmax = max(values)
        if relative_to is None:
            relative_to = min(values)

        if (vmax - relative_to) == 0:
            chart = bars[0] * len(values)
            return chart

        divisions = len(bars) - 1
        for value in values:
            chart += bars[int(divisions *
                              (value - relative_to) / (vmax - relative_to))]
        return chart

    def render_sparkline(self, **kwargs):
        spark_options = dict(
            width=200,
            height=50,
            show_dots=False,
            show_legend=False,
            show_y_labels=False,
            spacing=0,
            margin=5,
            explicit_size=True
        )
        spark_options.update(kwargs)
        return self.make_instance(spark_options).render()

    def _repr_svg_(self):
        """Display svg in IPython notebook"""
        return self.render(disable_xml_declaration=True)

    def _repr_png_(self):
        """Display png in IPython notebook"""
        return self.render_to_png()

########NEW FILE########
__FILENAME__ = bar
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Bar chart

"""

from __future__ import division
from pygal.graph.graph import Graph
from pygal.util import swap, ident, compute_scale, decorate


class Bar(Graph):
    """Bar graph"""

    _series_margin = .06
    _serie_margin = .06

    def __init__(self, *args, **kwargs):
        self._x_ranges = None
        super(Bar, self).__init__(*args, **kwargs)

    def _bar(self, parent, x, y, index, i, zero,
             secondary=False, rounded=False):
        width = (self.view.x(1) - self.view.x(0)) / self._len
        x, y = self.view((x, y))
        series_margin = width * self._series_margin
        x += series_margin
        width -= 2 * series_margin
        width /= self._order
        x += index * width
        serie_margin = width * self._serie_margin
        x += serie_margin
        width -= 2 * serie_margin
        height = self.view.y(zero) - y
        r = rounded * 1 if rounded else 0
        self.svg.transposable_node(
            parent, 'rect',
            x=x, y=y, rx=r, ry=r, width=width, height=height,
            class_='rect reactive tooltip-trigger')
        transpose = swap if self.horizontal else ident
        return transpose((x + width / 2, y + height / 2))

    def bar(self, serie_node, serie, index, rescale=False):
        """Draw a bar graph for a serie"""
        bars = self.svg.node(serie_node['plot'], class_="bars")
        if rescale and self.secondary_series:
            points = [
                (x, self._scale_diff + (y - self._scale_min_2nd) * self._scale)
                for x, y in serie.points if y is not None]
        else:
            points = serie.points

        for i, (x, y) in enumerate(points):
            if None in (x, y) or (self.logarithmic and y <= 0):
                continue
            metadata = serie.metadata.get(i)

            bar = decorate(
                self.svg,
                self.svg.node(bars, class_='bar'),
                metadata)
            val = self._format(serie.values[i])

            x_center, y_center = self._bar(
                bar, x, y, index, i, self.zero, secondary=rescale,
                rounded=serie.rounded_bars)
            self._tooltip_data(
                bar, val, x_center, y_center, classes="centered")
            self._static_value(serie_node, val, x_center, y_center)

    def _compute(self):
        if self._min:
            self._box.ymin = min(self._min, self.zero)
        if self._max:
            self._box.ymax = max(self._max, self.zero)

        x_pos = [
            x / self._len for x in range(self._len + 1)
        ] if self._len > 1 else [0, 1]  # Center if only one value

        self._points(x_pos)

        y_pos = compute_scale(
            self._box.ymin, self._box.ymax, self.logarithmic, self.order_min
        ) if not self.y_labels else list(map(float, self.y_labels))

        self._x_labels = self.x_labels and list(zip(self.x_labels, [
            (i + .5) / self._len for i in range(self._len)]))
        self._y_labels = list(zip(map(self._format, y_pos), y_pos))

    def _compute_secondary(self):
        if self.secondary_series:
            y_pos = list(zip(*self._y_labels))[1]
            ymin = self._secondary_min
            ymax = self._secondary_max

            min_0_ratio = (self.zero - self._box.ymin) / self._box.height or 1
            max_0_ratio = (self._box.ymax - self.zero) / self._box.height or 1

            if ymax > self._box.ymax:
                ymin = -(ymax - self.zero) * (1 / max_0_ratio - 1)
            else:
                ymax = (self.zero - ymin) * (1 / min_0_ratio - 1)

            left_range = abs(self._box.ymax - self._box.ymin)
            right_range = abs(ymax - ymin) or 1
            self._scale = left_range / right_range
            self._scale_diff = self._box.ymin
            self._scale_min_2nd = ymin
            self._y_2nd_labels = [
                (self._format(self._box.xmin + y * right_range / left_range),
                 y)
                for y in y_pos]

    def _plot(self):
        for index, serie in enumerate(self.series):
            self.bar(self._serie(index), serie, index)
        for index, serie in enumerate(self.secondary_series, len(self.series)):
            self.bar(self._serie(index), serie, index, True)

########NEW FILE########
__FILENAME__ = base
 # -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Base for pygal charts

"""

from __future__ import division
from pygal.view import Margin, Box
from pygal.util import (
    get_text_box, get_texts_box, cut, rad, humanize, truncate, split_title)
from pygal.svg import Svg
from pygal.util import cached_property, majorize
from math import sin, cos, sqrt


class BaseGraph(object):
    """Graphs commons"""

    _adapters = []

    def __init__(self, config, series, secondary_series, uuid, xml_filters):
        """Init the graph"""
        self.uuid = uuid
        self.__dict__.update(config.to_dict())
        self.config = config
        self.series = series or []
        self.secondary_series = secondary_series or []
        self.xml_filters = xml_filters or []
        self.horizontal = getattr(self, 'horizontal', False)
        self.svg = Svg(self)
        self._x_labels = None
        self._y_labels = None
        self._x_2nd_labels = None
        self._y_2nd_labels = None
        self.nodes = {}
        self.margin = Margin(*([self.margin] * 4))
        self._box = Box()
        self.view = None
        if self.logarithmic and self.zero == 0:
            # Explicit min to avoid interpolation dependency
            if self._dual:
                get = lambda x: x[1] or 1
            else:
                get = lambda x: x

            positive_values = list(filter(
                lambda x: x > 0,
                [get(val)
                 for serie in self.series for val in serie.safe_values]))

            self.zero = min(positive_values or 1,) or 1
        self._draw()
        self.svg.pre_render()

    @property
    def all_series(self):
        return self.series + self.secondary_series

    @property
    def _format(self):
        """Return the value formatter for this graph"""
        return self.config.value_formatter or (
            humanize if self.human_readable else str)

    def _compute(self):
        """Initial computations to draw the graph"""

    def _compute_margin(self):
        """Compute graph margins from set texts"""
        self._legend_at_left_width = 0
        for series_group in (self.series, self.secondary_series):
            if self.show_legend and series_group:
                h, w = get_texts_box(
                    map(lambda x: truncate(x, self.truncate_legend or 15),
                        cut(series_group, 'title')),
                    self.legend_font_size)
                if self.legend_at_bottom:
                    h_max = max(h, self.legend_box_size)
                    self.margin.bottom += self.spacing + h_max * round(
                        sqrt(self._order) - 1) * 1.5 + h_max
                else:
                    if series_group is self.series:
                        legend_width = self.spacing + w + self.legend_box_size
                        self.margin.left += legend_width
                        self._legend_at_left_width += legend_width
                    else:
                        self.margin.right += (
                            self.spacing + w + self.legend_box_size)

        for xlabels in (self._x_labels, self._x_2nd_labels):
            if xlabels:
                h, w = get_texts_box(
                    map(lambda x: truncate(x, self.truncate_label or 25),
                        cut(xlabels)),
                    self.label_font_size)
                self._x_labels_height = self.spacing + max(
                    w * sin(rad(self.x_label_rotation)), h)
                if xlabels is self._x_labels:
                    self.margin.bottom += self._x_labels_height
                else:
                    self.margin.top += self._x_labels_height
                if self.x_label_rotation:
                    self.margin.right = max(
                        w * cos(rad(self.x_label_rotation)),
                        self.margin.right)
        if not self._x_labels:
            self._x_labels_height = 0

        if self.show_y_labels:
            for ylabels in (self._y_labels, self._y_2nd_labels):
                if ylabels:
                    h, w = get_texts_box(
                        cut(ylabels), self.label_font_size)
                    if ylabels is self._y_labels:
                        self.margin.left += self.spacing + max(
                            w * cos(rad(self.y_label_rotation)), h)
                    else:
                        self.margin.right += self.spacing + max(
                            w * cos(rad(self.y_label_rotation)), h)

        self.title = split_title(
            self.title, self.width, self.title_font_size)

        if self.title:
            h, _ = get_text_box(self.title[0], self.title_font_size)
            self.margin.top += len(self.title) * (self.spacing + h)

        self.x_title = split_title(
            self.x_title, self.width - self.margin.x, self.title_font_size)

        self._x_title_height = 0
        if self.x_title:
            h, _ = get_text_box(self.x_title[0], self.title_font_size)
            height = len(self.x_title) * (self.spacing + h)
            self.margin.bottom += height
            self._x_title_height = height + self.spacing

        self.y_title = split_title(
            self.y_title, self.height - self.margin.y, self.title_font_size)

        self._y_title_height = 0
        if self.y_title:
            h, _ = get_text_box(self.y_title[0], self.title_font_size)
            height = len(self.y_title) * (self.spacing + h)
            self.margin.left += height
            self._y_title_height = height + self.spacing

    @cached_property
    def _legends(self):
        """Getter for series title"""
        return [serie.title for serie in self.series]

    @cached_property
    def _secondary_legends(self):
        """Getter for series title on secondary y axis"""
        return [serie.title for serie in self.secondary_series]

    @cached_property
    def _values(self):
        """Getter for series values (flattened)"""
        return [val
                for serie in self.series
                for val in serie.values
                if val is not None]

    @cached_property
    def _secondary_values(self):
        """Getter for secondary series values (flattened)"""
        return [val
                for serie in self.secondary_series
                for val in serie.values
                if val is not None]

    @cached_property
    def _len(self):
        """Getter for the maximum series size"""
        return max([
            len(serie.values)
            for serie in self.all_series] or [0])

    @cached_property
    def _secondary_min(self):
        """Getter for the minimum series value"""
        return (self.range[0] if (self.range and self.range[0] is not None)
                else (min(self._secondary_values)
                      if self._secondary_values else None))

    @cached_property
    def _min(self):
        """Getter for the minimum series value"""
        return (self.range[0] if (self.range and self.range[0] is not None)
                else (min(self._values)
                      if self._values else None))

    @cached_property
    def _max(self):
        """Getter for the maximum series value"""
        return (self.range[1] if (self.range and self.range[1] is not None)
                else (max(self._values) if self._values else None))

    @cached_property
    def _secondary_max(self):
        """Getter for the maximum series value"""
        return (self.range[1] if (self.range and self.range[1] is not None)
                else (max(self._secondary_values)
                      if self._secondary_values else None))

    @cached_property
    def _order(self):
        """Getter for the number of series"""
        return len(self.all_series)

    @cached_property
    def _x_major_labels(self):
        """Getter for the x major label"""
        if self.x_labels_major:
            return self.x_labels_major
        if self.x_labels_major_every:
            return [self._x_labels[i][0] for i in range(
                0, len(self._x_labels), self.x_labels_major_every)]
        if self.x_labels_major_count:
            label_count = len(self._x_labels)
            major_count = self.x_labels_major_count
            if (major_count >= label_count):
                return [label[0] for label in self._x_labels]

            return [self._x_labels[
                    int(i * (label_count - 1) / (major_count - 1))][0]
                    for i in range(major_count)]

        return []

    @cached_property
    def _y_major_labels(self):
        """Getter for the y major label"""
        if self.y_labels_major:
            return self.y_labels_major
        if self.y_labels_major_every:
            return [self._y_labels[i][1] for i in range(
                0, len(self._y_labels), self.y_labels_major_every)]
        if self.y_labels_major_count:
            label_count = len(self._y_labels)
            major_count = self.y_labels_major_count
            if (major_count >= label_count):
                return [label[1] for label in self._y_labels]

            return [self._y_labels[
                int(i * (label_count - 1) / (major_count - 1))][1]
                for i in range(major_count)]

        return majorize(
            cut(self._y_labels, 1)
        )

    def _draw(self):
        """Draw all the things"""
        self._compute()
        self._compute_secondary()
        self._post_compute()
        self._compute_margin()
        self._decorate()
        if self.series and self._has_data():
            self._plot()
        else:
            self.svg.draw_no_data()

    def _has_data(self):
        """Check if there is any data"""
        return sum(
            map(len, map(lambda s: s.safe_values, self.series))) != 0 and (
            sum(map(abs, self._values)) != 0)

    def render(self, is_unicode=False):
        """Render the graph, and return the svg string"""
        return self.svg.render(
            is_unicode=is_unicode, pretty_print=self.pretty_print)

    def render_tree(self):
        """Render the graph, and return lxml tree"""
        svg = self.svg.root
        for f in self.xml_filters:
            svg = f(svg)
        return svg

########NEW FILE########
__FILENAME__ = box
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Box plot
"""

from __future__ import division
from pygal.graph.graph import Graph
from pygal.util import compute_scale, decorate
from pygal._compat import is_list_like


class Box(Graph):
    """
    Box plot
    For each series, shows the median value, the 25th and 75th percentiles,
    and the values within
    1.5 times the interquartile range of the 25th and 75th percentiles.

    See http://en.wikipedia.org/wiki/Box_plot
    """
    _series_margin = .06

    def __init__(self, *args, **kwargs):
        super(Box, self).__init__(*args, **kwargs)

    @property
    def _format(self):
        """Return the value formatter for this graph"""
        sup = super(Box, self)._format

        def format_maybe_quartile(x):
            if is_list_like(x):
                return 'Q1: %s Q2: %s Q3: %s' % tuple(map(sup, x[1:4]))
            else:
                return sup(x)
        return format_maybe_quartile

    def _compute(self):
        """
        Compute parameters necessary for later steps
        within the rendering process
        """
        for serie in self.series:
            serie.values = self._box_points(serie.values)

        if self._min:
            self._box.ymin = min(self._min, self.zero)
        if self._max:
            self._box.ymax = max(self._max, self.zero)

        x_pos = [
            x / self._len for x in range(self._len + 1)
        ] if self._len > 1 else [0, 1]  # Center if only one value

        self._points(x_pos)

        y_pos = compute_scale(
            self._box.ymin, self._box.ymax, self.logarithmic, self.order_min
        ) if not self.y_labels else list(map(float, self.y_labels))

        self._x_labels = self.x_labels and list(zip(self.x_labels, [
            (i + .5) / self._order for i in range(self._order)]))
        self._y_labels = list(zip(map(self._format, y_pos), y_pos))

    def _plot(self):
        """
        Plot the series data
        """
        for index, serie in enumerate(self.series):
            self._boxf(self._serie(index), serie, index)

    def _boxf(self, serie_node, serie, index):
        """
        For a specific series, draw the box plot.
        """
        # Note: q0 and q4 do not literally mean the zero-th quartile
        # and the fourth quartile, but rather the distance from 1.5 times
        # the inter-quartile range to Q1 and Q3, respectively.
        boxes = self.svg.node(serie_node['plot'], class_="boxes")

        metadata = serie.metadata.get(0)

        box = decorate(
            self.svg,
            self.svg.node(boxes, class_='box'),
            metadata)
        val = self._format(serie.values)

        x_center, y_center = self._draw_box(box, serie.values, index)
        self._tooltip_data(box, val, x_center, y_center, classes="centered")
        self._static_value(serie_node, val, x_center, y_center)

    def _draw_box(self, parent_node, quartiles, box_index):
        """
        Return the center of a bounding box defined by a box plot.
        Draws a box plot on self.svg.
        """
        width = (self.view.x(1) - self.view.x(0)) / self._order
        series_margin = width * self._series_margin
        left_edge = self.view.x(0) + width * box_index + series_margin
        width -= 2 * series_margin

        # draw lines for whiskers - bottom, median, and top
        for i, whisker in enumerate(
                (quartiles[0], quartiles[2], quartiles[4])):
            whisker_width = width if i == 1 else width / 2
            shift = (width - whisker_width) / 2
            xs = left_edge + shift
            xe = left_edge + width - shift
            self.svg.line(
                parent_node,
                coords=[(xs, self.view.y(whisker)),
                        (xe, self.view.y(whisker))],
                class_='reactive tooltip-trigger',
                attrib={'stroke-width': 3})

        # draw lines connecting whiskers to box (Q1 and Q3)
        self.svg.line(
            parent_node,
            coords=[(left_edge + width / 2, self.view.y(quartiles[0])),
                    (left_edge + width / 2, self.view.y(quartiles[1]))],
            class_='reactive tooltip-trigger',
            attrib={'stroke-width': 2})
        self.svg.line(
            parent_node,
            coords=[(left_edge + width / 2, self.view.y(quartiles[4])),
                    (left_edge + width / 2, self.view.y(quartiles[3]))],
            class_='reactive tooltip-trigger',
            attrib={'stroke-width': 2})

        # box, bounded by Q1 and Q3
        self.svg.node(
            parent_node,
            tag='rect',
            x=left_edge,
            y=self.view.y(quartiles[1]),
            height=self.view.y(quartiles[3]) - self.view.y(quartiles[1]),
            width=width,
            class_='subtle-fill reactive tooltip-trigger')

        return (left_edge + width / 2, self.view.y(
            sum(quartiles) / len(quartiles)))

    @staticmethod
    def _box_points(values):
        """
        Return a 5-tuple of Q1 - 1.5 * IQR, Q1, Median, Q3,
        and Q3 + 1.5 * IQR for a list of numeric values.

        The iterator values may include None values.

        Uses quartile definition from  Mendenhall, W. and
        Sincich, T. L. Statistics for Engineering and the
        Sciences, 4th ed. Prentice-Hall, 1995.
        """
        def median(seq):
            n = len(seq)
            if n % 2 == 0:  # seq has an even length
                return (seq[n // 2] + seq[n // 2 - 1]) / 2
            else:  # seq has an odd length
                return seq[n // 2]

        # sort the copy in case the originals must stay in original order
        s = sorted([x for x in values if x is not None])
        n = len(s)
        if not n:
            return 0, 0, 0, 0, 0
        else:
            q2 = median(s)
            # See 'Method 3' in http://en.wikipedia.org/wiki/Quartile
            if n % 2 == 0:  # even
                q1 = median(s[:n // 2])
                q3 = median(s[n // 2:])
            else:  # odd
                if n == 1:  # special case
                    q1 = s[0]
                    q3 = s[0]
                elif n % 4 == 1:  # n is of form 4n + 1 where n >= 1
                    m = (n - 1) // 4
                    q1 = 0.25 * s[m-1] + 0.75 * s[m]
                    q3 = 0.75 * s[3*m] + 0.25 * s[3*m + 1]
                else:  # n is of form 4n + 3 where n >= 1
                    m = (n - 3) // 4
                    q1 = 0.75 * s[m] + 0.25 * s[m+1]
                    q3 = 0.25 * s[3*m+1] + 0.75 * s[3*m+2]

            iqr = q3 - q1
            q0 = q1 - 1.5 * iqr
            q4 = q3 + 1.5 * iqr
            return q0, q1, q2, q3, q4

########NEW FILE########
__FILENAME__ = datey
# -*- coding: utf-8 -*-
# This file is proposed as a part of pygal
# A python svg graph plotting library
#
# A python svg graph plotting library
# Copyright © 2012 Snarkturne  (modified from Kozea XY class)
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.

"""
DateY graph

Example :
import pygal
from datetime import datetime,timedelta

def jour(n) :
    return datetime(year=2014,month=1,day=1)+timedelta(days=n)

x=(1,20,35,54,345,898)
x=tuple(map(jour,x))
x_label=(0,100,200,300,400,500,600,700,800,900,1000)
x_label=map(jour,x_label)
y=(1,3,4,2,3,1)
graph=pygal.DateY(x_label_rotation=20)
graph.x_label_format = "%Y-%m-%d"
graph.x_labels = x_label
graph.add("graph1",list(zip(x,y))+[None,None])
graph.render_in_browser()
"""

from pygal._compat import total_seconds
from pygal.adapters import date
from pygal.util import compute_scale
from pygal.graph.xy import XY
import datetime


class DateY(XY):
    """ DateY Graph """
    _offset = datetime.datetime(year=2000, month=1, day=1)
    _adapters = [date]

    def _todate(self, d):
        """ Converts a number to a date """
        currDateTime = self._offset + datetime.timedelta(seconds=d or 0)
        return currDateTime.strftime(self.x_label_format)

    def _tonumber(self, d):
        """ Converts a date to a number """
        if d is None:
            return None
        return total_seconds(d - self._offset)

    def _get_value(self, values, i):
        return 'x=%s, y=%s' % (
            self._todate(values[i][0]), self._format(values[i][1]))

    def _compute(self):
        # Approximatively the same code as in XY.
        # The only difference is the transformation of dates to numbers
        # (beginning) and the reversed transformation to dates (end)
        self._offset = min([val[0]
                            for serie in self.series
                            for val in serie.values
                            if val[0] is not None]
                           or [datetime.datetime.fromtimestamp(0)])
        for serie in self.all_series:
            serie.values = [(self._tonumber(v[0]), v[1]) for v in serie.values]

        if self.xvals:
            xmin = min(self.xvals)
            xmax = max(self.xvals)
            rng = (xmax - xmin)
        else:
            rng = None

        if self.yvals:
            ymin = self._min
            ymax = self._max
            if self.include_x_axis:
                ymin = min(self._min or 0, 0)
                ymax = max(self._max or 0, 0)

        for serie in self.all_series:
            serie.points = serie.values
            if self.interpolate and rng:
                vals = list(zip(*sorted(
                    [t for t in serie.points if None not in t],
                    key=lambda x: x[0])))
                serie.interpolated = self._interpolate(vals[0], vals[1])

        if self.interpolate and rng:
            self.xvals = [val[0]
                          for serie in self.all_series
                          for val in serie.interpolated]
            self.yvals = [val[1]
                          for serie in self.all_series
                          for val in serie.interpolated]

            xmin = min(self.xvals)
            xmax = max(self.xvals)
            rng = (xmax - xmin)

        # Calculate/prcoess the x_labels
        if self.x_labels and all(
                map(lambda x: isinstance(
                    x, (datetime.datetime, datetime.date)), self.x_labels)):
            # Process the given x_labels
            x_labels_num = []
            for label in self.x_labels:
                x_labels_num.append(self._tonumber(label))
            x_pos = x_labels_num

            # Update the xmin/xmax to fit all of the x_labels and the data
            xmin = min(xmin, min(x_pos))
            xmax = max(xmax, max(x_pos))

            self._box.xmin, self._box.xmax = xmin, xmax
            self._box.ymin, self._box.ymax = ymin, ymax
        else:
            # Automatically generate the x_labels
            if rng:
                self._box.xmin, self._box.xmax = xmin, xmax
                self._box.ymin, self._box.ymax = ymin, ymax

            x_pos = compute_scale(
                self._box.xmin, self._box.xmax, self.logarithmic,
                self.order_min)

        # Always auto-generate the y labels
        y_pos = compute_scale(
            self._box.ymin, self._box.ymax, self.logarithmic, self.order_min)

        self._x_labels = list(zip(list(map(self._todate, x_pos)), x_pos))
        self._y_labels = list(zip(list(map(self._format, y_pos)), y_pos))

########NEW FILE########
__FILENAME__ = dot
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Dot chart

"""

from __future__ import division
from pygal.util import decorate, cut, safe_enumerate
from pygal.adapters import positive
from pygal.graph.graph import Graph


class Dot(Graph):
    """Dot graph"""

    _adapters = [positive]

    def dot(self, serie_node, serie, r_max):
        """Draw a dot line"""
        view_values = list(map(self.view, serie.points))
        for i, value in safe_enumerate(serie.values):
            x, y = view_values[i]
            size = r_max * value
            value = self._format(value)
            metadata = serie.metadata.get(i)
            dots = decorate(
                self.svg,
                self.svg.node(serie_node['plot'], class_="dots"),
                metadata)
            self.svg.node(dots, 'circle', cx=x, cy=y, r=size,
                          class_='dot reactive tooltip-trigger')

            self._tooltip_data(dots, value, x, y, classes='centered')
            self._static_value(serie_node, value, x, y)

    def _compute(self):
        x_len = self._len
        y_len = self._order
        self._box.xmax = x_len
        self._box.ymax = y_len

        x_pos = [n / 2 for n in range(1, 2 * x_len, 2)]
        y_pos = [n / 2 for n in reversed(range(1, 2 * y_len, 2))]

        for j, serie in enumerate(self.series):
            serie.points = [
                (x_pos[i], y_pos[j])
                for i in range(x_len)]

        self._x_labels = self.x_labels and list(zip(self.x_labels, x_pos))
        self._y_labels = list(zip(
            self.y_labels or cut(self.series, 'title'), y_pos))

    def _plot(self):
        r_max = min(
            self.view.x(1) - self.view.x(0),
            (self.view.y(0) or 0) - self.view.y(1)) / (2 * (self._max or 1) * 1.05)
        for index, serie in enumerate(self.series):
            self.dot(self._serie(index), serie, r_max)

########NEW FILE########
__FILENAME__ = frenchmap
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Worldmap chart

"""

from __future__ import division
from collections import defaultdict
from pygal.ghost import ChartCollection
from pygal.util import cut, cached_property, decorate
from pygal.graph.graph import Graph
from pygal._compat import u
from numbers import Number
from lxml import etree
import os


DEPARTMENTS = {
    '01': u("Ain"),
    '02': u("Aisne"),
    '03': u("Allier"),
    '04': u("Alpes-de-Haute-Provence"),
    '05': u("Hautes-Alpes"),
    '06': u("Alpes-Maritimes"),
    '07': u("Ardèche"),
    '08': u("Ardennes"),
    '09': u("Ariège"),
    '10': u("Aube"),
    '11': u("Aude"),
    '12': u("Aveyron"),
    '13': u("Bouches-du-Rhône"),
    '14': u("Calvados"),
    '15': u("Cantal"),
    '16': u("Charente"),
    '17': u("Charente-Maritime"),
    '18': u("Cher"),
    '19': u("Corrèze"),
    '2A': u("Corse-du-Sud"),
    '2B': u("Haute-Corse"),
    '21': u("Côte-d'Or"),
    '22': u("Côtes-d'Armor"),
    '23': u("Creuse"),
    '24': u("Dordogne"),
    '25': u("Doubs"),
    '26': u("Drôme"),
    '27': u("Eure"),
    '28': u("Eure-et-Loir"),
    '29': u("Finistère"),
    '30': u("Gard"),
    '31': u("Haute-Garonne"),
    '32': u("Gers"),
    '33': u("Gironde"),
    '34': u("Hérault"),
    '35': u("Ille-et-Vilaine"),
    '36': u("Indre"),
    '37': u("Indre-et-Loire"),
    '38': u("Isère"),
    '39': u("Jura"),
    '40': u("Landes"),
    '41': u("Loir-et-Cher"),
    '42': u("Loire"),
    '43': u("Haute-Loire"),
    '44': u("Loire-Atlantique"),
    '45': u("Loiret"),
    '46': u("Lot"),
    '47': u("Lot-et-Garonne"),
    '48': u("Lozère"),
    '49': u("Maine-et-Loire"),
    '50': u("Manche"),
    '51': u("Marne"),
    '52': u("Haute-Marne"),
    '53': u("Mayenne"),
    '54': u("Meurthe-et-Moselle"),
    '55': u("Meuse"),
    '56': u("Morbihan"),
    '57': u("Moselle"),
    '58': u("Nièvre"),
    '59': u("Nord"),
    '60': u("Oise"),
    '61': u("Orne"),
    '62': u("Pas-de-Calais"),
    '63': u("Puy-de-Dôme"),
    '64': u("Pyrénées-Atlantiques"),
    '65': u("Hautes-Pyrénées"),
    '66': u("Pyrénées-Orientales"),
    '67': u("Bas-Rhin"),
    '68': u("Haut-Rhin"),
    '69': u("Rhône"),
    '70': u("Haute-Saône"),
    '71': u("Saône-et-Loire"),
    '72': u("Sarthe"),
    '73': u("Savoie"),
    '74': u("Haute-Savoie"),
    '75': u("Paris"),
    '76': u("Seine-Maritime"),
    '77': u("Seine-et-Marne"),
    '78': u("Yvelines"),
    '79': u("Deux-Sèvres"),
    '80': u("Somme"),
    '81': u("Tarn"),
    '82': u("Tarn-et-Garonne"),
    '83': u("Var"),
    '84': u("Vaucluse"),
    '85': u("Vendée"),
    '86': u("Vienne"),
    '87': u("Haute-Vienne"),
    '88': u("Vosges"),
    '89': u("Yonne"),
    '90': u("Territoire de Belfort"),
    '91': u("Essonne"),
    '92': u("Hauts-de-Seine"),
    '93': u("Seine-Saint-Denis"),
    '94': u("Val-de-Marne"),
    '95': u("Val-d'Oise"),
    '971': u("Guadeloupe"),
    '972': u("Martinique"),
    '973': u("Guyane"),
    '974': u("Réunion"),
    # Not a area anymore but in case of...
    '975': u("Saint Pierre et Miquelon"),
    '976': u("Mayotte")
}


REGIONS = {
    '11': u("Île-de-France"),
    '21': u("Champagne-Ardenne"),
    '22': u("Picardie"),
    '23': u("Haute-Normandie"),
    '24': u("Centre"),
    '25': u("Basse-Normandie"),
    '26': u("Bourgogne"),
    '31': u("Nord-Pas-de-Calais"),
    '41': u("Lorraine"),
    '42': u("Alsace"),
    '43': u("Franche-Comté"),
    '52': u("Pays-de-la-Loire"),
    '53': u("Bretagne"),
    '54': u("Poitou-Charentes"),
    '72': u("Aquitaine"),
    '73': u("Midi-Pyrénées"),
    '74': u("Limousin"),
    '82': u("Rhône-Alpes"),
    '83': u("Auvergne"),
    '91': u("Languedoc-Roussillon"),
    '93': u("Provence-Alpes-Côte d'Azur"),
    '94': u("Corse"),
    '01': u("Guadeloupe"),
    '02': u("Martinique"),
    '03': u("Guyane"),
    '04': u("Réunion"),
    # Not a region anymore but in case of...
    '05': u("Saint Pierre et Miquelon"),
    '06': u("Mayotte")
}


with open(os.path.join(
        os.path.dirname(__file__),
        'fr.departments.svg')) as file:
    DPT_MAP = file.read()


with open(os.path.join(
        os.path.dirname(__file__),
        'fr.regions.svg')) as file:
    REG_MAP = file.read()


class FrenchMapDepartments(Graph):
    """French department map"""
    _dual = True
    x_labels = list(DEPARTMENTS.keys())
    area_names = DEPARTMENTS
    area_prefix = 'z'
    svg_map = DPT_MAP


    @cached_property
    def _values(self):
        """Getter for series values (flattened)"""
        return [val[1]
                for serie in self.series
                for val in serie.values
                if val[1] is not None]

    def _plot(self):
        map = etree.fromstring(self.svg_map)
        map.set('width', str(self.view.width))
        map.set('height', str(self.view.height))

        for i, serie in enumerate(self.series):
            safe_vals = list(filter(
                lambda x: x is not None, cut(serie.values, 1)))
            if not safe_vals:
                continue
            min_ = min(safe_vals)
            max_ = max(safe_vals)
            for j, (area_code, value) in enumerate(serie.values):
                if isinstance(area_code, Number):
                    area_code = '%2d' % area_code
                if value is None:
                    continue
                if max_ == min_:
                    ratio = 1
                else:
                    ratio = .3 + .7 * (value - min_) / (max_ - min_)
                areae = map.xpath(
                    "//*[contains(concat(' ', normalize-space(@class), ' '),"
                    " ' %s%s ')]" % (self.area_prefix, area_code))

                if not areae:
                    continue
                for area in areae:
                    cls = area.get('class', '').split(' ')
                    cls.append('color-%d' % i)
                    area.set('class', ' '.join(cls))
                    area.set('style', 'fill-opacity: %f' % (ratio))

                    metadata = serie.metadata.get(j)
                    if metadata:
                        parent = area.getparent()
                        node = decorate(self.svg, area, metadata)
                        if node != area:
                            area.remove(node)
                            index = parent.index(area)
                            parent.remove(area)
                            node.append(area)
                            parent.insert(index, node)

                    last_node = len(area) > 0 and area[-1]
                    if last_node is not None and last_node.tag == 'title':
                        title_node = last_node
                        text = title_node.text + '\n'
                    else:
                        title_node = self.svg.node(area, 'title')
                        text = ''
                    title_node.text = text + '[%s] %s: %s' % (
                        serie.title,
                        self.area_names[area_code], self._format(value))

        self.nodes['plot'].append(map)


class FrenchMapRegions(FrenchMapDepartments):
    """French regions map"""
    x_labels = list(REGIONS.keys())
    area_names = REGIONS
    area_prefix = 'a'
    svg_map = REG_MAP


class FrenchMap(ChartCollection):
    Regions = FrenchMapRegions
    Departments = FrenchMapDepartments


DEPARTMENTS_REGIONS = {
    "01": "82",
    "02": "22",
    "03": "83",
    "04": "93",
    "05": "93",
    "06": "93",
    "07": "82",
    "08": "21",
    "09": "73",
    "10": "21",
    "11": "91",
    "12": "73",
    "13": "93",
    "14": "25",
    "15": "83",
    "16": "54",
    "17": "54",
    "18": "24",
    "19": "74",
    "21": "26",
    "22": "53",
    "23": "74",
    "24": "72",
    "25": "43",
    "26": "82",
    "27": "23",
    "28": "24",
    "29": "53",
    "2A": "94",
    "2B": "94",
    "30": "91",
    "31": "73",
    "32": "73",
    "33": "72",
    "34": "91",
    "35": "53",
    "36": "24",
    "37": "24",
    "38": "82",
    "39": "43",
    "40": "72",
    "41": "24",
    "42": "82",
    "43": "83",
    "44": "52",
    "45": "24",
    "46": "73",
    "47": "72",
    "48": "91",
    "49": "52",
    "50": "25",
    "51": "21",
    "52": "21",
    "53": "52",
    "54": "41",
    "55": "41",
    "56": "53",
    "57": "41",
    "58": "26",
    "59": "31",
    "60": "22",
    "61": "25",
    "62": "31",
    "63": "83",
    "64": "72",
    "65": "73",
    "66": "91",
    "67": "42",
    "68": "42",
    "69": "82",
    "70": "43",
    "71": "26",
    "72": "52",
    "73": "82",
    "74": "82",
    "75": "11",
    "76": "23",
    "77": "11",
    "78": "11",
    "79": "54",
    "80": "22",
    "81": "73",
    "82": "73",
    "83": "93",
    "84": "93",
    "85": "52",
    "86": "54",
    "87": "74",
    "88": "41",
    "89": "26",
    "90": "43",
    "91": "11",
    "92": "11",
    "93": "11",
    "94": "11",
    "95": "11",
    "971": "01",
    "972": "02",
    "973": "03",
    "974": "04",
    "975": "05",
    "976": "06"
}


def aggregate_regions(values):
    if isinstance(values, dict):
        values = values.items()
    regions = defaultdict(int)
    for department, value in values:
        regions[DEPARTMENTS_REGIONS[department]] += value
    return list(regions.items())

########NEW FILE########
__FILENAME__ = funnel
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Funnel chart

"""

from __future__ import division
from pygal.util import decorate, cut, compute_scale
from pygal.adapters import positive, none_to_zero
from pygal.graph.graph import Graph


class Funnel(Graph):
    """Funnel graph"""

    _adapters = [positive, none_to_zero]

    def _format(self, value):
        return super(Funnel, self)._format(abs(value))

    def funnel(self, serie_node, serie, index):
        """Draw a dot line"""

        fmt = lambda x: '%f %f' % x
        for i, poly in enumerate(serie.points):
            metadata = serie.metadata.get(i)
            value = self._format(serie.values[i])

            funnels = decorate(
                self.svg,
                self.svg.node(serie_node['plot'], class_="funnels"),
                metadata)

            self.svg.node(
                funnels, 'polygon',
                points=' '.join(map(fmt, map(self.view, poly))),
                class_='funnel reactive tooltip-trigger')

            x, y = self.view((
                self._x_labels[index][1],  # Poly center from label
                sum([point[1] for point in poly]) / len(poly)))
            self._tooltip_data(funnels, value, x, y, classes='centered')
            self._static_value(serie_node, value, x, y)

    def _compute(self):
        x_pos = [
            (x + 1) / self._order for x in range(self._order)
        ] if self._order != 1 else [.5]  # Center if only one value

        previous = [[self.zero, self.zero] for i in range(self._len)]
        for i, serie in enumerate(self.series):
            y_height = - sum(serie.safe_values) / 2
            all_x_pos = [0] + x_pos
            serie.points = []
            for j, value in enumerate(serie.values):
                poly = []
                poly.append((all_x_pos[i], previous[j][0]))
                poly.append((all_x_pos[i], previous[j][1]))
                previous[j][0] = y_height
                y_height = previous[j][1] = y_height + value
                poly.append((all_x_pos[i + 1], previous[j][1]))
                poly.append((all_x_pos[i + 1], previous[j][0]))
                serie.points.append(poly)

        val_max = max(list(map(sum, cut(self.series, 'values'))) + [self.zero])
        self._box.ymin = -val_max
        self._box.ymax = val_max

        y_pos = compute_scale(
            self._box.ymin, self._box.ymax, self.logarithmic, self.order_min
        ) if not self.y_labels else list(map(float, self.y_labels))

        self._x_labels = list(
            zip(cut(self.series, 'title'),
                map(lambda x: x - 1 / (2 * self._order), x_pos)))
        self._y_labels = list(zip(map(self._format, y_pos), y_pos))

    def _plot(self):
        for index, serie in enumerate(self.series):
            self.funnel(
                self._serie(index), serie, index)

########NEW FILE########
__FILENAME__ = gauge
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Gauge chart

"""

from __future__ import division
from pygal.util import decorate, compute_scale
from pygal.view import PolarThetaView, PolarThetaLogView
from pygal.graph.graph import Graph


class Gauge(Graph):
    """Gauge graph"""

    def _set_view(self):
        if self.logarithmic:
            view_class = PolarThetaLogView
        else:
            view_class = PolarThetaView

        self.view = view_class(
            self.width - self.margin.x,
            self.height - self.margin.y,
            self._box)

    def needle(self, serie_node, serie):
        for i, theta in enumerate(serie.values):
            if theta is None:
                continue
            fmt = lambda x: '%f %f' % x
            value = self._format(serie.values[i])
            metadata = serie.metadata.get(i)
            gauges = decorate(
                self.svg,
                self.svg.node(serie_node['plot'], class_="dots"),
                metadata)

            self.svg.node(
                gauges, 'polygon', points=' '.join([
                    fmt(self.view((0, 0))),
                    fmt(self.view((.75, theta))),
                    fmt(self.view((.8, theta))),
                    fmt(self.view((.75, theta)))]),
                class_='line reactive tooltip-trigger')

            x, y = self.view((.75, theta))
            self._tooltip_data(gauges, value, x, y)
            self._static_value(serie_node, value, x, y)

    def _x_axis(self, draw_axes=True):
        axis = self.svg.node(self.nodes['plot'], class_="axis x gauge")

        for i, (label, theta) in enumerate(self._x_labels):
            guides = self.svg.node(axis, class_='guides')

            self.svg.line(
                guides, [self.view((.95, theta)), self.view((1, theta))],
                close=True,
                class_='line')

            self.svg.line(
                guides, [self.view((0, theta)), self.view((.95, theta))],
                close=True,
                class_='guide line %s' % (
                    'major' if i in (0, len(self._x_labels) - 1)
                    else ''))

            x, y = self.view((.9, theta))
            self.svg.node(
                guides, 'text',
                x=x,
                y=y
            ).text = label

    def _y_axis(self, draw_axes=True):
        axis = self.svg.node(self.nodes['plot'], class_="axis y gauge")
        x, y = self.view((0, 0))
        self.svg.node(axis, 'circle', cx=x, cy=y, r=4)

    def _compute(self):
        self.min_ = self._min or 0
        self.max_ = self._max or 0
        if self.max_ - self.min_ == 0:
            self.min_ -= 1
            self.max_ += 1

        self._box.set_polar_box(
            0, 1,
            self.min_,
            self.max_)
        x_pos = compute_scale(
            self.min_, self.max_, self.logarithmic, self.order_min
        )
        self._x_labels = list(zip(map(self._format, x_pos), x_pos))

    def _plot(self):
        for index, serie in enumerate(self.series):
            self.needle(
                self._serie(index), serie)

########NEW FILE########
__FILENAME__ = graph
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Commmon graphing functions

"""

from __future__ import division
from pygal.interpolate import INTERPOLATIONS
from pygal.graph.base import BaseGraph
from pygal.view import View, LogView, XYLogView
from pygal.util import (
    truncate, reverse_text_len, get_texts_box, cut, rad, decorate)
from math import sqrt, ceil, cos
from itertools import repeat, chain


class Graph(BaseGraph):
    """Graph super class containing generic common functions"""
    _dual = False

    def _decorate(self):
        """Draw all decorations"""
        self._set_view()
        self._make_graph()
        self._axes()
        self._legend()
        self._title()
        self._x_title()
        self._y_title()

    def _axes(self):
        """Draw axes"""
        self._x_axis()
        self._y_axis()

    def _set_view(self):
        """Assign a view to current graph"""
        if self.logarithmic:
            if self._dual:
                view_class = XYLogView
            else:
                view_class = LogView
        else:
            view_class = View

        self.view = view_class(
            self.width - self.margin.x,
            self.height - self.margin.y,
            self._box)

    def _make_graph(self):
        """Init common graph svg structure"""
        self.nodes['graph'] = self.svg.node(
            class_='graph %s-graph %s' % (
                self.__class__.__name__.lower(),
                'horizontal' if self.horizontal else 'vertical'))
        self.svg.node(self.nodes['graph'], 'rect',
                      class_='background',
                      x=0, y=0,
                      width=self.width,
                      height=self.height)
        self.nodes['plot'] = self.svg.node(
            self.nodes['graph'], class_="plot",
            transform="translate(%d, %d)" % (
                self.margin.left, self.margin.top))
        self.svg.node(self.nodes['plot'], 'rect',
                      class_='background',
                      x=0, y=0,
                      width=self.view.width,
                      height=self.view.height)
        self.nodes['title'] = self.svg.node(
            self.nodes['graph'],
            class_="titles")
        self.nodes['overlay'] = self.svg.node(
            self.nodes['graph'], class_="plot overlay",
            transform="translate(%d, %d)" % (
                self.margin.left, self.margin.top))
        self.nodes['text_overlay'] = self.svg.node(
            self.nodes['graph'], class_="plot text-overlay",
            transform="translate(%d, %d)" % (
                self.margin.left, self.margin.top))
        self.nodes['tooltip_overlay'] = self.svg.node(
            self.nodes['graph'], class_="plot tooltip-overlay",
            transform="translate(%d, %d)" % (
                self.margin.left, self.margin.top))
        self.nodes['tooltip'] = self.svg.node(
            self.nodes['tooltip_overlay'],
            transform='translate(0 0)',
            style="opacity: 0",
            **{'class': 'tooltip'})

        a = self.svg.node(self.nodes['tooltip'], 'a')
        self.svg.node(a, 'rect',
                      rx=self.tooltip_border_radius,
                      ry=self.tooltip_border_radius,
                      width=0, height=0,
                      **{'class': 'tooltip-box'})
        text = self.svg.node(a, 'text', class_='text')
        self.svg.node(text, 'tspan', class_='label')
        self.svg.node(text, 'tspan', class_='value')

    def _x_axis(self):
        """Make the x axis: labels and guides"""
        if not self._x_labels:
            return
        axis = self.svg.node(self.nodes['plot'], class_="axis x%s" % (
            ' always_show' if self.show_x_guides else ''
        ))
        truncation = self.truncate_label
        if not truncation:
            if self.x_label_rotation or len(self._x_labels) <= 1:
                truncation = 25
            else:
                first_label_position = self.view.x(self._x_labels[0][1]) or 0
                last_label_position = self.view.x(self._x_labels[-1][1]) or 0
                available_space = (
                    last_label_position - first_label_position) / (
                    len(self._x_labels) - 1)
                truncation = reverse_text_len(
                    available_space, self.label_font_size)
                truncation = max(truncation, 1)

        if 0 not in [label[1] for label in self._x_labels]:
            self.svg.node(axis, 'path',
                          d='M%f %f v%f' % (0, 0, self.view.height),
                          class_='line')
        lastlabel = self._x_labels[-1][0]

        for label, position in self._x_labels:
            major = label in self._x_major_labels
            if not (self.show_minor_x_labels or major):
                continue
            guides = self.svg.node(axis, class_='guides')
            x = self.view.x(position)
            y = self.view.height + 5
            last_guide = (self._y_2nd_labels and label == lastlabel)
            self.svg.node(
                guides, 'path',
                d='M%f %f v%f' % (x or 0, 0, self.view.height),
                class_='%s%sline' % (
                    'major ' if major else '',
                    'guide ' if position != 0 and not last_guide else ''))
            y += .5 * self.label_font_size + 5
            text = self.svg.node(
                guides, 'text',
                x=x,
                y=y,
                class_='major' if major else ''
            )

            if isinstance(label, dict):
                label = label['title']

            text.text = truncate(label, truncation)
            if text.text != label:
                self.svg.node(guides, 'title').text = label
            if self.x_label_rotation:
                text.attrib['transform'] = "rotate(%d %f %f)" % (
                    self.x_label_rotation, x, y)

        if self._x_2nd_labels:
            secondary_ax = self.svg.node(
                self.nodes['plot'], class_="axis x x2%s" % (
                    ' always_show' if self.show_x_guides else ''
                ))
            for label, position in self._x_2nd_labels:
                major = label in self._x_major_labels
                if not (self.show_minor_x_labels or major):
                    continue
                # it is needed, to have the same structure as primary axis
                guides = self.svg.node(secondary_ax, class_='guides')
                x = self.view.x(position)
                y = -5
                text = self.svg.node(
                    guides, 'text',
                    x=x,
                    y=y,
                    class_='major' if major else ''
                )
                text.text = label
                if self.x_label_rotation:
                    text.attrib['transform'] = "rotate(%d %f %f)" % (
                        -self.x_label_rotation, x, y)

    def _y_axis(self):
        """Make the y axis: labels and guides"""
        if not self._y_labels or not self.show_y_labels:
            return

        axis = self.svg.node(self.nodes['plot'], class_="axis y")

        if (0 not in [label[1] for label in self._y_labels] and
                self.show_y_guides):
            self.svg.node(
                axis, 'path',
                d='M%f %f h%f' % (0, self.view.height, self.view.width),
                class_='line'
            )

        for label, position in self._y_labels:
            major = position in self._y_major_labels
            if not (self.show_minor_y_labels or major):
                continue
            guides = self.svg.node(axis, class_='%sguides' % (
                'logarithmic ' if self.logarithmic else ''
            ))
            x = -5
            y = self.view.y(position)
            if not y:
                continue
            if self.show_y_guides:
                self.svg.node(
                    guides, 'path',
                    d='M%f %f h%f' % (0, y, self.view.width),
                    class_='%s%sline' % (
                        'major ' if major else '',
                        'guide ' if position != 0 else ''))
            text = self.svg.node(
                guides, 'text',
                x=x,
                y=y + .35 * self.label_font_size,
                class_='major' if major else ''
            )

            if isinstance(label, dict):
                label = label['title']
            text.text = label

            if self.y_label_rotation:
                text.attrib['transform'] = "rotate(%d %f %f)" % (
                    self.y_label_rotation, x, y)

        if self._y_2nd_labels:
            secondary_ax = self.svg.node(
                self.nodes['plot'], class_="axis y2")
            for label, position in self._y_2nd_labels:
                major = position in self._y_major_labels
                if not (self.show_minor_x_labels or major):
                    continue
                # it is needed, to have the same structure as primary axis
                guides = self.svg.node(secondary_ax, class_='guides')
                x = self.view.width + 5
                y = self.view.y(position)
                text = self.svg.node(
                    guides, 'text',
                    x=x,
                    y=y + .35 * self.label_font_size,
                    class_='major' if major else ''
                )
                text.text = label
                if self.y_label_rotation:
                    text.attrib['transform'] = "rotate(%d %f %f)" % (
                        self.y_label_rotation, x, y)

    def _legend(self):
        """Make the legend box"""
        if not self.show_legend:
            return
        truncation = self.truncate_legend
        if self.legend_at_bottom:
            x = self.margin.left + self.spacing
            y = (self.margin.top + self.view.height +
                 self._x_title_height +
                 self._x_labels_height + self.spacing)
            cols = ceil(sqrt(self._order)) or 1

            if not truncation:
                available_space = self.view.width / cols - (
                    self.legend_box_size + 5)
                truncation = reverse_text_len(
                    available_space, self.legend_font_size)
        else:
            x = self.spacing
            y = self.margin.top + self.spacing
            cols = 1
            if not truncation:
                truncation = 15

        legends = self.svg.node(
            self.nodes['graph'], class_='legends',
            transform='translate(%d, %d)' % (x, y))

        h = max(self.legend_box_size, self.legend_font_size)
        x_step = self.view.width / cols
        if self.legend_at_bottom:
            # if legends at the bottom, we dont split the windows
            # gen structure - (i, (j, (l, tf)))
            # i - global serie number - used for coloring and identification
            # j - position within current legend box
            # l - label
            # tf - whether it is secondary label
            gen = enumerate(enumerate(chain(
                zip(self._legends, repeat(False)),
                zip(self._secondary_legends, repeat(True)))))
            secondary_legends = legends  # svg node is the same
        else:
            gen = enumerate(chain(
                enumerate(zip(self._legends, repeat(False))),
                enumerate(zip(self._secondary_legends, repeat(True)))))

            # draw secondary axis on right
            x = self.margin.left + self.view.width + self.spacing
            if self._y_2nd_labels:
                h, w = get_texts_box(
                    cut(self._y_2nd_labels), self.label_font_size)
                x += self.spacing + max(w * cos(rad(self.y_label_rotation)), h)

            y = self.margin.top + self.spacing

            secondary_legends = self.svg.node(
                self.nodes['graph'], class_='legends',
                transform='translate(%d, %d)' % (x, y))

        for (global_serie_number, (i, (title, is_secondary))) in gen:

            col = i % cols
            row = i // cols

            legend = self.svg.node(
                secondary_legends if is_secondary else legends,
                class_='legend reactive activate-serie',
                id="activate-serie-%d" % global_serie_number)
            self.svg.node(
                legend, 'rect',
                x=col * x_step,
                y=1.5 * row * h + (
                    self.legend_font_size - self.legend_box_size
                    if self.legend_font_size > self.legend_box_size else 0
                ) / 2,
                width=self.legend_box_size,
                height=self.legend_box_size,
                class_="color-%d reactive" % (global_serie_number % 16)
            )

            if isinstance(title, dict):
                node = decorate(self.svg, legend, title)
                title = title['title']
            else:
                node = legend

            truncated = truncate(title, truncation)
            self.svg.node(
                node, 'text',
                x=col * x_step + self.legend_box_size + 5,
                y=1.5 * row * h + .5 * h + .3 * self.legend_font_size
            ).text = truncated

            if truncated != title:
                self.svg.node(legend, 'title').text = title

    def _title(self):
        """Make the title"""
        if self.title:
            for i, title_line in enumerate(self.title, 1):
                self.svg.node(
                    self.nodes['title'], 'text', class_='title plot_title',
                    x=self.width / 2,
                    y=i * (self.title_font_size + self.spacing)
                ).text = title_line

    def _x_title(self):
        """Make the X-Axis title"""
        y = (self.height - self.margin.bottom +
             self._x_labels_height)
        if self.x_title:
            for i, title_line in enumerate(self.x_title, 1):
                text = self.svg.node(
                    self.nodes['title'], 'text', class_='title',
                    x=self.margin.left + self.view.width / 2,
                    y=y + i * (self.title_font_size + self.spacing)
                )
                text.text = title_line

    def _y_title(self):
        """Make the Y-Axis title"""
        if self.y_title:
            yc = self.margin.top + self.view.height / 2
            for i, title_line in enumerate(self.y_title, 1):
                text = self.svg.node(
                    self.nodes['title'], 'text', class_='title',
                    x=self._legend_at_left_width,
                    y=i * (self.title_font_size + self.spacing) + yc
                )
                text.attrib['transform'] = "rotate(%d %f %f)" % (
                    -90, self._legend_at_left_width, yc)
                text.text = title_line

    def _serie(self, serie):
        """Make serie node"""
        return dict(
            plot=self.svg.node(
                self.nodes['plot'],
                class_='series serie-%d color-%d' % (
                    serie, serie % len(self.style['colors']))),
            overlay=self.svg.node(
                self.nodes['overlay'],
                class_='series serie-%d color-%d' % (
                    serie, serie % len(self.style['colors']))),
            text_overlay=self.svg.node(
                self.nodes['text_overlay'],
                class_='series serie-%d color-%d' % (
                    serie, serie % len(self.style['colors']))))

    def _interpolate(self, xs, ys):
        """Make the interpolation"""
        x = []
        y = []
        for i in range(len(ys)):
            if ys[i] is not None:
                x.append(xs[i])
                y.append(ys[i])

        interpolate = INTERPOLATIONS[self.interpolate]

        return list(interpolate(
            x, y, self.interpolation_precision,
            **self.interpolation_parameters))

    def _tooltip_data(self, node, value, x, y, classes=None):
        self.svg.node(node, 'desc', class_="value").text = value
        if classes is None:
            classes = []
            if x > self.view.width / 2:
                classes.append('left')
            if y > self.view.height / 2:
                classes.append('top')
            classes = ' '.join(classes)

        self.svg.node(node, 'desc',
                      class_="x " + classes).text = str(x)
        self.svg.node(node, 'desc',
                      class_="y " + classes).text = str(y)

    def _static_value(self, serie_node, value, x, y):
        if self.print_values:
            self.svg.node(
                serie_node['text_overlay'], 'text',
                class_='centered',
                x=x,
                y=y + self.value_font_size / 3
            ).text = value if self.print_zeroes or value != '0' else ''

    def _get_value(self, values, i):
        """Get the value formatted for tooltip"""
        return self._format(values[i][1])

    def _points(self, x_pos):
        for serie in self.all_series:
            serie.points = [
                (x_pos[i], v)
                for i, v in enumerate(serie.values)]
            if serie.points and self.interpolate:
                serie.interpolated = self._interpolate(x_pos, serie.values)
            else:
                serie.interpolated = []

    def _compute_secondary(self):
        # secondary y axis support
        if self.secondary_series and self._y_labels:
            y_pos = list(zip(*self._y_labels))[1]
            if self.include_x_axis:
                ymin = min(self._secondary_min, 0)
                ymax = max(self._secondary_max, 0)
            else:
                ymin = self._secondary_min
                ymax = self._secondary_max
            steps = len(y_pos)
            left_range = abs(y_pos[-1] - y_pos[0])
            right_range = abs(ymax - ymin) or 1
            scale = right_range / ((steps - 1) or 1)
            self._y_2nd_labels = [(self._format(ymin + i * scale), pos)
                                  for i, pos in enumerate(y_pos)]

            self._scale = left_range / right_range
            self._scale_diff = y_pos[0]
            self._scale_min_2nd = ymin

    def _post_compute(self):
        pass

########NEW FILE########
__FILENAME__ = histogram
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Histogram chart

"""

from __future__ import division
from pygal.graph.graph import Graph
from pygal.util import swap, ident, compute_scale, decorate, cached_property


class Histogram(Graph):
    """Histogram chart"""

    _dual = True
    _series_margin = 0


    @cached_property
    def _secondary_values(self):
        """Getter for secondary series values (flattened)"""
        return [val[0]
                for serie in self.secondary_series
                for val in serie.values
                if val[0] is not None]

    @cached_property
    def xvals(self):
        return [val
                for serie in self.all_series
                for dval in serie.values
                for val in dval[1:3]
                if val is not None]

    @cached_property
    def yvals(self):
        return [val[0]
                for serie in self.series
                for val in serie.values
                if val[0] is not None]

    def _has_data(self):
        """Check if there is any data"""
        return sum(
            map(len, map(lambda s: s.safe_values, self.series))) != 0 and any((
                sum(map(abs, self.xvals)) != 0,
                sum(map(abs, self.yvals)) != 0))

    def _bar(self, parent, x0, x1, y, index, i, zero,
             secondary=False, rounded=False):
        x, y = self.view((x0, y))
        x1, _ = self.view((x1, y))
        width = x1 - x
        height = self.view.y(zero) - y
        series_margin = width * self._series_margin
        x += series_margin
        width -= 2 * series_margin

        r = self.rounded_bars * 1 if self.rounded_bars else 0
        self.svg.transposable_node(
            parent, 'rect',
            x=x, y=y, rx=r, ry=r, width=width, height=height,
            class_='rect reactive tooltip-trigger')
        transpose = swap if self.horizontal else ident
        return transpose((x + width / 2, y + height / 2))

    def bar(self, serie_node, serie, index, rescale=False):
        """Draw a bar graph for a serie"""
        bars = self.svg.node(serie_node['plot'], class_="histbars")
        points = serie.points

        for i, (y, x0, x1) in enumerate(points):
            if None in (x0, x1, y) or (self.logarithmic and y <= 0):
                continue
            metadata = serie.metadata.get(i)

            bar = decorate(
                self.svg,
                self.svg.node(bars, class_='histbar'),
                metadata)
            val = self._format(serie.values[i][0])

            x_center, y_center = self._bar(
                bar, x0, x1, y, index, i, self.zero, secondary=rescale,
                rounded=serie.rounded_bars)
            self._tooltip_data(
                bar, val, x_center, y_center, classes="centered")
            self._static_value(serie_node, val, x_center, y_center)

    def _compute(self):
        if self.xvals:
            xmin = min(self.xvals)
            xmax = max(self.xvals)
            xrng = (xmax - xmin)
        else:
            xrng = None

        if self.yvals:
            ymin = min(min(self.yvals), self.zero)
            ymax = max(max(self.yvals), self.zero)
            yrng = (ymax - ymin)
        else:
            yrng = None

        for serie in self.all_series:
            serie.points = serie.values

        if xrng:
            self._box.xmin, self._box.xmax = xmin, xmax
        if yrng:
            self._box.ymin, self._box.ymax = ymin, ymax

        x_pos = compute_scale(
            self._box.xmin, self._box.xmax, self.logarithmic, self.order_min)
        y_pos = compute_scale(
            self._box.ymin, self._box.ymax, self.logarithmic, self.order_min)

        self._x_labels = list(zip(map(self._format, x_pos), x_pos))
        self._y_labels = list(zip(map(self._format, y_pos), y_pos))

    def _plot(self):
        for index, serie in enumerate(self.series):
            self.bar(self._serie(index), serie, index)
        for index, serie in enumerate(self.secondary_series, len(self.series)):
            self.bar(self._serie(index), serie, index, True)

########NEW FILE########
__FILENAME__ = horizontal
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Horizontal graph base

"""
from pygal.graph.graph import Graph
from pygal.view import HorizontalView, HorizontalLogView


class HorizontalGraph(Graph):
    """Horizontal graph"""
    def __init__(self, *args, **kwargs):
        self.horizontal = True
        super(HorizontalGraph, self).__init__(*args, **kwargs)

    def _post_compute(self):
        self._x_labels, self._y_labels = self._y_labels, self._x_labels
        self._x_2nd_labels, self._y_2nd_labels = (
            self._y_2nd_labels, self._x_2nd_labels)

    def _axes(self):
        self.view._force_vertical = True
        super(HorizontalGraph, self)._axes()
        self.view._force_vertical = False

    def _set_view(self):
        """Assign a view to current graph"""
        if self.logarithmic:
            view_class = HorizontalLogView
        else:
            view_class = HorizontalView

        self.view = view_class(
            self.width - self.margin.x,
            self.height - self.margin.y,
            self._box)

########NEW FILE########
__FILENAME__ = horizontalbar
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Horizontal bar graph

"""
from pygal.graph.horizontal import HorizontalGraph
from pygal.graph.bar import Bar


class HorizontalBar(HorizontalGraph, Bar):
    """Horizontal Bar graph"""

    def _plot(self):
        for index, serie in enumerate(self.series[::-1]):
            num = len(self.series) - index - 1
            self.bar(self._serie(num), serie, index)
        for index, serie in enumerate(self.secondary_series[::-1]):
            num = len(self.secondary_series) + len(self.series) - index - 1
            self.bar(self._serie(num), serie, index + len(self.series), True)

########NEW FILE########
__FILENAME__ = horizontalstackedbar
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Horizontal stacked graph

"""
from pygal.graph.horizontal import HorizontalGraph
from pygal.graph.stackedbar import StackedBar


class HorizontalStackedBar(HorizontalGraph, StackedBar):
    """Horizontal Stacked Bar graph"""

########NEW FILE########
__FILENAME__ = line
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Line chart

"""
from __future__ import division
from pygal.graph.graph import Graph
from pygal.util import cached_property, compute_scale, decorate


class Line(Graph):
    """Line graph"""

    def __init__(self, *args, **kwargs):
        self._self_close = False
        super(Line, self).__init__(*args, **kwargs)

    @cached_property
    def _values(self):
        return [
            val[1]
            for serie in self.series
            for val in (serie.interpolated
                        if self.interpolate else serie.points)
            if val[1] is not None and (not self.logarithmic or val[1] > 0)]

    @cached_property
    def _secondary_values(self):
        return [
            val[1]
            for serie in self.secondary_series
            for val in (serie.interpolated
                        if self.interpolate else serie.points)
            if val[1] is not None and (not self.logarithmic or val[1] > 0)]

    def _fill(self, values):
        """Add extra values to fill the line"""
        zero = self.view.y(min(max(self.zero, self._box.ymin), self._box.ymax))
        return ([(values[0][0], zero)] +
                values +
                [(values[-1][0], zero)])

    def line(self, serie_node, serie, rescale=False):
        """Draw the line serie"""
        if rescale and self.secondary_series:
            points = [
                (x, self._scale_diff + (y - self._scale_min_2nd) * self._scale)
                for x, y in serie.points if y is not None]
        else:
            points = serie.points
        view_values = list(map(self.view, points))
        if serie.show_dots:
            for i, (x, y) in enumerate(view_values):
                if None in (x, y):
                    continue
                if (serie.show_only_major_dots and
                        self.x_labels and i < len(self.x_labels) and
                        self.x_labels[i] not in self._x_major_labels):
                    continue

                metadata = serie.metadata.get(i)
                classes = []
                if x > self.view.width / 2:
                    classes.append('left')
                if y > self.view.height / 2:
                    classes.append('top')
                classes = ' '.join(classes)
                dots = decorate(
                    self.svg,
                    self.svg.node(serie_node['overlay'], class_="dots"),
                    metadata)
                val = self._get_value(serie.points, i)
                self.svg.node(dots, 'circle', cx=x, cy=y, r=serie.dots_size,
                              class_='dot reactive tooltip-trigger')
                self._tooltip_data(
                    dots, val, x, y)
                self._static_value(
                    serie_node, val,
                    x + self.value_font_size,
                    y + self.value_font_size)

        if serie.stroke:
            if self.interpolate:
                view_values = list(map(self.view, serie.interpolated))
            if serie.fill:
                view_values = self._fill(view_values)
            self.svg.line(
                serie_node['plot'], view_values, close=self._self_close,
                class_='line reactive' + (' nofill' if not serie.fill else ''))

    def _compute(self):
        # X Labels
        x_pos = [
            x / (self._len - 1) for x in range(self._len)
        ] if self._len != 1 else [.5]  # Center if only one value

        self._points(x_pos)

        if self.x_labels:
            label_len = len(self.x_labels)
            if label_len != self._len:
                label_pos = [0.5] if label_len == 1 else [
                    x / (label_len - 1) for x in range(label_len)
                ]
                self._x_labels = list(zip(self.x_labels, label_pos))
            else:
                self._x_labels = list(zip(self.x_labels, x_pos))
        else:
            self._x_labels = None

        if self.include_x_axis:
            # Y Label
            self._box.ymin = min(self._min or 0, 0)
            self._box.ymax = max(self._max or 0, 0)
        else:
            self._box.ymin = self._min
            self._box.ymax = self._max

        y_pos = compute_scale(
            self._box.ymin, self._box.ymax, self.logarithmic, self.order_min
        ) if not self.y_labels else list(map(float, self.y_labels))

        self._y_labels = list(zip(map(self._format, y_pos), y_pos))

    def _plot(self):
        for index, serie in enumerate(self.series):
            self.line(self._serie(index), serie)

        for index, serie in enumerate(self.secondary_series, len(self.series)):
            self.line(self._serie(index), serie, True)

########NEW FILE########
__FILENAME__ = pie
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Pie chart

"""

from __future__ import division
from pygal.util import decorate
from pygal.graph.graph import Graph
from pygal.adapters import positive, none_to_zero
from math import pi


class Pie(Graph):
    """Pie graph"""

    _adapters = [positive, none_to_zero]

    def slice(self, serie_node, start_angle, serie, total):
        """Make a serie slice"""
        dual = self._len > 1 and not self._order == 1

        slices = self.svg.node(serie_node['plot'], class_="slices")
        serie_angle = 0
        total_perc = 0
        original_start_angle = start_angle
        if self.half_pie:
            center = ((self.width - self.margin.x) / 2.,
                      (self.height - self.margin.y) / 1.25)
        else:
            center = ((self.width - self.margin.x) / 2.,
                      (self.height - self.margin.y) / 2.)

        radius = min(center)
        for i, val in enumerate(serie.values):
            perc = val / total
            if self.half_pie:
                angle = 2 * pi * perc / 2
            else:
                angle = 2 * pi * perc
            serie_angle += angle
            val = '{0:.2%}'.format(perc)
            metadata = serie.metadata.get(i)
            slice_ = decorate(
                self.svg,
                self.svg.node(slices, class_="slice"),
                metadata)
            if dual:
                small_radius = radius * .9
                big_radius = radius
            else:
                big_radius = radius * .9
                small_radius = radius * serie.inner_radius

            self.svg.slice(
                serie_node, slice_, big_radius, small_radius,
                angle, start_angle, center, val)
            start_angle += angle
            total_perc += perc

        if dual:
            val = '{0:.2%}'.format(total_perc)
            self.svg.slice(serie_node,
                           self.svg.node(slices, class_="big_slice"),
                           radius * .9, 0, serie_angle,
                           original_start_angle, center, val)
        return serie_angle

    def _plot(self):
        total = sum(map(sum, map(lambda x: x.values, self.series)))
        if total == 0:
            return
        if self.half_pie:
            current_angle = 3*pi/2
        else:
            current_angle = 0

        for index, serie in enumerate(self.series):
            angle = self.slice(
                self._serie(index), current_angle, serie, total)
            current_angle += angle

########NEW FILE########
__FILENAME__ = pyramid
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Pyramid chart

"""

from pygal.graph.horizontal import HorizontalGraph
from pygal.graph.verticalpyramid import VerticalPyramid


class Pyramid(HorizontalGraph, VerticalPyramid):
    """Horizontal Pyramid graph"""

########NEW FILE########
__FILENAME__ = radar
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Radar chart

"""

from __future__ import division
from pygal.graph.line import Line
from pygal.adapters import positive, none_to_zero
from pygal.view import PolarView, PolarLogView
from pygal.util import deg, cached_property, compute_scale, majorize, cut
from math import cos, pi


class Radar(Line):
    """Kiviat graph"""

    _adapters = [positive, none_to_zero]

    def __init__(self, *args, **kwargs):
        self.x_pos = None
        self._rmax = None
        super(Radar, self).__init__(*args, **kwargs)

    def _fill(self, values):
        return values

    def _get_value(self, values, i):
        return self._format(values[i][0])

    @cached_property
    def _values(self):
        if self.interpolate:
            return [val[0] for serie in self.series
                    for val in serie.interpolated]
        else:
            return super(Line, self)._values

    def _set_view(self):
        if self.logarithmic:
            view_class = PolarLogView
        else:
            view_class = PolarView

        self.view = view_class(
            self.width - self.margin.x,
            self.height - self.margin.y,
            self._box)

    def _x_axis(self, draw_axes=True):
        if not self._x_labels:
            return

        axis = self.svg.node(self.nodes['plot'], class_="axis x web")
        format_ = lambda x: '%f %f' % x
        center = self.view((0, 0))
        r = self._rmax
        if self.x_labels_major:
            x_labels_major = self.x_labels_major
        elif self.x_labels_major_every:
            x_labels_major = [self._x_labels[i][0] for i in range(
                0, len(self._x_labels), self.x_labels_major_every)]
        elif self.x_labels_major_count:
            label_count = len(self._x_labels)
            major_count = self.x_labels_major_count
            if (major_count >= label_count):
                x_labels_major = [label[0] for label in self._x_labels]
            else:
                x_labels_major = [self._x_labels[
                    int(i * label_count / major_count)][0]
                    for i in range(major_count)]
        else:
            x_labels_major = []

        for label, theta in self._x_labels:
            major = label in x_labels_major
            if not (self.show_minor_x_labels or major):
                continue
            guides = self.svg.node(axis, class_='guides')
            end = self.view((r, theta))
            self.svg.node(
                guides, 'path',
                d='M%s L%s' % (format_(center), format_(end)),
                class_='%sline' % ('major ' if major else ''))
            r_txt = (1 - self._box.__class__.margin) * self._box.ymax
            pos_text = self.view((r_txt, theta))
            text = self.svg.node(
                guides, 'text',
                x=pos_text[0],
                y=pos_text[1],
                class_='major' if major else '')
            text.text = label
            angle = - theta + pi / 2
            if cos(angle) < 0:
                angle -= pi
            text.attrib['transform'] = 'rotate(%f %s)' % (
                deg(angle), format_(pos_text))

    def _y_axis(self, draw_axes=True):
        if not self._y_labels:
            return

        axis = self.svg.node(self.nodes['plot'], class_="axis y web")

        if self.y_labels_major:
            y_labels_major = self.y_labels_major
        elif self.y_labels_major_every:
            y_labels_major = [self._y_labels[i][1] for i in range(
                0, len(self._y_labels), self.y_labels_major_every)]
        elif self.y_labels_major_count:
            label_count = len(self._y_labels)
            major_count = self.y_labels_major_count
            if (major_count >= label_count):
                y_labels_major = [label[1] for label in self._y_labels]
            else:
                y_labels_major = [self._y_labels[
                    int(i * (label_count - 1) / (major_count - 1))][1]
                    for i in range(major_count)]
        else:
            y_labels_major = majorize(
                cut(self._y_labels, 1)
            )
        for label, r in reversed(self._y_labels):
            major = r in y_labels_major
            if not (self.show_minor_y_labels or major):
                continue
            guides = self.svg.node(axis, class_='guides')
            self.svg.line(
                guides, [self.view((r, theta)) for theta in self.x_pos],
                close=True,
                class_='%sguide line' % (
                    'major ' if major else ''))
            x, y = self.view((r, self.x_pos[0]))
            self.svg.node(
                guides, 'text',
                x=x - 5,
                y=y,
                class_='major' if major else ''
            ).text = label

    def _compute(self):
        delta = 2 * pi / self._len if self._len else 0
        x_pos = [.5 * pi + i * delta for i in range(self._len + 1)]
        for serie in self.all_series:
            serie.points = [
                (v, x_pos[i])
                for i, v in enumerate(serie.values)]
            if self.interpolate:
                extended_x_pos = (
                    [.5 * pi - delta] + x_pos)
                extended_vals = (serie.values[-1:] +
                                 serie.values)
                serie.interpolated = list(
                    map(tuple,
                        map(reversed,
                            self._interpolate(
                                extended_x_pos, extended_vals))))

        # x labels space
        self._box.margin *= 2
        self._rmin = self.zero
        self._rmax = self._max or 1
        self._box.set_polar_box(self._rmin, self._rmax)

        y_pos = compute_scale(
            self._rmin, self._rmax, self.logarithmic, self.order_min,
            max_scale=8
        ) if not self.y_labels else list(map(int, self.y_labels))

        self._x_labels = self.x_labels and list(zip(self.x_labels, x_pos))
        self._y_labels = list(zip(map(self._format, y_pos), y_pos))

        self.x_pos = x_pos
        self._self_close = True

########NEW FILE########
__FILENAME__ = stackedbar
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Stacked Bar chart

"""

from __future__ import division
from pygal.graph.bar import Bar
from pygal.util import compute_scale, swap, ident
from pygal.adapters import none_to_zero


class StackedBar(Bar):
    """Stacked Bar graph"""

    _adapters = [none_to_zero]

    def _get_separated_values(self, secondary=False):
        series = self.secondary_series if secondary else self.series
        transposed = list(zip(*[serie.values for serie in series]))
        positive_vals = [sum([
            val for val in vals
            if val is not None and val >= self.zero])
            for vals in transposed]
        negative_vals = [sum([
            val
            for val in vals
            if val is not None and val < self.zero])
            for vals in transposed]
        return positive_vals, negative_vals

    def _compute_box(self, positive_vals, negative_vals):
        self._box.ymin = negative_vals and min(min(negative_vals), self.zero)
        self._box.ymax = positive_vals and max(max(positive_vals), self.zero)

    def _compute(self):
        positive_vals, negative_vals = self._get_separated_values()
        self._compute_box(positive_vals, negative_vals)

        if self.logarithmic:
            positive_vals = list(filter(lambda x: x > 0, positive_vals))
            negative_vals = list(filter(lambda x: x > 0, negative_vals))

        positive_vals = positive_vals or [self.zero]
        negative_vals = negative_vals or [self.zero]

        x_pos = [
            x / self._len for x in range(self._len + 1)
        ] if self._len > 1 else [0, 1]  # Center if only one value

        self._points(x_pos)
        y_pos = compute_scale(
            self._box.ymin, self._box.ymax, self.logarithmic, self.order_min
        ) if not self.y_labels else list(map(float, self.y_labels))
        self._x_ranges = zip(x_pos, x_pos[1:])

        self._x_labels = self.x_labels and list(zip(self.x_labels, [
            sum(x_range) / 2 for x_range in self._x_ranges]))
        self._y_labels = list(zip(map(self._format, y_pos), y_pos))

        self.negative_cumulation = [0] * self._len
        self.positive_cumulation = [0] * self._len

        if self.secondary_series:
            positive_vals, negative_vals = self._get_separated_values(True)
            positive_vals = positive_vals or [self.zero]
            negative_vals = negative_vals or [self.zero]
            self.secondary_negative_cumulation = [0] * self._len
            self.secondary_positive_cumulation = [0] * self._len
            self._pre_compute_secondary(positive_vals, negative_vals)

    def _pre_compute_secondary(self, positive_vals, negative_vals):
        self._secondary_min = (negative_vals and min(
            min(negative_vals), self.zero)) or self.zero
        self._secondary_max = (positive_vals and max(
            max(positive_vals), self.zero)) or self.zero

    def _bar(self, parent, x, y, index, i, zero,
             secondary=False, rounded=False):
        if secondary:
            cumulation = (self.secondary_negative_cumulation
                          if y < self.zero else
                          self.secondary_positive_cumulation)
        else:
            cumulation = (self.negative_cumulation
                          if y < self.zero else
                          self.positive_cumulation)
        zero = cumulation[i]
        cumulation[i] = zero + y
        if zero == 0:
            zero = self.zero
            y -= self.zero
        y += zero

        width = (self.view.x(1) - self.view.x(0)) / self._len
        x, y = self.view((x, y))
        y = y or 0
        series_margin = width * self._series_margin
        x += series_margin
        width -= 2 * series_margin
        if self.secondary_series:
            width /= 2
            x += int(secondary) * width
            serie_margin = width * self._serie_margin
            x += serie_margin
            width -= 2 * serie_margin
        height = self.view.y(zero) - y
        r = rounded * 1 if rounded else 0
        self.svg.transposable_node(
            parent, 'rect',
            x=x, y=y, rx=r, ry=r, width=width, height=height,
            class_='rect reactive tooltip-trigger')
        transpose = swap if self.horizontal else ident
        return transpose((x + width / 2, y + height / 2))

########NEW FILE########
__FILENAME__ = stackedline
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Stacked Line chart

"""
from __future__ import division
from pygal.graph.line import Line
from pygal.adapters import none_to_zero


class StackedLine(Line):
    """Stacked Line graph"""

    _adapters = [none_to_zero]

    def __init__(self, *args, **kwargs):
        self._previous_line = None
        super(StackedLine, self).__init__(*args, **kwargs)

    def _fill(self, values):
        if not self._previous_line:
            self._previous_line = values
            return super(StackedLine, self)._fill(values)
        new_values = values + list(reversed(self._previous_line))
        self._previous_line = values
        return new_values

    def _points(self, x_pos):
        for series_group in (self.series, self.secondary_series):
            accumulation = [0] * self._len
            for serie in series_group:
                accumulation = list(map(sum, zip(accumulation, serie.values)))
                serie.points = [
                    (x_pos[i], v)
                    for i, v in enumerate(accumulation)]
                if serie.points and self.interpolate:
                    serie.interpolated = self._interpolate(x_pos, accumulation)
                else:
                    serie.interpolated = []

########NEW FILE########
__FILENAME__ = supranationalworldmap
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Supranational Worldmap chart

"""

from __future__ import division
from pygal.graph.worldmap import Worldmap
from pygal.i18n import SUPRANATIONAL
from pygal.util import cut, decorate
from lxml import etree
import os

with open(os.path.join(
        os.path.dirname(__file__),
        'worldmap.svg')) as file:
    MAP = file.read()


class SupranationalWorldmap(Worldmap):
    """SupranationalWorldmap graph"""
    def _plot(self):
        map = etree.fromstring(MAP)
        map.set('width', str(self.view.width))
        map.set('height', str(self.view.height))

        for i, serie in enumerate(self.series):
            safe_vals = list(filter(
                lambda x: x is not None, cut(serie.values, 1)))
            if not safe_vals:
                continue
            min_ = min(safe_vals)
            max_ = max(safe_vals)
            serie.values = self.replace_supranationals(serie.values)
            for j, (country_code, value) in enumerate(serie.values):
                if value is None:
                    continue
                if max_ == min_:
                    ratio = 1
                else:
                    ratio = .3 + .7 * (value - min_) / (max_ - min_)
                country = map.find('.//*[@id="%s"]' % country_code)
                if country is None:
                    continue
                cls = country.get('class', '').split(' ')
                cls.append('color-%d' % i)
                country.set('class', ' '.join(cls))
                country.set(
                    'style', 'fill-opacity: %f' % (
                        ratio))

                metadata = serie.metadata.get(j)
                if metadata:
                    parent = country.getparent()
                    node = decorate(self.svg, country, metadata)
                    if node != country:
                        country.remove(node)
                        index = parent.index(country)
                        parent.remove(country)
                        node.append(country)
                        parent.insert(index, node)

                last_node = len(country) > 0 and country[-1]
                if last_node is not None and last_node.tag == 'title':
                    title_node = last_node
                    text = title_node.text + '\n'
                else:
                    title_node = self.svg.node(country, 'title')
                    text = ''
                title_node.text = text + '[%s] %s: %d' % (
                    serie.title,
                    self.country_names[country_code], value)

        self.nodes['plot'].append(map)

    def replace_supranationals(self, values):
        """Replaces the values if it contains a supranational code."""
        for i, (code, value) in enumerate(values[:]):
            for suprakey in SUPRANATIONAL.keys():
                if suprakey == code:
                    values.extend(
                        [(country, value) for country in SUPRANATIONAL[code]])
                    values.remove((code, value))
        return values

########NEW FILE########
__FILENAME__ = verticalpyramid
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Pyramid chart

"""

from __future__ import division
from pygal.adapters import positive
from pygal.graph.stackedbar import StackedBar


class VerticalPyramid(StackedBar):
    """Pyramid graph"""

    _adapters = [positive]

    def _format(self, value):
        value = value and abs(value)
        return super(VerticalPyramid, self)._format(value)

    def _get_separated_values(self, secondary=False):
        series = self.secondary_series if secondary else self.series
        positive_vals = map(sum, zip(
            *[serie.safe_values
              for index, serie in enumerate(series)
              if index % 2]))
        negative_vals = map(sum, zip(
            *[serie.safe_values
              for index, serie in enumerate(series)
              if not index % 2]))
        return list(positive_vals), list(negative_vals)

    def _compute_box(self, positive_vals, negative_vals):
        self._box.ymax = max(max(positive_vals or [self.zero]),
                             max(negative_vals or [self.zero]))
        self._box.ymin = - self._box.ymax

    def _pre_compute_secondary(self, positive_vals, negative_vals):
        self._secondary_max = max(max(positive_vals), max(negative_vals))
        self._secondary_min = - self._secondary_max

    def _bar(self, parent, x, y, index, i, zero,
             secondary=False, rounded=False):
        if index % 2:
            y = -y
        return super(VerticalPyramid, self)._bar(
            parent, x, y, index, i, zero, secondary, rounded)

########NEW FILE########
__FILENAME__ = worldmap
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Worldmap chart

"""

from __future__ import division
from pygal.util import cut, cached_property, decorate
from pygal.graph.graph import Graph
from pygal.i18n import COUNTRIES
from lxml import etree
import os

with open(os.path.join(
        os.path.dirname(__file__),
        'worldmap.svg')) as file:
    MAP = file.read()


class Worldmap(Graph):
    """Worldmap graph"""
    _dual = True
    x_labels = list(COUNTRIES.keys())
    country_names = COUNTRIES

    @cached_property
    def countries(self):
        return [val[0]
                for serie in self.all_series
                for val in serie.values
                if val[0] is not None]

    @cached_property
    def _values(self):
        """Getter for series values (flattened)"""
        return [val[1]
                for serie in self.series
                for val in serie.values
                if val[1] is not None]

    def _plot(self):
        map = etree.fromstring(MAP)
        map.set('width', str(self.view.width))
        map.set('height', str(self.view.height))

        for i, serie in enumerate(self.series):
            safe_vals = list(filter(
                lambda x: x is not None, cut(serie.values, 1)))
            if not safe_vals:
                continue
            min_ = min(safe_vals)
            max_ = max(safe_vals)
            for j, (country_code, value) in enumerate(serie.values):
                if value is None:
                    continue
                if max_ == min_:
                    ratio = 1
                else:
                    ratio = .3 + .7 * (value - min_) / (max_ - min_)
                country = map.find('.//*[@id="%s"]' % country_code)
                if country is None:
                    continue
                cls = country.get('class', '').split(' ')
                cls.append('color-%d' % i)
                country.set('class', ' '.join(cls))
                country.set(
                    'style', 'fill-opacity: %f' % (
                        ratio))

                metadata = serie.metadata.get(j)
                if metadata:
                    parent = country.getparent()
                    node = decorate(self.svg, country, metadata)
                    if node != country:
                        country.remove(node)
                        index = parent.index(country)
                        parent.remove(country)
                        node.append(country)
                        parent.insert(index, node)

                last_node = len(country) > 0 and country[-1]
                if last_node is not None and last_node.tag == 'title':
                    title_node = last_node
                    text = title_node.text + '\n'
                else:
                    title_node = self.svg.node(country, 'title')
                    text = ''
                title_node.text = text + '[%s] %s: %s' % (
                    serie.title,
                    self.country_names[country_code], self._format(value))

        self.nodes['plot'].append(map)

########NEW FILE########
__FILENAME__ = xy
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
XY Line graph

"""

from __future__ import division
from pygal.util import compute_scale, cached_property
from pygal.graph.line import Line


class XY(Line):
    """XY Line graph"""
    _dual = True

    @cached_property
    def xvals(self):
        return [val[0]
                for serie in self.all_series
                for val in serie.values
                if val[0] is not None]

    @cached_property
    def yvals(self):
        return [val[1]
                for serie in self.series
                for val in serie.values
                if val[1] is not None]

    @cached_property
    def _min(self):
        return (self.range[0] if (self.range and self.range[0] is not None)
                else (min(self.yvals) if self.yvals else None))

    @cached_property
    def _max(self):
        return (self.range[1] if (self.range and self.range[1] is not None)
                else (max(self.yvals) if self.yvals else None))

    def _has_data(self):
        """Check if there is any data"""
        return sum(
            map(len, map(lambda s: s.safe_values, self.series))) != 0 and any((
                sum(map(abs, self.xvals)) != 0,
                sum(map(abs, self.yvals)) != 0))

    def _compute(self):
        if self.xvals:
            xmin = min(self.xvals)
            xmax = max(self.xvals)
            xrng = (xmax - xmin)
        else:
            xrng = None

        if self.yvals:
            ymin = self._min
            ymax = self._max

            if self.include_x_axis:
                ymin = min(ymin or 0, 0)
                ymax = max(ymax or 0, 0)

            yrng = (ymax - ymin)
        else:
            yrng = None

        for serie in self.all_series:
            serie.points = serie.values
            if self.interpolate and xrng:
                vals = list(zip(*sorted(
                    filter(lambda t: None not in t,
                           serie.points), key=lambda x: x[0])))
                serie.interpolated = self._interpolate(vals[0], vals[1])

        if self.interpolate and xrng:
            self.xvals = [val[0]
                          for serie in self.all_series
                          for val in serie.interpolated]
            self.yvals = [val[1]
                          for serie in self.series
                          for val in serie.interpolated]
            if self.xvals:
                xmin = min(self.xvals)
                xmax = max(self.xvals)
                xrng = (xmax - xmin)
            else:
                xrng = None

        if xrng:
            self._box.xmin, self._box.xmax = xmin, xmax
        if yrng:
            self._box.ymin, self._box.ymax = ymin, ymax

        x_pos = compute_scale(
            self._box.xmin, self._box.xmax, self.logarithmic, self.order_min)
        y_pos = compute_scale(
            self._box.ymin, self._box.ymax, self.logarithmic, self.order_min)

        self._x_labels = list(zip(map(self._format, x_pos), x_pos))
        self._y_labels = list(zip(map(self._format, y_pos), y_pos))

########NEW FILE########
__FILENAME__ = i18n
COUNTRIES = {
    'ad': 'Andorra',
    'ae': 'United Arab Emirates',
    'af': 'Afghanistan',
    'al': 'Albania',
    'am': 'Armenia',
    'ao': 'Angola',
    'aq': 'Antarctica',
    'ar': 'Argentina',
    'at': 'Austria',
    'au': 'Australia',
    'az': 'Azerbaijan',
    'ba': 'Bosnia and Herzegovina',
    'bd': 'Bangladesh',
    'be': 'Belgium',
    'bf': 'Burkina Faso',
    'bg': 'Bulgaria',
    'bh': 'Bahrain',
    'bi': 'Burundi',
    'bj': 'Benin',
    'bn': 'Brunei Darussalam',
    'bo': 'Bolivia, Plurinational State of',
    'br': 'Brazil',
    'bt': 'Bhutan',
    'bw': 'Botswana',
    'by': 'Belarus',
    'bz': 'Belize',
    'ca': 'Canada',
    'cd': 'Congo, the Democratic Republic of the',
    'cf': 'Central African Republic',
    'cg': 'Congo',
    'ch': 'Switzerland',
    'ci': "Cote d'Ivoire",
    'cl': 'Chile',
    'cm': 'Cameroon',
    'cn': 'China',
    'co': 'Colombia',
    'cr': 'Costa Rica',
    'cu': 'Cuba',
    'cv': 'Cape Verde',
    'cy': 'Cyprus',
    'cz': 'Czech Republic',
    'de': 'Germany',
    'dj': 'Djibouti',
    'dk': 'Denmark',
    'do': 'Dominican Republic',
    'dz': 'Algeria',
    'ec': 'Ecuador',
    'ee': 'Estonia',
    'eg': 'Egypt',
    'eh': 'Western Sahara',
    'er': 'Eritrea',
    'es': 'Spain',
    'et': 'Ethiopia',
    'fi': 'Finland',
    'fr': 'France',
    'ga': 'Gabon',
    'gb': 'United Kingdom',
    'ge': 'Georgia',
    'gf': 'French Guiana',
    'gh': 'Ghana',
    'gl': 'Greenland',
    'gm': 'Gambia',
    'gn': 'Guinea',
    'gq': 'Equatorial Guinea',
    'gr': 'Greece',
    'gt': 'Guatemala',
    'gu': 'Guam',
    'gw': 'Guinea-Bissau',
    'gy': 'Guyana',
    'hk': 'Hong Kong',
    'hn': 'Honduras',
    'hr': 'Croatia',
    'ht': 'Haiti',
    'hu': 'Hungary',
    'id': 'Indonesia',
    'ie': 'Ireland',
    'il': 'Israel',
    'in': 'India',
    'iq': 'Iraq',
    'ir': 'Iran, Islamic Republic of',
    'is': 'Iceland',
    'it': 'Italy',
    'jm': 'Jamaica',
    'jo': 'Jordan',
    'jp': 'Japan',
    'ke': 'Kenya',
    'kg': 'Kyrgyzstan',
    'kh': 'Cambodia',
    'kp': "Korea, Democratic People's Republic of",
    'kr': 'Korea, Republic of',
    'kw': 'Kuwait',
    'kz': 'Kazakhstan',
    'la': "Lao People's Democratic Republic",
    'lb': 'Lebanon',
    'li': 'Liechtenstein',
    'lk': 'Sri Lanka',
    'lr': 'Liberia',
    'ls': 'Lesotho',
    'lt': 'Lithuania',
    'lu': 'Luxembourg',
    'lv': 'Latvia',
    'ly': 'Libyan Arab Jamahiriya',
    'ma': 'Morocco',
    'mc': 'Monaco',
    'md': 'Moldova, Republic of',
    'me': 'Montenegro',
    'mg': 'Madagascar',
    'mk': 'Macedonia, the former Yugoslav Republic of',
    'ml': 'Mali',
    'mm': 'Myanmar',
    'mn': 'Mongolia',
    'mo': 'Macao',
    'mr': 'Mauritania',
    'mt': 'Malta',
    'mu': 'Mauritius',
    'mv': 'Maldives',
    'mw': 'Malawi',
    'mx': 'Mexico',
    'my': 'Malaysia',
    'mz': 'Mozambique',
    'na': 'Namibia',
    'ne': 'Niger',
    'ng': 'Nigeria',
    'ni': 'Nicaragua',
    'nl': 'Netherlands',
    'no': 'Norway',
    'np': 'Nepal',
    'nz': 'New Zealand',
    'om': 'Oman',
    'pa': 'Panama',
    'pe': 'Peru',
    'pg': 'Papua New Guinea',
    'ph': 'Philippines',
    'pk': 'Pakistan',
    'pl': 'Poland',
    'pr': 'Puerto Rico',
    'ps': 'Palestine, State of',
    'pt': 'Portugal',
    'py': 'Paraguay',
    're': 'Reunion',
    'ro': 'Romania',
    'rs': 'Serbia',
    'ru': 'Russian Federation',
    'rw': 'Rwanda',
    'sa': 'Saudi Arabia',
    'sc': 'Seychelles',
    'sd': 'Sudan',
    'se': 'Sweden',
    'sg': 'Singapore',
    'sh': 'Saint Helena, Ascension and Tristan da Cunha',
    'si': 'Slovenia',
    'sk': 'Slovakia',
    'sl': 'Sierra Leone',
    'sm': 'San Marino',
    'sn': 'Senegal',
    'so': 'Somalia',
    'sr': 'Suriname',
    'st': 'Sao Tome and Principe',
    'sv': 'El Salvador',
    'sy': 'Syrian Arab Republic',
    'sz': 'Swaziland',
    'td': 'Chad',
    'tg': 'Togo',
    'th': 'Thailand',
    'tj': 'Tajikistan',
    'tl': 'Timor-Leste',
    'tm': 'Turkmenistan',
    'tn': 'Tunisia',
    'tr': 'Turkey',
    'tw': 'Taiwan, Province of China',
    'tz': 'Tanzania, United Republic of',
    'ua': 'Ukraine',
    'ug': 'Uganda',
    'us': 'United States',
    'uy': 'Uruguay',
    'uz': 'Uzbekistan',
    'va': 'Holy See (Vatican City State)',
    've': 'Venezuela, Bolivarian Republic of',
    'vn': 'Viet Nam',
    'ye': 'Yemen',
    'yt': 'Mayotte',
    'za': 'South Africa',
    'zm': 'Zambia',
    'zw': 'Zimbabwe'
}

EUROPE = ['at', 'be', 'bg', 'hr', 'cy', 'cz', 'dk', 'ee', 'fi', 'fr', 'de',
          'gr', 'hu', 'ie', 'it', 'lv', 'lt', 'lu', 'mt', 'nl', 'pl', 'pt',
          'ro', 'sk', 'si', 'es', 'se', 'gb']

EUR = ['be', 'de', 'ie', 'gr', 'es', 'fr', 'it', 'cy', 'lu', 'mt', 'nl', 'at',
       'pt', 'si', 'sk', 'fi', 'ee']

OECD = ['au', 'at', 'be', 'ca', 'cl', 'cz', 'dk', 'ee', 'fi', 'fr', 'de', 'gr',
        'hu', 'is', 'ie', 'il', 'it', 'jp', 'kr', 'lu', 'mx', 'nl', 'nz', 'no',
        'pl', 'pt', 'sk', 'si', 'es', 'se', 'ch', 'tr', 'gb', 'us']

NAFTA = ['ca', 'mx', 'us']


SUPRANATIONAL = {'europe': EUROPE, 'oecd': OECD, 'nafta': NAFTA, 'eur': EUR}


def set_countries(countries, clear=False):
    if clear:
        COUNTRIES.clear()
    COUNTRIES.update(countries)

########NEW FILE########
__FILENAME__ = interpolate
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Interpolation

"""
from __future__ import division
from math import sin


def quadratic_interpolate(x, y, precision=250, **kwargs):
    n = len(x) - 1
    delta_x = [x2 - x1 for x1, x2 in zip(x, x[1:])]
    delta_y = [y2 - y1 for y1, y2 in zip(y, y[1:])]
    slope = [delta_y[i] / delta_x[i] if delta_x[i] else 1 for i in range(n)]

    # Quadratic spline: a + bx + cx²
    a = y
    b = [0] * (n + 1)
    c = [0] * (n + 1)

    for i in range(1, n):
        b[i] = 2 * slope[i - 1] - b[i - 1]

    c = [(slope[i] - b[i]) / delta_x[i] if delta_x[i] else 0 for i in range(n)]

    for i in range(n + 1):
        yield x[i], a[i]
        if i == n or delta_x[i] == 0:
            continue
        for s in range(1, precision):
            X = s * delta_x[i] / precision
            X2 = X * X
            yield x[i] + X, a[i] + b[i] * X + c[i] * X2


def cubic_interpolate(x, y, precision=250, **kwargs):
    n = len(x) - 1
    # Spline equation is a + bx + cx² + dx³
    # ie: Spline part i equation is a[i] + b[i]x + c[i]x² + d[i]x³
    a = y
    b = [0] * (n + 1)
    c = [0] * (n + 1)
    d = [0] * (n + 1)
    m = [0] * (n + 1)
    z = [0] * (n + 1)

    h = [x2 - x1 for x1, x2 in zip(x, x[1:])]
    k = [a2 - a1 for a1, a2 in zip(a, a[1:])]
    g = [k[i] / h[i] if h[i] else 1 for i in range(n)]

    for i in range(1, n):
        j = i - 1
        l = 1 / (2 * (x[i + 1] - x[j]) - h[j] * m[j]) if x[i + 1] - x[j] else 0
        m[i] = h[i] * l
        z[i] = (3 * (g[i] - g[j]) - h[j] * z[j]) * l

    for j in reversed(range(n)):
        if h[j] == 0:
            continue
        c[j] = z[j] - (m[j] * c[j + 1])
        b[j] = g[j] - (h[j] * (c[j + 1] + 2 * c[j])) / 3
        d[j] = (c[j + 1] - c[j]) / (3 * h[j])

    for i in range(n + 1):
        yield x[i], a[i]
        if i == n or h[i] == 0:
            continue
        for s in range(1, precision):
            X = s * h[i] / precision
            X2 = X * X
            X3 = X2 * X
            yield x[i] + X, a[i] + b[i] * X + c[i] * X2 + d[i] * X3


def hermite_interpolate(x, y, precision=250,
                        type='cardinal', c=None, b=None, t=None):
    n = len(x) - 1
    m = [1] * (n + 1)
    w = [1] * (n + 1)
    delta_x = [x2 - x1 for x1, x2 in zip(x, x[1:])]
    if type == 'catmull_rom':
        type = 'cardinal'
        c = 0
    if type == 'finite_difference':
        for i in range(1, n):
            m[i] = w[i] = .5 * (
                (y[i + 1] - y[i]) / (x[i + 1] - x[i]) +
                (y[i] - y[i - 1]) / (
                    x[i] - x[i - 1])
            ) if x[i + 1] - x[i] and x[i] - x[i - 1] else 0

    elif type == 'kochanek_bartels':
        c = c or 0
        b = b or 0
        t = t or 0
        for i in range(1, n):
            m[i] = .5 * ((1 - t) * (1 + b) * (1 + c) * (y[i] - y[i - 1]) +
                         (1 - t) * (1 - b) * (1 - c) * (y[i + 1] - y[i]))
            w[i] = .5 * ((1 - t) * (1 + b) * (1 - c) * (y[i] - y[i - 1]) +
                         (1 - t) * (1 - b) * (1 + c) * (y[i + 1] - y[i]))

    if type == 'cardinal':
        c = c or 0
        for i in range(1, n):
            m[i] = w[i] = (1 - c) * (
                y[i + 1] - y[i - 1]) / (
                    x[i + 1] - x[i - 1]) if x[i + 1] - x[i - 1] else 0

    def p(i, x_):
        t = (x_ - x[i]) / delta_x[i]
        t2 = t * t
        t3 = t2 * t

        h00 = 2 * t3 - 3 * t2 + 1
        h10 = t3 - 2 * t2 + t
        h01 = - 2 * t3 + 3 * t2
        h11 = t3 - t2

        return (h00 * y[i] +
                h10 * m[i] * delta_x[i] +
                h01 * y[i + 1] +
                h11 * w[i + 1] * delta_x[i])

    for i in range(n + 1):
        yield x[i], y[i]
        if i == n or delta_x[i] == 0:
            continue
        for s in range(1, precision):
            X = x[i] + s * delta_x[i] / precision
            yield X, p(i, X)


def lagrange_interpolate(x, y, precision=250, **kwargs):
    n = len(x) - 1
    delta_x = [x2 - x1 for x1, x2 in zip(x, x[1:])]
    for i in range(n + 1):
        yield x[i], y[i]
        if i == n or delta_x[i] == 0:
            continue

        for s in range(1, precision):
            X = x[i] + s * delta_x[i] / precision
            s = 0
            for k in range(n + 1):
                p = 1
                for m in range(n + 1):
                    if m == k:
                        continue
                    if x[k] - x[m]:
                        p *= (X - x[m]) / (x[k] - x[m])
                s += y[k] * p
            yield X, s


def trigonometric_interpolate(x, y, precision=250, **kwargs):
    """As per http://en.wikipedia.org/wiki/Trigonometric_interpolation"""
    n = len(x) - 1
    delta_x = [x2 - x1 for x1, x2 in zip(x, x[1:])]
    for i in range(n + 1):
        yield x[i], y[i]
        if i == n or delta_x[i] == 0:
            continue

        for s in range(1, precision):
            X = x[i] + s * delta_x[i] / precision
            s = 0
            for k in range(n + 1):
                p = 1
                for m in range(n + 1):
                    if m == k:
                        continue
                    if sin(0.5 * (x[k] - x[m])):
                        p *= sin(0.5 * (X - x[m])) / sin(0.5 * (x[k] - x[m]))
                s += y[k] * p
            yield X, s

"""
These functions takes two lists of points x and y and
returns an iterator over the interpolation between all these points
with `precision` interpolated points between each of them

"""
INTERPOLATIONS = {
    'quadratic': quadratic_interpolate,
    'cubic': cubic_interpolate,
    'hermite': hermite_interpolate,
    'lagrange': lagrange_interpolate,
    'trigonometric': trigonometric_interpolate
}


if __name__ == '__main__':
    from pygal import XY
    points = [(.1, 7), (.3, -4), (.6, 10), (.9, 8), (1.4, 3), (1.7, 1)]
    xy = XY(show_dots=False)
    xy.add('normal', points)
    xy.add('quadratic', quadratic_interpolate(*zip(*points)))
    xy.add('cubic', cubic_interpolate(*zip(*points)))
    xy.render_in_browser()

########NEW FILE########
__FILENAME__ = serie
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Little helpers for series

"""
from pygal.util import cached_property


class Serie(object):
    """Serie containing title, values and the graph serie index"""
    def __init__(self, title, values, config, metadata=None):
        self.title = title
        self.values = values
        self.config = config
        self.__dict__.update(config.to_dict())
        self.metadata = metadata or {}

    @cached_property
    def safe_values(self):
        return list(filter(lambda x: x is not None, self.values))

########NEW FILE########
__FILENAME__ = style
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Charts styling
"""
from __future__ import division
from pygal.util import cycle_fill
from pygal import colors
from pygal.colors import darken, lighten
import sys


class Style(object):
    """Styling class containing colors for the css generation"""
    def __init__(
            self,
            background='black',
            plot_background='#111',
            foreground='#999',
            foreground_light='#eee',
            foreground_dark='#555',
            opacity='.8',
            opacity_hover='.9',
            transition='250ms',
            colors=(
                '#ff5995', '#b6e354', '#feed6c', '#8cedff', '#9e6ffe',
                '#899ca1', '#f8f8f2', '#bf4646', '#516083', '#f92672',
                '#82b414', '#fd971f', '#56c2d6', '#808384', '#8c54fe',
                '#465457')):
        self.background = background
        self.plot_background = plot_background
        self.foreground = foreground
        self.foreground_light = foreground_light
        self.foreground_dark = foreground_dark
        self.opacity = opacity
        self.opacity_hover = opacity_hover
        self.transition = transition
        self.colors = colors

    def get_colors(self, prefix):
        """Get the css color list"""

        def color(tupl):
            """Make a color css"""
            return ((
                '%s.color-{0}, %s.color-{0} a:visited {{\n'
                '  stroke: {1};\n'
                '  fill: {1};\n'
                '}}\n') % (prefix, prefix)).format(*tupl)

        return '\n'.join(map(color, enumerate(
            cycle_fill(self.colors, max(len(self.colors), 16)))))

    def to_dict(self):
        config = {}
        for attr in dir(self):
            if not attr.startswith('__'):
                value = getattr(self, attr)
                if not hasattr(value, '__call__'):
                    config[attr] = value
        return config


DefaultStyle = Style(opacity_hover='.4', opacity='.8')


LightStyle = Style(
    background='white',
    plot_background='rgba(0, 0, 255, 0.1)',
    foreground='rgba(0, 0, 0, 0.7)',
    foreground_light='rgba(0, 0, 0, 0.9)',
    foreground_dark='rgba(0, 0, 0, 0.5)',
    colors=('#242424', '#9f6767', '#92ac68',
            '#d0d293', '#9aacc3', '#bb77a4',
            '#77bbb5', '#777777'))


NeonStyle = Style(
    opacity='.1',
    opacity_hover='.75',
    transition='1s ease-out')


CleanStyle = Style(
    background='transparent',
    plot_background='rgba(240, 240, 240, 0.7)',
    foreground='rgba(0, 0, 0, 0.9)',
    foreground_light='rgba(0, 0, 0, 0.9)',
    foreground_dark='rgba(0, 0, 0, 0.5)',
    colors=(
        'rgb(12,55,149)', 'rgb(117,38,65)', 'rgb(228,127,0)', 'rgb(159,170,0)',
        'rgb(149,12,12)'))


solarized_colors = (
    '#b58900', '#cb4b16', '#dc322f', '#d33682',
    '#6c71c4', '#268bd2', '#2aa198', '#859900')


DarkSolarizedStyle = Style(
    background='#073642',
    plot_background='#002b36',
    foreground='#839496',
    foreground_light='#fdf6e3',
    foreground_dark='#657b83',
    opacity='.66',
    opacity_hover='.9',
    transition='500ms ease-in',
    colors=solarized_colors)


LightSolarizedStyle = Style(
    background='#fdf6e3',
    plot_background='#eee8d5',
    foreground='#657b83',
    foreground_light='#073642',
    foreground_dark='#073642',
    opacity='.6',
    opacity_hover='.9',
    transition='500ms ease-in',
    colors=solarized_colors)


RedBlueStyle = Style(
    background=lighten('#e6e7e9', 7),
    plot_background=lighten('#e6e7e9', 10),
    foreground='rgba(0, 0, 0, 0.9)',
    foreground_light='rgba(0, 0, 0, 0.9)',
    foreground_dark='rgba(0, 0, 0, 0.5)',
    opacity='.6',
    opacity_hover='.9',
    colors=(
        '#d94e4c', '#e5884f', '#39929a',
        lighten('#d94e4c', 10),  darken('#39929a', 15), lighten('#e5884f', 17),
        darken('#d94e4c', 10), '#234547'))


LightColorizedStyle = Style(
    background='#f8f8f8',
    plot_background=lighten('#f8f8f8', 3),
    foreground='#333',
    foreground_light='#666',
    foreground_dark='rgba(0, 0 , 0, 0.5)',
    opacity='.5',
    opacity_hover='.9',
    transition='250ms ease-in',
    colors=(
        '#fe9592', '#534f4c', '#3ac2c0', '#a2a7a1',
        darken('#fe9592', 15), lighten('#534f4c', 15), lighten('#3ac2c0', 15),
        lighten('#a2a7a1', 15), lighten('#fe9592', 15), darken('#3ac2c0', 10)))


DarkColorizedStyle = Style(
    background=darken('#3a2d3f', 5),
    plot_background=lighten('#3a2d3f', 2),
    foreground='rgba(255, 255, 255, 0.9)',
    foreground_light='rgba(255, 255, 255, 0.9)',
    foreground_dark='rgba(255, 255 , 255, 0.5)',
    opacity='.2',
    opacity_hover='.7',
    transition='250ms ease-in',
    colors=(
        '#c900fe', '#01b8fe', '#59f500', '#ff00e4', '#f9fa00',
        darken('#c900fe', 20), darken('#01b8fe', 15), darken('#59f500', 20),
        darken('#ff00e4', 15), lighten('#f9fa00', 20)))


TurquoiseStyle = Style(
    background=darken('#1b8088', 15),
    plot_background=darken('#1b8088', 17),
    foreground='rgba(255, 255, 255, 0.9)',
    foreground_light='rgba(255, 255, 255, 0.9)',
    foreground_dark='rgba(255, 255 , 255, 0.5)',
    opacity='.5',
    opacity_hover='.9',
    transition='250ms ease-in',
    colors=(
        '#93d2d9', '#ef940f', '#8C6243', '#fff',
        darken('#93d2d9', 20),  lighten('#ef940f', 15),
        lighten('#8c6243', 15), '#1b8088'))


LightGreenStyle = Style(
    background=lighten('#f3f3f3', 3),
    plot_background='#fff',
    foreground='#333333',
    foreground_light='#666',
    foreground_dark='#222222',
    opacity='.5',
    opacity_hover='.9',
    transition='250ms ease-in',
    colors=(
        '#7dcf30', '#247fab', lighten('#7dcf30', 10), '#ccc',
        darken('#7dcf30', 15), '#ddd', lighten('#247fab', 10),
        darken('#247fab', 15)))


DarkGreenStyle = Style(
    background=darken('#251e01', 3),
    plot_background=darken('#251e01', 1),
    foreground='rgba(255, 255, 255, 0.9)',
    foreground_light='rgba(255, 255, 255, 0.9)',
    foreground_dark='rgba(255, 255, 255, 0.6)',
    opacity='.6',
    opacity_hover='.9',
    transition='250ms ease-in',
    colors=(
        '#adde09', '#6e8c06', '#4a5e04', '#fcd202', '#C1E34D',
        lighten('#fcd202', 25)))


DarkGreenBlueStyle = Style(
    background='#000',
    plot_background=lighten('#000', 8),
    foreground='rgba(255, 255, 255, 0.9)',
    foreground_light='rgba(255, 255, 255, 0.9)',
    foreground_dark='rgba(255, 255, 255, 0.6)',
    opacity='.55',
    opacity_hover='.9',
    transition='250ms ease-in',
    colors=(lighten('#34B8F7', 15), '#7dcf30', '#247fab',
            darken('#7dcf30', 10), lighten('#247fab', 10),
            lighten('#7dcf30', 10), darken('#247fab', 10), '#fff'))


BlueStyle = Style(
    background=darken('#f8f8f8', 3),
    plot_background='#f8f8f8',
    foreground='rgba(0, 0, 0, 0.9)',
    foreground_light='rgba(0, 0, 0, 0.9)',
    foreground_dark='rgba(0, 0, 0, 0.6)',
    opacity='.5',
    opacity_hover='.9',
    transition='250ms ease-in',
    colors=(
        '#00b2f0', '#43d9be', '#0662ab', darken('#00b2f0', 20),
        lighten('#43d9be', 20), lighten('#7dcf30', 10), darken('#0662ab', 15),
        '#ffd541', '#7dcf30', lighten('#00b2f0', 15), darken('#ffd541', 20)))


SolidColorStyle = Style(
    background='#FFFFFF',
    plot_background='#FFFFFF',
    foreground='#000000',
    foreground_light='#000000',
    foreground_dark='#828282',
    opacity='.8',
    opacity_hover='.9',
    transition='400ms ease-in',
    colors=('#FF9900', '#DC3912', '#4674D1', '#109618', '#990099',
            '#0099C6', '#DD4477', '#74B217', '#B82E2E', '#316395', '#994499'))


styles = {'default': DefaultStyle,
          'light': LightStyle,
          'neon': NeonStyle,
          'clean': CleanStyle,
          'light_red_blue': RedBlueStyle,
          'dark_solarized': DarkSolarizedStyle,
          'light_solarized': LightSolarizedStyle,
          'dark_colorized': DarkColorizedStyle,
          'light_colorized': LightColorizedStyle,
          'turquoise': TurquoiseStyle,
          'green': LightGreenStyle,
          'dark_green': DarkGreenStyle,
          'dark_green_blue': DarkGreenBlueStyle,
          'blue': BlueStyle,
          'solid_color': SolidColorStyle}


parametric_styles = {}
for op in ('lighten', 'darken', 'saturate', 'desaturate', 'rotate'):
    name = op.capitalize() + 'Style'

    def get_style_for(op_name):
        operation = getattr(colors, op_name)

        def parametric_style(color, step=10, max_=None, base_style=None,
                             **kwargs):
            if max_ is None:
                violency = {
                    'darken': 50,
                    'lighten': 50,
                    'saturate': 100,
                    'desaturate': 100,
                    'rotate': 360
                }
                max__ = violency[op_name]
            else:
                max__ = max_

            def modifier(index):
                percent = max__ * index / (step - 1)
                return operation(color, percent)

            colors = list(map(modifier, range(0, max(2, step))))

            if base_style is None:
                return Style(colors=colors, **kwargs)
            opts = dict(base_style.__dict__)
            opts.update({'colors': colors})
            opts.update(kwargs)
            return Style(**opts)

        return parametric_style

    style = get_style_for(op)
    parametric_styles[name] = style
    setattr(sys.modules[__name__], name, style)

########NEW FILE########
__FILENAME__ = svg
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Svg helper

"""

from __future__ import division
from pygal._compat import to_str, u
import io
import os
import json
from datetime import date, datetime
from numbers import Number
from lxml import etree
from math import cos, sin, pi
from pygal.util import template, coord_format, minify_css
from pygal import __version__


class Svg(object):
    """Svg object"""
    ns = 'http://www.w3.org/2000/svg'

    def __init__(self, graph):
        self.graph = graph
        if not graph.no_prefix:
            self.id = '#chart-%s ' % graph.uuid
        else:
            self.id = ''
        self.processing_instructions = [
            etree.PI(u('xml'), u("version='1.0' encoding='utf-8'"))]
        self.root = etree.Element(
            "{%s}svg" % self.ns,
            nsmap={
                None: self.ns,
                'xlink': 'http://www.w3.org/1999/xlink',
            })
        self.root.attrib['id'] = self.id.lstrip('#').rstrip()
        self.root.attrib['class'] = 'pygal-chart'
        self.root.append(
            etree.Comment(u(
                'Generated with pygal %s ©Kozea 2011-2014 on %s' % (
                    __version__, date.today().isoformat()))))
        self.root.append(etree.Comment(u('http://pygal.org')))
        self.root.append(etree.Comment(u('http://github.com/Kozea/pygal')))
        self.defs = self.node(tag='defs')
        self.title = self.node(tag='title')
        self.title.text = graph.title or 'Pygal'

    def add_styles(self):
        """Add the css to the svg"""
        colors = self.graph.config.style.get_colors(self.id)
        all_css = []
        for css in ['base.css'] + list(self.graph.css):
            if '://' in css:
                self.processing_instructions.append(
                    etree.PI(
                        u('xml-stylesheet'), u('href="%s"' % css)))
            else:
                if css.startswith('inline:'):
                    css_text = css[len('inline:'):]
                else:
                    if not os.path.exists(css):
                        css = os.path.join(
                            os.path.dirname(__file__), 'css', css)
                    with io.open(css, encoding='utf-8') as f:
                        css_text = template(
                            f.read(),
                            style=self.graph.config.style,
                            colors=colors,
                            font_sizes=self.graph.config.font_sizes(),
                            id=self.id)
                if not self.graph.pretty_print:
                    css_text = minify_css(css_text)
                all_css.append(css_text)
        self.node(
            self.defs, 'style', type='text/css').text = '\n'.join(all_css)

    def add_scripts(self):
        """Add the js to the svg"""
        common_script = self.node(self.defs, 'script', type='text/javascript')
        common_script.text = " = ".join(
            ("window.config", json.dumps(
                self.graph.config.to_dict(),
                default=lambda o: (
                    o.isoformat() if isinstance(o, (datetime, date))
                    else json.JSONEncoder().default(o))
            )))

        for js in self.graph.js:
            if '://' in js:
                self.node(
                    self.defs, 'script', type='text/javascript', href=js)
            else:
                script = self.node(self.defs, 'script', type='text/javascript')
                with io.open(js, encoding='utf-8') as f:
                    script.text = f.read()

    def node(self, parent=None, tag='g', attrib=None, **extras):
        """Make a new svg node"""
        if parent is None:
            parent = self.root
        attrib = attrib or {}
        attrib.update(extras)

        def in_attrib_and_number(key):
            return key in attrib and isinstance(attrib[key], Number)

        for pos, dim in (('x', 'width'), ('y', 'height')):
            if in_attrib_and_number(dim) and attrib[dim] < 0:
                attrib[dim] = - attrib[dim]
                if in_attrib_and_number(pos):
                    attrib[pos] = attrib[pos] - attrib[dim]

        for key, value in dict(attrib).items():
            if value is None:
                del attrib[key]

            attrib[key] = to_str(value)
            if key.endswith('_'):
                attrib[key.rstrip('_')] = attrib[key]
                del attrib[key]
            elif key == 'href':
                attrib['{http://www.w3.org/1999/xlink}' + key] = attrib[key]
                del attrib[key]
        return etree.SubElement(parent, tag, attrib)

    def transposable_node(self, parent=None, tag='g', attrib=None, **extras):
        """Make a new svg node which can be transposed if horizontal"""
        if self.graph.horizontal:
            for key1, key2 in (('x', 'y'), ('width', 'height')):
                attr1 = extras.get(key1, None)
                attr2 = extras.get(key2, None)
                extras[key1], extras[key2] = attr2, attr1
        return self.node(parent, tag, attrib, **extras)

    def line(self, node, coords, close=False, **kwargs):
        """Draw a svg line"""
        line_len = len(coords)
        if line_len < 2:
            return
        root = 'M%s L%s Z' if close else 'M%s L%s'
        origin_index = 0
        while origin_index < line_len and None in coords[origin_index]:
            origin_index += 1
        if origin_index == line_len:
            return
        origin = coord_format(coords[origin_index])
        line = ' '.join([coord_format(c)
                         for c in coords[origin_index + 1:]
                         if None not in c])
        self.node(node, 'path',
                  d=root % (origin, line), **kwargs)

    def slice(
            self, serie_node, node, radius, small_radius,
            angle, start_angle, center, val):
        """Draw a pie slice"""
        project = lambda rho, alpha: (
            rho * sin(-alpha), rho * cos(-alpha))
        diff = lambda x, y: (x[0] - y[0], x[1] - y[1])
        fmt = lambda x: '%f %f' % x
        get_radius = lambda r: fmt(tuple([r] * 2))
        absolute_project = lambda rho, theta: fmt(
            diff(center, project(rho, theta)))

        if angle == 2 * pi:
            self.node(node, 'circle',
                      cx=center[0],
                      cy=center[1],
                      r=radius,
                      class_='slice reactive tooltip-trigger')
        elif angle > 0:
            to = [absolute_project(radius, start_angle),
                  absolute_project(radius, start_angle + angle),
                  absolute_project(small_radius, start_angle + angle),
                  absolute_project(small_radius, start_angle)]
            self.node(node, 'path',
                      d='M%s A%s 0 %d 1 %s L%s A%s 0 %d 0 %s z' % (
                          to[0],
                          get_radius(radius), int(angle > pi), to[1],
                          to[2],
                          get_radius(small_radius), int(angle > pi), to[3]),
                      class_='slice reactive tooltip-trigger')
        x, y = diff(center, project(
            (radius + small_radius) / 2, start_angle + angle / 2))

        self.graph._tooltip_data(node, val, x, y, classes="centered")
        if angle >= 0.3:  # 0.3 radians is about 17 degrees
            self.graph._static_value(serie_node, val, x, y)

    def pre_render(self):
        """Last things to do before rendering"""
        self.add_styles()
        self.add_scripts()
        self.root.set(
            'viewBox', '0 0 %d %d' % (self.graph.width, self.graph.height))
        if self.graph.explicit_size:
            self.root.set('width', str(self.graph.width))
            self.root.set('height', str(self.graph.height))

    def draw_no_data(self):
        no_data = self.node(self.graph.nodes['text_overlay'], 'text',
                            x=self.graph.view.width / 2,
                            y=self.graph.view.height / 2,
                            class_='no_data')
        no_data.text = self.graph.no_data_text

    def render(self, is_unicode=False, pretty_print=False):
        """Last thing to do before rendering"""
        for f in self.graph.xml_filters:
            self.root = f(self.root)
        svg = etree.tostring(
            self.root, pretty_print=pretty_print,
            xml_declaration=False,
            encoding='utf-8')
        if not self.graph.disable_xml_declaration:
            svg = b'\n'.join(
                [etree.tostring(
                    pi, encoding='utf-8', pretty_print=pretty_print)
                 for pi in self.processing_instructions]
            ) + b'\n' + svg
        if self.graph.disable_xml_declaration or is_unicode:
            svg = svg.decode('utf-8')
        return svg

########NEW FILE########
__FILENAME__ = table
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Table maker

"""

from pygal.graph.base import BaseGraph
from pygal.util import template
from lxml.html import builder, tostring
import uuid


class HTML(object):
    def __getattribute__(self, attr):
        return getattr(builder, attr.upper())


class Table(BaseGraph):
    _dual = None

    def __init__(self, config, series, secondary_series, uuid, xml_filters):
        "Init the table"
        self.uuid = uuid
        self.series = series or []
        self.secondary_series = secondary_series or []
        self.xml_filters = xml_filters or []
        self.__dict__.update(config.to_dict())
        self.config = config

    def render(self, total=False, transpose=False, style=False):
        html = HTML()
        attrs = {}

        if style:
            attrs['id'] = 'table-%s' % uuid.uuid4()

        table = []

        _ = lambda x: x if x is not None else ''

        if self.x_labels:
            labels = list(self.x_labels)
            if len(labels) < self._len:
                labels += [None] * (self._len - len(labels))
            if len(labels) > self._len:
                labels = labels[:self._len]
            table.append(labels)

        if total:
            if len(table):
                table[0].append('Total')
            else:
                table.append([None] * (self._len + 1) + ['Total'])
            acc = [0] * (self._len + 1)

        for i, serie in enumerate(self.series):
            row = [serie.title]
            if total:
                sum_ = 0
            for j, value in enumerate(serie.values):
                if total:
                    acc[j] += value
                    sum_ += value
                row.append(self._format(value))
            if total:
                acc[-1] += sum_
                row.append(self._format(sum_))
            table.append(row)

        width = self._len + 1
        if total:
            width += 1
            table.append(['Total'])
            for val in acc:
                table[-1].append(self._format(val))

        # Align values
        len_ = max([len(r) for r in table] or [0])

        for i, row in enumerate(table[:]):
            len_ = len(row)
            if len_ < width:
                table[i] = row + [None] * (width - len_)

        if not transpose:
            table = list(zip(*table))

        thead = []
        tbody = []
        tfoot = []

        if not transpose or self.x_labels:
            # There's always series title but not always x_labels
            thead = [table[0]]
            tbody = table[1:]
        else:
            tbody = table

        parts = []
        if thead:
            parts.append(
                html.thead(
                    *[html.tr(
                        *[html.th(_(col)) for col in r]
                    ) for r in thead]
                )
            )
        if tbody:
            parts.append(
                html.tbody(
                    *[html.tr(
                        *[html.td(_(col)) for col in r]
                    ) for r in tbody]
                )
            )
        if tfoot:
            parts.append(
                html.tfoot(
                    *[html.tr(
                        *[html.th(_(col)) for col in r]
                    ) for r in tfoot]
                )
            )

        table = tostring(
            html.table(
                *parts, **attrs
            )
        )
        if style:
            if style is True:
                css = '''
                  #{{ id }}{
                    width: 100%;
                  }
                  #{{ id }} tbody tr:nth-child(odd) td {
                    background-color: #f9f9f9;
                  }
                '''
            else:
                css = style
            table = tostring(html.style(
                template(css, **attrs),
                scoped='scoped')) + table
        if self.disable_xml_declaration:
            table = table.decode('utf-8')
        return table

########NEW FILE########
__FILENAME__ = test_bar
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
from pygal import Bar


def test_simple_bar():
    bar = Bar()
    rng = [-3, -32, -39]
    bar.add('test1', rng)
    bar.add('test2', map(abs, rng))
    bar.x_labels = map(str, rng)
    bar.title = "Bar test"
    q = bar.render_pyquery()
    assert len(q(".axis.x")) == 1
    assert len(q(".axis.y")) == 1
    assert len(q(".legend")) == 2
    assert len(q(".plot .series rect")) == 2 * 3

########NEW FILE########
__FILENAME__ = test_box
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
from pygal.graph.box import Box
from pygal import Box as ghostedBox


def test_quartiles():
    a = [-2.0, 3.0, 4.0, 5.0, 8.0]  # odd test data
    q0, q1, q2, q3, q4 = Box._box_points(a)

    assert q1 == 7.0 / 4.0
    assert q2 == 4.0
    assert q3 == 23 / 4.0
    assert q0 == 7.0 / 4.0 - 6.0  # q1 - 1.5 * iqr
    assert q4 == 23 / 4.0 + 6.0  # q3 + 1.5 * iqr

    b = [1.0, 4.0, 6.0, 8.0]  # even test data
    q0, q1, q2, q3, q4 = Box._box_points(b)

    assert q2 == 5.0

    c = [2.0, None, 4.0, 6.0, None]  # odd with None elements
    q0, q1, q2, q3, q4 = Box._box_points(c)

    assert q2 == 4.0

    d = [4]
    q0, q1, q2, q3, q4 = Box._box_points(d)

    assert q0 == 4
    assert q1 == 4
    assert q2 == 4
    assert q3 == 4
    assert q4 == 4


def test_simple_box():
    box = ghostedBox()
    box.add('test1', [-1, 2, 3, 3.1, 3.2, 4, 5])
    box.add('test2', [2, 3, 5, 6, 6, 4])
    box.title = 'Box test'
    q = box.render_pyquery()

    assert len(q(".axis.y")) == 1
    assert len(q(".legend")) == 2
    assert len(q(".plot .series rect")) == 2

########NEW FILE########
__FILENAME__ = test_colors
from pygal.colors import (
    rgb_to_hsl, hsl_to_rgb, darken, lighten, saturate, desaturate, rotate)


def test_darken():
    assert darken('#800', 20) == '#220000'
    assert darken('#800', 0) == '#880000'
    assert darken('#ffffff', 10) == '#e6e6e6'
    assert darken('#000000', 10) == '#000000'
    assert darken('#f3148a', 25) == '#810747'
    assert darken('#121212', 1) == '#0f0f0f'
    assert darken('#999999', 100) == '#000000'
    assert darken('#1479ac', 8) == '#105f87'


def test_lighten():
    assert lighten('#800', 20) == '#ee0000'
    assert lighten('#800', 0) == '#880000'
    assert lighten('#ffffff', 10) == '#ffffff'
    assert lighten('#000000', 10) == '#1a1a1a'
    assert lighten('#f3148a', 25) == '#f98dc6'
    assert lighten('#121212', 1) == '#151515'
    assert lighten('#999999', 100) == '#ffffff'
    assert lighten('#1479ac', 8) == '#1893d1'


def test_saturate():
    assert saturate('#000', 20) == '#000000'
    assert saturate('#fff', 20) == '#ffffff'
    assert saturate('#8a8', 100) == '#33ff33'
    assert saturate('#855', 20) == '#9e3f3f'


def test_desaturate():
    assert desaturate('#000', 20) == '#000000'
    assert desaturate('#fff', 20) == '#ffffff'
    assert desaturate('#8a8', 100) == '#999999'
    assert desaturate('#855', 20) == '#726b6b'


def test_rotate():
    assert rotate('#000', 45) == '#000000'
    assert rotate('#fff', 45) == '#ffffff'
    assert rotate('#811', 45) == '#886a11'
    assert rotate('#8a8', 360) == '#88aa88'
    assert rotate('#8a8', 0) == '#88aa88'
    assert rotate('#8a8', -360) == '#88aa88'


def test_hsl_to_rgb_part_0():
    assert hsl_to_rgb(0, 100, 50) == (255, 0, 0)
    assert hsl_to_rgb(60, 100, 50) == (255, 255, 0)
    assert hsl_to_rgb(120, 100, 50) == (0, 255, 0)
    assert hsl_to_rgb(180, 100, 50) == (0, 255, 255)
    assert hsl_to_rgb(240, 100, 50) == (0, 0, 255)
    assert hsl_to_rgb(300, 100, 50) == (255, 0, 255)


def test_rgb_to_hsl_part_0():
    assert rgb_to_hsl(255, 0, 0) == (0, 100, 50)
    assert rgb_to_hsl(255, 255, 0) == (60, 100, 50)
    assert rgb_to_hsl(0, 255, 0) == (120, 100, 50)
    assert rgb_to_hsl(0, 255, 255) == (180, 100, 50)
    assert rgb_to_hsl(0, 0, 255) == (240, 100, 50)
    assert rgb_to_hsl(255, 0, 255) == (300, 100, 50)


def test_hsl_to_rgb_part_1():
    assert hsl_to_rgb(-360, 100, 50) == (255, 0, 0)
    assert hsl_to_rgb(-300, 100, 50) == (255, 255, 0)
    assert hsl_to_rgb(-240, 100, 50) == (0, 255, 0)
    assert hsl_to_rgb(-180, 100, 50) == (0, 255, 255)
    assert hsl_to_rgb(-120, 100, 50) == (0, 0, 255)
    assert hsl_to_rgb(-60, 100, 50) == (255, 0, 255)


def test_rgb_to_hsl_part_1():
    # assert rgb_to_hsl(255, 0, 0) == (-360, 100, 50)
    # assert rgb_to_hsl(255, 255, 0) == (-300, 100, 50)
    # assert rgb_to_hsl(0, 255, 0) == (-240, 100, 50)
    # assert rgb_to_hsl(0, 255, 255) == (-180, 100, 50)
    # assert rgb_to_hsl(0, 0, 255) == (-120, 100, 50)
    # assert rgb_to_hsl(255, 0, 255) == (-60, 100, 50)
    pass


def test_hsl_to_rgb_part_2():
    assert hsl_to_rgb(360, 100, 50) == (255, 0, 0)
    assert hsl_to_rgb(420, 100, 50) == (255, 255, 0)
    assert hsl_to_rgb(480, 100, 50) == (0, 255, 0)
    assert hsl_to_rgb(540, 100, 50) == (0, 255, 255)
    assert hsl_to_rgb(600, 100, 50) == (0, 0, 255)
    assert hsl_to_rgb(660, 100, 50) == (255, 0, 255)


def test_rgb_to_hsl_part_2():
    # assert rgb_to_hsl(255, 0, 0) == (360, 100, 50)
    # assert rgb_to_hsl(255, 255, 0) == (420, 100, 50)
    # assert rgb_to_hsl(0, 255, 0) == (480, 100, 50)
    # assert rgb_to_hsl(0, 255, 255) == (540, 100, 50)
    # assert rgb_to_hsl(0, 0, 255) == (600, 100, 50)
    # assert rgb_to_hsl(255, 0, 255) == (660, 100, 50)
    pass


def test_hsl_to_rgb_part_3():
    assert hsl_to_rgb(6120, 100, 50) == (255, 0, 0)
    assert hsl_to_rgb(-9660, 100, 50) == (255, 255, 0)
    assert hsl_to_rgb(99840, 100, 50) == (0, 255, 0)
    assert hsl_to_rgb(-900, 100, 50) == (0, 255, 255)
    assert hsl_to_rgb(-104880, 100, 50) == (0, 0, 255)
    assert hsl_to_rgb(2820, 100, 50) == (255, 0, 255)


def test_rgb_to_hsl_part_3():
    # assert rgb_to_hsl(255, 0, 0) == (6120, 100, 50)
    # assert rgb_to_hsl(255, 255, 0) == (-9660, 100, 50)
    # assert rgb_to_hsl(0, 255, 0) == (99840, 100, 50)
    # assert rgb_to_hsl(0, 255, 255) == (-900, 100, 50)
    # assert rgb_to_hsl(0, 0, 255) == (-104880, 100, 50)
    # assert rgb_to_hsl(255, 0, 255) == (2820, 100, 50)
    pass


def test_hsl_to_rgb_part_4():
    assert hsl_to_rgb(0, 100, 50) == (255, 0, 0)
    assert hsl_to_rgb(12, 100, 50) == (255, 51, 0)
    assert hsl_to_rgb(24, 100, 50) == (255, 102, 0)
    assert hsl_to_rgb(36, 100, 50) == (255, 153, 0)
    assert hsl_to_rgb(48, 100, 50) == (255, 204, 0)
    assert hsl_to_rgb(60, 100, 50) == (255, 255, 0)
    assert hsl_to_rgb(72, 100, 50) == (204, 255, 0)
    assert hsl_to_rgb(84, 100, 50) == (153, 255, 0)
    assert hsl_to_rgb(96, 100, 50) == (102, 255, 0)
    assert hsl_to_rgb(108, 100, 50) == (51, 255, 0)
    assert hsl_to_rgb(120, 100, 50) == (0, 255, 0)


def test_rgb_to_hsl_part_4():
    assert rgb_to_hsl(255, 0, 0) == (0, 100, 50)
    assert rgb_to_hsl(255, 51, 0) == (12, 100, 50)
    assert rgb_to_hsl(255, 102, 0) == (24, 100, 50)
    assert rgb_to_hsl(255, 153, 0) == (36, 100, 50)
    assert rgb_to_hsl(255, 204, 0) == (48, 100, 50)
    assert rgb_to_hsl(255, 255, 0) == (60, 100, 50)
    assert rgb_to_hsl(204, 255, 0) == (72, 100, 50)
    assert rgb_to_hsl(153, 255, 0) == (84, 100, 50)
    assert rgb_to_hsl(102, 255, 0) == (96, 100, 50)
    assert rgb_to_hsl(51, 255, 0) == (108, 100, 50)
    assert rgb_to_hsl(0, 255, 0) == (120, 100, 50)


def test_hsl_to_rgb_part_5():
    assert hsl_to_rgb(120, 100, 50) == (0, 255, 0)
    assert hsl_to_rgb(132, 100, 50) == (0, 255, 51)
    assert hsl_to_rgb(144, 100, 50) == (0, 255, 102)
    assert hsl_to_rgb(156, 100, 50) == (0, 255, 153)
    assert hsl_to_rgb(168, 100, 50) == (0, 255, 204)
    assert hsl_to_rgb(180, 100, 50) == (0, 255, 255)
    assert hsl_to_rgb(192, 100, 50) == (0, 204, 255)
    assert hsl_to_rgb(204, 100, 50) == (0, 153, 255)
    assert hsl_to_rgb(216, 100, 50) == (0, 102, 255)
    assert hsl_to_rgb(228, 100, 50) == (0, 51, 255)
    assert hsl_to_rgb(240, 100, 50) == (0, 0, 255)


def test_rgb_to_hsl_part_5():
    assert rgb_to_hsl(0, 255, 0) == (120, 100, 50)
    assert rgb_to_hsl(0, 255, 51) == (132, 100, 50)
    assert rgb_to_hsl(0, 255, 102) == (144, 100, 50)
    assert rgb_to_hsl(0, 255, 153) == (156, 100, 50)
    assert rgb_to_hsl(0, 255, 204) == (168, 100, 50)
    assert rgb_to_hsl(0, 255, 255) == (180, 100, 50)
    assert rgb_to_hsl(0, 204, 255) == (192, 100, 50)
    assert rgb_to_hsl(0, 153, 255) == (204, 100, 50)
    assert rgb_to_hsl(0, 102, 255) == (216, 100, 50)
    assert rgb_to_hsl(0, 51, 255) == (228, 100, 50)
    assert rgb_to_hsl(0, 0, 255) == (240, 100, 50)


def test_hsl_to_rgb_part_6():
    assert hsl_to_rgb(240, 100, 50) == (0, 0, 255)
    assert hsl_to_rgb(252, 100, 50) == (51, 0, 255)
    assert hsl_to_rgb(264, 100, 50) == (102, 0, 255)
    assert hsl_to_rgb(276, 100, 50) == (153, 0, 255)
    assert hsl_to_rgb(288, 100, 50) == (204, 0, 255)
    assert hsl_to_rgb(300, 100, 50) == (255, 0, 255)
    assert hsl_to_rgb(312, 100, 50) == (255, 0, 204)
    assert hsl_to_rgb(324, 100, 50) == (255, 0, 153)
    assert hsl_to_rgb(336, 100, 50) == (255, 0, 102)
    assert hsl_to_rgb(348, 100, 50) == (255, 0, 51)
    assert hsl_to_rgb(360, 100, 50) == (255, 0, 0)


def test_rgb_to_hsl_part_6():
    assert rgb_to_hsl(0, 0, 255) == (240, 100, 50)
    assert rgb_to_hsl(51, 0, 255) == (252, 100, 50)
    assert rgb_to_hsl(102, 0, 255) == (264, 100, 50)
    assert rgb_to_hsl(153, 0, 255) == (276, 100, 50)
    assert rgb_to_hsl(204, 0, 255) == (288, 100, 50)
    assert rgb_to_hsl(255, 0, 255) == (300, 100, 50)
    assert rgb_to_hsl(255, 0, 204) == (312, 100, 50)
    assert rgb_to_hsl(255, 0, 153) == (324, 100, 50)
    assert rgb_to_hsl(255, 0, 102) == (336, 100, 50)
    assert rgb_to_hsl(255, 0, 51) == (348, 100, 50)
    # assert rgb_to_hsl(255, 0, 0) == (360, 100, 50)


def test_hsl_to_rgb_part_7():
    assert hsl_to_rgb(0, 20, 50) == (153, 102, 102)
    assert hsl_to_rgb(0, 60, 50) == (204, 51, 51)
    assert hsl_to_rgb(0, 100, 50) == (255, 0, 0)


def test_rgb_to_hsl_part_7():
    assert rgb_to_hsl(153, 102, 102) == (0, 20, 50)
    assert rgb_to_hsl(204, 51, 51) == (0, 60, 50)
    assert rgb_to_hsl(255, 0, 0) == (0, 100, 50)


def test_hsl_to_rgb_part_8():
    assert hsl_to_rgb(60, 20, 50) == (153, 153, 102)
    assert hsl_to_rgb(60, 60, 50) == (204, 204, 51)
    assert hsl_to_rgb(60, 100, 50) == (255, 255, 0)


def test_rgb_to_hsl_part_8():
    assert rgb_to_hsl(153, 153, 102) == (60, 20, 50)
    assert rgb_to_hsl(204, 204, 51) == (60, 60, 50)
    assert rgb_to_hsl(255, 255, 0) == (60, 100, 50)


def test_hsl_to_rgb_part_9():
    assert hsl_to_rgb(120, 20, 50) == (102, 153, 102)
    assert hsl_to_rgb(120, 60, 50) == (51, 204, 51)
    assert hsl_to_rgb(120, 100, 50) == (0, 255, 0)


def test_rgb_to_hsl_part_9():
    assert rgb_to_hsl(102, 153, 102) == (120, 20, 50)
    assert rgb_to_hsl(51, 204, 51) == (120, 60, 50)
    assert rgb_to_hsl(0, 255, 0) == (120, 100, 50)


def test_hsl_to_rgb_part_10():
    assert hsl_to_rgb(180, 20, 50) == (102, 153, 153)
    assert hsl_to_rgb(180, 60, 50) == (51, 204, 204)
    assert hsl_to_rgb(180, 100, 50) == (0, 255, 255)


def test_rgb_to_hsl_part_10():
    assert rgb_to_hsl(102, 153, 153) == (180, 20, 50)
    assert rgb_to_hsl(51, 204, 204) == (180, 60, 50)
    assert rgb_to_hsl(0, 255, 255) == (180, 100, 50)


def test_hsl_to_rgb_part_11():
    assert hsl_to_rgb(240, 20, 50) == (102, 102, 153)
    assert hsl_to_rgb(240, 60, 50) == (51, 51, 204)
    assert hsl_to_rgb(240, 100, 50) == (0, 0, 255)


def test_rgb_to_hsl_part_11():
    assert rgb_to_hsl(102, 102, 153) == (240, 20, 50)
    assert rgb_to_hsl(51, 51, 204) == (240, 60, 50)
    assert rgb_to_hsl(0, 0, 255) == (240, 100, 50)


def test_hsl_to_rgb_part_12():
    assert hsl_to_rgb(300, 20, 50) == (153, 102, 153)
    assert hsl_to_rgb(300, 60, 50) == (204, 51, 204)
    assert hsl_to_rgb(300, 100, 50) == (255, 0, 255)


def test_rgb_to_hsl_part_12():
    assert rgb_to_hsl(153, 102, 153) == (300, 20, 50)
    assert rgb_to_hsl(204, 51, 204) == (300, 60, 50)
    assert rgb_to_hsl(255, 0, 255) == (300, 100, 50)


def test_hsl_to_rgb_part_13():
    assert hsl_to_rgb(0, 100, 0) == (0, 0, 0)
    assert hsl_to_rgb(0, 100, 10) == (51, 0, 0)
    assert hsl_to_rgb(0, 100, 20) == (102, 0, 0)
    assert hsl_to_rgb(0, 100, 30) == (153, 0, 0)
    assert hsl_to_rgb(0, 100, 40) == (204, 0, 0)
    assert hsl_to_rgb(0, 100, 50) == (255, 0, 0)
    assert hsl_to_rgb(0, 100, 60) == (255, 51, 51)
    assert hsl_to_rgb(0, 100, 70) == (255, 102, 102)
    assert hsl_to_rgb(0, 100, 80) == (255, 153, 153)
    assert hsl_to_rgb(0, 100, 90) == (255, 204, 204)
    assert hsl_to_rgb(0, 100, 100) == (255, 255, 255)


def test_rgb_to_hsl_part_13():
    assert rgb_to_hsl(0, 0, 0) == (0, 0, 0)
    assert rgb_to_hsl(51, 0, 0) == (0, 100, 10)
    assert rgb_to_hsl(102, 0, 0) == (0, 100, 20)
    assert rgb_to_hsl(153, 0, 0) == (0, 100, 30)
    assert rgb_to_hsl(204, 0, 0) == (0, 100, 40)
    assert rgb_to_hsl(255, 0, 0) == (0, 100, 50)
    assert rgb_to_hsl(255, 51, 51) == (0, 100, 60)
    assert rgb_to_hsl(255, 102, 102) == (0, 100, 70)
    assert rgb_to_hsl(255, 153, 153) == (0, 100, 80)
    assert rgb_to_hsl(255, 204, 204) == (0, 100, 90)
    assert rgb_to_hsl(255, 255, 255) == (0, 0, 100)


def test_hsl_to_rgb_part_14():
    assert hsl_to_rgb(60, 100, 0) == (0, 0, 0)
    assert hsl_to_rgb(60, 100, 10) == (51, 51, 0)
    assert hsl_to_rgb(60, 100, 20) == (102, 102, 0)
    assert hsl_to_rgb(60, 100, 30) == (153, 153, 0)
    assert hsl_to_rgb(60, 100, 40) == (204, 204, 0)
    assert hsl_to_rgb(60, 100, 50) == (255, 255, 0)
    assert hsl_to_rgb(60, 100, 60) == (255, 255, 51)
    assert hsl_to_rgb(60, 100, 70) == (255, 255, 102)
    assert hsl_to_rgb(60, 100, 80) == (255, 255, 153)
    assert hsl_to_rgb(60, 100, 90) == (255, 255, 204)
    assert hsl_to_rgb(60, 100, 100) == (255, 255, 255)


def test_rgb_to_hsl_part_14():
    # assert rgb_to_hsl(0, 0, 0) == (60, 100, 0)
    assert rgb_to_hsl(51, 51, 0) == (60, 100, 10)
    assert rgb_to_hsl(102, 102, 0) == (60, 100, 20)
    assert rgb_to_hsl(153, 153, 0) == (60, 100, 30)
    assert rgb_to_hsl(204, 204, 0) == (60, 100, 40)
    assert rgb_to_hsl(255, 255, 0) == (60, 100, 50)
    assert rgb_to_hsl(255, 255, 51) == (60, 100, 60)
    assert rgb_to_hsl(255, 255, 102) == (60, 100, 70)
    assert rgb_to_hsl(255, 255, 153) == (60, 100, 80)
    assert rgb_to_hsl(255, 255, 204) == (60, 100, 90)
    # assert rgb_to_hsl(255, 255, 255) == (60, 100, 100)


def test_hsl_to_rgb_part_15():
    assert hsl_to_rgb(120, 100, 0) == (0, 0, 0)
    assert hsl_to_rgb(120, 100, 10) == (0, 51, 0)
    assert hsl_to_rgb(120, 100, 20) == (0, 102, 0)
    assert hsl_to_rgb(120, 100, 30) == (0, 153, 0)
    assert hsl_to_rgb(120, 100, 40) == (0, 204, 0)
    assert hsl_to_rgb(120, 100, 50) == (0, 255, 0)
    assert hsl_to_rgb(120, 100, 60) == (51, 255, 51)
    assert hsl_to_rgb(120, 100, 70) == (102, 255, 102)
    assert hsl_to_rgb(120, 100, 80) == (153, 255, 153)
    assert hsl_to_rgb(120, 100, 90) == (204, 255, 204)
    assert hsl_to_rgb(120, 100, 100) == (255, 255, 255)


def test_rgb_to_hsl_part_15():
    # assert rgb_to_hsl(0, 0, 0) == (120, 100, 0)
    assert rgb_to_hsl(0, 51, 0) == (120, 100, 10)
    assert rgb_to_hsl(0, 102, 0) == (120, 100, 20)
    assert rgb_to_hsl(0, 153, 0) == (120, 100, 30)
    assert rgb_to_hsl(0, 204, 0) == (120, 100, 40)
    assert rgb_to_hsl(0, 255, 0) == (120, 100, 50)
    assert rgb_to_hsl(51, 255, 51) == (120, 100, 60)
    assert rgb_to_hsl(102, 255, 102) == (120, 100, 70)
    assert rgb_to_hsl(153, 255, 153) == (120, 100, 80)
    assert rgb_to_hsl(204, 255, 204) == (120, 100, 90)
    # assert rgb_to_hsl(255, 255, 255) == (120, 100, 100)


def test_hsl_to_rgb_part_16():
    assert hsl_to_rgb(180, 100, 0) == (0, 0, 0)
    assert hsl_to_rgb(180, 100, 10) == (0, 51, 51)
    assert hsl_to_rgb(180, 100, 20) == (0, 102, 102)
    assert hsl_to_rgb(180, 100, 30) == (0, 153, 153)
    assert hsl_to_rgb(180, 100, 40) == (0, 204, 204)
    assert hsl_to_rgb(180, 100, 50) == (0, 255, 255)
    assert hsl_to_rgb(180, 100, 60) == (51, 255, 255)
    assert hsl_to_rgb(180, 100, 70) == (102, 255, 255)
    assert hsl_to_rgb(180, 100, 80) == (153, 255, 255)
    assert hsl_to_rgb(180, 100, 90) == (204, 255, 255)
    assert hsl_to_rgb(180, 100, 100) == (255, 255, 255)


def test_rgb_to_hsl_part_16():
    # assert rgb_to_hsl(0, 0, 0) == (180, 100, 0)
    assert rgb_to_hsl(0, 51, 51) == (180, 100, 10)
    assert rgb_to_hsl(0, 102, 102) == (180, 100, 20)
    assert rgb_to_hsl(0, 153, 153) == (180, 100, 30)
    assert rgb_to_hsl(0, 204, 204) == (180, 100, 40)
    assert rgb_to_hsl(0, 255, 255) == (180, 100, 50)
    assert rgb_to_hsl(51, 255, 255) == (180, 100, 60)
    assert rgb_to_hsl(102, 255, 255) == (180, 100, 70)
    assert rgb_to_hsl(153, 255, 255) == (180, 100, 80)
    assert rgb_to_hsl(204, 255, 255) == (180, 100, 90)
    # assert rgb_to_hsl(255, 255, 255) == (180, 100, 100)


def test_hsl_to_rgb_part_17():
    assert hsl_to_rgb(240, 100, 0) == (0, 0, 0)
    assert hsl_to_rgb(240, 100, 10) == (0, 0, 51)
    assert hsl_to_rgb(240, 100, 20) == (0, 0, 102)
    assert hsl_to_rgb(240, 100, 30) == (0, 0, 153)
    assert hsl_to_rgb(240, 100, 40) == (0, 0, 204)
    assert hsl_to_rgb(240, 100, 50) == (0, 0, 255)
    assert hsl_to_rgb(240, 100, 60) == (51, 51, 255)
    assert hsl_to_rgb(240, 100, 70) == (102, 102, 255)
    assert hsl_to_rgb(240, 100, 80) == (153, 153, 255)
    assert hsl_to_rgb(240, 100, 90) == (204, 204, 255)
    assert hsl_to_rgb(240, 100, 100) == (255, 255, 255)


def test_rgb_to_hsl_part_17():
    # assert rgb_to_hsl(0, 0, 0) == (240, 100, 0)
    assert rgb_to_hsl(0, 0, 51) == (240, 100, 10)
    assert rgb_to_hsl(0, 0, 102) == (240, 100, 20)
    assert rgb_to_hsl(0, 0, 153) == (240, 100, 30)
    assert rgb_to_hsl(0, 0, 204) == (240, 100, 40)
    assert rgb_to_hsl(0, 0, 255) == (240, 100, 50)
    assert rgb_to_hsl(51, 51, 255) == (240, 100, 60)
    assert rgb_to_hsl(102, 102, 255) == (240, 100, 70)
    assert rgb_to_hsl(153, 153, 255) == (240, 100, 80)
    assert rgb_to_hsl(204, 204, 255) == (240, 100, 90)
    # assert rgb_to_hsl(255, 255, 255) == (240, 100, 100)


def test_hsl_to_rgb_part_18():
    assert hsl_to_rgb(300, 100, 0) == (0, 0, 0)
    assert hsl_to_rgb(300, 100, 10) == (51, 0, 51)
    assert hsl_to_rgb(300, 100, 20) == (102, 0, 102)
    assert hsl_to_rgb(300, 100, 30) == (153, 0, 153)
    assert hsl_to_rgb(300, 100, 40) == (204, 0, 204)
    assert hsl_to_rgb(300, 100, 50) == (255, 0, 255)
    assert hsl_to_rgb(300, 100, 60) == (255, 51, 255)
    assert hsl_to_rgb(300, 100, 70) == (255, 102, 255)
    assert hsl_to_rgb(300, 100, 80) == (255, 153, 255)
    assert hsl_to_rgb(300, 100, 90) == (255, 204, 255)
    assert hsl_to_rgb(300, 100, 100) == (255, 255, 255)


def test_rgb_to_hsl_part_18():
    # assert rgb_to_hsl(0, 0, 0) == (300, 100, 0)
    assert rgb_to_hsl(51, 0, 51) == (300, 100, 10)
    assert rgb_to_hsl(102, 0, 102) == (300, 100, 20)
    assert rgb_to_hsl(153, 0, 153) == (300, 100, 30)
    assert rgb_to_hsl(204, 0, 204) == (300, 100, 40)
    assert rgb_to_hsl(255, 0, 255) == (300, 100, 50)
    assert rgb_to_hsl(255, 51, 255) == (300, 100, 60)
    assert rgb_to_hsl(255, 102, 255) == (300, 100, 70)
    assert rgb_to_hsl(255, 153, 255) == (300, 100, 80)
    assert rgb_to_hsl(255, 204, 255) == (300, 100, 90)
    # assert rgb_to_hsl(255, 255, 255) == (300, 100, 100)

########NEW FILE########
__FILENAME__ = test_config
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.

from pygal import (
    Line, Dot, Pie, Radar, Config, Bar, Funnel, Worldmap,
    SupranationalWorldmap, Histogram, Gauge, Box, XY,
    Pyramid, DateY, HorizontalBar, HorizontalStackedBar,
    FrenchMap_Regions, FrenchMap_Departments)
from pygal._compat import u
from pygal.test.utils import texts
from pygal.test import pytest_generate_tests
from tempfile import NamedTemporaryFile


def test_config_behaviours():
    line1 = Line()
    line1.show_legend = False
    line1.fill = True
    line1.pretty_print = True
    line1.no_prefix = True
    line1.x_labels = ['a', 'b', 'c']
    line1.add('_', [1, 2, 3])
    l1 = line1.render()

    q = line1.render_pyquery()
    assert len(q(".axis.x")) == 1
    assert len(q(".axis.y")) == 1
    assert len(q(".plot .series path")) == 1
    assert len(q(".legend")) == 0
    assert len(q(".x.axis .guides")) == 3
    assert len(q(".y.axis .guides")) == 21
    assert len(q(".dots")) == 3
    assert q(".axis.x text").map(texts) == ['a', 'b', 'c']

    line2 = Line(
        show_legend=False,
        fill=True,
        pretty_print=True,
        no_prefix=True,
        x_labels=['a', 'b', 'c'])
    line2.add('_', [1, 2, 3])
    l2 = line2.render()
    assert l1 == l2

    class LineConfig(Config):
        show_legend = False
        fill = True
        pretty_print = True
        no_prefix = True
        x_labels = ['a', 'b', 'c']

    line3 = Line(LineConfig)
    line3.add('_', [1, 2, 3])
    l3 = line3.render()
    assert l1 == l3

    line4 = Line(LineConfig())
    line4.add('_', [1, 2, 3])
    l4 = line4.render()
    assert l1 == l4

    line_config = Config()
    line_config.show_legend = False
    line_config.fill = True
    line_config.pretty_print = True
    line_config.no_prefix = True
    line_config.x_labels = ['a', 'b', 'c']

    line5 = Line(line_config)
    line5.add('_', [1, 2, 3])
    l5 = line5.render()
    assert l1 == l5


def test_config_alterations_class():
    class LineConfig(Config):
        no_prefix = True
        show_legend = False
        fill = True
        pretty_print = True
        x_labels = ['a', 'b', 'c']

    line1 = Line(LineConfig)
    line1.add('_', [1, 2, 3])
    l1 = line1.render()

    LineConfig.stroke = False
    line2 = Line(LineConfig)
    line2.add('_', [1, 2, 3])
    l2 = line2.render()
    assert l1 != l2

    l1bis = line1.render()
    assert l1 == l1bis


def test_config_alterations_instance():
    class LineConfig(Config):
        no_prefix = True
        show_legend = False
        fill = True
        pretty_print = True
        x_labels = ['a', 'b', 'c']

    config = LineConfig()
    line1 = Line(config)
    line1.add('_', [1, 2, 3])
    l1 = line1.render()

    config.stroke = False
    line2 = Line(config)
    line2.add('_', [1, 2, 3])
    l2 = line2.render()
    assert l1 != l2

    l1bis = line1.render()
    assert l1 == l1bis


def test_config_alterations_kwargs():
    class LineConfig(Config):
        no_prefix = True
        show_legend = False
        fill = True
        pretty_print = True
        x_labels = ['a', 'b', 'c']

    config = LineConfig()

    line1 = Line(config)
    line1.add('_', [1, 2, 3])
    l1 = line1.render()

    line1.stroke = False
    l1bis = line1.render()
    assert l1 != l1bis

    line2 = Line(config)
    line2.add('_', [1, 2, 3])
    l2 = line2.render()
    assert l1 == l2
    assert l1bis != l2

    line3 = Line(config, title='Title')
    line3.add('_', [1, 2, 3])
    l3 = line3.render()
    assert l3 != l2

    l2bis = line2.render()
    assert l2 == l2bis


def test_logarithmic():
    line = Line(logarithmic=True)
    line.add('_', [1, 10 ** 10, 1])
    q = line.render_pyquery()
    assert len(q(".axis.x")) == 0
    assert len(q(".axis.y")) == 1
    assert len(q(".plot .series path")) == 1
    assert len(q(".legend")) == 1
    assert len(q(".x.axis .guides")) == 0
    assert len(q(".y.axis .guides")) == 51
    assert len(q(".dots")) == 3


def test_interpolation(Chart):
    chart = Chart(interpolate='cubic')
    chart.add('1', [1, 3, 12, 3, 4])
    chart.add('2', [7, -4, 10, None, 8, 3, 1])
    q = chart.render_pyquery()
    assert len(q(".legend")) == 2


def test_no_data_interpolation(Chart):
    chart = Chart(interpolate='cubic')
    q = chart.render_pyquery()
    assert q(".text-overlay text").text() == "No data"


def test_no_data_with_empty_serie_interpolation(Chart):
    chart = Chart(interpolate='cubic')
    chart.add('Serie', [])
    q = chart.render_pyquery()
    assert q(".text-overlay text").text() == "No data"


def test_logarithmic_bad_interpolation():
    line = Line(logarithmic=True, interpolate='cubic')
    line.add('_', [.001, .00000001, 1])
    q = line.render_pyquery()
    assert len(q(".y.axis .guides")) == 41


def test_logarithmic_big_scale():
    line = Line(logarithmic=True)
    line.add('_', [10 ** -10, 10 ** 10, 1])
    q = line.render_pyquery()
    assert len(q(".y.axis .guides")) == 41


def test_value_formatter():
    line = Line(value_formatter=lambda x: str(x) + u('‰'))
    line.add('_', [10 ** 4, 10 ** 5, 23 * 10 ** 4])
    q = line.render_pyquery()
    assert len(q(".y.axis .guides")) == 11
    assert q(".axis.y text").map(texts) == list(map(
        lambda x: str(x) + u('‰'), map(float, range(20000, 240000, 20000))))


def test_logarithmic_small_scale():
    line = Line(logarithmic=True)
    line.add('_', [1 + 10 ** 10, 3 + 10 ** 10, 2 + 10 ** 10])
    q = line.render_pyquery()
    assert len(q(".y.axis .guides")) == 21


def test_human_readable():
    line = Line()
    line.add('_', [10 ** 4, 10 ** 5, 23 * 10 ** 4])
    q = line.render_pyquery()
    assert q(".axis.y text").map(texts) == list(map(
        str, map(float, range(20000, 240000, 20000))))
    line.human_readable = True
    q = line.render_pyquery()
    assert q(".axis.y text").map(texts) == list(map(
        lambda x: '%dk' % x, range(20, 240, 20)))


def test_show_legend():
    line = Line()
    line.add('_', [1, 2, 3])
    q = line.render_pyquery()
    assert len(q(".legend")) == 1
    line.show_legend = False
    q = line.render_pyquery()
    assert len(q(".legend")) == 0


def test_show_dots():
    line = Line()
    line.add('_', [1, 2, 3])
    q = line.render_pyquery()
    assert len(q(".dots")) == 3
    line.show_dots = False
    q = line.render_pyquery()
    assert len(q(".dots")) == 0


def test_no_data():
    line = Line()
    q = line.render_pyquery()
    assert q(".text-overlay text").text() == "No data"
    line.no_data_text = u("þæ®þæ€€&ĳ¿’€")
    q = line.render_pyquery()
    assert q(".text-overlay text").text() == u("þæ®þæ€€&ĳ¿’€")


def test_include_x_axis(Chart):
    chart = Chart()
    if Chart in (Pie, Radar, Funnel, Dot, Gauge, Worldmap,
                 SupranationalWorldmap, Histogram, Box,
                 FrenchMap_Regions, FrenchMap_Departments):
        return
    if not chart.cls._dual:
        data = 100, 200, 150
    else:
        data = (1, 100), (3, 200), (2, 150)
    chart.add('_', data)
    q = chart.render_pyquery()
    # Ghost thing
    yaxis = ".axis.%s .guides text" % (
        'y' if not chart._last__inst.horizontal else 'x')
    if not issubclass(chart.cls, Bar().cls):
        assert '0.0' not in q(yaxis).map(texts)
    else:
        assert '0.0' in q(yaxis).map(texts)
    chart.include_x_axis = True
    q = chart.render_pyquery()
    assert '0.0' in q(yaxis).map(texts)


def test_css(Chart):
    css = "{{ id }}text { fill: #bedead; }\n"
    with NamedTemporaryFile('w') as f:
        f.write(css)
        f.flush()

        config = Config()
        config.css.append(f.name)

        chart = Chart(config)
        chart.add('/', [10, 1, 5])
        svg = chart.render().decode('utf-8')
        assert '#bedead' in svg


def test_inline_css(Chart):
    css = "{{ id }}text { fill: #bedead; }\n"

    config = Config()
    config.css.append('inline:' + css)
    chart = Chart(config)
    chart.add('/', [10, 1, 5])
    svg = chart.render().decode('utf-8')
    assert '#bedead' in svg


def test_meta_config():
    from pygal.config import CONFIG_ITEMS
    assert all(c.name != 'Unbound' for c in CONFIG_ITEMS)


def test_label_rotation(Chart):
    chart = Chart(x_label_rotation=28, y_label_rotation=76)
    chart.add('1', [4, -5, 123, 59, 38])
    chart.add('2', [89, 0, 8, .12, 8])
    chart.x_labels = ['one', 'twoooooooooooooooooooooo', 'three', '4']
    q = chart.render_pyquery()
    if Chart in (Line, Bar):
        assert len(q('.axis.x text[transform^="rotate(28"]')) == 4
        assert len(q('.axis.y text[transform^="rotate(76"]')) == 13


def test_legend_at_bottom(Chart):
    chart = Chart(legend_at_bottom=True)
    chart.add('1', [4, -5, 123, 59, 38])
    chart.add('2', [89, 0, 8, .12, 8])
    chart.x_labels = ['one', 'twoooooooooooooooooooooo', 'three', '4']
    lab = chart.render()
    chart.legend_at_bottom = False
    assert lab != chart.render()


def test_x_y_title(Chart):
    chart = Chart(title='I Am A Title',
                  x_title="I am a x title",
                  y_title="I am a y title")
    chart.add('1', [4, -5, 123, 59, 38])
    chart.add('2', [89, 0, 8, .12, 8])
    chart.x_labels = ['one', 'twoooooooooooooooooooooo', 'three', '4']
    q = chart.render_pyquery()
    assert len(q('.titles .title')) == 3


def test_x_label_major(Chart):
    if Chart in (
            Pie, Funnel, Dot, Gauge, Worldmap,
            SupranationalWorldmap, Histogram, Box,
            FrenchMap_Regions, FrenchMap_Departments,
            Pyramid, DateY):
        return
    chart = Chart()
    chart.add('test', range(12))
    chart.x_labels = map(str, range(12))

    q = chart.render_pyquery()
    assert len(q(".axis.x text.major")) == 0

    chart.x_labels_major = ['1', '5', '11', '1.0', '5.0', '11.0']
    q = chart.render_pyquery()
    assert len(q(".axis.x text.major")) == 3
    assert len(q(".axis.x text")) == 12

    chart.show_minor_x_labels = False
    q = chart.render_pyquery()
    assert len(q(".axis.x text.major")) == 3
    assert len(q(".axis.x text")) == 3

    chart.show_minor_x_labels = True
    chart.x_labels_major = None
    chart.x_labels_major_every = 2
    q = chart.render_pyquery()
    assert len(q(".axis.x text.major")) == 6
    assert len(q(".axis.x text")) == 12

    chart.x_labels_major_every = None
    chart.x_labels_major_count = 4
    q = chart.render_pyquery()
    assert len(q(".axis.x text.major")) == 4
    assert len(q(".axis.x text")) == 12

    chart.x_labels_major_every = None
    chart.x_labels_major_count = 78
    q = chart.render_pyquery()
    assert len(q(".axis.x text.major")) == 12
    assert len(q(".axis.x text")) == 12


def test_y_label_major(Chart):
    if Chart in (
            Pie, Funnel, Dot, Gauge, Worldmap,
            SupranationalWorldmap, Histogram, Box,
            FrenchMap_Regions, FrenchMap_Departments,
            HorizontalBar, HorizontalStackedBar,
            Pyramid, DateY):
        return
    chart = Chart()
    data = range(12)
    if Chart == XY:
        data = list(zip(*[range(12), range(12)]))
    chart.add('test', data)
    chart.y_labels = range(12)

    q = chart.render_pyquery()
    assert len(q(".axis.y text.major")) == 3

    chart.y_labels_major = [1.0, 5.0, 11.0]
    q = chart.render_pyquery()
    assert len(q(".axis.y text.major")) == 3
    assert len(q(".axis.y text")) == 12

    chart.show_minor_y_labels = False
    q = chart.render_pyquery()
    assert len(q(".axis.y text.major")) == 3
    assert len(q(".axis.y text")) == 3

    chart.show_minor_y_labels = True
    chart.y_labels_major = None
    chart.y_labels_major_every = 2
    q = chart.render_pyquery()
    assert len(q(".axis.y text.major")) == 6
    assert len(q(".axis.y text")) == 12

    chart.y_labels_major_every = None
    chart.y_labels_major_count = 4
    q = chart.render_pyquery()
    assert len(q(".axis.y text.major")) == 4
    assert len(q(".axis.y text")) == 12

    chart.y_labels_major_every = None
    chart.y_labels_major_count = 78
    q = chart.render_pyquery()
    assert len(q(".axis.y text.major")) == 12
    assert len(q(".axis.y text")) == 12


def test_no_y_labels(Chart):
    chart = Chart()
    chart.y_labels = []
    chart.add('_', [1, 2, 3])
    chart.add('?', [10, 21, 5])
    assert chart.render_pyquery()


def test_fill(Chart):
    chart = Chart(fill=True)
    chart.add('_', [1, 2, 3])
    chart.add('?', [10, 21, 5])
    assert chart.render_pyquery()

########NEW FILE########
__FILENAME__ = test_date
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
from pygal import DateY
from pygal.test.utils import texts
from datetime import datetime


def test_date():
    datey = DateY(truncate_label=1000)
    datey.add('dates', [
        (datetime(2013, 1, 2), 300),
        (datetime(2013, 1, 12), 412),
        (datetime(2013, 2, 2), 823),
        (datetime(2013, 2, 22), 672)
    ])

    q = datey.render_pyquery()

    assert list(
        map(lambda t: t.split(' ')[0],
            q(".axis.x text").map(texts))) == [
        '2013-01-02',
        '2013-01-13',
        '2013-01-25',
        '2013-02-05',
        '2013-02-17'
    ]

    datey.x_labels = [
        datetime(2013, 1, 1),
        datetime(2013, 2, 1),
        datetime(2013, 3, 1)
    ]

    q = datey.render_pyquery()
    assert list(
        map(lambda t: t.split(' ')[0],
            q(".axis.x text").map(texts))) == [
        '2013-01-01',
        '2013-02-01',
        '2013-03-01'
    ]


def test_date_overflow():
    datey = DateY(truncate_label=1000)
    datey.add('dates', [1, 2, -1000000, 5, 100000000])
    assert datey.render_pyquery()

########NEW FILE########
__FILENAME__ = test_donut
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
from pygal import Pie


def test_donut():
    chart = Pie(inner_radius=.3, pretty_print=True)
    chart.title = 'Browser usage in February 2012 (in %)'
    chart.add('IE', 19.5)
    chart.add('Firefox', 36.6)
    chart.add('Chrome', 36.3)
    chart.add('Safari', 4.5)
    chart.add('Opera', 2.3)
    assert chart.render()


def test_multiseries_donut():
    # this just demos that the multiseries pie does not respect
    # the inner_radius
    chart = Pie(inner_radius=.3, pretty_print=True)
    chart.title = 'Browser usage by version in February 2012 (in %)'
    chart.add('IE', [5.7, 10.2, 2.6, 1])
    chart.add('Firefox', [.6, 16.8, 7.4, 2.2, 1.2, 1, 1, 1.1, 4.3, 1])
    chart.add('Chrome', [.3, .9, 17.1, 15.3, .6, .5, 1.6])
    chart.add('Safari', [4.4, .1])
    chart.add('Opera', [.1, 1.6, .1, .5])
    assert chart.render()


def test_half_pie():
    pie = Pie()
    pie.add('IE', 19.5)
    pie.add('Firefox', 36.6)
    pie.add('Chrome', 36.3)
    pie.add('Safari', 4.5)
    pie.add('Opera', 2.3)

    half = Pie(half_pie=True)
    half.add('IE', 19.5)
    half.add('Firefox', 36.6)
    half.add('Chrome', 36.3)
    half.add('Safari', 4.5)
    half.add('Opera', 2.3)
    assert pie.render() != half.render()

########NEW FILE########
__FILENAME__ = test_frenchmap
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.

from pygal import (
    FrenchMap_Regions, FrenchMap_Departments)
from pygal.graph.frenchmap import REGIONS, DEPARTMENTS, aggregate_regions


def test_frenchmaps():
    datas = {}
    for dept in DEPARTMENTS.keys():
        datas[dept] = int(''.join([x for x in dept if x.isdigit()])) * 10

    fmap = FrenchMap_Departments()
    fmap.add('departements', datas)
    q = fmap.render_pyquery()
    assert len(
        q('#departements .departement,#dom-com .departement')
    ) == len(DEPARTMENTS)

    fmap = FrenchMap_Regions()
    fmap.add('regions', aggregate_regions(datas))
    q = fmap.render_pyquery()
    assert len(q('#regions .region,#dom-com .region')) == len(REGIONS)

    assert aggregate_regions(datas.items()) == aggregate_regions(datas)

########NEW FILE########
__FILENAME__ = test_graph
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.

import os
import pygal
import uuid
import sys
import pytest
from pygal import i18n
from pygal.graph.frenchmap import DEPARTMENTS, REGIONS
from pygal.util import cut
from pygal._compat import u
from pygal.test import pytest_generate_tests, make_data

try:
    import cairosvg
except ImportError:
    cairosvg = None


def test_multi_render(Chart, datas):
    chart = Chart()
    chart = make_data(chart, datas)
    chart.x_labels = (str(a) for a in 'labels')
    chart.y_labels = (str(a) for a in range(6))
    svg = chart.render()
    for i in range(2):
        assert svg == chart.render()


def test_render_to_file(Chart, datas):
    file_name = '/tmp/test_graph-%s.svg' % uuid.uuid4()
    if os.path.exists(file_name):
        os.remove(file_name)

    chart = Chart()
    chart = make_data(chart, datas)
    chart.render_to_file(file_name)
    with open(file_name) as f:
        assert 'pygal' in f.read()
    os.remove(file_name)


@pytest.mark.skipif(not cairosvg, reason="CairoSVG not installed")
def test_render_to_png(Chart, datas):
    file_name = '/tmp/test_graph-%s.png' % uuid.uuid4()
    if os.path.exists(file_name):
        os.remove(file_name)

    chart = Chart()
    chart = make_data(chart, datas)
    chart.render_to_png(file_name)
    png = chart._repr_png_()

    with open(file_name, 'rb') as f:
        assert png == f.read()
    os.remove(file_name)


def test_metadata(Chart):
    chart = Chart()
    v = range(7)
    if Chart in (pygal.Box,):
        return  # summary charts cannot display per-value metadata
    elif Chart == pygal.XY:
        v = list(map(lambda x: (x, x + 1), v))
    elif Chart == pygal.Worldmap or Chart == pygal.SupranationalWorldmap:
        v = [(i, k) for k, i in enumerate(i18n.COUNTRIES.keys())]
    elif Chart == pygal.FrenchMap_Regions:
        v = [(i, k) for k, i in enumerate(REGIONS.keys())]
    elif Chart == pygal.FrenchMap_Departments:
        v = [(i, k) for k, i in enumerate(DEPARTMENTS.keys())]

    chart.add('Serie with metadata', [
        v[0],
        {'value': v[1]},
        {'value': v[2], 'label': 'Three'},
        {'value': v[3], 'xlink': 'http://4.example.com/'},
        {'value': v[4], 'xlink': 'http://5.example.com/', 'label': 'Five'},
        {'value': v[5], 'xlink': {
            'href': 'http://6.example.com/'}, 'label': 'Six'},
        {'value': v[6], 'xlink': {
            'href': 'http://7.example.com/',
            'target': '_blank'}, 'label': 'Seven'}
    ])
    q = chart.render_pyquery()
    for md in (
            'Three', 'http://4.example.com/',
            'Five', 'http://7.example.com/', 'Seven'):
        assert md in cut(q('desc'), 'text')

    if Chart == pygal.Pie:
        # Slices with value 0 are not rendered
        assert len(v) - 1 == len(q('.tooltip-trigger').siblings('.value'))
    elif Chart not in (
            pygal.Worldmap, pygal.SupranationalWorldmap,
            pygal.FrenchMap_Regions, pygal.FrenchMap_Departments):
        # Tooltip are not working on maps
        assert len(v) == len(q('.tooltip-trigger').siblings('.value'))


def test_empty_lists(Chart):
    chart = Chart()
    chart.add('A', [1, 2])
    chart.add('B', [])
    chart.x_labels = ('red', 'green', 'blue')
    q = chart.render_pyquery()
    assert len(q(".legend")) == 2


def test_empty_lists_with_nones(Chart):
    chart = Chart()
    chart.add('A', [None, None])
    chart.add('B', [None, 4, 4])
    chart.x_labels = ('red', 'green', 'blue')
    q = chart.render_pyquery()
    assert len(q(".legend")) == 2


def test_non_iterable_value(Chart):
    chart = Chart(no_prefix=True)
    chart.add('A', 1)
    chart.add('B', 2)
    chart.x_labels = ('red', 'green', 'blue')
    chart1 = chart.render()
    chart = Chart(no_prefix=True)
    chart.add('A', [1])
    chart.add('B', [2])
    chart.x_labels = ('red', 'green', 'blue')
    chart2 = chart.render()
    assert chart1 == chart2


def test_iterable_types(Chart):
    chart = Chart(no_prefix=True)
    chart.add('A', [1, 2])
    chart.add('B', [])
    chart.x_labels = ('red', 'green', 'blue')
    chart1 = chart.render()

    chart = Chart(no_prefix=True)
    chart.add('A', (1, 2))
    chart.add('B', tuple())
    chart.x_labels = ('red', 'green', 'blue')
    chart2 = chart.render()
    assert chart1 == chart2


def test_values_by_dict(Chart):
    chart1 = Chart(no_prefix=True)
    chart2 = Chart(no_prefix=True)

    if not issubclass(Chart, (
            pygal.Worldmap,
            pygal.FrenchMap_Departments,
            pygal.FrenchMap_Regions)):
        chart1.add('A', {'red': 10, 'green': 12, 'blue': 14})
        chart1.add('B', {'green': 11, 'red': 7})
        chart1.add('C', {'blue': 7})
        chart1.add('D', {})
        chart1.add('E', {'blue': 2, 'red': 13})
        chart1.x_labels = ('red', 'green', 'blue')

        chart2.add('A', [10, 12, 14])
        chart2.add('B', [7, 11])
        chart2.add('C', [None, None, 7])
        chart2.add('D', [])
        chart2.add('E', [13, None, 2])
        chart2.x_labels = ('red', 'green', 'blue')
    else:
        chart1.add('A', {'fr': 10, 'us': 12, 'jp': 14})
        chart1.add('B', {'cn': 99})
        chart1.add('C', {})

        chart2.add('A', [('fr', 10), ('us', 12), ('jp', 14)])
        chart2.add('B', [('cn', 99)])
        chart2.add('C', [None, (None, None)])

    assert chart1.render() == chart2.render()


def test_no_data_with_no_values(Chart):
    chart = Chart()
    q = chart.render_pyquery()
    assert q(".text-overlay text").text() == "No data"


def test_no_data_with_no_values_with_include_x_axis(Chart):
    chart = Chart(include_x_axis=True)
    q = chart.render_pyquery()
    assert q(".text-overlay text").text() == "No data"


def test_no_data_with_empty_serie(Chart):
    chart = Chart()
    chart.add('Serie', [])
    q = chart.render_pyquery()
    assert q(".text-overlay text").text() == "No data"


def test_no_data_with_empty_series(Chart):
    chart = Chart()
    chart.add('Serie1', [])
    chart.add('Serie2', [])
    q = chart.render_pyquery()
    assert q(".text-overlay text").text() == "No data"


def test_no_data_with_none(Chart):
    chart = Chart()
    chart.add('Serie', None)
    q = chart.render_pyquery()
    assert q(".text-overlay text").text() == "No data"


def test_no_data_with_list_of_none(Chart):
    chart = Chart()
    chart.add('Serie', [None])
    q = chart.render_pyquery()
    assert q(".text-overlay text").text() == "No data"


def test_no_data_with_lists_of_nones(Chart):
    chart = Chart()
    chart.add('Serie1', [None, None, None, None])
    chart.add('Serie2', [None, None, None])
    q = chart.render_pyquery()
    assert q(".text-overlay text").text() == "No data"


def test_unicode_labels_decode(Chart):
    chart = Chart()
    chart.add(u('Série1'), [{
        'value': 1,
        'xlink': 'http://1/',
        'label': u('{\}Â°ĳæð©&×&<—×€¿_…\{_…')
    }, {
        'value': 2,
        'xlink': {
            'href': 'http://6.example.com/'
        },
        'label': u('æÂ°€≠|€æÂ°€əæ')
    }, {
        'value': 3,
        'label': 'unicode <3'
    }])
    chart.x_labels = [u('&œ'), u('¿?'), u('††††††††'), 'unicode <3']
    chart.render_pyquery()


def test_unicode_labels_python2(Chart):
    if sys.version_info[0] == 3:
        return
    chart = Chart()
    chart.add(u('Série1'), [{
        'value': 1,
        'xlink': 'http://1/',
        'label': eval("u'{\}Â°ĳæð©&×&<—×€¿_…\{_…'")
    }, {
        'value': 2,
        'xlink': {
            'href': 'http://6.example.com/'
        },
        'label': eval("u'æÂ°€≠|€æÂ°€əæ'")
    }, {
        'value': 3,
        'label': eval("'unicode <3'")
    }])
    chart.x_labels = eval("[u'&œ', u'¿?', u'††††††††', 'unicode <3']")
    chart.render_pyquery()


def test_unicode_labels_python3(Chart):
    if sys.version_info[0] == 2:
        return
    chart = Chart()
    chart.add(u('Série1'), [{
        'value': 1,
        'xlink': 'http://1/',
        'label': eval("'{\}Â°ĳæð©&×&<—×€¿_…\{_…'")
    }, {
        'value': 2,
        'xlink': {
            'href': 'http://6.example.com/'
        },
        'label': eval("'æÂ°€≠|€æÂ°€əæ'")
    }, {
        'value': 3,
        'label': eval("b'unicode <3'")
    }])
    chart.x_labels = eval("['&œ', '¿?', '††††††††', 'unicode <3']")
    chart.render_pyquery()


def test_labels_with_links(Chart):
    chart = Chart()
    # link on chart and label
    chart.add({
        'title': 'Red', 'xlink': {'href': 'http://en.wikipedia.org/wiki/Red'}
    }, [{
        'value': 2,
        'label': 'This is red',
        'xlink': {'href': 'http://en.wikipedia.org/wiki/Red'}}])

    # link on chart only
    chart.add('Green', [{
        'value': 4,
        'label': 'This is green',
        'xlink': {
            'href': 'http://en.wikipedia.org/wiki/Green',
            'target': '_top'}}])

    # link on label only opens in new tab
    chart.add({'title': 'Yellow', 'xlink': {
        'href': 'http://en.wikipedia.org/wiki/Yellow',
        'target': '_blank'}}, 7)

    # link on chart only
    chart.add('Blue', [{
        'value': 5,
        'xlink': {
            'href': 'http://en.wikipedia.org/wiki/Blue',
            'target': '_blank'}}])

    # link on label and chart with diffrent behaviours
    chart.add({
        'title': 'Violet',
        'xlink': 'http://en.wikipedia.org/wiki/Violet_(color)'
    }, [{
        'value': 3,
        'label': 'This is violet',
        'xlink': {
            'href': 'http://en.wikipedia.org/wiki/Violet_(color)',
            'target': '_self'}}])

    q = chart.render_pyquery()
    links = q('a')

    if issubclass(chart.cls,
                  (pygal.graph.worldmap.Worldmap,
                   pygal.graph.frenchmap.FrenchMapDepartments)):
        # No country is found in this case so:
        assert len(links) == 4  # 3 links and 1 tooltip
    else:
        assert len(links) == 8  # 7 links and 1 tooltip


def test_sparkline(Chart, datas):
    chart = Chart()
    chart = make_data(chart, datas)
    assert chart.render_sparkline()


def test_secondary(Chart):
    chart = Chart()
    rng = [83, .12, -34, 59]
    chart.add('First serie', rng)
    chart.add('Secondary serie',
              map(lambda x: x * 2, rng),
              secondary=True)
    assert chart.render_pyquery()


def test_ipython_notebook(Chart, datas):
    chart = Chart()
    chart = make_data(chart, datas)
    assert chart._repr_svg_()


def test_long_title(Chart, datas):
    chart = Chart(
        title="A chart is a graphical representation of data, in which "
        "'the data is represented by symbols, such as bars in a bar chart, "
        "lines in a line chart, or slices in a pie chart'. A chart can "
        "represent tabular numeric data, functions or some kinds of "
        "qualitative structure and provides different info.")
    chart = make_data(chart, datas)
    q = chart.render_pyquery()
    assert len(q('.titles text')) == 5

########NEW FILE########
__FILENAME__ = test_histogram
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.

from pygal import Histogram


def test_histogram():
    hist = Histogram()
    hist.add('1', [
        (2, 0, 1),
        (4, 1, 3),
        (3, 3.5, 5),
        (1.5, 5, 10)
    ])
    hist.add('2', [(2, 2, 8)], secondary=True)
    q = hist.render_pyquery()
    assert len(q('.rect')) == 5

########NEW FILE########
__FILENAME__ = test_interpolate
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.

from pygal.test import pytest_generate_tests, make_data


def test_cubic(Chart, datas):
    chart = Chart(interpolate='cubic')
    chart = make_data(chart, datas)
    assert chart.render()


def test_cubic_prec(Chart, datas):
    chart = Chart(interpolate='cubic', interpolation_precision=200)
    chart = make_data(chart, datas)

    chart_low = Chart(interpolate='cubic', interpolation_precision=5)
    chart_low = make_data(chart, datas)

    assert len(chart.render()) >= len(chart_low.render())


def test_quadratic(Chart, datas):
    chart = Chart(interpolate='quadratic')
    chart = make_data(chart, datas)
    assert chart.render()


def test_lagrange(Chart, datas):
    chart = Chart(interpolate='lagrange')
    chart = make_data(chart, datas)
    assert chart.render()


def test_trigonometric(Chart, datas):
    chart = Chart(interpolate='trigonometric')
    chart = make_data(chart, datas)
    assert chart.render()


def test_hermite(Chart, datas):
    chart = Chart(interpolate='hermite')
    chart = make_data(chart, datas)
    assert chart.render()


def test_hermite_finite(Chart, datas):
    chart = Chart(interpolate='hermite',
                  interpolation_parameters={'type': 'finite_difference'})
    chart = make_data(chart, datas)
    assert chart.render()


def test_hermite_cardinal(Chart, datas):
    chart = Chart(interpolate='hermite',
                  interpolation_parameters={'type': 'cardinal',  'c': .75})
    chart = make_data(chart, datas)
    assert chart.render()

def test_hermite_catmull_rom(Chart, datas):
    chart = Chart(interpolate='hermite',
                  interpolation_parameters={'type': 'catmull_rom'})
    chart = make_data(chart, datas)
    assert chart.render()


def test_hermite_kochanek_bartels(Chart, datas):
    chart = Chart(interpolate='hermite',
                  interpolation_parameters={
                      'type': 'kochanek_bartels', 'b': -1, 'c': 1, 't': 1})
    chart = make_data(chart, datas)
    assert chart.render()

    chart = Chart(interpolate='hermite',
                  interpolation_parameters={
                      'type': 'kochanek_bartels', 'b': -1, 'c': -8, 't': 0})
    chart = make_data(chart, datas)
    assert chart.render()

    chart = Chart(interpolate='hermite',
                  interpolation_parameters={
                      'type': 'kochanek_bartels', 'b': 0, 'c': 10, 't': -1})
    chart = make_data(chart, datas)
    assert chart.render()

########NEW FILE########
__FILENAME__ = test_line
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
from __future__ import division
from pygal import Line
from pygal.test.utils import texts
from math import cos, sin


def test_simple_line():
    line = Line()
    rng = range(-30, 31, 5)
    line.add('test1', [cos(x / 10) for x in rng])
    line.add('test2', [sin(x / 10) for x in rng])
    line.add('test3', [cos(x / 10) - sin(x / 10) for x in rng])
    line.x_labels = map(str, rng)
    line.title = "cos sin and cos - sin"
    q = line.render_pyquery()
    assert len(q(".axis.x")) == 1
    assert len(q(".axis.y")) == 1
    assert len(q(".plot .series path")) == 3
    assert len(q(".legend")) == 3
    assert len(q(".x.axis .guides")) == 13
    assert len(q(".y.axis .guides")) == 13
    assert len(q(".dots")) == 3 * 13
    assert q(".axis.x text").map(texts) == [
        '-30', '-25', '-20', '-15', '-10', '-5',
        '0', '5', '10', '15', '20', '25', '30']
    assert q(".axis.y text").map(texts) == [
        '-1.2', '-1.0', '-0.8', '-0.6', '-0.4', '-0.2',
        '0.0', '0.2', '0.4', '0.6', '0.8', '1.0', '1.2']
    assert q(".title").text() == 'cos sin and cos - sin'
    assert q(".legend text").map(texts) == ['test1', 'test2', 'test3']


def test_line():
    line = Line()
    rng = [8, 12, 23, 73, 39, 57]
    line.add('Single serie', rng)
    line.title = "One serie"
    q = line.render_pyquery()
    assert len(q(".axis.x")) == 0
    assert len(q(".axis.y")) == 1
    assert len(q(".plot .series path")) == 1
    assert len(q(".x.axis .guides")) == 0
    assert len(q(".y.axis .guides")) == 7


def test_one_dot():
    line = Line()
    line.add('one dot', [12])
    line.x_labels = ['one']
    q = line.render_pyquery()
    assert len(q(".axis.x")) == 1
    assert len(q(".axis.y")) == 1
    assert len(q(".y.axis .guides")) == 1


def test_no_dot():
    line = Line()
    line.add('no dot', [])
    q = line.render_pyquery()
    assert q(".text-overlay text").text() == 'No data'


def test_no_dot_at_all():
    q = Line().render_pyquery()
    assert q(".text-overlay text").text() == 'No data'


def test_not_equal_x_labels():
    line = Line()
    line.add('test1', range(100))
    line.x_labels = map(str, range(11))
    q = line.render_pyquery()
    assert len(q(".dots")) == 100
    assert len(q(".axis.x")) == 1
    assert q(".axis.x text").map(texts) == ['0', '1', '2', '3', '4', '5', '6',
                                            '7', '8', '9', '10']


def test_only_major_dots_every():
    line = Line(show_only_major_dots=True, x_labels_major_every=3)
    line.add('test', range(12))
    line.x_labels = map(str, range(12))
    q = line.render_pyquery()
    assert len(q(".dots")) == 4


def test_only_major_dots_no_labels():
    line = Line(show_only_major_dots=True)
    line.add('test', range(12))
    q = line.render_pyquery()
    assert len(q(".dots")) == 12


def test_only_major_dots_count():
    line = Line(show_only_major_dots=True)
    line.add('test', range(12))
    line.x_labels = map(str, range(12))
    line.x_labels_major_count = 2
    q = line.render_pyquery()
    assert len(q(".dots")) == 2


def test_only_major_dots():
    line = Line(show_only_major_dots=True,)
    line.add('test', range(12))
    line.x_labels = map(str, range(12))
    line.x_labels_major = ['1', '5', '11']
    q = line.render_pyquery()
    assert len(q(".dots")) == 3


def test_line_secondary():
    line = Line()
    rng = [8, 12, 23, 73, 39, 57]
    line.add('First serie', rng)
    line.add('Secondary serie',
             map(lambda x: x * 2, rng),
             secondary=True)
    line.title = "One serie"
    q = line.render_pyquery()
    assert len(q(".axis.x")) == 0
    assert len(q(".axis.y")) == 1
    assert len(q(".plot .series path")) == 2
    assert len(q(".x.axis .guides")) == 0
    assert len(q(".y.axis .guides")) == 7

########NEW FILE########
__FILENAME__ = test_map
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.

from pygal import (
    Worldmap, SupranationalWorldmap)
from pygal.i18n import COUNTRIES, SUPRANATIONAL, set_countries
import operator
try:
    from functools import reduce
except ImportError:
    pass

_COUNTRIES = dict(COUNTRIES)


def test_worldmap():
    set_countries(_COUNTRIES, True)
    datas = {}
    for i, ctry in enumerate(COUNTRIES):
        datas[ctry] = i

    wmap = Worldmap()
    wmap.add('countries', datas)
    q = wmap.render_pyquery()
    assert len(
        q('.country.color-0')
    ) == len(COUNTRIES)
    assert 'France' in q('#fr').text()


def test_worldmap_i18n():
    set_countries(_COUNTRIES, True)
    datas = {}
    for i, ctry in enumerate(COUNTRIES):
        datas[ctry] = i

    set_countries({'fr': 'Francia'})
    wmap = Worldmap()
    wmap.add('countries', datas)
    q = wmap.render_pyquery()
    assert len(
        q('.country.color-0')
    ) == len(COUNTRIES)
    assert 'Francia' in q('#fr').text()


def test_worldmap_i18n_clear():
    set_countries(_COUNTRIES, True)
    wmap = Worldmap()
    wmap.add('countries', dict(fr=12))
    set_countries({'fr': 'Frankreich'}, clear=True)
    q = wmap.render_pyquery()
    assert len(
        q('.country.color-0')
    ) == 1
    assert 'Frankreich' in q('#fr').text()


def test_supranationalworldmap():
    set_countries(_COUNTRIES, True)
    datas = {}
    for i, supra in enumerate(SUPRANATIONAL):
        datas[supra] = i + 1

    wmap = SupranationalWorldmap()
    wmap.add('supra', datas)
    q = wmap.render_pyquery()
    assert len(
        q('.country.color-0')
    ) == len(
        reduce(operator.or_, map(set, SUPRANATIONAL.values())))

########NEW FILE########
__FILENAME__ = test_pie
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
import os
import uuid
from pygal import Pie


def test_donut():
    chart = Pie(inner_radius=.3, pretty_print=True)
    chart.title = 'Browser usage in February 2012 (in %)'
    chart.add('IE', 19.5)
    chart.add('Firefox', 36.6)
    chart.add('Chrome', 36.3)
    chart.add('Safari', 4.5)
    chart.add('Opera', 2.3)
    assert chart.render()


def test_multiseries_donut():
    # this just demos that the multiseries pie does not respect
    # the inner_radius
    chart = Pie(inner_radius=.3, pretty_print=True)
    chart.title = 'Browser usage by version in February 2012 (in %)'
    chart.add('IE', [5.7, 10.2, 2.6, 1])
    chart.add('Firefox', [.6, 16.8, 7.4, 2.2, 1.2, 1, 1, 1.1, 4.3, 1])
    chart.add('Chrome', [.3, .9, 17.1, 15.3, .6, .5, 1.6])
    chart.add('Safari', [4.4, .1])
    chart.add('Opera', [.1, 1.6, .1, .5])
    assert chart.render()


def test_half_pie():
    pie = Pie()
    pie.add('IE', 19.5)
    pie.add('Firefox', 36.6)
    pie.add('Chrome', 36.3)
    pie.add('Safari', 4.5)
    pie.add('Opera', 2.3)

    half = Pie(half_pie=True)
    half.add('IE', 19.5)
    half.add('Firefox', 36.6)
    half.add('Chrome', 36.3)
    half.add('Safari', 4.5)
    half.add('Opera', 2.3)
    assert pie.render() != half.render()

########NEW FILE########
__FILENAME__ = test_serie_config
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.

from pygal.test import pytest_generate_tests
from pygal import Line


def test_serie_config():
    s1 = [1, 3, 12, 3, 4]
    s2 = [7, -4, 10, None, 8, 3, 1]

    chart = Line()
    chart.add('1', s1)
    chart.add('2', s2)
    q = chart.render_pyquery()
    assert len(q('.serie-0 .line')) == 1
    assert len(q('.serie-1 .line')) == 1
    assert len(q('.serie-0 .dot')) == 5
    assert len(q('.serie-1 .dot')) == 6

    chart = Line(stroke=False)
    chart.add('1', s1)
    chart.add('2', s2)
    q = chart.render_pyquery()
    assert len(q('.serie-0 .line')) == 0
    assert len(q('.serie-1 .line')) == 0
    assert len(q('.serie-0 .dot')) == 5
    assert len(q('.serie-1 .dot')) == 6

    chart = Line()
    chart.add('1', s1, stroke=False)
    chart.add('2', s2)
    q = chart.render_pyquery()
    assert len(q('.serie-0 .line')) == 0
    assert len(q('.serie-1 .line')) == 1
    assert len(q('.serie-0 .dot')) == 5
    assert len(q('.serie-1 .dot')) == 6

    chart = Line(stroke=False)
    chart.add('1', s1, stroke=True)
    chart.add('2', s2)
    q = chart.render_pyquery()
    assert len(q('.serie-0 .line')) == 1
    assert len(q('.serie-1 .line')) == 0
    assert len(q('.serie-0 .dot')) == 5
    assert len(q('.serie-1 .dot')) == 6

########NEW FILE########
__FILENAME__ = test_sparktext
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
from pygal import Line, Bar
from pygal._compat import u


def test_basic_sparktext():
    chart = Line()
    chart.add('_', [1, 5, 22, 13, 53])
    assert chart.render_sparktext() == u('▁▁▃▂█')


def test_all_sparktext():
    chart = Line()
    chart.add('_', range(8))
    assert chart.render_sparktext() == u('▁▂▃▄▅▆▇█')


def test_shifted_sparktext():
    chart = Line()
    chart.add('_', list(map(lambda x: x + 10000, range(8))))
    assert chart.render_sparktext() == u('▁▂▃▄▅▆▇█')
    assert chart.render_sparktext(relative_to=0) == u('▇▇▇▇▇▇▇█')


def test_another_sparktext():
    chart = Line()
    chart.add('_', [0, 30, 55, 80, 33, 150])
    assert chart.render_sparktext() == u('▁▂▃▄▂█')
    assert chart.render_sparktext() == chart.render_sparktext()
    chart2 = Bar()
    chart2.add('_', [0, 30, 55, 80, 33, 150])
    assert chart2.render_sparktext() == chart.render_sparktext()


def test_negative_and_float_and_no_data_sparktext():
    chart = Line()
    chart.add('_', [0.1, 0.2, 0.9, -0.5])
    assert chart.render_sparktext() == u('▁▂█▁')

    chart2 = Line()
    chart2.add('_', [])
    assert chart2.render_sparktext() == u('')

    chart3 = Line()
    assert chart3.render_sparktext() == u('')


def test_same_max_and_relative_values_sparktext():
    chart = Line()
    chart.add('_', [0, 0, 0, 0, 0])
    assert chart.render_sparktext() == u('▁▁▁▁▁')

    chart2 = Line()
    chart2.add('_', [1, 1, 1, 1, 1])
    assert chart2.render_sparktext(relative_to=1) == u('▁▁▁▁▁')

########NEW FILE########
__FILENAME__ = test_stacked
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
from pygal import StackedLine


def test_stacked_line():
    stacked = StackedLine()
    stacked.add('one_two', [1, 2])
    stacked.add('ten_twelve', [10, 12])
    q = stacked.render_pyquery()
    assert set(q("desc.value").text().split(' ')) == set(
        ('1', '2', '11', '14'))


def test_stacked_line_log():
    stacked = StackedLine(logarithmic=True)
    stacked.add('one_two', [1, 2])
    stacked.add('ten_twelve', [10, 12])
    q = stacked.render_pyquery()
    assert set(q("desc.value").text().split(' ')) == set(
        ('1', '2', '11', '14'))


def test_stacked_line_interpolate():
    stacked = StackedLine(interpolate='cubic')
    stacked.add('one_two', [1, 2])
    stacked.add('ten_twelve', [10, 12])
    q = stacked.render_pyquery()
    assert set(q("desc.value").text().split(' ')) == set(
        ('1', '2', '11', '14'))

########NEW FILE########
__FILENAME__ = test_style
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
from pygal import Line
from pygal.style import (
    LightStyle,
    LightenStyle, DarkenStyle, SaturateStyle, DesaturateStyle, RotateStyle
)

STYLES = LightenStyle, DarkenStyle, SaturateStyle, DesaturateStyle, RotateStyle


def test_parametric_styles():
    chart = None
    for style in STYLES:
        line = Line(style=style('#f4e83a'))
        line.add('_', [1, 2, 3])
        line.x_labels = 'abc'
        new_chart = line.render()
        assert chart != new_chart
        chart = new_chart


def test_parametric_styles_with_parameters():
    line = Line(style=RotateStyle(
        '#de3804', step=12, max_=180, base_style=LightStyle))
    line.add('_', [1, 2, 3])
    line.x_labels = 'abc'
    assert line.render()

########NEW FILE########
__FILENAME__ = test_table
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
from pygal import Pie
from pyquery import PyQuery as pq


def test_pie_table():
    chart = Pie(inner_radius=.3, pretty_print=True)
    chart.title = 'Browser usage in February 2012 (in %)'
    chart.add('IE', 19.5)
    chart.add('Firefox', 36.6)
    chart.add('Chrome', 36.3)
    chart.add('Safari', 4.5)
    chart.add('Opera', 2.3)
    q = pq(chart.render_table())
    assert len(q('table')) == 1

########NEW FILE########
__FILENAME__ = test_util
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
from pygal._compat import u
from pygal.util import (
    round_to_int, round_to_float, _swap_curly, template, humanize,
    truncate, minify_css, majorize)
from pytest import raises


def test_round_to_int():
    assert round_to_int(154231, 1000) == 154000
    assert round_to_int(154231, 10) == 154230
    assert round_to_int(154231, 100000) == 200000
    assert round_to_int(154231, 50000) == 150000
    assert round_to_int(154231, 500) == 154000
    assert round_to_int(154231, 200) == 154200
    assert round_to_int(154361, 200) == 154400


def test_round_to_float():
    assert round_to_float(12.01934, .01) == 12.02
    assert round_to_float(12.01134, .01) == 12.01
    assert round_to_float(12.1934, .1) == 12.2
    assert round_to_float(12.1134, .1) == 12.1
    assert round_to_float(12.1134, .001) == 12.113
    assert round_to_float(12.1134, .00001) == 12.1134
    assert round_to_float(12.1934, .5) == 12.0
    assert round_to_float(12.2934, .5) == 12.5


def test_swap_curly():
    for str in (
            'foo',
            u('foo foo foo bar'),
            'foo béè b¡ð/ĳə˘©þß®~¯æ',
            u('foo béè b¡ð/ĳə˘©þß®~¯æ')):
        assert _swap_curly(str) == str
    assert _swap_curly('foo{bar}baz') == 'foo{{bar}}baz'
    assert _swap_curly('foo{{bar}}baz') == 'foo{bar}baz'
    assert _swap_curly('{foo}{{bar}}{baz}') == '{{foo}}{bar}{{baz}}'
    assert _swap_curly('{foo}{{{bar}}}{baz}') == '{{foo}}{{{bar}}}{{baz}}'
    assert _swap_curly('foo{ bar }baz') == 'foo{{ bar }}baz'
    assert _swap_curly('foo{ bar}baz') == 'foo{{ bar}}baz'
    assert _swap_curly('foo{bar }baz') == 'foo{{bar }}baz'
    assert _swap_curly('foo{{ bar }}baz') == 'foo{bar}baz'
    assert _swap_curly('foo{{bar }}baz') == 'foo{bar}baz'
    assert _swap_curly('foo{{ bar}}baz') == 'foo{bar}baz'


def test_format():
    assert template('foo {{ baz }}', baz='bar') == 'foo bar'
    with raises(KeyError):
        assert template('foo {{ baz }}') == 'foo baz'

    class Object(object):
        pass
    obj = Object()
    obj.a = 1
    obj.b = True
    obj.c = '3'
    assert template(
        'foo {{ o.a }} {{o.b}}-{{o.c}}',
        o=obj) == 'foo 1 True-3'


def test_humanize():
    assert humanize(1) == '1'
    assert humanize(1.) == '1'
    assert humanize(10) == '10'
    assert humanize(12.5) == '12.5'
    assert humanize(1000) == '1k'
    assert humanize(5000) == '5k'
    assert humanize(100000) == '100k'
    assert humanize(1253) == '1.253k'
    assert humanize(1250) == '1.25k'

    assert humanize(0.1) == '100m'
    assert humanize(0.01) == '10m'
    assert humanize(0.001) == '1m'
    assert humanize(0.002) == '2m'
    assert humanize(0.0025) == '2.5m'
    assert humanize(0.0001) == u('100µ')
    assert humanize(0.000123) == u('123µ')
    assert humanize(0.00001) == u('10µ')
    assert humanize(0.000001) == u('1µ')
    assert humanize(0.0000001) == u('100n')
    assert humanize(0.0000000001) == u('100p')

    assert humanize(0) == '0'
    assert humanize(0.) == '0'
    assert humanize(-1337) == '-1.337k'
    assert humanize(-.000000042) == '-42n'


def test_truncate():
    assert truncate('1234567890', 50) == '1234567890'
    assert truncate('1234567890', 5) == u('1234…')
    assert truncate('1234567890', 1) == u('…')
    assert truncate('1234567890', 9) == u('12345678…')
    assert truncate('1234567890', 10) == '1234567890'
    assert truncate('1234567890', 0) == '1234567890'
    assert truncate('1234567890', -1) == '1234567890'


def test_minify_css():
    css = '''
/*
 * Font-sizes from config, override with care
 */

.title  {
  font-family: sans;

  font-size:  12 ;
}

.legends .legend text {
  font-family: monospace;
  font-size: 14 ;}
'''
    assert minify_css(css) == (
        '.title{font-family:sans;font-size:12}'
        '.legends .legend text{font-family:monospace;font-size:14}')


def test_major():
    assert majorize(()) == []
    assert majorize((0,)) == []
    assert majorize((0, 1)) == []
    assert majorize((0, 1, 2)) == []
    assert majorize((-1, 0, 1, 2)) == [0]
    assert majorize((0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1)) == [0, .5, 1]
    assert majorize((0, .2, .4, .6, .8, 1)) == [0, 1]
    assert majorize((-.4, -.2, 0, .2, .4, .6, .8, 1)) == [0, 1]
    assert majorize(
        (-1, -.8, -.6, -.4, -.2, 0, .2, .4, .6, .8, 1)) == [-1, 0, 1]
    assert majorize((0, .2, .4, .6, .8, 1, 1.2, 1.4, 1.6)) == [0, 1]
    assert majorize((0, .2, .4, .6, .8, 1, 1.2, 1.4, 1.6, 1.8, 2)) == [0, 1, 2]
    assert majorize(
        (0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120)) == [0, 50, 100]
    assert majorize(
        (0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20,
         22, 24, 26, 28, 30, 32, 34, 36)) == [0, 10, 20, 30]
    assert majorize((0, 1, 2, 3, 4, 5)) == [0, 5]
    assert majorize((-5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5)) == [-5, 0, 5]
    assert majorize((-5, 5, -4, 4, 0, 1, -1, 3, -2, 2, -3)) == [-5, 0, 5]
    assert majorize((0, 1, 2, 3, 4)) == [0]
    assert majorize((3, 4, 5, 6)) == [5]
    assert majorize((0, 1, 2, 3, 4, 5, 6, 7, 8)) == [0, 5]
    assert majorize((-5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5)) == [-5, 0, 5]
    assert majorize((-6, -5, -4, -3, -2, -1, 0, 1, 2, 3)) == [-5, 0]
    assert majorize((-6, -5, -4, -3)) == [-5]
    assert majorize((1, 10, 100, 1000, 10000, 100000)) == []
    assert majorize(range(30, 70, 5)) == [30, 40, 50, 60]
    assert majorize(range(20, 55, 2)) == [20, 30, 40, 50]
    assert majorize(range(21, 83, 3)) == [30, 45, 60, 75]
    # TODO: handle crazy cases
    # assert majorize(range(20, 83, 3)) == [20, 35, 50, 65, 80]

########NEW FILE########
__FILENAME__ = test_view
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.

from pygal.test import pytest_generate_tests, make_data


def test_all_logarithmic(Chart):
    chart = Chart(logarithmic=True)
    chart.add('1', [1, 30, 8, 199, -23])
    chart.add('2', [87, 42, .9, 189, 81])
    assert chart.render()

########NEW FILE########
__FILENAME__ = test_xml_filters
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
from pygal import Bar

class ChangeBarsXMLFilter(object):
    def __init__(self, a, b):
        self.data = [b[i] - a[i] for i in range(len(a))]

    def __call__(self, T):
        subplot = Bar(legend_at_bottom=True, explicit_size=True, width=800, height=150)
        subplot.add("Difference", self.data)
        subplot = subplot.render_tree()
        subplot = subplot.xpath("g")[0]
        T.insert(2, subplot)
        T.xpath("g")[1].set('transform', 'translate(0,150), scale(1,0.75)')
        return T

def test_xml_filters_round_trip():
    plot = Bar()
    plot.add("A", [60, 75, 80, 78, 83, 90])
    plot.add("B", [92, 87, 81, 73, 68, 55])
    before = plot.render()
    plot.add_xml_filter(lambda T: T)
    after = plot.render()
    assert before == after

def test_xml_filters_change_bars():
    plot = Bar(legend_at_bottom=True, explicit_size=True, width=800, height=600)
    A = [60, 75, 80, 78, 83, 90]
    B = [92, 87, 81, 73, 68, 55]
    plot.add("A", A)
    plot.add("B", B)
    plot.add_xml_filter(ChangeBarsXMLFilter(A,B))
    q = plot.render_tree()
    assert len(q.xpath("g")) == 2
    assert q.xpath("g")[1].attrib["transform"] == "translate(0,150), scale(1,0.75)"

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
from pyquery import PyQuery as pq


def texts(i, e):
    return pq(e).text()

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Various utils

"""
from __future__ import division
from pygal._compat import to_str, u, is_list_like
import re
from decimal import Decimal
from math import floor, pi, log, log10, ceil
from itertools import cycle
from functools import reduce
from pygal.adapters import not_zero, positive
ORDERS = u("yzafpnµm kMGTPEZY")


def float_format(number):
    """Format a float to a precision of 3, without zeroes or dots"""
    return ("%.3f" % number).rstrip('0').rstrip('.')


def humanize(number):
    """Format a number to engineer scale"""
    order = number and int(floor(log(abs(number)) / log(1000)))
    human_readable = ORDERS.split(" ")[int(order > 0)]
    if order == 0 or order > len(human_readable):
        return float_format(number / (1000 ** int(order)))
    return (
        float_format(number / (1000 ** int(order))) +
        human_readable[int(order) - int(order > 0)])


def majorize(values):
    """Filter sequence to return only major considered numbers"""
    sorted_values = sorted(values)
    if len(values) <= 3 or (
            abs(2 * sorted_values[1] - sorted_values[0] - sorted_values[2]) >
            abs(1.5 * (sorted_values[1] - sorted_values[0]))):
        return []
    values_step = sorted_values[1] - sorted_values[0]
    full_range = sorted_values[-1] - sorted_values[0]
    step = 10 ** int(log10(full_range))
    if step == values_step:
        step *= 10
    step_factor = 10 ** (int(log10(step)) + 1)
    if round(step * step_factor) % (round(values_step * step_factor) or 1):
        # TODO: Find lower common multiple instead
        step *= values_step
    if full_range <= 2 * step:
        step *= .5
    elif full_range >= 5 * step:
        step *= 5
    major_values = [
        value for value in values if value / step == round(value / step)]
    return [value for value in sorted_values if value in major_values]


def round_to_int(number, precision):
    """Round a number to a precision"""
    precision = int(precision)
    rounded = (int(number) + precision / 2) // precision * precision
    return rounded


def round_to_float(number, precision):
    """Round a float to a precision"""
    rounded = Decimal(
        str(floor((number + precision / 2) // precision))
    ) * Decimal(str(precision))
    return float(rounded)


def round_to_scale(number, precision):
    """Round a number or a float to a precision"""
    if precision < 1:
        return round_to_float(number, precision)
    return round_to_int(number, precision)


def cut(list_, index=0):
    """Cut a list by index or arg"""
    if isinstance(index, int):
        cut_ = lambda x: x[index]
    else:
        cut_ = lambda x: getattr(x, index)
    return list(map(cut_, list_))


def rad(degrees):
    """Convert degrees in radiants"""
    return pi * degrees / 180


def deg(radiants):
    """Convert radiants in degrees"""
    return 180 * radiants / pi


def _swap_curly(string):
    """Swap single and double curly brackets"""
    return (string
            .replace('{{ ', '{{')
            .replace('{{', '\x00')
            .replace('{', '{{')
            .replace('\x00', '{')
            .replace(' }}', '}}')
            .replace('}}', '\x00')
            .replace('}', '}}')
            .replace('\x00', '}'))


def template(string, **kwargs):
    """Format a string using double braces"""
    return _swap_curly(string).format(**kwargs)


def coord_format(xy):
    """Format x y coords to svg"""
    return '%f %f' % xy

swap = lambda tuple_: tuple(reversed(tuple_))
ident = lambda x: x


def compute_logarithmic_scale(min_, max_, min_scale, max_scale):
    """Compute an optimal scale for logarithmic"""
    if max_ <= 0 or min_ <= 0:
        return []
    min_order = int(floor(log10(min_)))
    max_order = int(ceil(log10(max_)))
    positions = []
    amplitude = max_order - min_order
    if amplitude <= 1:
        return []
    detail = 10.
    while amplitude * detail < min_scale * 5:
        detail *= 2
    while amplitude * detail > max_scale * 3:
        detail /= 2
    for order in range(min_order, max_order + 1):
        for i in range(int(detail)):
            tick = (10 * i / detail or 1) * 10 ** order
            tick = round_to_scale(tick, tick)
            if min_ <= tick <= max_ and tick not in positions:
                positions.append(tick)
    return positions


def compute_scale(
        min_, max_, logarithmic=False, order_min=None,
        min_scale=4, max_scale=20):
    """Compute an optimal scale between min and max"""
    if min_ == 0 and max_ == 0:
        return [0]
    if max_ - min_ == 0:
        return [min_]
    if logarithmic:
        log_scale = compute_logarithmic_scale(
            min_, max_, min_scale, max_scale)
        if log_scale:
            return log_scale
            # else we fallback to normal scalling
    order = round(log10(max(abs(min_), abs(max_)))) - 1
    if order_min is not None and order < order_min:
        order = order_min
    else:
        while ((max_ - min_) / (10 ** order) < min_scale and
               (order_min is None or order > order_min)):
            order -= 1
    step = float(10 ** order)
    while (max_ - min_) / step > max_scale:
        step *= 2.
    positions = []
    position = round_to_scale(min_, step)
    while position < (max_ + step):
        rounded = round_to_scale(position, step)
        if min_ <= rounded <= max_:
            if rounded not in positions:
                positions.append(rounded)
        position += step
    if len(positions) < 2:
        return [min_, max_]
    return positions


def text_len(length, fs):
    """Approximation of text width"""
    return length * 0.6 * fs


def reverse_text_len(width, fs):
    """Approximation of text length"""
    return int(width / (0.6 * fs))


def get_text_box(text, fs):
    """Approximation of text bounds"""
    return (fs, text_len(len(text), fs))


def get_texts_box(texts, fs):
    """Approximation of multiple texts bounds"""
    def get_text_title(texts):
        for text in texts:
            if isinstance(text, dict):
                yield text['title']
            else:
                yield text
    max_len = max(map(len, get_text_title(texts)))
    return (fs, text_len(max_len, fs))


def decorate(svg, node, metadata):
    """Add metedata next to a node"""
    if not metadata:
        return node
    xlink = metadata.get('xlink')
    if xlink:
        if not isinstance(xlink, dict):
            xlink = {'href': xlink, 'target': '_blank'}
        node = svg.node(node, 'a', **xlink)

    for key, value in metadata.items():
        if key == 'xlink' and isinstance(value, dict):
            value = value.get('href', value)
        if value:
            svg.node(node, 'desc', class_=key).text = to_str(value)
    return node


def cycle_fill(short_list, max_len):
    """Fill a list to max_len using a cycle of it"""
    short_list = list(short_list)
    list_cycle = cycle(short_list)
    while len(short_list) < max_len:
        short_list.append(next(list_cycle))
    return short_list


def truncate(string, index):
    """Truncate a string at index and add ..."""
    if len(string) > index and index > 0:
        string = string[:index - 1] + u('…')
    return string


# Stolen from brownie http://packages.python.org/Brownie/
class cached_property(object):
    """Optimize a static property"""
    def __init__(self, getter, doc=None):
        self.getter = getter
        self.__module__ = getter.__module__
        self.__name__ = getter.__name__
        self.__doc__ = doc or getter.__doc__

    def __get__(self, obj, type_=None):
        if obj is None:
            return self
        value = obj.__dict__[self.__name__] = self.getter(obj)
        return value

css_comments = re.compile(r'/\*.*?\*/', re.MULTILINE | re.DOTALL)


def minify_css(css):
    # Inspired by slimmer by Peter Bengtsson
    remove_next_comment = 1
    for css_comment in css_comments.findall(css):
        if css_comment[-3:] == '\*/':
            remove_next_comment = 0
            continue
        if remove_next_comment:
            css = css.replace(css_comment, '')
        else:
            remove_next_comment = 1

    # >= 2 whitespace becomes one whitespace
    css = re.sub(r'\s\s+', ' ', css)
    # no whitespace before end of line
    css = re.sub(r'\s+\n', '', css)
    # Remove space before and after certain chars
    for char in ('{', '}', ':', ';', ','):
        css = re.sub(char + r'\s', char, css)
        css = re.sub(r'\s' + char, char, css)
    css = re.sub(r'}\s(#|\w)', r'}\1', css)
    # no need for the ; before end of attributes
    css = re.sub(r';}', r'}', css)
    css = re.sub(r'}//-->', r'}\n//-->', css)
    return css.strip()


def compose(f, g):
    """Chain functions"""
    fun = lambda *args, **kwargs: f(g(*args, **kwargs))
    fun.__name__ = "%s o %s" % (f.__name__, g.__name__)
    return fun


def safe_enumerate(iterable):
    for i, v in enumerate(iterable):
        if v is not None:
            yield i, v


def prepare_values(raw, config, cls):
    """Prepare the values to start with sane values"""
    from pygal.serie import Serie
    from pygal.config import SerieConfig
    from pygal.graph.datey import DateY
    from pygal.graph.histogram import Histogram
    from pygal.graph.worldmap import Worldmap
    from pygal.graph.frenchmap import FrenchMapDepartments
    if config.x_labels is None and hasattr(cls, 'x_labels'):
        config.x_labels = cls.x_labels
    if config.zero == 0 and issubclass(cls, (Worldmap, FrenchMapDepartments)):
        config.zero = 1

    for key in ('x_labels', 'y_labels'):
        if getattr(config, key):
            setattr(config, key, list(getattr(config, key)))
    if not raw:
        return

    adapters = list(cls._adapters) or [lambda x:x]
    if config.logarithmic:
        for fun in not_zero, positive:
            if fun in adapters:
                adapters.remove(fun)
        adapters = adapters + [positive, not_zero]
    adapter = reduce(compose, adapters) if not config.strict else ident
    series = []

    raw = [(
        title,
        list(raw_values) if not isinstance(raw_values, dict) else raw_values,
        serie_config_kwargs
    ) for title, raw_values, serie_config_kwargs in raw]

    width = max([len(values) for _, values, _ in raw] +
                [len(config.x_labels or [])])

    for title, raw_values, serie_config_kwargs in raw:
        metadata = {}
        values = []
        if isinstance(raw_values, dict):
            if issubclass(cls, (Worldmap, FrenchMapDepartments)):
                raw_values = list(raw_values.items())
            else:
                value_list = [None] * width
                for k, v in raw_values.items():
                    if k in config.x_labels:
                        value_list[config.x_labels.index(k)] = v
                raw_values = value_list

        for index, raw_value in enumerate(
                raw_values + (
                    (width - len(raw_values)) * [None]  # aligning values
                    if len(raw_values) < width else [])):
            if isinstance(raw_value, dict):
                raw_value = dict(raw_value)
                value = raw_value.pop('value', None)
                metadata[index] = raw_value
            else:
                value = raw_value

            # Fix this by doing this in charts class methods
            if issubclass(cls, Histogram):
                if value is None:
                    value = (None, None, None)
                elif not is_list_like(value):
                    value = (value, config.zero, config.zero)
                value = list(map(adapter, value))
            elif cls._dual:
                if value is None:
                    value = (None, None)
                elif not is_list_like(value):
                    value = (value, config.zero)
                if issubclass(cls, DateY) or issubclass(
                        cls, (Worldmap, FrenchMapDepartments)):
                    value = (adapter(value[0]), value[1])
                else:
                    value = list(map(adapter, value))
            else:
                value = adapter(value)
            values.append(value)
        serie_config = SerieConfig()
        serie_config(**config.to_dict())
        serie_config(**serie_config_kwargs)
        series.append(Serie(title, values, serie_config, metadata))
    return series


def split_title(title, width, title_fs):
    titles = []
    if not title:
        return titles
    size = reverse_text_len(width, title_fs * 1.1)
    title_lines = title.split("\n")
    for title_line in title_lines:
        while len(title_line) > size:
            title_part = title_line[:size]
            i = title_part.rfind(' ')
            if i == -1:
                i = len(title_part)
            titles.append(title_part[:i])
            title_line = title_line[i:].strip()
        titles.append(title_line)
    return titles

########NEW FILE########
__FILENAME__ = view
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
"""
Projection and bounding helpers
"""

from __future__ import division
from math import sin, cos, log10, pi


class Margin(object):
    """Graph margin"""
    def __init__(self, top, right, bottom, left):
        self.top = top
        self.right = right
        self.bottom = bottom
        self.left = left

    @property
    def x(self):
        """Helper for total x margin"""
        return self.left + self.right

    @property
    def y(self):
        """Helper for total y margin"""
        return self.top + self.bottom


class Box(object):
    """Chart boundings"""
    margin = .02

    def __init__(self, xmin=0, ymin=0, xmax=1, ymax=1):
        self._xmin = xmin
        self._ymin = ymin
        self._xmax = xmax
        self._ymax = ymax

    def set_polar_box(self, rmin=0, rmax=1, tmin=0, tmax=2 * pi):
        self._rmin = rmin
        self._rmax = rmax
        self._tmin = tmin
        self._tmax = tmax
        self.xmin = self.ymin = rmin - rmax
        self.xmax = self.ymax = rmax - rmin

    @property
    def xmin(self):
        return self._xmin

    @xmin.setter
    def xmin(self, value):
        if value:
            self._xmin = value

    @property
    def ymin(self):
        return self._ymin

    @ymin.setter
    def ymin(self, value):
        if value:
            self._ymin = value

    @property
    def xmax(self):
        return self._xmax

    @xmax.setter
    def xmax(self, value):
        if value:
            self._xmax = value

    @property
    def ymax(self):
        return self._ymax

    @ymax.setter
    def ymax(self, value):
        if value:
            self._ymax = value

    @property
    def width(self):
        """Helper for box width"""
        return self.xmax - self.xmin

    @property
    def height(self):
        """Helper for box height"""
        return self.ymax - self.ymin

    def swap(self):
        """Return the box (for horizontal graphs)"""
        self.xmin, self.ymin = self.ymin, self.xmin
        self.xmax, self.ymax = self.ymax, self.xmax

    def fix(self, with_margin=True):
        """Correct box when no values and take margin in account"""
        if not self.width:
            self.xmax = self.xmin + 1
        if not self.height:
            self.ymin -= .5
            self.ymax = self.ymin + 1
        xmargin = self.margin * self.width
        self.xmin -= xmargin
        self.xmax += xmargin
        if with_margin:
            ymargin = self.margin * self.height
            self.ymin -= ymargin
            self.ymax += ymargin


class View(object):
    """Projection base class"""
    def __init__(self, width, height, box):
        self.width = width
        self.height = height
        self.box = box
        self.box.fix()

    def x(self, x):
        """Project x"""
        if x is None:
            return None
        return self.width * (x - self.box.xmin) / self.box.width

    def y(self, y):
        """Project y"""
        if y is None:
            return None
        return (self.height - self.height *
                (y - self.box.ymin) / self.box.height)

    def __call__(self, xy):
        """Project x and y"""
        x, y = xy
        return (self.x(x), self.y(y))


class HorizontalView(View):
    def __init__(self, width, height, box):
        self._force_vertical = None
        self.width = width
        self.height = height

        self.box = box
        self.box.fix()
        self.box.swap()

    def x(self, x):
        """Project x"""
        if x is None:
            return None
        if self._force_vertical:
            return super(HorizontalView, self).x(x)
        return super(HorizontalView, self).y(x)

    def y(self, y):
        if y is None:
            return None
        if self._force_vertical:
            return super(HorizontalView, self).y(y)
        return super(HorizontalView, self).x(y)


class PolarView(View):
    """Polar projection for pie like graphs"""

    def __call__(self, rhotheta):
        """Project rho and theta"""
        if None in rhotheta:
            return None, None
        rho, theta = rhotheta
        return super(PolarView, self).__call__(
            (rho * cos(theta), rho * sin(theta)))


class PolarLogView(View):
    """Logarithmic polar projection"""

    def __init__(self, width, height, box):
        super(PolarLogView, self).__init__(width, height, box)
        if not hasattr(box, '_rmin') or not hasattr(box, '_rmax'):
            raise Exception(
                'Box must be set with set_polar_box for polar charts')
        self.log10_rmax = log10(self.box._rmax)
        self.log10_rmin = log10(self.box._rmin)

    def __call__(self, rhotheta):
        """Project rho and theta"""
        if None in rhotheta:
            return None, None
        rho, theta = rhotheta
        # Center case
        if rho == 0:
            return super(PolarLogView, self).__call__((0, 0))
        rho = (self.box._rmax - self.box._rmin) * (
            log10(rho) - self.log10_rmin) / (
            self.log10_rmax - self.log10_rmin)
        return super(PolarLogView, self).__call__(
            (rho * cos(theta), rho * sin(theta)))


class PolarThetaView(View):
    """Logarithmic polar projection"""

    def __init__(self, width, height, box):
        super(PolarThetaView, self).__init__(width, height, box)
        if not hasattr(box, '_tmin') or not hasattr(box, '_tmax'):
            raise Exception(
                'Box must be set with set_polar_box for polar charts')

    def __call__(self, rhotheta):
        """Project rho and theta"""
        if None in rhotheta:
            return None, None
        rho, theta = rhotheta
        aperture = pi / 3
        if theta > self.box._tmax:
            theta = (3 * pi - aperture / 2) / 2
        elif theta < self.box._tmin:
            theta = (3 * pi + aperture / 2) / 2
        else:
            start = 3 * pi / 2 + aperture / 2
            theta = start + (2 * pi - aperture) * (
                theta - self.box._tmin) / (
                self.box._tmax - self.box._tmin)
        return super(PolarThetaView, self).__call__(
            (rho * cos(theta), rho * sin(theta)))


class PolarThetaLogView(View):
    """Logarithmic polar projection"""

    def __init__(self, width, height, box):
        super(PolarThetaLogView, self).__init__(width, height, box)
        if not hasattr(box, '_tmin') or not hasattr(box, '_tmax'):
            raise Exception(
                'Box must be set with set_polar_box for polar charts')
        self.log10_tmax = log10(self.box._tmax) if self.box._tmax > 0 else 0
        self.log10_tmin = log10(self.box._tmin) if self.box._tmin > 0 else 0

    def __call__(self, rhotheta):
        """Project rho and theta"""

        if None in rhotheta:
            return None, None
        rho, theta = rhotheta
        # Center case
        if theta == 0:
            return super(PolarThetaLogView, self).__call__((0, 0))
        theta = self.box._tmin + (self.box._tmax - self.box._tmin) * (
            log10(theta) - self.log10_tmin) / (
            self.log10_tmax - self.log10_tmin)
        aperture = pi / 3
        if theta > self.box._tmax:
            theta = (3 * pi - aperture / 2) / 2
        elif theta < self.box._tmin:
            theta = (3 * pi + aperture / 2) / 2
        else:
            start = 3 * pi / 2 + aperture / 2
            theta = start + (2 * pi - aperture) * (
                theta - self.box._tmin) / (
                self.box._tmax - self.box._tmin)

        return super(PolarThetaLogView, self).__call__(
            (rho * cos(theta), rho * sin(theta)))


class LogView(View):
    """Logarithmic projection """
    # Do not want to call the parent here
    def __init__(self, width, height, box):
        self.width = width
        self.height = height
        self.box = box
        self.log10_ymax = log10(self.box.ymax) if self.box.ymax > 0 else 0
        self.log10_ymin = log10(self.box.ymin) if self.box.ymin > 0 else 0
        self.box.fix(False)

    def y(self, y):
        """Project y"""
        if y is None or y <= 0 or self.log10_ymax - self.log10_ymin == 0:
            return 0
        return (self.height - self.height *
                (log10(y) - self.log10_ymin)
                / (self.log10_ymax - self.log10_ymin))


class XLogView(View):
    """Logarithmic projection """
    # Do not want to call the parent here
    def __init__(self, width, height, box):
        self.width = width
        self.height = height
        self.box = box
        self.log10_xmax = log10(self.box.xmax) if self.box.xmax > 0 else 0
        self.log10_xmin = log10(self.box.xmin) if self.box.xmin > 0 else 0
        self.box.fix(False)

    def x(self, x):
        """Project x"""
        if x is None or x <= 0 or self.log10_xmax - self.log10_xmin == 0:
            return None
        return (self.width *
                (log10(x) - self.log10_xmin)
                / (self.log10_xmax - self.log10_xmin))


class XYLogView(XLogView, LogView):
    def __init__(self, width, height, box):
        self.width = width
        self.height = height
        self.box = box
        self.log10_ymax = log10(self.box.ymax) if self.box.ymax > 0 else 0
        self.log10_ymin = log10(self.box.ymin) if self.box.ymin > 0 else 0
        self.log10_xmax = log10(self.box.xmax) if self.box.xmax > 0 else 0
        self.log10_xmin = log10(self.box.xmin) if self.box.xmin > 0 else 0
        self.box.fix(False)


class HorizontalLogView(XLogView):
    """Logarithmic projection """
    # Do not want to call the parent here
    def __init__(self, width, height, box):
        self._force_vertical = None
        self.width = width
        self.height = height
        self.box = box
        self.log10_xmax = log10(self.box.ymax) if self.box.ymax > 0 else 0
        self.log10_xmin = log10(self.box.ymin) if self.box.ymin > 0 else 0
        self.box.fix(False)
        self.box.swap()

    def x(self, x):
        """Project x"""
        if x is None:
            return None
        if self._force_vertical:
            return super(HorizontalLogView, self).x(x)
        return super(XLogView, self).y(x)

    def y(self, y):
        if y is None:
            return None
        if self._force_vertical:
            return super(XLogView, self).y(y)
        return super(HorizontalLogView, self).x(y)

########NEW FILE########
__FILENAME__ = _compat
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
import sys
from collections import Iterable

if sys.version_info[0] == 3:
    base = (str, bytes)
    coerce = str
else:
    base = basestring
    coerce = unicode


def is_list_like(value):
    return isinstance(value, Iterable) and not isinstance(value, (base, dict))


def is_str(string):
    return isinstance(string, base)


def to_str(string):
    if not is_str(string):
        return coerce(string)
    return string


def u(s):
    if sys.version_info[0] == 2:
        return s.decode('utf-8')
    return s


def total_seconds(td):
    if sys.version_info[:2] == (2, 6):
        return (
            (td.days * 86400 + td.seconds) * 10 ** 6 + td.microseconds
        ) / 10 ** 6
    return td.total_seconds()

########NEW FILE########
__FILENAME__ = pygal_gen
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of pygal
#
# A python svg graph plotting library
# Copyright © 2012-2014 Kozea
#
# This library is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pygal. If not, see <http://www.gnu.org/licenses/>.
import argparse
import pygal

parser = argparse.ArgumentParser(
    description='Generate pygal chart in command line',
    prog='pygal_gen')

parser.add_argument('-t', '--type', dest='type', default='Line',
                    choices=map(lambda x: x.__name__, pygal.CHARTS),
                    help='Kind of chart to generate')

parser.add_argument('-o', '--output', dest='filename', default='pygal_out.svg',
                    help='Filename to write the svg to')

parser.add_argument('-s', '--serie', dest='series', nargs='+', action='append',
                    help='Add a serie in the form (title val1 val2...)')

parser.add_argument('--version', action='version',
                    version='pygal %s' % pygal.__version__)

for key in pygal.config.CONFIG_ITEMS:
    opt_name = key.name
    val = key.value
    opts = {}
    if key.type == list:
        opts['type'] = key.subtype
        opts['nargs'] = '+'
    else:
        opts['type'] = key.type

    if opts['type'] == bool:
        del opts['type']
        opts['action'] = 'store_true' if not val else 'store_false'
        if val:
            opt_name = 'no-' + opt_name
    if key.name == 'interpolate':
        opts['choices'] = list(pygal.interpolate.INTERPOLATIONS.keys())
    parser.add_argument(
        '--%s' % opt_name, dest=key.name, default=val, **opts)

config = parser.parse_args()

chart = getattr(pygal, config.type)(**vars(config))

for serie in config.series:
    chart.add(serie[0], map(float, serie[1:]))

chart.render_to_file(config.filename)

########NEW FILE########
