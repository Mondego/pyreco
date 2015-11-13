__FILENAME__ = colors_meteor_example
'''trying to reconstruct Meteor color application'''

from webalchemy import server
from webalchemy.widgets.basic.menu import Menu


class ColorsMeteorApp:

    @staticmethod
    def initialize_shared_data(sdata):
        # shared state between sessions in process
        def add_update(d1, d2):
            for k, v in d2.items():
                d1[k] = d1.get(k, 0) + v
        add_update(sdata, {
            'boo': 0,
            'baar': 0,
            'wowowowowo!!!': 0,
            'this is cool': 0,
            'WEBALCHEMY ROCKS': 0,
        })

    # this method is called when a new session starts
    def initialize(self, **kwargs):
        # remember these for later use
        self.rdoc = kwargs['remote_document']
        self.com = kwargs['comm_handler']
        self.sdata = kwargs['shared_data']
        self.tdata = kwargs['tab_data']

        # insert a title
        title = self.rdoc.body.element(h1='COLORS I REALLY LIKE :)')
        title.style(
            fontFamily='Arial, Verdana, Sans-serif',
            fontSize='3.5em',
        )
        self.rdoc.props.title = 'colors app!'

        # insert a menu
        self.menu = self.build_menu()
        self.menu.element.style(
            marginLeft='50px',
            marginBottom='30px',
            width='400px',
            borderWidth='2px')
        self.rdoc.body.append(self.menu.element)

        # insert a button
        button = self.rdoc.body.element(button='Like!')
        button.style(
            fontFamily='Arial, Verdana, Sans-serif',
            fontSize='1.5em',
        )

        def button_click_p():
            if srv(self.menu.element).app.selected is None: return
            srv(self.menu.increase_count_by)(srv(self.menu.element).app.selected, 1)
            rpc(self.color_liked, srv(self.menu.element).app.selected.id,
                srv(self.menu.element).app.selected.app.color, 1)

        button.events.add(click=button_click_p, translate=True)

        # insert another button !!
        button2 = self.rdoc.body.element(button='UNLike!')
        button2.style(
            fontFamily='Arial, Verdana, Sans-serif',
            fontSize='1.5em',
        )
        def button_click_n():
            if srv(self.menu.element).app.selected is None: return
            srv(self.menu.increase_count_by)(srv(self.menu.element).app.selected, -1)
            rpc(self.color_liked, srv(self.menu.element).app.selected.id,
                srv(self.menu.element).app.selected.app.color, -1)

        button2.events.add(click=button_click_n, translate=True)

    def color_liked(self, sender_com_id, item_id, color, amount):
        if sender_com_id == self.com.id:
            # button clicked on this session
            self.sdata[color] += int(amount)
            self.com.rpc(self.color_liked, item_id, color, amount)
        else:
            # button clicked by other session
            item = self.menu.id_dict[item_id]
            self.menu.increase_count_by(item, int(amount))

    def color_selected(self, sender_id, color):
        self.tdata['selected color text'] = color

    def build_menu(self):
        # the following function will be used to initialize all menu items
        def on_add(item):
            nonlocal m
            col = item.text
            item.app.color = col
            item.app.clickedcount = self.sdata.get(col, 0)
            m.increase_count_by(item, 0)
            if item.text == self.tdata.get('selected color text', None):
                m.select_color(item)

        # create a menu element with the above item initializer
        m = Menu(self.rdoc, on_add)

        # function to increase the count in front-end

        def menu_sort():
            def srt_func(a, b):
                if a.app.clickedcount < b.app.clickedcount: return -1
                if a.app.clickedcount > b.app.clickedcount: return 1
                return 0
            e = srv(m.element)
            arr = Array.prototype.slice.call(e.children).sort(srt_func)
            for item in arr:
                e.appendChild(item)

        m.sort = self.rdoc.translate(menu_sort)

        def increase_count_by(element, amount):
            element.app.clickedcount += amount
            srv(m.sort)()
            element.textContent = '(' + element.app.clickedcount + ') ' + element.app.color

        m.increase_count_by = self.rdoc.translate(increase_count_by)

        def select_color(element):
            if element.target is not None:
                element = element.target
            element.classList.add('selected')
            if srv(m.element).app.selected and srv(m.element).app.selected!=element:
                srv(m.element).app.selected.classList.remove('selected')
            srv(m.element).app.selected = element
            rpc(self.color_selected, element.app.color)

        m.select_color = self.rdoc.translate(select_color)

        m.element.events.add(click=m.select_color)

        # style the menu
        m.rule_menu.style(display='table', margin='10px')
        m.rule_item.style(
            color='#000000',
            fontSize='1.5em',
            textTransform='uppercase',
            fontFamily='Arial, Verdana, Sans-serif',
            float='bottom',
            padding='10px',
            listStyle='none',
            cursor='pointer',
            webkitTransition='all 0.3s linear',
            webkitUserSelect='none'
        )
        m.rule_item_hover.style(
            color='#ffffff',
            background='#000000',
            paddingLeft='20px',
        )
        m.rule_item_selected.style(
            padding='10px',
            background='#FF0000',
            color='#000000',
            webkitTransform='rotate(3deg)'
        )
        # populate the menu with shared colors dict
        m.add_item(*self.sdata.keys())
        m.sort()
        return m

if __name__ == '__main__':
    # this self import is needed to do live-editing. Everything else works without it
    from colors_meteor_example import ColorsMeteorApp
    server.run(ColorsMeteorApp)

########NEW FILE########
__FILENAME__ = hello_world_example
from webalchemy import server

class HellowWorldApp:
    def initialize(self, **kwargs):
        self.rdoc = kwargs['remote_document']
        self.print_hi = self.rdoc.translate(self.print_hi)
        self.rdoc.body.element(h1='Hello World!').events.add(click=self.clicked, translate=True)
        self.rdoc.body.element(h2='--------------')
        self.rdoc.stylesheet.rule('h1').style(
            color='#FF0000',
            marginLeft='75px',
            marginTop='75px',
            background='#00FF00'
        )

    def clicked(self):
        self.textContent = self.textContent[1:]
        rpc(self.handle_click_on_backend, 'some message', 'just so you see how to pass paramaters')
        srv(self.print_hi)()

    def handle_click_on_backend(self, sender_id, m1, m2):
        self.rdoc.body.element(h1=m1+m2)

    def print_hi(self):
        print('hi!')

if __name__ == '__main__':
    # this import is necessary because of the live editing. Everything else works OK without it
    from hello_world_example import HellowWorldApp
    server.run(HellowWorldApp)



########NEW FILE########
__FILENAME__ = jquerymobile_example
from webalchemy import server

class JQueryMobileExample:

    # Include the jQuery mobile stylesheet and the jQuery/jQuery mobile scripts
    stylesheets = ['http://code.jquery.com/mobile/1.4.0/jquery.mobile-1.4.0.min.css']
    include = ['http://code.jquery.com/jquery-1.10.2.min.js',
               'http://code.jquery.com/mobile/1.4.0/jquery.mobile-1.4.0.min.js']
               
    # Use the modified html
    main_html_file_path = "jquerymobile_example.html"

    def initialize(self, **kwargs):
        self.rdoc = kwargs['remote_document']
        # Grab the main <div> from the html document and inject some elements
        self.main = self.rdoc.getElementById('main')
        self.main.element(h1="Main content")
        self.main.element(button="A button")
        # Force jQuery to redraw (enhance) the document
        self.rdoc.JS('jQuery(#{self.main}).trigger("create")')


if __name__ == '__main__':
    # this import is necessary because of the live editing. Everything else works OK without it
    from jquerymobile_example import JQueryMobileExample
    server.run(JQueryMobileExample)

########NEW FILE########
__FILENAME__ = math_explorer
from webalchemy.Stacker import Stacker, HtmlShortcuts
from webalchemy.stacker_wrappers.bootstrap_3.bootstrap3_wrapper import BootstrapShortcuts
from sympy import *

examples = [
    (r'Take the derivative of \(\sin{(x)}e^x\)', 'diff(sin(x)*exp(x), x)'),
    (r'Compute \(\int(e^x\sin{(x)} + e^x\cos{(x)})\,dx\)', 'integrate(exp(x)*sin(x) + exp(x)*cos(x), x)'),
    (r'Compute \(\int_{-\infty}^\infty \sin{(x^2)}\,dx\)', 'integrate(sin(x**2), (x, -oo, oo))'),
    (r'Find \(\lim_{x\to 0}\frac{\sin{(x)}}{x}\)', 'limit(sin(x)/x, x, 0)'),
    (r'Solve \(x^2 - 2 = 0\)', 'solve(x**2 - 2, x)'),
    (r'Solve the differential equation \(y'' - y = e^t\)', '''y = Function('y'); dsolve(Eq(y(t).diff(t, t) - y(t), exp(t)), y(t))'''),
    (r'Find the eigenvalues of \(\left[\begin{smallmatrix}1 & 2\\2 & 2\end{smallmatrix}\right]\)', 'Matrix([[1, 2], [2, 2]]).eigenvals()'),
    (r'Rewrite the Bessel function \(J_{\nu}\left(z\right)\) in terms of the spherical Bessel function \(j_\nu(z)\)','besselj(nu, z).rewrite(jn)')
]

functions = ['diff', 'integrate', 'limit', ]

class MathExplorer:
    """Application to explore math from the browser"""

    include = ['//ajax.googleapis.com/ajax/libs/jquery/1.10.2/jquery.min.js',
               '//netdna.bootstrapcdn.com/bootstrap/3.1.0/js/bootstrap.min.js',
               'http://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML']
    stylesheets = ['//netdna.bootstrapcdn.com/bootstrap/3.1.0/css/bootstrap.min.css']

    def initialize(self, **kwargs):
        self.rdoc = kwargs['remote_document']
        s = Stacker(self.rdoc.body)
        h = HtmlShortcuts(s)
        b = BootstrapShortcuts(s)
        with b.container(), b.row(), b.col(md=12):
            with h.div(cls='page-header'):
                with h.h1(text="The Math Exploerer"):
                    h.small(text=" use it for... uhm... exploring math?")
            with b.row(), b.col(md=12):
                with b.alert(dismissable=True):
                    h.h4(text="Warning:")
                    h.p(innerHtml="This example uses SymPy's sympify to parse user input which is <strong>unsafe</strong> - use at your own risk and please consider before running it on a web server...")
            with b.row():
                # left column
                with b.col(md=7):
                    with b.panel():
                        self.pbody = b.panel_body(style={'minHeight':'500px', 'overflowY':'auto'})
                    with h.div(cls='well'):
                        self.inp = h.input(cls='form-control', att={'placeholder': "Enter Math here (see examples)"})
                        self.inp.events.add(keydown=self.execute, translate=True)
                # right column
                with b.col(md=5):
                    with b.panel(flavor='success'):
                        with b.panel_heading(text="Examples:"):
                            b.button(text="toggle", att={'data-toggle':"collapse", 'data-target':"#examples_body"},
                                     size='xs',
                                     cls="pull-right")
                        with b.list_group(customvarname='examples_body', cls='collapse in'):
                            for desc, codes in examples:
                                with b.list_group_item(text=desc.replace('\\', '\\\\')):
                                    for code in codes.split(';'):
                                        h.br()
                                        h.code(text=code).events.add(click=lambda: self.inp.prop(value=code))
                    with b.panel(flavor='info'):
                        b.panel_heading(text="Symbols:")
                        b.panel_body(text="x")
                    with b.panel(flavor='info'):
                        b.panel_heading(text="Functions:")
                        b.panel_body(text="bla bla")
        self.rdoc.JS('MathJax.Hub.Queue(["Typeset",MathJax.Hub, "examples_body"]);')

    def execute(e):
        if e.keyCode == weba.KeyCode.ENTER:
            rpc(self.calc_with_sympy, self.value)

    def calc_with_sympy(self, sender_id, text):
        try:
            self.pbody.element(p=str(sympify(text)))
        except Exception as e:
            self.pbody.element('p').prop.innerHTML = str(e).replace("\n", '<br>')


if __name__ == "__main__":
    from webalchemy import server
    from math_explorer import MathExplorer
    server.run(MathExplorer)





########NEW FILE########
__FILENAME__ = freeze_app
import sys
import os

PACKAGE_PARENT = '../../'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))


from webalchemy import server
from three_d_earth import ThreeDEarth as app

if __name__ == '__main__':

    server.generate_static(app)

########NEW FILE########
__FILENAME__ = serve_through_websocket
from webalchemy import server
from three_d_earth import ThreeDEarth


if __name__ == '__main__':
    server.run(ThreeDEarth)

########NEW FILE########
__FILENAME__ = three_d_earth
from webalchemy import config

FREEZE_OUTPUT = 'webglearth.html'


class Earth:

    def __init__(self):
        self.width = window.innerWidth
        self.height = window.innerHeight

        # Earth params
        self.radius = 0.5
        self.segments = 64
        self.rotation = 6

        self.scene = new(THREE.Scene)

        self.camera = new(THREE.PerspectiveCamera, 45, self.width / self.height, 0.01, 1000)
        self.camera.position.z = 1.5

        self.renderer = new(THREE.WebGLRenderer)
        self.renderer.setSize(self.width, self.height)

        self.scene.add(new(THREE.AmbientLight, 0x333333))

        self.light = new(THREE.DirectionalLight, 0xffffff, 1)
        self.light.position.set(5, 3, 5)
        self.scene.add(self.light)

        self.sphere = self.createSphere(self.radius, self.segments)
        self.sphere.rotation.y = self.rotation
        self.scene.add(self.sphere)

        self.clouds = self.createClouds(self.radius, self.segments)
        self.clouds.rotation.y = self.rotation
        self.scene.add(self.clouds)

        self.stars = self.createStars(90, 64)
        self.scene.add(self.stars)

        self.mx = 0
        self.my = 0
        self.mdx = 0
        self.mdy = 0
        self.angx = 0
        self.angy = 0
        self.renderer.domElement.onmouseup = self.wrap(self, self.mouseup)
        self.renderer.domElement.onmousedown = self.wrap(self, self.mousedown)

    def mousemove(self, e):
        self.mdx += e.screenX - self.mx
        self.mdy += e.screenY - self.my
        self.mx = e.screenX
        self.my = e.screenY

    def mouseup(self, e):
        self.renderer.domElement.onmousemove = None

    def mousedown(self, e):
        self.mx = e.screenX
        self.my = e.screenY
        self.renderer.domElement.onmousemove = self.wrap(self, self.mousemove)

    def wrap(self, object, method):
        def wrapper():
            return method.apply(object, arguments)
        return wrapper

    def render(self):
        if Math.abs(self.mdx) > 1.1 or Math.abs(self.mdy) > 1.1:
            self.angx -= self.mdx/5000
            self.mdx -= self.mdx/20
            if Math.abs(self.angy + self.mdy/5000) < 3.14/2:
                self.angy += self.mdy/10000
                self.mdy -= self.mdy/20
            self.camera.position.x = 1.5 *Math.sin(self.angx) *Math.cos(self.angy)
            self.camera.position.z = 1.5 *Math.cos(self.angx) *Math.cos(self.angy)
            self.camera.position.y = 1.5 *Math.sin(self.angy)
            self.camera.lookAt(self.scene.position)

        self.sphere.rotation.y += 0.0005
        self.clouds.rotation.y += 0.0004
        requestAnimationFrame(self.wrap(self, self.render))
        self.renderer.render(self.scene, self.camera)


    def createSphere(self, radius, segments):
        geometry = new(THREE.SphereGeometry, radius, segments, segments)
        material = new(THREE.MeshPhongMaterial, {
                        'map':         THREE.ImageUtils.loadTexture('static/lowres_noclouds.jpg'),
                        'bumpMap':     THREE.ImageUtils.loadTexture('static/lowres_elevbump.jpg'),
                        'bumpScale':   0.005,
                        'specularMap': THREE.ImageUtils.loadTexture('static/lowres_water.png'),
                        'specular':    new(THREE.Color, 'grey')
        })
        return new(THREE.Mesh, geometry, material)

    def createClouds(self, radius, segments):
        geometry = new(THREE.SphereGeometry, radius + 0.005, segments, segments)
        material = new(THREE.MeshPhongMaterial, {
                        'map':         THREE.ImageUtils.loadTexture('static/lowres_fairclouds.png'),
                        'transparent': true
        })
        return new(THREE.Mesh, geometry,  material)

    def createStars(self, radius, segments):
        geometry = new(THREE.SphereGeometry, radius, segments, segments)
        material = new(THREE.MeshBasicMaterial, {
                        'map':  THREE.ImageUtils.loadTexture('static/lowres_starfield.png'),
                        'side': THREE.BackSide
        })
        return new(THREE.Mesh, geometry, material)


class ThreeDEarth:

    include = ['https://rawgithub.com/mrdoob/three.js/master/build/three.min.js']
    config = config.from_object(__name__)

    def initialize(self, **kwargs):
        self.rdoc = kwargs['remote_document']
        self.rdoc.body.style(
            margin=0,
            overflow='hidden',
            backgroundColor='#000'
        )
        self.earth = self.rdoc.new(Earth)
        self.rdoc.body.append(self.earth.renderer.domElement)

        self.rdoc.stylesheet.rule('a').style(color='#FFF')
        e = self.rdoc.body.element('p')
        e.prop.innerHTML = "Powered by <a href='https://github.com/skariel/webalchemy'>Webalchemy</a><br/>" +\
            "Adapted from <a href='https://github.com/turban/webgl-earth/blob/master/index.html'>this</a><br/>" +\
            "Pure Python source is <a href='https://github.com/skariel/webalchemy/blob/master/examples/three_d_earth/three_d_earth.py'>here</a>"
        e.style(
            color='#FFF',
            position='absolute',
            left='10px', top='10px'
        )

        self.earth.render()




########NEW FILE########
__FILENAME__ = board
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class board:
    def __init__(self, rdoc, n, px):
        self.rdoc = rdoc
        self.n = n
        rdoc.props.title = 'TicTacToe!'
        self.svg = rdoc.element('svg')
        self.px = px
        self.dx = self.px / self.n
        self.svg.app.actual_cursorx = 0
        self.svg.app.actual_cursory = 0
        self.svg.app.cursorx_index = 0
        self.svg.app.cursory_index = 0
        self.svg.app.n = self.n
        self.svg.app.checked = {}
        self.svg.att.width = px
        self.svg.att.height = px

        self.__create_styles()
        self.__style()
        self.__draw_board()
        self.__set_events()

    def __draw_board(self):
        dx = self.dx
        rng = range(self.n)
        # draw vertical lines
        for xi in rng[1:]:
            l = self.rdoc.element('line')
            l.att.x1 = l.att.x2 = dx * xi
            l.att.y1 = 0
            l.att.y2 = self.px
            self.svg.append(l)
            # draw horizontal lines
        for yi in rng[1:]:
            l = self.rdoc.element('line')
            l.att.y1 = l.att.y2 = dx * yi
            l.att.x1 = 0
            l.att.x2 = self.px
            self.svg.append(l)
            # draw cursor
        self.cursor = self.rdoc.element('rect')
        self.cursor.att.x = 0
        self.cursor.att.y = 0
        self.cursor.att.width = dx
        self.cursor.att.height = dx
        self.svg.append(self.cursor)

    def __set_events(self):
        self.mouse_move_event_handler = self.rdoc.jsfunction('e', body='''
            var mx= e.pageX-#{self.svg}.offsetLeft;
            var my= e.pageY-#{self.svg}.offsetTop;
            #{self.svg}.app.cursorx_index= ~~ (mx / #{self.dx});
            #{self.svg}.app.cursory_index= ~~ (my / #{self.dx});
            ''')
        self.svg.events.add(mousemove=self.mouse_move_event_handler)
        self.update_cursor_position = self.rdoc.jsfunction(body='''
            var truncated_cursorx= #{self.svg}.app.cursorx_index*#{self.dx};
            var truncated_cursory= #{self.svg}.app.cursory_index*#{self.dx};
            var dx= (truncated_cursorx - #{self.svg}.app.actual_cursorx) / 3.0;
            if ((dx>0.01)||(dx<-0.01)) {
                #{self.svg}.app.actual_cursorx+= dx;
                #{self.cursor}.setAttribute('x',#{self.svg}.app.actual_cursorx)
            }
            var dy= (truncated_cursory - #{self.svg}.app.actual_cursory) / 3.0;
            if ((dy>0.01)||(dy<-0.01)) {
                #{self.svg}.app.actual_cursory+= dy;
                #{self.cursor}.setAttribute('y',#{self.svg}.app.actual_cursory)
            }
            ''')
        self.rdoc.startinterval(20, self.update_cursor_position)

        dx = self.dx
        il = self.rdoc.inline
        self.rdoc.begin_block()
        il('var inx= #{self.svg}.app.cursory_index*#{self.svg}.app.n+#{self.svg}.app.cursorx_index;')
        il('if (inx in #{self.svg}.app.checked) return;')
        il('#{self.svg}.app.checked[inx]="o";')
        c = self.rdoc.element('circle')
        c.att.cx = il('#{self.svg}.app.cursorx_index*#{self.dx}+' + str(dx / 2))
        c.att.cy = il('#{self.svg}.app.cursory_index*#{self.dx}+' + str(dx / 2))
        c.att.r = il(str(dx / 2) + '-9')
        self.svg.append(c)
        self.draw_circle = self.rdoc.jsfunction('event')
        self.svg.events.add(click=self.draw_circle)

        self.rdoc.begin_block()
        il('var inx= #{self.svg}.app.cursory_index*#{self.svg}.app.n+#{self.svg}.app.cursorx_index;')
        il('if (inx in #{self.svg}.app.checked) return;')
        il('#{self.svg}.app.checked[inx]="x";')
        g = self.rdoc.element('g')
        l1 = self.rdoc.element('line')
        l1.cls.append('x')
        il('var xl= #{self.svg}.app.cursorx_index*#{self.dx}+7;')
        il('var xr= xl+#{self.dx}-14;')
        il('var yt= #{self.svg}.app.cursory_index*#{self.dx}+7;')
        il('var yb= yt+#{self.dx}-14;')
        l1.att.x1 = il('xl')
        l1.att.y1 = il('yt')
        l1.att.x2 = il('xr')
        l1.att.y2 = il('yb')
        g.append(l1)
        l2 = self.rdoc.element('line')
        l2.cls.append('x')
        l2.att.x1 = il('xr')
        l2.att.y1 = il('yt')
        l2.att.x2 = il('xl')
        l2.att.y2 = il('yb')
        g.append(l2)
        self.svg.append(g)
        self.draw_x = self.rdoc.jsfunction('event')
        self.svg.events.add(click=self.draw_x)

    def __create_styles(self):
        self.stylesheet = self.rdoc.stylesheet
        vn = '#' + self.svg.varname
        self.rule_svg = self.stylesheet.rule(vn)
        self.rule_lines = self.stylesheet.rule(vn + ' > line')
        self.rule_rect = self.stylesheet.rule(vn + ' > rect')
        self.rule_circle = self.stylesheet.rule(vn + ' > circle')
        self.rule_circle_hover = self.stylesheet.rule(vn + ' > circle:hover')
        self.rule_x = self.stylesheet.rule(vn + ' > g > line')
        self.rule_x_hover = self.stylesheet.rule(vn + ' > g:hover > line')

    def __style(self):
        self.rule_lines.style(
            stroke='black',
            strokeWidth=3
        )
        self.rule_rect.style(
            fill='grey',
            fillOpacity=0.8,
            strokeWidth=0,
        )
        self.rule_circle.style(
            stroke='red',
            fillOpacity=0.0,
            strokeWidth=5,
            webkitTransition='all 0.3s linear',
        )
        self.rule_circle_hover.style(
            strokeWidth=15
        )
        self.rule_x.style(
            stroke='green',
            strokeWidth=5,
            webkitTransition='all 0.3s linear',
        )
        self.rule_x_hover.style(
            stroke='green',
            strokeWidth=15
        )

########NEW FILE########
__FILENAME__ = tictactoe_example
'''
a massive multiplayer tictactoe server

This is WIP, no quite working yet...
'''

import logging
from tornado import gen

from board import board

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class TickTackToeApp:
    @gen.coroutine
    def initialize(self, remotedocument, wshandler, sessionid, tabid):
        # remember these for later use
        self.rdoc = remotedocument
        self.wsh = wshandler
        log.info('New session opened, id=' + self.wsh.id)

        self.board = board(self.rdoc, 13, 500.0)
        self.rdoc.body.append(self.board.svg)

########NEW FILE########
__FILENAME__ = freeze_app
from webalchemy import server
from todomvc import AppTodoMvc as app

if __name__ == '__main__':
    server.generate_static(app)

########NEW FILE########
__FILENAME__ = serve_through_websocket
from webalchemy import server
from todomvc import AppTodoMvc as app

if __name__ == '__main__':
    server.run(app)

########NEW FILE########
__FILENAME__ = todomvc
from webalchemy import config
from webalchemy.mvc import controller


class Item:
    def __init__(self, text):
        self.completed = False
        self.text = text


class DataModel:
    def __init__(self):
        # loading local list of todos
        self.itemlist = JSON.parse(localStorage.getItem('webatodomvcdata')) or []

    def set_all_completed(self, comp_or_not):
        for item in self.itemlist:
            item.completed = comp_or_not
        self.persist()

    def remove_completed(self):
        self.itemlist = self.itemlist.filter(lambda i:  not i.completed)
        self.persist()

    def remove_item(self, i):
        self.itemlist.splice(i, 1)
        self.persist()

    def add_item(self, txt):
        self.itemlist.push(new(Item, txt))
        self.persist()

    def toggle_item_completed(self, i, v):
        self.itemlist[i].completed = v
        self.persist()

    def persist(self):
        localStorage.setItem('webatodomvcdata', JSON.stringify(self.itemlist))

    def calc_completed_and_remaining(self):
        self.completed = 0
        for item in self.itemlist:
            if item.completed:
                self.completed += 1
        self.remaining = self.itemlist.length - self.completed


class ViewModel:
    def __init__(self):
        self.itembeingedited = None

    def new_item_keyup(self, e):
        if e.keyCode == weba.KeyCode.ESC: e.target.blur()
        if e.keyCode == weba.KeyCode.ENTER:
            if e.target.value.trim() != '':
                e.target.app.m.add_item(e.target.value)
                e.target.value = ''

    def edit_keyup(self, e, i):
        if e.keyCode == weba.KeyCode.ESC:
            self.itembeingedited = None
        if e.keyCode != weba.KeyCode.ENTER: return
        self.itembeingedited = None
        e.target.app.m.itemlist[i].text = e.target.value
        if e.target.value.trim() == '':
            e.target.app.m.remove_item(i)

    def editing_item_changed(self, e, i, tothisitem):
        if tothisitem:
            e.focus()
            e.value = e.app.m.itemlist[i].text
        else:
            e.blur()

    def should_hide(self, e, i):
        return (e.app.m.itemlist[i].completed and location.hash == '#/active') or \
           (not e.app.m.itemlist[i].completed and location.hash == '#/completed')

    def finish_editing(self, i):
        if self.itembeingedited == i:
            self.itembeingedited = None


class Settings:
    FREEZE_OUTPUT = 'todomvc.html'


class AppTodoMvc:

    main_html_file_path = 'static/template/index.html'
    config = config.from_object(Settings)

    def initialize(self, **kwargs):
        self.rdoc = kwargs['remote_document']
        self.datamodel = self.rdoc.new(DataModel)
        self.viewmodel = self.rdoc.new(ViewModel)
        self.rdoc.translate(Item)

        controller(self.rdoc, kwargs['main_html'], m=self.datamodel, vm=self.viewmodel,
                   prerender=self.datamodel.calc_completed_and_remaining)


########NEW FILE########
__FILENAME__ = config
import imp
import os.path
import importlib


DEFAULT_SETTINGS = {
    'SERVER_STATIC_PATH': 'static',
    'SERVER_PORT': 8080,
    'SERVER_SSL_CERT': None,
    'SERVER_SSL_KEY': None,
    'SERVER_MONITORED_FILES': None,
    'SERVER_MAIN_ROUTE': None,
    'FREEZE_OUTPUT': None,
}


def read_config_from_app(app):
    settings = DEFAULT_SETTINGS.copy()
    if hasattr(app, 'config'):
        settings.update(app.config)
    return settings


def from_object(obj):
    if isinstance(obj, str):
        obj = importlib.import_module(obj)
    cfg = Config()
    for key in dir(obj):
        if key.isupper():
            cfg[key] = getattr(obj, key)
    return cfg


def from_pyfile(filename, root=None):
    if not (root is None):
        filename = os.path.join(root, filename)
    mod = imp.new_module('config')
    mod.__file__ = filename
    with open(filename) as config_file:
        exec(compile(config_file.read(), filename, 'exec'), mod.__dict__)
    return from_object(mod)


def from_envvar(variable_name):
    value = os.environ.get(variable_name)
    if not value:
        return dict()
    return from_pyfile(value)


def from_dict(d):
    cfg = Config()
    cfg.update(d)
    return cfg


class Config(dict):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def from_object(self, obj):
        self.update(from_object(obj))

    def from_pyfile(self, filename, root=None):
        self.update(from_pyfile(filename, root))

    def from_envvar(self, variable_name):
        self.update(from_envvar(variable_name))

    def from_dict(self, d):
        self.update(from_dict(d))


########NEW FILE########
__FILENAME__ = htmlparser
from html.parser import HTMLParser


def get_element_ids(html):
    ids = []

    class MyHTMLParser(HTMLParser):
        def handle_starttag(self, tag, attrs):
            for attr in attrs:
                if attr[0] == 'id':
                    ids.append(attr[1])
    parser = MyHTMLParser()
    parser.feed(html)
    return ids

########NEW FILE########
__FILENAME__ = mainhtml
import os.path

from bs4 import BeautifulSoup

from .remotedocument import RemoteDocument


def get_main_html_file_path(app):
    if hasattr(app, 'main_html_file_path'):
        return app.main_html_file_path

    main_dir = os.path.realpath(__file__)
    main_dir = os.path.dirname(main_dir)
    return os.path.join(main_dir, 'main.html')

# js files to be injected to main html, in this order:
js_files_to_inject_to_live_app = [
    'js/reconnecting_ws.js',
    'js/cookie.js',
    'js/vendor.js',
    'js/comm.js',
    'js/reconnection_overlay.js',
    'js/classy.js',
    'js/weba.js',
]

js_files_to_inject_to_frozen_app = [
    'js/classy.js',
    'js/weba.js',
]


def get_soup_head_body_and_scripts(app):
    with open(get_main_html_file_path(app), 'r') as f:
        html = f.read()
    s = BeautifulSoup(html)
    if not s.html.head:
        s.html.insert(0, s.new_tag('head'))
    head = s.html.head
    script = s.new_tag('script')
    s.html.append(script)
    if not s.html.body:
        s.html.append(s.new_tag('body'))
    body = s.html.body
    return s, head, body, script


def fill_head(app, s, head):
    head.append(s.new_tag('script', src='http://cdn.sockjs.org/sockjs-0.3.min.js'))
    if hasattr(app, 'include'):
        for i in app.include:
            head.append(s.new_tag('script', src=i))
    if hasattr(app, 'meta'):
        for m in app.meta:
            head.append(s.new_tag('meta', **m))
    if hasattr(app, 'stylesheets'):
        for stl in app.stylesheets:
            head.append(s.new_tag('link', rel='stylesheet', href=stl))


def generate_main_html_for_server(app, ssl):
    s, head, body, script = get_soup_head_body_and_scripts(app)

    # filling in the script tag with all contents from js files:
    basedir = os.path.dirname(__file__)
    for fn in js_files_to_inject_to_live_app:
        full_fn = os.path.join(basedir, fn)
        with open(full_fn, 'r') as f:
            text = f.read()
            if fn == 'js/comm.js':
                # socket url...
                if ssl:
                    text = text.replace('__SOCKET_URL__', "'https://'+location.host+'/app'")
                else:
                    text = text.replace('__SOCKET_URL__', "'http://'+location.host+'/app'")
            script.append(text+'\n')

    fill_head(app, s, head)
    body.attrs['onload'] = 'init_communication()'

    return s.prettify()


def generate_static_main_html(app):
    s, head, body, script = get_soup_head_body_and_scripts(app)

    # filling in the script tag with all contents from js files:
    basedir = os.path.dirname(__file__)
    for fn in js_files_to_inject_to_frozen_app:
        full_fn = os.path.join(basedir, fn)
        with open(full_fn, 'r') as f:
            script.append(f.read()+'\n')

    fill_head(app, s, head)

    rdoc = RemoteDocument()
    app().initialize(remote_document=rdoc, main_html=s.prettify())
    generated_scripts = rdoc.pop_all_code()
    script.append('\n\n'+generated_scripts+'\n\n')

    return s.prettify()



########NEW FILE########
__FILENAME__ = monkeypatch
from pythonium.veloce.veloce import Veloce

def monkeypatch_pythonium():
    '''

    a few fixes:
        - slices
        - lambda

    and a few things related to webalchemy:
        - call magic functions

    '''
    def fixed_visit_Subscript(self, node):
        slice = self.visit(node.slice)
        if not slice.startswith('slice('):
            return '{}[{}]'.format(self.visit(node.value), slice)
        else:
            return '{}.{}'.format(self.visit(node.value), slice)


    def fixed_visit_Lambda(self, node):
        args, kwargs, vararg, varkwargs = self.visit(node.args)
        name = '__lambda{}'.format(self.uuid())
        self.writer.write('var {} = function({}) {{'.format(name, ', '.join(args)))
        self.writer.push()
        self._unpack_arguments(args, kwargs, vararg, varkwargs)
        body = 'return '
        body += self.visit(node.body)
        self.writer.write(body)
        self.writer.pull()
        self.writer.write('}')
        return name

    def weba_visit_Call(self, node):
        name = self.visit(node.func)
        if name == 'instanceof':
            # this gets used by "with javascript:" blocks
            # to test if an instance is a JavaScript type
            args = list(map(self.visit, node.args))
            if len(args) == 2:
                return '{} instanceof {}'.format(*tuple(args))
            else:
                raise SyntaxError(args)
        elif name == 'JSObject':
            if node.keywords:
                kwargs = map(self.visit, node.keywords)
                f = lambda x: '"{}": {}'.format(x[0], x[1])
                out = ', '.join(map(f, kwargs))
                return '{{}}'.format(out)
            else:
                return 'Object()'
        elif name == 'var':
            args = map(self.visit, node.args)
            out = ', '.join(args)
            return 'var {}'.format(out)
        elif name == 'new':
            args = list(map(self.visit, node.args))
            object = args[0]
            args = ', '.join(args[1:])
            return 'new {}({})'.format(object, args)
        # WEBA HERE!
        elif name == 'rpc':
            args = list(map(self.visit, node.args))
            args = ', '.join(args)
            return '#rpc{{{}}}'.format(args)
        elif name == 'srv':
            args = list(map(self.visit, node.args))
            args = ', '.join(args)
            return '#{{{}}}'.format(args)
        # END OF WEBA MANIPULATIONS!
        elif name == 'super':
            args = ', '.join(map(self.visit, node.args))
            return 'this.$super({})'.format(args)
        elif name == 'JSArray':
            if node.args:
                args = map(self.visit, node.args)
                out = ', '.join(args)
            else:
                out = ''
            return '[{}]'.format(out)
        elif name == 'jscode':
            return node.args[0].s
        elif name == 'jstype':
            return self.visit(node.args[0])
        elif name == 'print':
            args = [self.visit(e) for e in node.args]
            s = 'console.log({})'.format(', '.join(args))
            return s
        else:
            # positional args
            if node.args:
                args = [self.visit(e) for e in node.args]
                args = [e for e in args if e]
            else:
                args = []
            # variable arguments aka. starargs
            call_arguments = 'call_arguments{}'.format(self.uuid())
            if node.starargs:
                varargs = self.visit(node.starargs)
                code = "for i in {}: jscode('{}.push(i)')".format(varargs, call_arguments)
                self.writer.write(self.translate(code))
            # keywords and variable keywords arguments aka. starkwargs
            if node.kwargs:
                kwargs = self.visit(node.kwargs)
                if node.keywords:
                    for key, value in map(self.visit, node.keywords):
                        self.writer.write('{}["{}"] = {};'.format(kwargs, key, value))
            elif node.keywords:
                kwargs = '__pythonium_kwargs'
                self.writer.write('var __pythonium_kwargs = {};')
                for key, value in map(self.visit, node.keywords):
                    self.writer.write('{}["{}"] = {};'.format(kwargs, key, value))
            if node.kwargs or node.keywords:
                # XXX: define for every call since we can't define it globaly
                self.writer.write('__ARGUMENTS_PADDING__ = {};')
                args.append('__ARGUMENTS_PADDING__')
                args.append(kwargs)
            return '{}({})'.format(name, ', '.join(args))

    def weba_visit_NameConstant(self, node):
        if node.value is None:
            return 'undefined'
        elif node.value is True:
            return 'true'
        elif node.value is False:
            return 'false'
        return str(node.value).replace('__DOLLAR__', '$')

    Veloce.visit_Lambda = fixed_visit_Lambda
    Veloce.visit_Subscript = fixed_visit_Subscript
    Veloce.visit_Call = weba_visit_Call
    Veloce.visit_NameConstant = weba_visit_NameConstant


def monkeypatch():
    monkeypatch_pythonium()
########NEW FILE########
__FILENAME__ = mvc
from html.parser import HTMLParser


class controller:
    def __init__(self, rdoc, html, m=None, vm=None, prerender=None, run=True):
        self.rdoc = rdoc
        class c:
            pass
        self.e = c()
        self.model = m or self.rdoc.dict()
        self.viewmodel = vm or self.rdoc.dict()
        self.prerender = prerender

        self.cls = self.rdoc.jsfunction('vm', 'm', 'e', 'newval', 'i', 'cls', body='''
            if (newval)
                e.classList.add(cls);
            else
                e.classList.remove(cls);
            ''')

        self.style = self.rdoc.jsfunction('vm', 'm', 'e', 'newval', 'i', 'style_att', 'style_opt', body='''
            if (newval)
                e.style[style_att]=style_opt;
            else
                e.style[style_att]='';
        ''')

        self.repeat = self.rdoc.jsfunction('vm', 'm', 'e', 'newval', 'i', body='''
            if (typeof e.app.template=='undefined') {
                e.app.template = e.children[0];
                e.removeChild(e.children[0]);
            }

            var ec = e.children;
            var ecl = ec.length;
            var arr = newval;
            var arrl = arr.length;
            var c = arrl-ecl;
            var te = e.app.template;
            var tag = te.tagName;
            var ih = te.innerHTML;
            var app = te.app;
            var eid = String(e.getAttribute('id'));
            var tid = String(te.getAttribute('id'));
            var id = eid+'_'+tid+'_';

            function copy_app_execute_controller(to, from, i) {
                if (typeof to.app=='undefined')
                    to.app = {};
                if ((typeof from.app!='undefined')&&
                    (typeof from.app.execute_controller!='undefined')) {
                    to.app.execute_controller = from.app.execute_controller;
                    to.app.oldval = new Array(from.app.oldval.length);
                }
                to.app.i = i;
                to.app.m = m;
                to.app.vm = vm;

                var fc = from.children;
                if (typeof fc=='undefined')
                    return;
                var tc = to.children;
                var l = tc.length;
                for (var ci=0; ci<l; ci++)
                    copy_app_execute_controller(tc[ci], fc[ci], i)
            }

            if (c>0)
                // add new elements
                for (var i=0; i<c; i++) {
                    var ee = te.cloneNode(true);
                    var eid = id+(i+ecl);
                    ee.setAttribute('id', eid);
                    ee.innerHTML = ih;
                    ee.app = {};
                    copy_app_execute_controller(ee, te, ecl+i);
                    e.appendChild(ee);
                }
            else
                // remove un-needed elements
                for (var i=c; i<0; i++)
                    e.removeChild(ec[ec.length-1]);
        ''')

        self.property = self.rdoc.jsfunction('vw', 'm', 'e', 'newval', 'i', 'prop', body='''
            e[prop] = newval;
        ''')

        self.code = self.rdoc.jsfunction('vm', 'm', 'e', 'newval', 'i', 'code', body='''
            eval(code);
        ''')

        self.ismuttable = self.rdoc.jsfunction('test', body='''return (test && (typeof test == 'object' || typeof test == 'function'))''')

        self.bind_html(html)

        if run:
            self.call_on_request_frame()

    def execute(self):
        self.rdoc.JS('''
            function crawl_element(e) {
                if ((typeof e!='undefined')&&(typeof e.app!='undefined')) {
                    e.app.m = #{self.model};
                    e.app.vm = #{self.viewmodel};
                    if (typeof e.app.execute_controller!='undefined')
                        for (var j=0, k=e.app.execute_controller, kl=k.length; j<kl; j++)
                            k[j](#{self.viewmodel}, #{self.model}, e, j, e.app.i);
                }
                for (var i=0, ec=e.children, ecl=ec.length; i<ecl; i++)
                    crawl_element(ec[i]);
            }
            crawl_element(document.body);
        ''')

    def bind(self, at, element, code, *varargs):
        if isinstance(code, str):
            fnc = self.rdoc.jsfunction('vm', 'm', 'e', 'i', body='return '+code)
        else:
            fnc = code
        whattodo = getattr(self, at)
        params = ','.join(varargs)
        s = '#{params}'
        if params:
            s = ',' + s
        self.rdoc.JS('''
            if (typeof #{element}.app == 'undefined')
                #{element}.app = {};
            if (typeof #{element}.app.execute_controller == 'undefined')
                #{element}.app.execute_controller = [];
            if (typeof #{element}.app.oldval == 'undefined')
                #{element}.app.oldval = [];
            #{element}.app.oldval.push(undefined);
            #{element}.app.m = #{self.model};
            #{element}.app.vm = #{self.viewmodel};
            #{element}.app.execute_controller.push(
                function(vm, m, e, j, i) {
                    var newval = #{fnc}(vm, m, e, i);
                    if ((#{self.ismuttable}(newval)) || (newval != e.app.oldval[j])) {
                        #{whattodo}(vm, m, e, newval, i'''+s+''');
                        e.app.oldval[j] = newval;
                    }
                });
        ''', encapsulate_strings=False)
        # TODO: remove above closure, for performance... maybe just turn the jsfunctions into strings to be embedded?

    def bind_html(self, html):
        class MyHTMLParser(HTMLParser):
            def __init__(self, ctrl):
                super().__init__()
                self.ctrl = ctrl
                self.tagdict = {}

            def handle_starttag(self, tag, attrs):
                if tag in self.tagdict:
                    self.tagdict[tag] += 1
                else:
                    self.tagdict[tag] = 0
                e = self.ctrl.rdoc.element(tag)
                self.ctrl.rdoc.JS('#{e} = document.getElementsByTagName(#{tag})['+str(self.tagdict[tag])+']')
                self.ctrl.rdoc.JS('''
                    if (typeof #{e}.app=='undefined')
                        #{e}.app = {};
                    #{e}.app.m = #{self.ctrl.model};
                    #{e}.app.vm = #{self.ctrl.viewmodel};
                ''')
                for attr in attrs:
                    if attr[0] == 'id':
                        eid = attr[1]
                        setattr(self.ctrl.e, eid.replace('-', '_').strip().replace(' ', '_'), e)
                    elif attr[0].startswith('weba-'):
                        at = attr[0][5:]
                        fv = attr[1]
                        for v in fv.split(':&:'):
                            s = v.split('::')
                            c = s[-1]
                            v = [l.strip() for l in s[:-1]]
                            self.ctrl.bind(at, e, c, *v)

        parser = MyHTMLParser(self)
        parser.feed(html)

    def call_on_request_frame(self):
        js = ''
        if hasattr(self, 'prerender'):
            js = '#{self.prerender}();\n'
        js += '''
            #{js_execute}();
            window.requestAnimationFrame(__recursive__);
        '''
        js_execute = self.rdoc.jsfunction(self.execute)
        fnc = self.rdoc.jsfunction(js, call=True, recursive=True)

########NEW FILE########
__FILENAME__ = remotedocument
import re
import random
import inspect
import logging

from ast import parse
from types import FunctionType
from inspect import getsource
from textwrap import dedent

from pythonium.veloce.veloce import Veloce

from webalchemy.saferef import safeRef
from webalchemy.htmlparser import get_element_ids


def srv():
    """
    stub so the ide doesn't show errows
    """
    pass


def rpc():
    """
    stub so the ide doesn't show errows
    """
    pass

def _vtranslate(code):
    tree = parse(code)
    translator = Veloce()
    translator.visit(tree)
    return translator.writer.value()


def _transchange(s, newname):
    """
    change a js function name. The function has to be generated by _vtranslate for this to work...
    """
    splt = _vtranslate(s).split('=', 1)
    splt0 = splt[0].split()
    splt0[1] = newname+' ='
    return ' '.join(splt0)+splt[1]


# logger for internal purposes
log = logging.getLogger(__name__)


class KeyCode:
    ENTER = 13
    ESC = 27


class StyleAtt:
    # TODO: populate this...
    _style_atts_requiring_vendor = {'transition', 'transform', 'userSelect', 'animation'}

    @staticmethod
    def _vendorize(vendor_prefix, item):
        if item == 'float':
            return ['cssFloat']
        if item.startswith('vendor'):
            real_item_cap = item[6:]
            real_item_uncap = real_item_cap[:1].lower() + real_item_cap[1:]
        elif item in StyleAtt._style_atts_requiring_vendor:
            real_item_cap = item[0].upper() + item[1:]
            real_item_uncap = item
        else:
            return [item]
        vendorized = [real_item_uncap]
        if vendor_prefix:
            vendorized.append(vendor_prefix + real_item_cap)
        return vendorized

    def __init__(self, rdoc, varname):
        super().__setattr__('rdoc', rdoc)
        super().__setattr__('varname', varname)
        super().__setattr__('d', {})

    def __setitem__(self, item, val):
        if isinstance(val, type({})):
            strval = '"{'
            for k, v in val.items():
                strv = ': ' + self.rdoc.stringify(v, encapsulate_strings=False) + ';\n'
                for ki in StyleAtt._vendorize(self.rdoc.vendor_prefix, k):
                    strval += ki
                    strval += strv
            strval += '}"'
        else:
            strval = self.rdoc.stringify(val)
        for vi in StyleAtt._vendorize(self.rdoc.vendor_prefix, item):
            js = self.varname + '.style["' + vi + '"]=' + strval + ';\n'
            self.rdoc.inline(js)
            self.d[vi] = val

    def __setattr__(self, attr, val):
        self[attr] = val

    def __getitem__(self, item):
        js = self.varname + '.style["' + item + '"];\n'
        self.rdoc.inline(js)
        return self.d[item]

    def __getattr__(self, name):
        return self[name]

    def __delitem__(self, item):
        for vi in StyleAtt._vendorize(self.rdoc.vendor_prefix, item):
            js = self.varname + '.style.removeProperty("' + vi + '");\n'
            self.rdoc.inline(js)
            del self.d[vi]

    def __delattr__(self, name):
        del self[name]

    def __call__(self, d=None, **kwargs):
        if d:
            if isinstance(d, dict):
                for k, v in d.items():
                    self[k] = v
            else:
                self['d'] = d
        for k, v in kwargs.items():
            self[k] = v


class ClassAtt:
    def __init__(self, rdoc, varname):
        self.rdoc = rdoc
        self.varname = varname
        self.lst = []

    def append(self, *varargs):
        for name in varargs:
            js = self.varname + '.classList.add("' + name + '");\n'
            self.rdoc.inline(js)
            self.lst.append(name)

    def extend(self, name_list):
        for name in name_list:
            self.append(name)

    def remove(self, *varargs):
        for name in varargs:
            js = self.varname + '.classList.remove("' + name + '");\n'
            self.rdoc.inline(js)
            self.lst.remove(name)

    def toggle(self, *varargs):
        for name in varargs:
            js = self.varname+'.classList.toggle("'+name+'");\n'
            self.rdoc.inline(js)
            if name in self.lst:
                self.lst.remove(name)
            else:
                self.lst.append(name)

    def replace(self, old_name, new_name):
        self.remove(old_name)
        self.append(new_name)

    def set(self, value):
        '''Set classes from value
        value is either list of strings or space separated string'''
        if isinstance(value, str):
            value = filter(None, value.split(" "))
        js = self.varname + '.className = "'+ ' '.join(value)+'";'
        self.rdoc.inline(js)
        self.lst = value
        


    def __delitem__(self, name):
        self.remove(name)


class SimpleAtt:
    def __init__(self, rdoc, varname):
        super().__setattr__('rdoc', rdoc)
        super().__setattr__('varname', varname)
        super().__setattr__('d', {})

    def __setitem__(self, item, val):
        js = self.varname + '.setAttribute("' + item + '",' + self.rdoc.stringify(val) + ');\n'
        self.rdoc.inline(js)
        self.d[item] = val

    def __setattr__(self, attr, val):
        self[attr] = val

    def __getitem__(self, item):
        js = self.varname + '.getAttribute("' + item + '");\n'
        self.rdoc.inline(js)
        return self.d[item]

    def __getattr__(self, name):
        return self[name]

    def __delitem__(self, item):
        js = self.varname + '.removeAttribute("' + item + '");\n'
        self.rdoc.inline(js)
        del self.d[item]

    def __delattr__(self, name):
        del self[name]

    def __call__(self, **kwargs):
        for k, v in kwargs.items():
            self[k] = v

    def __contains__(self, item):
        return item in self.d


class EventListener:
    def __init__(self, rdoc, varname, level=2):
        self.rdoc = rdoc
        self.varname = varname
        self.level = level

    def add(self, translate=False, **kwargs):
        for event, listener in kwargs.items():
            l = self.rdoc.stringify(listener, encapsulate_strings=False, pop_line=False, translate=translate)
            l = _inline(l, level=self.level, stringify=self.rdoc.stringify, rpcweakrefs=self.rdoc.jsrpcweakrefs)
            if not translate:
                js = self.varname + '.addEventListener("' + event + '",' + l + ',false);\n'
            else:
                js = l + '\n' + self.varname + '.addEventListener("' + event + '",' + listener.__name__ + ',false);\n'
            self.rdoc.inline(js)

    def remove(self, event, listener):
        l = self.rdoc.stringify(listener, encapsulate_strings=False, pop_line=False)
        l = _inline(l, level=self.level, stringify=self.rdoc.stringify, rpcweakrefs=self.rdoc.jsrpcweakrefs)
        js = self.varname + '.removeEventListener("' + event + '",' + l + ');\n'
        self.rdoc.inline(js)


class CallableProp:
    def __init__(self, rdoc, varname, namespace=None):
        super().__setattr__('rdoc', rdoc)
        if namespace:
            super().__setattr__('varname', varname + '.' + namespace)
        else:
            super().__setattr__('varname', varname)
        super().__setattr__('d', {})

    def __getattr__(self, name):
        def fnc(*varargs):
            js = self.varname + '.' + name + '('+','.join(self.rdoc.stringify(v) for v in varargs)+');\n'
            self.rdoc.inline(js)
        return fnc

class SimpleProp:
    def __init__(self, rdoc, varname=None, namespace=None, create=False):
        super().__setattr__('rdoc', rdoc)
        if not varname:
            super().__setattr__('varname', self.rdoc.get_new_uid())
            js = self.varname+'={};\n'
            self.rdoc.inline(js)
        else:
            super().__setattr__('varname', varname)
        if namespace:
            super().__setattr__('varname', varname + '.' + namespace)
        super().__setattr__('d', {})
        if create:
            self.rdoc.inline(self.varname + '= {};\n')

    def __setitem__(self, item, val):
        v = self.rdoc.stringify(val)
        js = self.varname + '["' + str(item) + '"]=' + v + ';\n'
        self.rdoc.inline(js)
        self.d[item] = val

    def __setattr__(self, attr, val):
        self[attr] = val

    def __getitem__(self, item):
        js = self.varname + '["' + str(item) + '"];\n'
        self.rdoc.inline(js)
        try:
            return self.d[item]
        except:
            pass

    def __getattr__(self, name):
        return self[name]

    def __delitem__(self, item):
        js = 'delete ' + self.varname + '["' + item + '"];\n'
        self.rdoc.inline(js)
        del self.d[item]

    def __delattr__(self, name):
        del self[name]

    def __call__(self, **kwargs):
        for k, v in kwargs.items():
            self[k] = v


class Element:
    # Namespace in which to create items of type 'typ'
    # this is good to handle SVGs, etc.
    _ns_typ_dict = {
        'svg': 'ww3/svg',
        'line': 'ww3/svg',
        'rect': 'ww3/svg',
        'circle': 'ww3/svg',
        'ellipse': 'ww3/svg',
        'polyline': 'ww3/svg',
        'polygon': 'ww3/svg',
        'path': 'ww3/svg',
        'g': 'ww3/svg',
    }

    # List of namespaces
    _unique_ns = {
        'ww3/svg': 'http://www.w3.org/2000/svg',
    }

    # additional attributes that elements of type 'typ' should have
    _add_attr_typ_dict = {
        'svg': {'xmlns': 'http://www.w3.org/2000/svg'},
    }

    def __init__(self, rdoc, typ=None, text=None, customvarname=None, fromid=None, app=True, 
                    cls="", att={}, style={}, innerHtml=None,
                    **kwargs):
        '''Initialize an Element - to be synced with client side
        
        rdoc:  remote document
        typ:   type of element (eg. div, span, input, button, form, etc...)
        text:  text to put inside element
        customvarname:  becomes the id of the element (generated if None)
        fromid:  id of existing element - None to generate id for new Element
        app:  Boolean, create app attribute on the proxy
        cls:  space separated classes
        att:  attributes  (eg.  colspan=3)
        style:  style (eg. margin-top:50px)
        innerHtml: overrides text parameter.
        
        Alternate init (shortcut):     Element(h1="Hello")    -->  typ="h1"   text="Hello"
        '''
        if not typ and len(kwargs) == 1:
            typ, text = kwargs.popitem()
        self.varname = customvarname if (customvarname) else rdoc.get_new_uid()
        self.rdoc = rdoc
        self.typ = typ
        self.parent = None
        self.childs = []
        if not fromid:
            if typ in Element._ns_typ_dict:
                ns = Element._unique_ns[Element._ns_typ_dict[typ]]
                js = 'var ' + self.varname + '=document.createElementNS("' + ns + '","' + typ + '");\n'
            else:
                js = 'var ' + self.varname + '=document.createElement("' + typ + '");\n'
        else:
            js = 'var ' + self.varname + '=document.getElementById("' + fromid + '");\n'
        if innerHtml is not None:
            self._text = innerHtml
            js += self.varname + '.innerHTML="'+innerHtml+'";\n'
        elif text is not None:
            self._text = text
            js += self.varname + '.textContent="' + text + '";\n'
        else:
            self._text = ''
        rdoc.inline(js)

        self.cls = ClassAtt(rdoc, self.varname)
        if cls:
            self.cls.set(cls)
        self.att = SimpleAtt(rdoc, self.varname)
        if att:
            self.att(**att)
        self.style = StyleAtt(rdoc, self.varname)
        if self.style:
            self.style(**style)

        self.events = EventListener(rdoc, self.varname)
        if app:
            self.app = SimpleProp(rdoc, self.varname, 'app', create=True)
        self.prop = SimpleProp(self.rdoc, self.varname, None)
        self.cal = CallableProp(self.rdoc, self.varname, None)
        if typ in Element._add_attr_typ_dict:
            self.att(**Element._add_attr_typ_dict[typ])
        self.att.id = self.varname

    def remove(self):
        s = self.varname + '.parentNode.removeChild(' + self.varname + ');\n'
        self.rdoc.inline(s)
        self.parent.childs.remove(self)
        self.parent = None

    def append(self, es, track=False):
        handled = False
        if not hasattr(es, 'varname'):
            try:
                for e in es:
                    if track:
                        self.childs.append(e)
                        if isinstance(e, Element):
                            es.parent = self
                    s = self.varname + '.appendChild(' + e.varname + ');\n'
                    self.rdoc.inline(s)
                handled = True
            except:
                pass
        if not handled:
            if track:
                self.childs.append(es)
                if isinstance(es, Element):
                    es.parent = self
            s = self.varname + '.appendChild(' + es.varname + ');\n'
            self.rdoc.inline(s)

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, text):
        self.set_text(text)

    def set_text(self, text, transmit=True):
        self._text = text
        if transmit:
            js = self.varname + '.textContent="' + text + '";\n'
            self.rdoc.inline(js)

    def __str__(self):
        return self.varname

    def element(self, typ=None, text=None, app=True, track=False, **kwargs):
        es = self.rdoc.element(typ, text, app=app, **kwargs)
        self.append(es, track)
        return es


class Window:
    def __init__(self, rdoc):
        self.rdoc = rdoc
        self.varname = 'window'
        self.events = EventListener(rdoc, self.varname)


_rec1_inline = re.compile(r'#\{([^}]*)\}')
_rec2_rpc = re.compile(r'#rpc\{([^}]*)\}')


def _evl(item, glo, loc):
    sitem = item.split('.')
    if sitem[0]=='this':
        sitem[0]='self'
    if sitem[0] in loc:
        rep = loc[sitem[0]]
    else:
        rep = glo[sitem[0]]
    if len(sitem) > 1:
        for it in sitem[1:]:
            rep = getattr(rep, it)
    return rep


def _inline(code, level=1, stringify=None, rpcweakrefs=None, **kwargs):
    # inline interpolation...
    prev_frame = inspect.getouterframes(inspect.currentframe())[level][0]
    loc = prev_frame.f_locals
    glo = prev_frame.f_globals
    for item in _rec1_inline.findall(code):
        rep = _evl(item, glo, loc)
        if not stringify:
            rep = rep.varname if hasattr(rep, 'varname') else str(rep)
        else:
            rep = stringify(rep, encapsulate_strings=kwargs.get('encapsulate_strings', True))
        code = code.replace('#{%s}' % item, rep)

    if rpcweakrefs is not None:
        for item in _rec2_rpc.findall(code):
            sitem = item.split(',')
            litem = sitem[0].strip().replace('this.', 'self.')
            ritem = ','.join(sitem[1:])
            fnc = _evl(litem, glo, loc)
            rep = str(random.randint(0, 1e16))

            def ondelete(r):
                del rpcweakrefs[r.__rep]

            wr = safeRef(fnc, ondelete)
            wr.__rep = rep
            # TODO: should we check for existance first? i.e. every RPC should have its own random number, or can we reuse it?
            rpcweakrefs[rep] = wr
            code = code.replace('#rpc{%s}' % item, 'rpc(%s)' % ("'"+rep+"',"+ritem))

    return code


class Interval:
    def __init__(self, rdoc, ms, exp=None, level=2):
        self.rdoc = rdoc
        self.varname = rdoc.get_new_uid()
        self.ms = ms
        self.is_running = True
        # TODO: replace this with a jsfunction...
        code = self.rdoc.stringify(exp, pop_line=False)
        code = _inline(code, level=level, rpcweakrefs=self.rdoc.rpcweakrefs)
        js = 'var ' + self.varname + '=setInterval(' + code + ',' + str(ms) + ');\n'
        rdoc.inline(js)

    def stop(self):
        self.is_running = False
        js = 'clearInterval(' + self.varname + ');\n'
        self.rdoc.inline(js)


class JSFunction:
    def __init__(self, rdoc, *varargs, body=None, level=2, varname=None, recursive=False, **kwargs):
        if len(varargs) == 2 and not body:
            body = varargs[1]
            varargs = (varargs[0],)
        elif len(varargs) == 1 and not body:
            body = varargs[0]
            varargs = ()
        self.rdoc = rdoc
        self.varname = varname if (varname) else rdoc.get_new_uid()


        code = self.rdoc.stringify(body, encapsulate_strings=False, pop_line=False, vars=varargs)

        if recursive:
            code = code.replace('__recursive__', self.varname)

        code = _inline(code, level=level, stringify=rdoc.stringify, rpcweakrefs=self.rdoc.jsrpcweakrefs, encapsulate_strings=False)

        code = code.rstrip(';\n')
        args = ','.join(varargs)
        if not code.startswith('function'):
            self.js = 'var '+self.varname + '=function(' + args + '){\n' + code + '\n}\n'
        else:
            self.js = 'var ' + self.varname + '='+code+'\n'
        rdoc.inline(self.js)
        if kwargs.get('call', False):
            self()

    def __call__(self, *varargs):
        js = self.varname + '(' + ','.join([self.rdoc.stringify(v) for v in varargs]) + ');\n'
        self.rdoc.inline(js)

    def __str__(self):
        return self.varname + '();\n'


class JSClass:
    # TODO: cache the creation of classes!
    def __init__(self, rdoc, cls, level=2, new=True):
        super().__setattr__('rdoc', rdoc)
        super().__setattr__('classname', cls.__name__)
        super().__setattr__('varname', rdoc.get_new_uid())

        js = _vtranslate(dedent(getsource(cls)))

        if new:
            js += '\n' + self.varname + ' = new '+self.classname + '();\n'
        else:
            js += '\n' + self.varname + ' = '+self.classname + ';\n'

        self.rdoc.JS(js, level=level)

        class jsmethod:
            def __init__(self, jsclass, name):
                self.jsclass = jsclass
                self.varname = jsclass.varname + '.' + name

            def __call__(self, *varargs):
                self.jsclass.rdoc.inline(self.varname+'('+','.join(varargs)+');\n')

        for attr in dir(cls):
            if attr.startswith('__'):
                continue
            if not isinstance(getattr(cls, attr), FunctionType):
                continue
            super().__setattr__(attr, jsmethod(self, attr))

    def __getattr__(self, item):
        class attr:
            def __init__(self, rdoc, name):
                super().__setattr__('rdoc', rdoc)
                super().__setattr__('varname', name)

            def __getattr__(self, item):
                return attr(self.rdoc, self.varname + '.' + item)

            def __setattr__(self, item, val):
                js = self.varname + '.' + item + '=' + self.rdoc.stringify(val)
                self.rdoc.inline(js)

            def __getitem__(self, key):
                return attr(self.rdoc, self.varname + '[' + str(key) + ']')

            def __call__(self, *varargs):
                self.rdoc.inline(self.varname+'('+','.join([self.rdoc.stringify(a) for a in varargs])+');\n')

        return attr(self.rdoc, self.varname + '.' + item)

    def __setattr__(self, item, val):
        js = self.varname + '.' + item + '=' + self.rdoc.stringify(val)
        self.rdoc.inline(js)

    def __call__(self, *varargs):
        self.rdoc.inline(self.varname+'('+','.join([self.rdoc.stringify(a) for a in varargs])+');\n')


class _StyleSheet:
    def __init__(self, rdoc):
        self.rdoc = rdoc
        self.element = rdoc.element('style')
        self.varname = self.element.varname
        self.element.att.type = 'text/css'
        self.rdoc.body.append(self.element)
        js = 'var ' + self.varname + '=document.styleSheets[0];\n'
        self.rdoc.inline(js)

    def rule(self, selector, **kwargs):
        return _Rule(self, selector, **kwargs)


class _Rule:
    def __init__(self, stylesheet, selector, **kwargs):
        if selector.split()[0] == '@keyframes' and stylesheet.rdoc.vendor_prefix == 'webkit':
            selector = '@-webkit-' + selector[1:]
        self.stylesheet = stylesheet
        self.rdoc = self.stylesheet.rdoc
        self.varname = self.rdoc.get_new_uid()
        self.selector = selector
        ssn = self.stylesheet.varname
        js = ssn + '.insertRule("' + selector + ' {}",' + ssn + '.cssRules.length);\n'
        js += 'var ' + self.varname + '=' + ssn + '.cssRules[' + ssn + '.cssRules.length-1];\n'
        self.rdoc.inline(js)
        self.style = StyleAtt(self.rdoc, self.varname)
        self.style(**kwargs)


class RemoteDocument:
    # TODO: remove block altogether...
    def __init__(self):
        self.varname = 'document'
        self.__uid_count = 0
        self.__code_strings = []
        self.__block_ixs = []
        self.__varname_element_dict = {}
        self.body = Element(self, 'body', '', customvarname='document.body')
        self.head = Element(self, 'head', '', customvarname='document.head')
        self.pop_all_code()  # body and head are special: created by static content
        self.app = SimpleProp(self, 'document', 'app', create=True)
        self.props = SimpleProp(self, 'document')
        self.localStorage = SimpleProp(self, 'localStorage')
        self.sessionStorage = SimpleProp(self, 'localStorage')
        self.stylesheet = _StyleSheet(self)
        self.vendor_prefix = None
        self.jsrpcweakrefs = {}
        self.window = Window(self)
        self.KeyCode = KeyCode

    def parse_elements(self, html):
        class E:
            pass
        e = E()
        for id in get_element_ids(html):
            try:
                attr_id = id.replace('-', '_').replace(' ', '_')
                setattr(e, attr_id, self.getElementById(id))
            except:
                pass
        return e

    def set_vendor_prefix(self, vendor_prefix):
        self.vendor_prefix = vendor_prefix

    def get_element_from_varname(self, varname) -> Element:
        return self.__varname_element_dict[varname]

    def getElementById(self, fromid, app=False):
        return Element(self, fromid=fromid, app=app)

    def element(self, typ=None, text=None, app=True, **kwargs):
        kwargs["app"] = app
        return Element(self, typ, text, **kwargs)

    def startinterval(self, ms, exp=None):
        return Interval(self, ms, exp, level=3)

    def jsfunction(self, *varargs, body=None, level=3, **kwargs):
        return JSFunction(self, *varargs, body=body, level=level, **kwargs)

    def get_new_uid(self):
        uid = '__v' + str(self.__uid_count)
        self.__uid_count += 1
        return uid

    def begin_block(self):
        self.__block_ixs.append(len(self.__code_strings))

    def cancel_block(self):
        self.__block_ixs.pop()

    def pop_block(self):
        ix = self.__block_ixs.pop()
        code = ''
        for i in range(len(self.__code_strings) - ix):
            code = self.__code_strings.pop() + code
        return code

    def pop_all_code(self):
        code = ''.join(self.__code_strings)
        del self.__code_strings[:]
        del self.__block_ixs[:]
        return code

    def pop_line(self):
        return self.__code_strings.pop()

    def inline(self, text, *varargs):
        """
        insert a code block (contained in 'text' parameter)
        """
        if varargs:
            text = text.format(*(v.varname for v in varargs))
        self.__code_strings.append(text)

    def JS(self, text, encapsulate_strings=True, level=2):
        self.__code_strings.append(_inline(text, level=level, stringify=self.stringify, rpcweakrefs=self.jsrpcweakrefs, encapsulate_strings=encapsulate_strings))

    def msg(self, text):
        self.inline('message("' + text + '");')

    def stylesheet(self):
        return _StyleSheet(self)

    def dict(self):
        return SimpleProp(self)

    def stringify(self, val=None, custom_stringify=None, encapsulate_strings=True, pop_line=True, vars=None, translate=False):
        if type(val) is bool:
            return 'true' if val else 'false'
        if hasattr(val, 'varname'):
            return val.varname
        if type(val) is str:
            return '"' + str(val) + '"' if encapsulate_strings else val
        if callable(val):
            if translate:
                return _vtranslate(dedent(getsource(val)))
            else:
                self.begin_block()
                tmp = val(*vars) if vars else val()
                if tmp:
                    self.cancel_block()
                else:
                    tmp = self.pop_block()
                if not tmp:
                    raise Exception('cant find callable '+val.__name__+'. Maybe it needs to get translated?')
                if not vars:
                    return 'function(){' + tmp + '}'
                else:
                    for v in vars:
                        tmp = tmp.replace('"'+v+'"', v)
                    return 'function('+','.join(v for v in vars)+'){' + tmp + '}'
        if val is None:
            if pop_line:
                return self.pop_line()
            return self.pop_block()
        if custom_stringify:
            return custom_stringify(val)
        return str(val)

    def new(self, cls):
        return JSClass(self, cls, level=4)

    def translate(self, cls):
        return JSClass(self, cls, level=4, new=False)


########NEW FILE########
__FILENAME__ = saferef
# this won't be needed in Python 3.4 :)
# taken from:
# https://github.com/django/django/blob/master/django/dispatch/saferef.py

"""
"Safe weakrefs", originally from pyDispatcher.

Provides a way to safely weakref any function, including bound methods (which
aren't handled by the core weakref module).
"""

import traceback
import weakref


def safeRef(target, onDelete=None):
    """Return a *safe* weak reference to a callable target

    target -- the object to be weakly referenced, if it's a
        bound method reference, will create a BoundMethodWeakref,
        otherwise creates a simple weakref.
    onDelete -- if provided, will have a hard reference stored
        to the callable to be called after the safe reference
        goes out of scope with the reference object, (either a
        weakref or a BoundMethodWeakref) as argument.
    """
    if hasattr(target, '__self__'):
        if target.__self__ is not None:
            # Turn a bound method into a BoundMethodWeakref instance.
            # Keep track of these instances for lookup by disconnect().
            assert hasattr(target, '__func__'), """safeRef target %r has __self__, but no __func__, don't know how to create reference""" % (target,)
            reference = get_bound_method_weakref(
                target=target,
                onDelete=onDelete
            )
            return reference
    if callable(onDelete):
        return weakref.ref(target, onDelete)
    else:
        return weakref.ref(target)


class BoundMethodWeakref(object):
    """'Safe' and reusable weak references to instance methods

    BoundMethodWeakref objects provide a mechanism for
    referencing a bound method without requiring that the
    method object itself (which is normally a transient
    object) is kept alive.  Instead, the BoundMethodWeakref
    object keeps weak references to both the object and the
    function which together define the instance method.

    Attributes:
        key -- the identity key for the reference, calculated
            by the class's calculateKey method applied to the
            target instance method
        deletionMethods -- sequence of callable objects taking
            single argument, a reference to this object which
            will be called when *either* the target object or
            target function is garbage collected (i.e. when
            this object becomes invalid).  These are specified
            as the onDelete parameters of safeRef calls.
        weakSelf -- weak reference to the target object
        weakFunc -- weak reference to the target function

    Class Attributes:
        _allInstances -- class attribute pointing to all live
            BoundMethodWeakref objects indexed by the class's
            calculateKey(target) method applied to the target
            objects.  This weak value dictionary is used to
            short-circuit creation so that multiple references
            to the same (object, function) pair produce the
            same BoundMethodWeakref instance.

    """

    _allInstances = weakref.WeakValueDictionary()

    def __new__(cls, target, onDelete=None, *arguments, **named):
        """Create new instance or return current instance

        Basically this method of construction allows us to
        short-circuit creation of references to already-
        referenced instance methods.  The key corresponding
        to the target is calculated, and if there is already
        an existing reference, that is returned, with its
        deletionMethods attribute updated.  Otherwise the
        new instance is created and registered in the table
        of already-referenced methods.
        """
        key = cls.calculateKey(target)
        current = cls._allInstances.get(key)
        if current is not None:
            current.deletionMethods.append(onDelete)
            return current
        else:
            base = super(BoundMethodWeakref, cls).__new__(cls)
            cls._allInstances[key] = base
            base.__init__(target, onDelete, *arguments, **named)
            return base

    def __init__(self, target, onDelete=None):
        """Return a weak-reference-like instance for a bound method

        target -- the instance-method target for the weak
            reference, must have __self__ and __func__ attributes
            and be reconstructable via:
                target.__func__.__get__( target.__self__ )
            which is true of built-in instance methods.
        onDelete -- optional callback which will be called
            when this weak reference ceases to be valid
            (i.e. either the object or the function is garbage
            collected).  Should take a single argument,
            which will be passed a pointer to this object.
        """
        def remove(weak, self=self):
            """Set self.isDead to true when method or instance is destroyed"""
            methods = self.deletionMethods[:]
            del self.deletionMethods[:]
            try:
                del self.__class__._allInstances[self.key]
            except KeyError:
                pass
            for function in methods:
                try:
                    if callable(function):
                        function(self)
                except Exception as e:
                    try:
                        traceback.print_exc()
                    except AttributeError:
                        print('Exception during saferef %s cleanup function %s: %s' % (
                            self, function, e)
                        )
        self.deletionMethods = [onDelete]
        self.key = self.calculateKey(target)
        self.weakSelf = weakref.ref(target.__self__, remove)
        self.weakFunc = weakref.ref(target.__func__, remove)
        self.selfName = str(target.__self__)
        self.funcName = str(target.__func__.__name__)

    @classmethod
    def calculateKey(cls, target):
        """Calculate the reference key for this reference

        Currently this is a two-tuple of the id()'s of the
        target object and the target function respectively.
        """
        return (id(target.__self__), id(target.__func__))

    def __str__(self):
        """Give a friendly representation of the object"""
        return """%s( %s.%s )""" % (
            self.__class__.__name__,
            self.selfName,
            self.funcName,
        )

    __repr__ = __str__

    def __hash__(self):
        return hash(self.key)

    def __bool__(self):
        """Whether we are still a valid reference"""
        return self() is not None

    def __nonzero__(self):      # Python 2 compatibility
        return type(self).__bool__(self)

    def __eq__(self, other):
        """Compare with another reference"""
        if not isinstance(other, self.__class__):
            return self.__class__ == type(other)
        return self.key == other.key

    def __call__(self):
        """Return a strong reference to the bound method

        If the target cannot be retrieved, then will
        return None, otherwise returns a bound instance
        method for our object and function.

        Note:
            You may call this method any number of times,
            as it does not invalidate the reference.
        """
        target = self.weakSelf()
        if target is not None:
            function = self.weakFunc()
            if function is not None:
                return function.__get__(target)
        return None


class BoundNonDescriptorMethodWeakref(BoundMethodWeakref):
    """A specialized BoundMethodWeakref, for platforms where instance methods
    are not descriptors.

    It assumes that the function name and the target attribute name are the
    same, instead of assuming that the function is a descriptor. This approach
    is equally fast, but not 100% reliable because functions can be stored on an
    attribute named differenty than the function's name such as in:

    class A: pass
    def foo(self): return "foo"
    A.bar = foo

    But this shouldn't be a common use case. So, on platforms where methods
    aren't descriptors (such as Jython) this implementation has the advantage
    of working in the most cases.
    """
    def __init__(self, target, onDelete=None):
        """Return a weak-reference-like instance for a bound method

        target -- the instance-method target for the weak
            reference, must have __self__ and __func__ attributes
            and be reconstructable via:
                target.__func__.__get__( target.__self__ )
            which is true of built-in instance methods.
        onDelete -- optional callback which will be called
            when this weak reference ceases to be valid
            (i.e. either the object or the function is garbage
            collected).  Should take a single argument,
            which will be passed a pointer to this object.
        """
        assert getattr(target.__self__, target.__name__) == target, \
               ("method %s isn't available as the attribute %s of %s" %
                (target, target.__name__, target.__self__))
        super(BoundNonDescriptorMethodWeakref, self).__init__(target, onDelete)

    def __call__(self):
        """Return a strong reference to the bound method

        If the target cannot be retrieved, then will
        return None, otherwise returns a bound instance
        method for our object and function.

        Note:
            You may call this method any number of times,
            as it does not invalidate the reference.
        """
        target = self.weakSelf()
        if target is not None:
            function = self.weakFunc()
            if function is not None:
                # Using partial() would be another option, but it erases the
                # "signature" of the function. That is, after a function is
                # curried, the inspect module can't be used to determine how
                # many arguments the function expects, nor what keyword
                # arguments it supports, and pydispatcher needs this
                # information.
                return getattr(target, function.__name__)
        return None


def get_bound_method_weakref(target, onDelete):
    """Instantiates the appropiate BoundMethodWeakRef, depending on the details of
    the underlying class method implementation"""
    if hasattr(target, '__get__'):
        # target method is a descriptor, so the default implementation works:
        return BoundMethodWeakref(target=target, onDelete=onDelete)
    else:
        # no luck, use the alternative implementation:
        return BoundNonDescriptorMethodWeakref(target=target, onDelete=onDelete)
########NEW FILE########
__FILENAME__ = server
"""WebAlchemy Server implementation.

When the "run" method is invoked with an application as argument 
the server sets some configurations and executes the Tornado Webserver
with two handlers.

The _MainHandler is responsible for handling the requests to the base 
html file. The base html file, in the client, then connects through a 
websocket to the WebAlchemy server.

The WebSocketHandler is responsible for starting the application and 
handling the client requests through the websocket.

This file includes also resources for monitoring changes in local files.
"""


import os
import imp
import sys
import time
import random
import logging
import os.path
import linecache

from types import ModuleType
from collections import OrderedDict

from uuid import uuid1

import tornado
import tornado.web
import tornado.ioloop

from sockjs.tornado import SockJSRouter, SockJSConnection

from tornado import gen

from .remotedocument import RemoteDocument
from .mainhtml import generate_main_html_for_server, generate_static_main_html
from .config import read_config_from_app, from_dict

# logger for internal purposes
log = logging.getLogger(__name__)


def _generate_session_id():
    """Generate a session id.
    a Version 1 uuid as specified by RFC4122, see here: http://tools.ietf.org/html/rfc4122.html"""
    return str(uuid1())

@gen.coroutine
def async_delay(secs):
    """Forces an asynchronous delay on the Tornado server loop.
    This allows us to implement our own loops without messing with the main Tornado loop."""
    yield gen.Task(tornado.ioloop.IOLoop.instance().add_timeout, time.time() + secs)

def _dreload(module, dreload_blacklist_starting_with, just_visit=False):
    """Reloads a module.
    This is usually called when a local file is changed."""
    _s = {module.__name__}
    _base_file = os.path.realpath(module.__file__)
    _base_path = os.path.dirname(_base_file)
    _reloaded_files = []

    def __dreload(mdl):
        """Recursively reload modules."""
        nonlocal _s
        nonlocal _base_path
        nonlocal _reloaded_files

        for name in dir(mdl):
            mm = getattr(mdl, name)
            if type(mm) is not ModuleType:
                if (hasattr(mm, '__module__') and
                        mm.__module__ is not None):
                    mm = sys.modules[mm.__module__]

            if (not hasattr(mm, '__file__') or
                    not os.path.realpath(mm.__file__).startswith(_base_path) or
                    mm.__name__[0] == '_' or
                    '._' in mm.__name__ or
                    mm.__name__ in _s or
                    any(mm.__name__.startswith(bln) for bln in dreload_blacklist_starting_with)):
                continue

            _s.add(mm.__name__)
            __dreload(mm)
        _reloaded_files.append(os.path.realpath(mdl.__file__))
        if not just_visit:
            log.info('reloading: ' + str(mdl.__name__))
            linecache.clearcache()
            imp.reload(mdl)
        else:
            log.info('visiting: ' + str(mdl.__name__))

    __dreload(module)
    return _reloaded_files


# ================================ #
#      Tornado server handlers     #
# ================================ #

class _MainHandler(tornado.web.RequestHandler):
    """Handles the initial requests to the main html page."""

    def initialize(self, **kwargs):
        log.info('Initiallizing new app!')
        self.main_html = kwargs['main_html']

    @gen.coroutine
    def get(self, *varargs):
        """ Implement the HTTP GET method. """
        self.add_header('X-UA-Compatible', 'IE=edge')
        if not varargs:
            varargs = ('',)
        self.main_html = self.main_html.replace('__ARGS__', str(varargs[0]))
        self.write(self.main_html)


@gen.coroutine
def async_delay(secs):
    yield gen.Task(tornado.ioloop.IOLoop.instance().add_timeout, time.time() + secs)


class WebSocketHandler(SockJSConnection):
    """Handless the websocket calls from the client."""

    @gen.coroutine
    def on_open(self, info):
        log.info('Websocket opened. Initiallizing a websocket handler!')
        self.id = _generate_session_id()
        self.remotedocument = RemoteDocument()
        self.closed = True
        self.session_id = None
        self.tab_id = None
        self.vendor_type = None
        self.additional_args = self.session.server.settings['handler_args']
        self.shared_data = self.additional_args['shared_data']
        self.session_data_store = self.additional_args['session_data_store']
        self.tab_data_store = self.additional_args['tab_data_store']
        self.session_data = None
        self.tab_data = None
        self.local_doc = self.additional_args['local_doc_class']()
        self.local_doc_initialized = False
        self.sharedhandlers = self.additional_args['shared_wshandlers']
        self.sharedhandlers[self.id] = self
        self.is_new_tab = None
        self.is_new_session = None
        self.main_html = self.additional_args['main_html']
        self.closed = False

    @gen.coroutine
    def handle_binary_message(self, message):
        # TODO: implement this!
        raise NotImplementedError
    
    @gen.coroutine
    def on_close(self):
        """Removes all shared function handlers and prepares
        the application for termination or reloading."""
        self.closed = True
        log.info('WebSocket closed')
        log.info('Removing shared doc')
        del self.sharedhandlers[self.id]
        if hasattr(self.local_doc, 'onclose'):
            log.info('Calling local document onclose:')
            try:
                # Inform application of the termination and yield results
                res = self.local_doc.onclose()
                if (res):
                    yield res
            except:
                log.exception('Failed handling local document onclose. Exception:')

    @gen.coroutine
    def on_message(self, message):
        """Receives a message from the client and handles it according to the content."""
        log.info('Message received:\n' + message)
        try:
            if not isinstance(message, str):
                log.info('binary data')
                yield self.handle_binary_message(message)
            elif message == 'heartbeat':
                # Heartbeat is only to keep connections alive
                pass
            elif not self.local_doc_initialized:
                log.info('Initializing local document...')
                yield self.init_localdocument(message)
                yield self.send_heartbeat()
            else:
                if message.startswith('rpc: '):
                    yield self.handle_js_to_py_rpc_message(message)
                elif message != 'done':
                    log.info('Passing message to document inmessage...')
                    res = self.local_doc.inmessage(message)
                    if (res):
                        yield res
                elif message != 'done':
                    raise Exception('bad message received: ' + str(message))
            yield self.flush_dom()
        except:
            log.exception('Failed handling message:')

    @gen.coroutine
    def send_data(self, text, data):
        # TODO: implement!
        # will have to have a binary format for both text and binary data
        # also change the handling in the client
        raise NotImplementedError

    @gen.coroutine
    def flush_dom(self):
        """Clears the DOM manipulation content on the remote document."""
        code = self.remotedocument.pop_all_code()
        if code != '':
            log.info('FLUSHING DOM WITH FOLLOWING MESSAGE:\n' + code)
            #yield async_delay(2)  # this is good to simulate latency
            self.send(code)
        else:
            log.info('FLUSHING DOM: **NOTHING TO FLUSH**')

    @gen.coroutine
    def please_reload(self):
        """Sends a reload request through the websocket and closes."""
        self.send('location.reload();\n')
        self.close()

    @gen.coroutine
    def msg_to_sessions(self, msg, send_to_self=False, to_session_ids=None):
        """Broadcasts a message to all sessions in the 'to_session_ids' list.
        If no sessions are mentioned, it broadcasts to all sessions. """
        log.info('Sending message to sessions ' + str(len(self.sharedhandlers)) + ' documents in process:')
        log.info('Message: ' + msg)
        session_ids = to_session_ids if (to_session_ids) else self.sharedhandlers.keys()
        for _id in session_ids:
            handler = self.sharedhandlers[_id]
            if (handler is not self) or send_to_self:
                try:
                    res = handler.local_doc.outmessage(self.id, msg)
                    if (res):
                        yield res
                    yield handler.flush_dom()
                except:
                    log.exception('Failed handling outmessage. Exception:')

    @gen.coroutine
    def prepare_session_for_general_reload(self):
        if hasattr(self.local_doc, 'prepare_session_for_general_reload'):
            log.info('preparing session for reload...')
            res = self.local_doc.prepare_session_for_general_reload()
            if (res):
                yield res
                
    @gen.coroutine
    def handle_binary_message(self, message):
        # TODO: implement this!
        raise NotImplementedError

    @gen.coroutine
    def send_heartbeat(self):
        """Keeps sending a message to keep the client alive."""
        while True:
            if self.closed:
                return
            # we have to send something executable by JS, or else treat it on the other side...
            self.send(';')
            log.info('sending heartbeat...')
            yield async_delay(random.random()*10 + 25)
            
    @gen.coroutine
    def init_localdocument(self, message):
        """ Procedure to initiate the local application. """
        self.session_id = message.split(':')
        if len(self.session_id) < 2:
            return
        self.session_id = self.session_id[1]
        self.is_new_session = False
        if self.session_id == 'null':
            log.info('initializing new session...')
            self.is_new_session = True
            self.session_id = self.id
            self.remotedocument.inline('set_cookie("webalchemy","' + self.session_id + '",3);\n')
        self.tab_id = message.split(':')[3]
        self.is_new_tab = False
        if self.tab_id == '':
            log.info('initializing new tab...')
            self.tab_id = self.id
            self.remotedocument.inline('window.name="' + self.tab_id + '";\n')
            self.is_new_tab = True
        self.vendor_type = message.split(':')[-1]
        self.remotedocument.set_vendor_prefix(self.vendor_type)
        self.session_data = self.session_data_store.get_store(self.session_id)
        self.tab_data = self.tab_data_store.get_store(self.tab_id)
        
        # Initializes the application and yields any returning results
        res = self.local_doc.initialize(remote_document=self.remotedocument, comm_handler=self,
                                        session_id=self.session_id, tab_id=self.tab_id,
                                        shared_data=self.shared_data, session_data=self.session_data,
                                        tab_data=self.tab_data, is_new_tab=self.is_new_tab,
                                        is_new_session=self.is_new_session,
                                        main_html=self.main_html)
        if (res):
            yield res
        self.local_doc_initialized = True

    @gen.coroutine
    def handle_js_to_py_rpc_message(self, msg):
        """Handles a RPC request initiated on the client."""
        log.info('Handling message as js->py RPC call')
        # Retrieve the arguments from the message
        pnum, *etc = msg[5:].split(',')
        pnum = int(pnum)
        args_len = etc[:pnum]
        args_txt = ''.join(etc[pnum:])
        args = []
        curr_pos = 0
        for ln in args_len:
            ln = int(ln)
            args.append(args_txt[curr_pos:curr_pos + ln])
            curr_pos += ln
        rep, *args = args
        # Get the reference to the local function
        wr = self.remotedocument.jsrpcweakrefs[rep]
        fn = wr()
        if fn is None:
            del self.remotedocument.jsrpcweakrefs[rep]
        log.info('Calling local function: ' + str(fn))
        log.info('With args: ' + str(args))
        try:
            # Execute the function and yield any results
            # TODO: Has the client permission to execute the function?
            res = fn(self.id, *args)
            if (res):
                yield res
        except:
            log.exception('JS RPC call failed')

    @gen.coroutine
    def rpc(self, f, *varargs, send_to_self=False, to_session_ids=None, **kwargs):
        """Executes a local initiated RPC call."""
        log.info('Sending py->py rpc: ' + f.__name__)
        log.info('PARAMS: varargs: ' + str(varargs) + ' kwargs: ' + str(kwargs)) 
        session_ids = to_session_ids if (to_session_ids) else self.sharedhandlers.keys()
        # Get the session handlers and execute the function
        for _id in session_ids:
            handler = self.sharedhandlers[_id]
            if (handler is not self) or send_to_self:
                try:
                    res = getattr(handler.local_doc, f.__name__)(self.id, *varargs, **kwargs)
                    if (res):
                        yield res
                    yield handler.flush_dom()
                except:
                    log.exception('PY RPC call failed for target session: ' + _id)


# ================================ #
#          Reload handler          #
# ================================ #

class _AppUpdater:
    """Tracks changes in local files and triggers reloads."""

    def __init__(self, app, kwa, router, cls, shared_wshandlers, dreload_blacklist_starting_with, shared_data,
                 additional_monitored_files):
        self.app = app
        self.kwa = kwa
        self.router = router
        self.cls = cls
        self.shared_wshandlers = shared_wshandlers
        self.shared_data = shared_data
        self.dreload_blacklist_starting_with = dreload_blacklist_starting_with
        self.mdl = sys.modules[self.cls.__module__]
        self.mdl_fn = self.mdl.__file__
        self.monitored_files = _dreload(self.mdl, self.dreload_blacklist_starting_with, just_visit=True)
        self.set_additional_monitored_files(additional_monitored_files)
        log.info('monitored files: ' + str(self.monitored_files))
        self.last_time_modified = {fn: os.stat(fn).st_mtime for fn in self.monitored_files}

    def set_additional_monitored_files(self, fns):
        if fns:
            self.monitored_files.extend(fns)

    def update_app(self):
        """This method will be looping on the server so it can track changes in local files.
        Every time a change is found, it reloads the application."""
        try:
            # Compare file system modification times with the caches and returns if no modification is found.
            # this is inside a try block so we track for missing files
            if not any(os.stat(fn).st_mtime != self.last_time_modified[fn] for fn in self.monitored_files):
                return
        except:
            pass
        log.info('Reloading document!')
        self.last_time_modified = {fn: os.stat(fn).st_mtime for fn in self.monitored_files}
        data = None
        if hasattr(self.cls, 'prepare_app_for_general_reload'):
            data = self.cls.prepare_app_for_general_reload()
        _dreload(self.mdl, self.dreload_blacklist_starting_with)
        tmp_cls = getattr(self.mdl, self.cls.__name__)
        if hasattr(tmp_cls, 'recover_app_from_general_reload'):
            tmp_cls.recover_app_from_general_reload(data)
        if hasattr(tmp_cls, 'initialize_shared_data'):
            tmp_cls.initialize_shared_data(self.shared_data)


        settings = read_config_from_app(tmp_cls)
        settings.update(from_dict(self.kwa))
        ssl = not (settings['SERVER_SSL_CERT'] is None)

        # Generate the main html for the client
        main_html = generate_main_html_for_server(tmp_cls, ssl)

        self.router.settings['handler_args']['local_doc_class'] = tmp_cls
        self.router.settings['handler_args']['main_html'] = main_html
        self.app.handlers[0][1][-1].kwargs['main_html'] = main_html


        for wsh in list(self.shared_wshandlers.values()):
            wsh.prepare_session_for_general_reload()
            wsh.please_reload()


class PrivateDataStore:
    """Implements a simple data storage."""

    def __init__(self):
        self._dict = dict()

    def get_store(self, uid):
        if (uid not in self._dict):
            self._dict[uid] = OrderedDict()
        return self._dict[uid]

    def remove_store(self, uid):
        del self._dict[uid]


# ================================ #
#         Server execution         #
# ================================ #

def run(app=None, **kwargs):
    """WebAlchemy server 'run'.
    
    Receives a WebAlchemy application as argument and other optional arguments.
    
    Loads configuration parameters from the application, sets the URL paths on
    the server, configures the function handlers and sets up the Tornado server.
    
    """


    settings = read_config_from_app(app)
    settings.update(from_dict(kwargs))

    # Application settings
    port = settings['SERVER_PORT']
    static_path_from_local_doc_base = settings['SERVER_STATIC_PATH']
    shared_data_class = kwargs.get('shared_data_class', OrderedDict)
    tab_data_store_class = kwargs.get('private_data_store_class', PrivateDataStore)
    session_data_store_class = kwargs.get('private_data_store_class', PrivateDataStore)
    ssl = not (settings['SERVER_SSL_CERT'] is None)
    ssl_cert_file = settings['SERVER_SSL_CERT']
    ssl_key_file = settings['SERVER_SSL_KEY']
    main_explicit_route = settings['SERVER_MAIN_ROUTE']
    if not main_explicit_route:
        main_route = r'/'
    else:
        main_route = r'/' + main_explicit_route

    # Configure local static path, if given
    if static_path_from_local_doc_base:
        mdl = sys.modules[app.__module__]
        mdl_fn = mdl.__file__
        static_path = os.path.realpath(mdl_fn)
        static_path = os.path.dirname(static_path)
        static_path = os.path.join(static_path, static_path_from_local_doc_base)
        log.info('static_path: ' + static_path)
    else:
        static_path = None

    # Configure shared handlers
    shared_wshandlers = {}
    shared_data = shared_data_class()
    if hasattr(app, 'initialize_shared_data'):
        app.initialize_shared_data(shared_data)
    session_data_store = session_data_store_class()
    tab_data_store = tab_data_store_class()

    # Generate the main html for the client
    main_html = generate_main_html_for_server(app, ssl)

    # setting-up the tornado server
    ws_route = main_route + '/app' if not main_route.endswith('/') else main_route + 'app'
    router = SockJSRouter(WebSocketHandler, ws_route,
                          dict(handler_args=dict(local_doc_class=app,
                                                 shared_wshandlers=shared_wshandlers,
                                                 shared_data=shared_data,
                                                 session_data_store=session_data_store,
                                                 tab_data_store=tab_data_store,
                                                 main_explicit_route=main_explicit_route,
                                                 main_html=main_html)))

    # Set up the tornado wserver
    # We use the _MainHandler to serve the main html file and the
    # WebSocketHandler to handle subsequent websocket requests from the clients
    application = tornado.web.Application(router.urls + [(main_route, _MainHandler, dict(main_html=main_html))],
                                          static_path=static_path)
    dreload_blacklist_starting_with = ('webalchemy', 'tornado')
    additional_monitored_files = settings['SERVER_MONITORED_FILES']
    
    # Set up the service to monitore changes in local files
    au = _AppUpdater(application, kwargs, router, app, shared_wshandlers, dreload_blacklist_starting_with,
                     shared_data, additional_monitored_files=additional_monitored_files)
    tornado.ioloop.PeriodicCallback(au.update_app, 1000).start()
    
    # Handle certifications
    if not ssl:
        application.listen(port)
    else:
        mdl = sys.modules[app.__module__]
        mdl_fn = mdl.__file__
        lib_dir = os.path.realpath(mdl_fn)
        lib_dir = os.path.dirname(lib_dir)
        application.listen(port, ssl_options={
            'certfile': os.path.join(lib_dir, ssl_cert_file),
            'keyfile': os.path.join(lib_dir, ssl_key_file),
        })

    log.info('starting Tornado event loop')
    tornado.ioloop.IOLoop.instance().start()


def generate_static(app):
    """Generates an application which can be served in a static folder."""
    settings = read_config_from_app(app)
    writefile = settings['FREEZE_OUTPUT']
    static_html = generate_static_main_html(app)
    with open(writefile, 'w') as f:
        f.write(static_html)


########NEW FILE########
__FILENAME__ = Stacker


class Stacker:
    '''Allow stacking element creation with "with" statements
    
    eg.
    s = Stacker(self.rdoc.body)
    with s.stack('div', cls='panel'):
        s.stack('div', text='Hello', cls='panel-heading')
        with s.stack('div', cls='panel-body'):
            s.stack(p="this is text inside body")
            s.stack('button', cls='btn btn-primary')
        s.stack('div', text="panel footer here", cls="panel-footer")
    '''
    def __init__(self, element, prev_stacker=None):
        # proxy everything to element - copy __dict__ and __class__
        self.__class__ = type(element.__class__.__name__,
                              (self.__class__, element.__class__),
                              {})
        self.__dict__ = element.__dict__

        if prev_stacker:
            self._stack = prev_stacker._stack
        else:
            self._stack = [element]
        self._element = element

        
    def stack(self, *args, **kwargs):
        '''Create an element - parent is head of stack'''
        parent = self._stack[-1]
        e = parent.element(*args, **kwargs)
        se = self.__class__(e, self)
        return se
         
    def __enter__(self, **kwargs):
        self._stack.append(self._element)
        return self
    
    def __exit__(self, type, value, traceback):
        self._stack.pop()



class StackerWrapper:
    '''Wrapper for stacker object
    '''
    def __init__(self, stacker):
        self.stacker = stacker

    def stack(self, *args, **kwargs):
        return self.stacker.stack(*args, **kwargs)


class HtmlShortcuts(StackerWrapper):
    '''Wrapper for Stacker that provides Html entities shortcuts

    eg.
    h = HtmlShortcuts(Stacker(self.rdoc.body))

    with h.div(cls='panel'):
        h.div(text='hello', cls='panel-heading')
        with h.div(cls='panel-body'):
            h.p('this is text inside body')
            h.button(cls='btn btn-primary')
        h.div(text='panel footer here', cls=panel-footer')
    '''



    ###############################################################################
    # "Shortcut" methods for element types

    # Sections

    def section(self, *args, **kwargs):
        '''
          The section element represents a generic section of a document or
          application. A section, in this context, is a thematic grouping of content,
          typically with a heading.
        '''
        return self.stack(typ="section", *args, **kwargs)

    def nav(self, *args, **kwargs):
        '''
      The nav element represents a section of a page that links to other pages or
      to parts within the page: a section with navigation links.
      '''
        return self.stack(typ="nav", *args, **kwargs)
    
    def article(self, *args, **kwargs):
        '''
      The article element represents a self-contained composition in a document,
      page, application, or site and that is, in principle, independently
      distributable or reusable, e.g. in syndication. This could be a forum post, a
      magazine or newspaper article, a blog entry, a user-submitted comment, an
      interactive widget or gadget, or any other independent item of content.
      '''
        return self.stack(typ="article", *args, **kwargs)
    
    def aside(self, *args, **kwargs):
        '''
      The aside element represents a section of a page that consists of content
      that is tangentially related to the content around the aside element, and
      which could be considered separate from that content. Such sections are
      often represented as sidebars in printed typography.
      '''
        return self.stack(typ="aside", *args, **kwargs)
    
    def h1(self, *args, **kwargs):
        '''
      Represents the highest ranking heading.
      '''
        return self.stack(typ="h1", *args, **kwargs)
    
    def h2(self, *args, **kwargs):
        '''
      Represents the second-highest ranking heading.
      '''
        return self.stack(typ="h2", *args, **kwargs)
    
    def h3(self, *args, **kwargs):
        '''
      Represents the third-highest ranking heading.
      '''
        return self.stack(typ="h3", *args, **kwargs)
    
    def h4(self, *args, **kwargs):
        '''
      Represents the fourth-highest ranking heading.
      '''
        return self.stack(typ="h4", *args, **kwargs)
    
    def h5(self, *args, **kwargs):
        '''
      Represents the fifth-highest ranking heading.
      '''
        return self.stack(typ="h5", *args, **kwargs)
    
    def h6(self, *args, **kwargs):
        '''
      Represents the sixth-highest ranking heading.
      '''
        return self.stack(typ="h6", *args, **kwargs)
    
    def hgroup(self, *args, **kwargs):
        '''
      The hgroup element represents the heading of a section. The element is used
      to group a set of h1-h6 elements when the heading has multiple levels, such
      as subheadings, alternative titles, or taglines.
      '''
        return self.stack(typ="hgroup", *args, **kwargs)
    
    def header(self, *args, **kwargs):
        '''
      The header element represents a group of introductory or navigational aids.
      '''
        return self.stack(typ="header", *args, **kwargs)
    
    def footer(self, *args, **kwargs):
        '''
      The footer element represents a footer for its nearest ancestor sectioning
      content or sectioning root element. A footer typically contains information
      about its section such as who wrote it, links to related documents,
      copyright data, and the like.
      '''
        return self.stack(typ="footer", *args, **kwargs)
    
    def address(self, *args, **kwargs):
        '''
      The address element represents the contact information for its nearest
      article or body element ancestor. If that is the body element, then the
      contact information applies to the document as a whole.
      '''
        return self.stack(typ="address", *args, **kwargs)
    
    
    # Grouping content
    
    def p(self, *args, **kwargs):
        '''
      The p element represents a paragraph.
      '''
        return self.stack(typ="p", *args, **kwargs)
    
    def hr(self, *args, **kwargs):
        '''
      The hr element represents a paragraph-level thematic break, e.g. a scene
      change in a story, or a transition to another topic within a section of a
      reference book.
      '''
        kwargs["is_single"] = True # TODO
        return self.stack(typ="hr", *args, **kwargs)
    
    def pre(self, *args, **kwargs):
        '''
      The pre element represents a block of preformatted text, in which structure
      is represented by typographic conventions rather than by elements.
      '''
        kwargs["is_pretty"] = False
        return self.stack(typ="pre", *args, **kwargs)
    
    def blockquote(self, *args, **kwargs):
        '''
      The blockquote element represents a section that is quoted from another
      source.
      '''
        return self.stack(typ="blockquote", *args, **kwargs)
    
    def ol(self, *args, **kwargs):
        '''
      The ol element represents a list of items, where the items have been
      intentionally ordered, such that changing the order would change the
      meaning of the document.
      '''
        return self.stack(typ="ol", *args, **kwargs)
    
    def ul(self, *args, **kwargs):
        '''
      The ul element represents a list of items, where the order of the items is
      not important - that is, where changing the order would not materially change
      the meaning of the document.
      '''
        return self.stack(typ="ul", *args, **kwargs)
    
    def li(self, *args, **kwargs):
        '''
      The li element represents a list item. If its parent element is an ol, ul, or
      menu element, then the element is an item of the parent element's list, as
      defined for those elements. Otherwise, the list item has no defined
      list-related relationship to any other li element.
      '''
        return self.stack(typ="li", *args, **kwargs)
    
    def dl(self, *args, **kwargs):
        '''
      The dl element represents an association list consisting of zero or more
      name-value groups (a description list). Each group must consist of one or
      more names (dt elements) followed by one or more values (dd elements).
      Within a single dl element, there should not be more than one dt element for
      each name.
      '''
        return self.stack(typ="dl", *args, **kwargs)
    
    def dt(self, *args, **kwargs):
        '''
      The dt element represents the term, or name, part of a term-description group
      in a description list (dl element).
      '''
        return self.stack(typ="dt", *args, **kwargs)
    
    def dd(self, *args, **kwargs):
        '''
      The dd element represents the description, definition, or value, part of a
      term-description group in a description list (dl element).
      '''
        return self.stack(typ="dd", *args, **kwargs)
    
    def figure(self, *args, **kwargs):
        '''
      The figure element represents some flow content, optionally with a caption,
      that is self-contained and is typically referenced as a single unit from the
      main flow of the document.
      '''
        return self.stack(typ="figure", *args, **kwargs)
    
    def figcaption(self, *args, **kwargs):
        '''
      The figcaption element represents a caption or legend for the rest of the
      contents of the figcaption element's parent figure element, if any.
      '''
        return self.stack(typ="figcaption", *args, **kwargs)
    
    def div(self, *args, **kwargs):
        '''
      The div element has no special meaning at all. It represents its children. It
      can be used with the class, lang, and title attributes to mark up semantics
      common to a group of consecutive elements.
      '''
        return self.stack(typ="div", *args, **kwargs)
    
    
    
    # Text semantics
    
    def a(self, *args, **kwargs):
        '''
      If the a element has an href attribute, then it represents a hyperlink (a
      hypertext anchor).
    
      If the a element has no href attribute, then the element represents a
      placeholder for where a link might otherwise have been placed, if it had been
      relevant.
      '''
        return self.stack(typ="a", *args, **kwargs)
    
    def em(self, *args, **kwargs):
        '''
      The em element represents stress emphasis of its contents.
      '''
        return self.stack(typ="em", *args, **kwargs)
    
    def strong(self, *args, **kwargs):
        '''
      The strong element represents strong importance for its contents.
      '''
        return self.stack(typ="strong", *args, **kwargs)
    
    def small(self, *args, **kwargs):
        '''
      The small element represents side comments such as small print.
      '''
        return self.stack(typ="small", *args, **kwargs)
    
    def s(self, *args, **kwargs):
        '''
      The s element represents contents that are no longer accurate or no longer
      relevant.
      '''
        return self.stack(typ="s", *args, **kwargs)
    
    def cite(self, *args, **kwargs):
        '''
      The cite element represents the title of a work (e.g. a book, a paper, an
      essay, a poem, a score, a song, a script, a film, a TV show, a game, a
      sculpture, a painting, a theatre production, a play, an opera, a musical, an
      exhibition, a legal case report, etc). This can be a work that is being
      quoted or referenced in detail (i.e. a citation), or it can just be a work
      that is mentioned in passing.
      '''
        return self.stack(typ="cite", *args, **kwargs)
    
    def q(self, *args, **kwargs):
        '''
      The q element represents some phrasing content quoted from another source.
      '''
        return self.stack(typ="q", *args, **kwargs)
    
    def dfn(self, *args, **kwargs):
        '''
      The dfn element represents the defining instance of a term. The paragraph,
      description list group, or section that is the nearest ancestor of the dfn
      element must also contain the definition(s) for the term given by the dfn
      element.
      '''
        return self.stack(typ="dfn", *args, **kwargs)
    
    def abbr(self, *args, **kwargs):
        '''
      The abbr element represents an abbreviation or acronym, optionally with its
      expansion. The title attribute may be used to provide an expansion of the
      abbreviation. The attribute, if specified, must contain an expansion of the
      abbreviation, and nothing else.
      '''
        return self.stack(typ="abbr", *args, **kwargs)
    
    def time_(self, *args, **kwargs):
        '''
      The time element represents either a time on a 24 hour clock, or a precise
      date in the proleptic Gregorian calendar, optionally with a time and a
      time-zone offset.
      '''
        return self.stack(typ="time_", *args, **kwargs)
    _time = time_
    
    def code(self, *args, **kwargs):
        '''
      The code element represents a fragment of computer code. This could be an XML
      element name, a filename, a computer program, or any other string that a
      computer would recognize.
      '''
        return self.stack(typ="code", *args, **kwargs)
    
    def var(self, *args, **kwargs):
        '''
      The var element represents a variable. This could be an actual variable in a
      mathematical expression or programming context, an identifier representing a
      constant, a function parameter, or just be a term used as a placeholder in
      prose.
      '''
        return self.stack(typ="var", *args, **kwargs)
    
    def samp(self, *args, **kwargs):
        '''
      The samp element represents (sample) output from a program or computing
      system.
      '''
        return self.stack(typ="samp", *args, **kwargs)
    
    def kbd(self, *args, **kwargs):
        '''
      The kbd element represents user input (typically keyboard input, although it
      may also be used to represent other input, such as voice commands).
      '''
        return self.stack(typ="kbd", *args, **kwargs)
    
    def sub(self, *args, **kwargs):
        '''
      The sub element represents a subscript.
      '''
        return self.stack(typ="sub", *args, **kwargs)
    
    def sup(self, *args, **kwargs):
        '''
      The sup element represents a superscript.
      '''
        return self.stack(typ="sup", *args, **kwargs)
    
    def i(self, *args, **kwargs):
        '''
      The i element represents a span of text in an alternate voice or mood, or
      otherwise offset from the normal prose in a manner indicating a different
      quality of text, such as a taxonomic designation, a technical term, an
      idiomatic phrase from another language, a thought, or a ship name in Western
      texts.
      '''
        return self.stack(typ="i", *args, **kwargs)
    
    def b(self, *args, **kwargs):
        '''
      The b element represents a span of text to which attention is being drawn for
      utilitarian purposes without conveying any extra importance and with no
      implication of an alternate voice or mood, such as key words in a document
      abstract, product names in a review, actionable words in interactive
      text-driven software, or an article lede.
      '''
        return self.stack(typ="b", *args, **kwargs)
    
    def u(self, *args, **kwargs):
        '''
      The u element represents a span of text with an unarticulated, though
      explicitly rendered, non-textual annotation, such as labeling the text as
      being a proper name in Chinese text (a Chinese proper name mark), or
      labeling the text as being misspelt.
      '''
        return self.stack(typ="u", *args, **kwargs)
    
    def mark(self, *args, **kwargs):
        '''
      The mark element represents a run of text in one document marked or
      highlighted for reference purposes, due to its relevance in another context.
      When used in a quotation or other block of text referred to from the prose,
      it indicates a highlight that was not originally present but which has been
      added to bring the reader's attention to a part of the text that might not
      have been considered important by the original author when the block was
      originally written, but which is now under previously unexpected scrutiny.
      When used in the main prose of a document, it indicates a part of the
      document that has been highlighted due to its likely relevance to the user's
      current activity.
      '''
        return self.stack(typ="mark", *args, **kwargs)
    
    def ruby(self, *args, **kwargs):
        '''
      The ruby element allows one or more spans of phrasing content to be marked
      with ruby annotations. Ruby annotations are short runs of text presented
      alongside base text, primarily used in East Asian typography as a guide for
      pronunciation or to include other annotations. In Japanese, this form of
      typography is also known as furigana.
      '''
        return self.stack(typ="ruby", *args, **kwargs)
    
    def rt(self, *args, **kwargs):
        '''
      The rt element marks the ruby text component of a ruby annotation.
      '''
        return self.stack(typ="rt", *args, **kwargs)
    
    def rp(self, *args, **kwargs):
        '''
      The rp element can be used to provide parentheses around a ruby text
      component of a ruby annotation, to be shown by user agents that don't support
      ruby annotations.
      '''
        return self.stack(typ="rp", *args, **kwargs)
    
    def bdi(self, *args, **kwargs):
        '''
      The bdi element represents a span of text that is to be isolated from its
      surroundings for the purposes of bidirectional text formatting.
      '''
        return self.stack(typ="bdi", *args, **kwargs)
    
    def bdo(self, *args, **kwargs):
        '''
      The bdo element represents explicit text directionality formatting control
      for its children. It allows authors to override the Unicode bidirectional
      algorithm by explicitly specifying a direction override.
      '''
        return self.stack(typ="bdo", *args, **kwargs)
    
    def span(self, *args, **kwargs):
        '''
      The span element doesn't mean anything on its own, but can be useful when
      used together with the global attributes, e.g. class, lang, or dir. It
      represents its children.
      '''
        return self.stack(typ="span", *args, **kwargs)
    
    def br(self, *args, **kwargs):
      '''
      The br element represents a line break.
      '''
      kwargs["is_single"] = True # TODO
      return self.stack(typ="br", *args, **kwargs)
    
    def wbr(self, *args, **kwargs):
      '''
      The wbr element represents a line break opportunity.
      '''
      kwargs["is_single"] = True # TODO
      return self.stack(typ="wbr", *args, **kwargs)
    
    
    
    # Edits
    
    def ins(self, *args, **kwargs):
        '''
      The ins element represents an addition to the document.
      '''
        return self.stack(typ="ins", *args, **kwargs)
    
    def del_(self, *args, **kwargs):
        '''
      The del element represents a removal from the document.
      '''
        return self.stack(typ="del_", *args, **kwargs)
    
    
    # Embedded content
    
    def img(self, *args, **kwargs):
        '''
      An img element represents an image.
      '''
        kwargs["is_single"] = True # TODO
        return self.stack(typ="img", *args, **kwargs)
    
    def iframe(self, *args, **kwargs):
        '''
      The iframe element represents a nested browsing context.
      '''
        return self.stack(typ="iframe", *args, **kwargs)
    
    def embed(self, *args, **kwargs):
        '''
      The embed element represents an integration point for an external (typically
      non-HTML) application or interactive content.
      '''
        kwargs["is_single"] = True # TODO
        return self.stack(typ="embed", *args, **kwargs)
    
    def object_(self, *args, **kwargs):
        '''
      The object element can represent an external resource, which, depending on
      the type of the resource, will either be treated as an image, as a nested
      browsing context, or as an external resource to be processed by a plugin.
      '''
        return self.stack(typ="object_", *args, **kwargs)
    _object = object_
    
    def param(self, *args, **kwargs):
        '''
      The param element defines parameters for plugins invoked by object elements.
      It does not represent anything on its own.
      '''
        kwargs["is_single"] = True # TODO
        return self.stack(typ="param", *args, **kwargs)
    
    def video(self, *args, **kwargs):
        '''
      A video element is used for playing videos or movies, and audio files with
      captions.
      '''
        return self.stack(typ="video", *args, **kwargs)
    
    def audio(self, *args, **kwargs):
        '''
      An audio element represents a sound or audio stream.
      '''
        return self.stack(typ="audio", *args, **kwargs)
    
    def source(self, *args, **kwargs):
        '''
      The source element allows authors to specify multiple alternative media
      resources for media elements. It does not represent anything on its own.
      '''
        kwargs["is_single"] = True # TODO
        return self.stack(typ="source", *args, **kwargs)
    
    def track(self, *args, **kwargs):
        '''
      The track element allows authors to specify explicit external timed text
      tracks for media elements. It does not represent anything on its own.
      '''
        kwargs["is_single"] = True # TODO
        return self.stack(typ="track", *args, **kwargs)
    
    def canvas(self, *args, **kwargs):
        '''
      The canvas element provides scripts with a resolution-dependent bitmap
      canvas, which can be used for rendering graphs, game graphics, or other
      visual images on the fly.
      '''
        return self.stack(typ="canvas", *args, **kwargs)
    
    def map_(self, *args, **kwargs):
        '''
      The map element, in conjunction with any area element descendants, defines an
      image map. The element represents its children.
      '''
        return self.stack(typ="map_", *args, **kwargs)
    
    def area(self, *args, **kwargs):
        '''
      The area element represents either a hyperlink with some text and a
      corresponding area on an image map, or a dead area on an image map.
      '''
        kwargs["is_single"] = True # TODO
        return self.stack(typ="area", *args, **kwargs)
    
    
    # Tabular data
    
    def table(self, *args, **kwargs):
        '''
      The table element represents data with more than one dimension, in the form
      of a table.
      '''
        return self.stack(typ="table", *args, **kwargs)
    
    def caption(self, *args, **kwargs):
        '''
      The caption element represents the title of the table that is its parent, if
      it has a parent and that is a table element.
      '''
        return self.stack(typ="caption", *args, **kwargs)
    
    def colgroup(self, *args, **kwargs):
        '''
      The colgroup element represents a group of one or more columns in the table
      that is its parent, if it has a parent and that is a table element.
      '''
        return self.stack(typ="colgroup", *args, **kwargs)
    
    def col(self, *args, **kwargs):
        '''
      If a col element has a parent and that is a colgroup element that itself has
      a parent that is a table element, then the col element represents one or more
      columns in the column group represented by that colgroup.
      '''
        kwargs["is_single"] = True # TODO
        return self.stack(typ="col", *args, **kwargs)
    
    def tbody(self, *args, **kwargs):
        '''
      The tbody element represents a block of rows that consist of a body of data
      for the parent table element, if the tbody element has a parent and it is a
      table.
      '''
        return self.stack(typ="tbody", *args, **kwargs)
    
    def thead(self, *args, **kwargs):
        '''
      The thead element represents the block of rows that consist of the column
      labels (headers) for the parent table element, if the thead element has a
      parent and it is a table.
      '''
        return self.stack(typ="thead", *args, **kwargs)
    
    def tfoot(self, *args, **kwargs):
        '''
      The tfoot element represents the block of rows that consist of the column
      summaries (footers) for the parent table element, if the tfoot element has a
      parent and it is a table.
      '''
        return self.stack(typ="tfoot", *args, **kwargs)
    
    def tr(self, *args, **kwargs):
        '''
      The tr element represents a row of cells in a table.
      '''
        return self.stack(typ="tr", *args, **kwargs)
    
    def td(self, *args, **kwargs):
        '''
      The td element represents a data cell in a table.
      '''
        return self.stack(typ="td", *args, **kwargs)
    
    def th(self, *args, **kwargs):
        '''
      The th element represents a header cell in a table.
      '''
        return self.stack(typ="th", *args, **kwargs)
    
    
    
    # Forms
    
    def form(self, *args, **kwargs):
        '''
      The form element represents a collection of form-associated elements, some of
      which can represent editable values that can be submitted to a server for
      processing.
      '''
        return self.stack(typ="form", *args, **kwargs)
    
    def fieldset(self, *args, **kwargs):
        '''
      The fieldset element represents a set of form controls optionally grouped
      under a common name.
      '''
        return self.stack(typ="fieldset", *args, **kwargs)
    
    def legend(self, *args, **kwargs):
        '''
      The legend element represents a caption for the rest of the contents of the
      legend element's parent fieldset element, if any.
      '''
        return self.stack(typ="legend", *args, **kwargs)
    
    def label(self, *args, **kwargs):
        '''
      The label represents a caption in a user interface. The caption can be
      associated with a specific form control, known as the label element's labeled
      control, either using for attribute, or by putting the form control inside
      the label element itself.
      '''
        return self.stack(typ="label", *args, **kwargs)
    
    def input_(self, *args, **kwargs):
        '''
      The input element represents a typed data field, usually with a form control
      to allow the user to edit the data.
      '''
        kwargs["is_single"] = True # TODO
        return self.stack(typ="input", *args, **kwargs)
    input = _input = input_
    
    def button(self, *args, **kwargs):
        '''
      The button element represents a button. If the element is not disabled, then
      the user agent should allow the user to activate the button.
      '''
        return self.stack(typ="button", *args, **kwargs)
    
    def select(self, *args, **kwargs):
        '''
      The select element represents a control for selecting amongst a set of
      options.
      '''
        return self.stack(typ="select", *args, **kwargs)
    
    def datalist(self, *args, **kwargs):
        '''
      The datalist element represents a set of option elements that represent
      predefined options for other controls. The contents of the element represents
      fallback content for legacy user agents, intermixed with option elements that
      represent the predefined options. In the rendering, the datalist element
      represents nothing and it, along with its children, should be hidden.
      '''
        return self.stack(typ="datalist", *args, **kwargs)
    
    def optgroup(self, *args, **kwargs):
        '''
      The optgroup element represents a group of option elements with a common
      label.
      '''
        return self.stack(typ="optgroup", *args, **kwargs)
    
    def option(self, *args, **kwargs):
        '''
      The option element represents an option in a select element or as part of a
      list of suggestions in a datalist element.
      '''
        return self.stack(typ="option", *args, **kwargs)
    
    def textarea(self, *args, **kwargs):
        '''
      The textarea element represents a multiline plain text edit control for the
      element's raw value. The contents of the control represent the control's
      default value.
      '''
        return self.stack(typ="textarea", *args, **kwargs)
    
    def keygen(self, *args, **kwargs):
        '''
      The keygen element represents a key pair generator control. When the
      control's form is submitted, the private key is stored in the local keystore,
      and the public key is packaged and sent to the server.
      '''
        kwargs["is_single"] = True # TODO
        return self.stack(typ="keygen", *args, **kwargs)
    
    def output(self, *args, **kwargs):
        '''
      The output element represents the result of a calculation.
      '''
        return self.stack(typ="output", *args, **kwargs)
    
    def progress(self, *args, **kwargs):
        '''
      The progress element represents the completion progress of a task. The
      progress is either indeterminate, indicating that progress is being made but
      that it is not clear how much more work remains to be done before the task is
      complete (e.g. because the task is waiting for a remote host to respond), or
      the progress is a number in the range zero to a maximum, giving the fraction
      of work that has so far been completed.
      '''
        return self.stack(typ="progress", *args, **kwargs)
    
    def meter(self, *args, **kwargs):
        '''
      The meter element represents a scalar measurement within a known range, or a
      fractional value; for example disk usage, the relevance of a query result, or
      the fraction of a voting population to have selected a particular candidate.
      '''
        return self.stack(typ="meter", *args, **kwargs)
    
    
    # Interactive elements
    
    def details(self, *args, **kwargs):
        '''
      The details element represents a disclosure widget from which the user can
      obtain additional information or controls.
      '''
        return self.stack(typ="details", *args, **kwargs)
    
    def summary(self, *args, **kwargs):
        '''
      The summary element represents a summary, caption, or legend for the rest of
      the contents of the summary element's parent details element, if any.
      '''
        return self.stack(typ="summary", *args, **kwargs)
    
    def command(self, *args, **kwargs):
        '''
      The command element represents a command that the user can invoke.
      '''
        kwargs["is_single"] = True # TODO
        return self.stack(typ="command", *args, **kwargs)
    
    def menu(self, *args, **kwargs):
        '''
      The menu element represents a list of commands.
      '''
        return self.stack(typ="menu", *args, **kwargs)





########NEW FILE########
__FILENAME__ = bootstrap3_wrapper
from ...Stacker import StackerWrapper

class BootstrapShortcuts(StackerWrapper):
    '''Stacker wrapper for Bootstrap entities shortcuts

    eg.
    s = Stacker(self.rdoc.body)
    b = BootstrapShortcuts(s)
    h = HtmlShortcuts(s)
    with b.row(), b.col(md=7, md_offset=2), s.panel('info'):
        b.panel_heading('Hello')
        with b.panel_body():
            h.p(text="this is text inside body")                      # note "p" is regular html <p>  using the "HtmlShortcuts"
            b.button(typ='primary', size="lg", block=True, text='Click here')
        b.panel_footer("panel footer here")

    Note: you need to add Bootstrap CSS and (optional) JS
        stylesheets = ['//netdna.bootstrapcdn.com/bootstrap/3.1.0/css/bootstrap.min.css']
        include = ['//netdna.bootstrapcdn.com/bootstrap/3.1.0/js/bootstrap.min.js']
    '''

    ###############################################################################
    # "Shortcut" methods for element types

    def container(self, fluid=True, *args, **kwargs):
        '''Center page - see http://getbootstrap.com/css/#overview-container
        Fluid - use percent width
        '''
        return self.stack(typ='div', cls='container-fluid' if fluid else 'container', *args, **kwargs)

    # Grid:  Row and Columns - see http://getbootstrap.com/css/#grid
    def row(self, *args, **kwargs):
        '''Row is composed of 12 grid cells - below Row there should be at least one Column '''
        return self.stack(typ='div', *args, **kwargs)

    def col(self, *args, **kwargs):
        '''Column

        kwargs integers (0..12) for keys of the template:
        [xs|sm|md|lg]_[|offset|pull|push]
        '''
        cls = kwargs.get('cls', '').split()
        for screensize in ('xs', 'sm', 'md', 'lg'):
            for modifier in ('', 'offset', 'pull', 'push'):
                param = "{}_{}".format(screensize, modifier) if modifier else screensize
                if param in kwargs:
                    cls.append('col-{}-{}'.format(param, kwargs[screensize]))
        kwargs['cls'] = cls
        return self.stack(typ='div',  *args, **kwargs)


    def table(self, striped=False, bordered=False, hover=False, condensed=False, *args, **kwargs):
        '''Table - see http://getbootstrap.com/css/#tables'''
        cls = kwargs.get('cls', '').split()
        cls.append('table')
        if striped:
            cls.append('table-striped')
        if bordered:
            cls.append('table-bordered')
        if hover:
            cls.append('table-hover')
        if condensed:
            cls.append('table-condensed')
        kwargs['cls'] = cls
        return self.stack(typ='div',  *args, **kwargs)


    def button(self, typ="button", size="", block=False, active=False, disabled=False, flavor='default', *args, **kwargs):
        '''Bootstrap Button  see http://getbootstrap.com/css/#buttons

          tag can be: a, button, input (input is not recommended)
          flavor can be:  default, primary, success, info, warning, danger, link
          size can be: "lg" (large), "" (default), "sm" (small), "xs" (xtra-small)
          block:  for block level
        '''
        att = {}
        cls = kwargs.get('cls', '').split()
        cls.append("btn")
        cls.append("btn-"+typ)
        if size:
            cls.append("btn-"+size)
        if block:
            cls.append("btn-block")
        if active:
            cls.append("active")
        if disabled:
            cls.append("disabled")
            att["disabled"]="disabled"
        if "att" in kwargs:
            att.update(kwargs["att"])
            del kwargs['att']
        kwargs['cls'] = cls
        return self.stack(typ=typ, att=att, *args, **kwargs)


    def glyphicon(self, icon, *args, **kwargs):
        '''Bootstrap Icon - see http://getbootstrap.com/components/#glyphicons'''
        cls = kwargs.get('cls', '').split()
        cls.append('glyphicon')
        cls.append('glyphicon-{}'.format(icon))
        kwargs['cls'] = cls
        return self.stack(typ='span', *args, **kwargs)

    def alert(self, flavor='danger', dismissable=False, *args, **kwargs):
        '''Alerts - see http://getbootstrap.com/components/#alerts'''
        cls = kwargs.get('cls', '').split()
        cls.append('alert')
        cls.append('alert-{}'.format(flavor))
        if dismissable:
            cls.append('alert-dismissible')
        kwargs['cls'] = cls
        res = self.stack(typ='div', *args, **kwargs)
        if dismissable:
            with res:
                self.stack(typ='button', cls='close', att={'data-dismiss':'alert', 'aria-hidden':'true'}, innerHtml='&times;')
        return res

    def list_group(self, items=[], *args, **kwargs):
        '''Bootstrap List Group - http://getbootstrap.com/components/#list-group

        items (optional) - list of text items
        '''
        cls = kwargs.get('cls', '').split()
        cls.append('list-group')
        kwargs['cls'] = cls
        res = self.stack(typ='ul', *args, **kwargs)
        if items:
            with res:
                for item in items:
                    self.list_group_item(text=item)
        return res

    def list_group_item(self, *args, **kwargs):
        cls = kwargs.get('cls', '').split()
        cls.append('list-group-item')
        kwargs['cls'] = cls
        return self.stack(typ='li', *args, **kwargs)


    def panel(self, flavor="default", *args, **kwargs):
        '''Panel - see http://getbootstrap.com/components/#panels'''
        cls = kwargs.get('cls', '').split()
        cls.append('panel')
        cls.append('panel-{}'.format(flavor))
        kwargs['cls'] = cls
        return self.stack(typ='div', *args, **kwargs)

    def panel_heading(self, *args, **kwargs):
        cls = kwargs.get('cls', '').split()
        cls.append('panel-heading')
        kwargs['cls'] = cls
        return self.stack(typ='div', *args, **kwargs)

    def panel_body(self, *args, **kwargs):
        cls = kwargs.get('cls', '').split()
        cls.append('panel-body')
        kwargs['cls'] = cls
        return self.stack(typ='div', *args, **kwargs)

    def panel_footer(self, *args, **kwargs):
        cls = kwargs.get('cls', '').split()
        cls.append('panel-footer')
        kwargs['cls'] = cls
        return self.stack(typ='div', *args, **kwargs)
########NEW FILE########
__FILENAME__ = menu
class Menu:

    def __init__(self, rdoc, on_add=None):
        self.rdoc = rdoc
        self.element = rdoc.element('nav')
        vn = '#' + self.element.varname
        self.rule_menu = rdoc.stylesheet.rule(vn)
        self.rule_item = rdoc.stylesheet.rule(vn + ' > li')
        self.rule_item_hover = rdoc.stylesheet.rule(vn + ' > li:hover')
        self.rule_item_selected = rdoc.stylesheet.rule(vn + ' > li.selected')
        self.rule_item_selected_hover = rdoc.stylesheet.rule(vn + ' > li.selected:hover')
        self.on_add = on_add
        self.id_dict = {}

    def add_item(self, *varargs):
        for text in varargs:
            i = self.rdoc.element('li', text)
            self.id_dict[i.att.varname] = i
            self.element.append(i)
            if self.on_add:
                self.on_add(i)

########NEW FILE########
__FILENAME__ = sort
# TODO: well, implement!
########NEW FILE########
__FILENAME__ = table
class Table:
    def __init__(self, rdoc, rows, cols, has_header=True, has_index=True, on_add_row=None, on_add_data_cell=None,
                 on_add_header_cell=None):
        self.rdoc = rdoc
        self.rowsc = rows
        self.colsc = cols
        self.element = rdoc.element('table')
        vn = '#' + self.element.varname
        self.rule_table = rdoc.stylesheet.rule(vn)
        self.rule_row = rdoc.stylesheet.rule(vn + ' > tr')
        self.rule_row_hover = rdoc.stylesheet.rule(vn + ' > tr:hover')
        self.rule_datacell = rdoc.stylesheet.rule(vn + ' > tr > td')
        self.rule_datacell_hover = rdoc.stylesheet.rule(vn + ' > tr > td:hover')
        self.rule_headercell = rdoc.stylesheet.rule(vn + ' > tr > th')
        self.rule_headercell_hover = rdoc.stylesheet.rule(vn + ' > tr > th:hover')
        self.rule_row_selected = rdoc.stylesheet.rule(vn + ' > tr.selected')
        self.rule_row_selected_hover = rdoc.stylesheet.rule(vn + ' > tr.selected:hover')
        self.rule_datacell_selected = rdoc.stylesheet.rule(vn + ' > tr > td.selected')
        self.rule_datacell_selected_hover = rdoc.stylesheet.rule(vn + ' > tr > td.selected:hover')
        self.rule_headercell_selected = rdoc.stylesheet.rule(vn + ' > tr > th.selected')
        self.rule_headercell_selected_hover = rdoc.stylesheet.rule(vn + ' > tr > th.selected:hover')
        self.rule_row_header = rdoc.stylesheet.rule(vn + ' > tr.header')
        self.rule_row_header_hover = rdoc.stylesheet.rule(vn + ' > tr.header:hover')
        self.rule_datacell_index = rdoc.stylesheet.rule(vn + ' > tr > td.index')
        self.rule_datacell_index_hover = rdoc.stylesheet.rule(vn + ' > tr > td.index:hover')

        # build an empty table...
        self.row_col_items = {}
        self.rows = []
        for row_ix in range(rows):
            row = self.rdoc.element('tr')
            self.rows.append(row)
            if row_ix == 0 and has_header:
                row.cls.append('header')
            if on_add_row:
                on_add_row(row, row_ix)
            self.element.append(row)
            for col_ix in range(cols):
                if has_header and row_ix == 0:
                    cell = self.rdoc.element('th', 'empty!!')
                    if on_add_header_cell:
                        on_add_header_cell(cell, row_ix, col_ix, self.colsc)
                else:
                    cell = self.rdoc.element('td', 'empty!')
                    if on_add_data_cell:
                        on_add_data_cell(cell, row_ix, col_ix, self.rowsc, self.colsc)
                if col_ix == 0 and has_index:
                    cell.cls.append('index')
                row.append(cell)
                self.row_col_items[(row_ix, col_ix)] = cell

########NEW FILE########
