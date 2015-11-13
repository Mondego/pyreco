__FILENAME__ = appcodegen
# Copyright (c) 2012-2013 Turbulenz Limited

"""
This file contains all of the code generation, formatting and default
templates for the build tools.  This includes the set of variables
used to render the html templates, the format of dependency
information and the set of shared options across the code build tools.
"""

from turbulenz_tools.utils.dependencies import find_file_in_dirs
from turbulenz_tools.utils.profiler import Profiler
from turbulenz_tools.tools.toolsexception import ToolsException
from turbulenz_tools.tools.templates import read_file_utf8

import os.path
import glob
from re import compile as re_compile
from logging import getLogger

__version__ = '1.1.4'

LOG = getLogger(__name__)

############################################################

DEFAULT_HTML_TEMPLATE = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
    <title>
        /*{% block tz_app_title %}*//*{{ tz_app_title_var }}*//*{% endblock %}*/
    </title>
    <meta http-equiv="Content-Type" content="text/html;charset=utf-8" >
    <style type="text/css">
html, body, div, span, object, iframe, h1, h2, p, a, img, ul, li, fieldset, form, label, legend, table, thead, tbody, tfoot, tr, th, td {
    border: 0;
    font-size: 100%;
    margin: 0;
    outline: 0;
    padding: 0;
    vertical-align: baseline;
}
    </style>
    <!-- block tz_app_header -->
    /*{% block tz_app_header %}*//*{% endblock %}*/
    <!-- end tz_app_header -->
</head>
<body style="background:#B4B4B4;font:normal normal normal 13px/1.231 Helvetica,Arial,sans-serif;text-shadow:1px 1px #F9F8F8;">
    <div id="titlebar" style="position:fixed;height:65px;top:0;right:0;left:0;">
        <strong style="font-size:24px;line-height:64px;margin:16px;">
            <!-- block tz_app_title_name -->
            /*{% block tz_app_title_name %}*/
            /*{{ tz_app_title_name_var }}*/
            /*{% endblock %}*/
            <!-- end tz_app_title_name -->
        </strong>
        <div id="titlelogo"
             style="float:right;width:27px;height:27px;margin:18px 24px;">
        </div>
    </div>
    <div id="sidebar"
         style="background:#B4B4B4;position:fixed;width:303px;top:65px;left:0;">
        <!-- block tz_app_html_controls -->
        /*{% block tz_app_html_controls %}*/
        /*{% endblock %}*/
        <!-- end tz_app_html_controls -->
    </div>
    <div id="engine" style="background:#939393;position:fixed;top:65px;
                            bottom:0;right:0;left:303px;
                            border-left:1px solid #898989;">
        <!--
          HTML to create a plugin or canvas instance.
          Supplied by 'tz_engine_div' variable.
        -->
        /*{{ tz_engine_div }}*/
    </div>

    <!-- begin 'tz_include_js' variable -->
    /*{{ tz_include_js }}*/
    <!-- end 'tz_include_js' variable -->

    <script type="text/javascript">
      // ----------------------------------------
      // Embedded code and startup code.
      // Supplied by 'tz_startup_code' variable.
      // ----------------------------------------
      /*{{ tz_startup_code }}*/
    </script>

</body>
</html>
"""

############################################################

def default_parser_options(parser):
    """
    Command line options shared by make*.py tools
    """

    parser.add_option("--version", action="store_true", dest="output_version",
                      default=False, help="output version number")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      default=False, help="verbose output")
    parser.add_option("-s", "--silent", action="store_true", dest="silent",
                      default=False, help="silent running")

    # Input / Output (input .html and .js files don't need a prefix)
    parser.add_option("-o", "--output", action="store", dest="output",
                      help="output file to process")
    parser.add_option("-t", "--templatedir", action="append", dest="templatedirs",
                      default=[], help="template directory (multiple allowed)")

    # Dependency generation
    parser.add_option("-M", "--dependency", action="store_true",
                      dest="dependency", default=False,
                      help="output dependencies")
    parser.add_option("--MF", action="store", dest="dependency_file",
                      help="dependencies output to file")

    # "use strict" options
    parser.add_option("--use-strict", action="store_true", dest="use_strict",
                      default=False, help='enforce "use strict"; statement. '
                      'This adds a single "use strict"; line at the top of the '
                      'JavaScript code.')
    parser.add_option("--include-use-strict", action="store_true",
                      dest="include_use_strict", default=False,
                      help='don\'t strip out "use strict"; statements. '
                      'By default all "use strict"; statements are removed '
                      'from the output file.')

    # Hybrid
    parser.add_option("--hybrid", action="store_true", dest="hybrid",
                      default=False, help="canvas, canvas_dev modes only. "
                      "Start up a plugin as well as a canvas-based "
                      "TurbulenzEngine. The plugin will be available as "
                      "TurbulenzEnginePlugin.")

    # Profiling
    def _enable_profiler(_options, _opt_str, _value, _parser):
        Profiler.enable()
    parser.add_option("--profile", action="callback", callback=_enable_profiler,
                      help="enable the collection and output of profiling "
                      "information")

    # Injecting files
    parser.add_option("--no-inject", action="store_true", dest="noinject",
                      default=False, help="Don't inject default library files")

############################################################

def render_js(context, options, templates_js, inject_js):
    """
    Renders the templates in templates_js, as if the first template
    began with include declarations for each of the files in
    inject_js.  Returns the result of rendering, and the list of
    includes that were not inlined.  (rendered_js, inc_js)

    For dev modes, the list of includes is returned in inc_js as
    relative paths from the output file.  For release modes, includes
    are all inlined (inc_js == []).
    """

    regex_use_strict = re_compile('"use strict";')

    out = []
    inc_js = []
    outfile_dir = os.path.abspath(os.path.dirname(options.output)) + os.sep

    includes_seen = []

    # Any headers

    if options.use_strict:
        out.append('"use strict";')

    if options.mode in [ 'plugin', 'canvas' ]:
        out.append('(function () {')

    # Functions for handling includes

    def _find_include_or_error(name):
        try:
            f = find_file_in_dirs(name, options.templatedirs)
        except Exception, ex:
            raise ToolsException(str(ex))
        if f is None:
            raise ToolsException("No file '%s' in any template dir" % name)
        LOG.info(" resolved '%s' to path '%s'", name, f)
        return f

    def handle_javascript_dev(name):
        file_path = _find_include_or_error(name)
        if file_path in includes_seen:
            LOG.info(" include '%s' (%s) already listed", name, file_path)
            return ""
        includes_seen.append(file_path)

        # Calculate relative path name
        # rel_path = file_path.replace(outfile_dir, '').replace('\\', '/')
        # if rel_path == file_path:
        #     raise ToolsException("Included file '%s' found at '%s', which is "
        #                          "not in a child directory of the output file "
        #                          "'%s' in directory %s" % (name, file_path,
        #                                                    options.output,
        #                                                    outfile_dir))
        rel_path = os.path.relpath(file_path, outfile_dir).replace('\\', '/')

        inc_js.append(rel_path)
        return ""

    def handle_javascript_release(name):
        if options.stripdebug and os.path.basename(name) == "debug.js":
            LOG.warning("App attempting to include debug.js.  Removing.")
            return ""
        file_path = _find_include_or_error(name)
        if file_path in includes_seen:
            LOG.info(" include '%s' (%s) already listed", name, file_path)
            return ""
        includes_seen.append(file_path)

        d = read_file_utf8(file_path)

        if options.include_use_strict:
            return d
        else:
            # strip out any "use strict"; lines
            return regex_use_strict.sub('', d)

    if options.mode in [ 'plugin', 'canvas' ]:
        handle_javascript = handle_javascript_release
    else:
        handle_javascript = handle_javascript_dev
    context['javascript'] = handle_javascript

    # Inject any includes at the start, either embedding them or
    # adding to the inc_js list.

    for inj in inject_js:
        js_line = handle_javascript(inj)
        if js_line:
            out.append(js_line)

    # Render templates

    out += [t.render(context) for t in templates_js]
    del context['javascript']

    # Any footer code

    if options.mode == 'plugin':
        out.append("""
    if (!TurbulenzEngine.onload)
    {
        window.alert("Entry point 'TurbulenzEngine.onload' must be defined.");
        return;
    }
    TurbulenzEngine.onload.call(this);
}());""")

    if options.mode == 'canvas':
        out.append('window.TurbulenzEngine = TurbulenzEngine;}());')

    # Combine all parts into a single string

    return ("\n".join(out), inc_js)

def render_js_extract_includes(context, options, templates_js, injects):
    """
    Renders the templates in templates_js against the given context
    and just collects the set of 'javascript('...')' includes.  Will
    optionally handle a list of files to be injected.

    Returns an array of absolute paths, removing duplicates.
    """

    includes = []

    def _find_in_dirs_or_error(name):
        file_path = find_file_in_dirs(name, options.templatedirs)
        if file_path is None:
            raise ToolsException("No file '%s' in any template dir" % name)
        if file_path in includes:
            LOG.info(" include '%s' (%s) already listed", name, file_path)
            return
        LOG.info(" resolved '%s' to path '%s'", name, file_path)
        includes.append(file_path)

    # In release mode, filter out debug.js

    if options.mode in [ 'plugin', 'canvas' ] and options.stripdebug:
        _do_find_in_dirs_or_error = _find_in_dirs_or_error
        # pylint: disable=E0102
        def _find_in_dirs_or_error(name):
            if os.path.basename(name) == "debug.js":
                LOG.warning("App attempting to include debug.js.  Removing.")
                return
            _do_find_in_dirs_or_error(name)
        # pylint: enable=E0102

    # Deal with any injects

    for i in injects:
        _find_in_dirs_or_error(i)

    # Use the templating engine to deal with remaining includes

    def handle_javascipt_extract_includes(name):
        _find_in_dirs_or_error(name)
        return ""

    context['javascript'] = handle_javascipt_extract_includes

    for t in templates_js:
        t.render(context)

    del context['javascript']

    return includes

############################################################

def output_dependency_info(dependency_file, output_file, dependencies):
    """
    This dependency write outputs dependency information in a format
    consistent with the GCC -M flags.
    """

    try:
        with open(dependency_file, "wb") as f:
            f.write(output_file)
            f.write(" ")
            f.write(dependency_file)
            f.write(" : \\\n")
            for d in dependencies:
                f.write("    ")
                f.write(d)
                f.write(" \\\n")
            f.write("\n\n")
            for d in dependencies:
                f.write(d)
                f.write(" :\n\n")
    except IOError:
        raise ToolsException("failed to write file: %s" % dependency_file)

############################################################

def context_from_options(options, title):

    # Sanity check

    if options.hybrid:
        if options.mode not in [ 'canvas', 'canvas-debug' ]:
            raise ToolsException("--hybrid option available only in canvas and "
                                 "canvas_dev modes")

    # Set up the context

    context = {}
    context['tz_app_title_name_var'] = title
    context['tz_app_title_var'] = title

    context['tz_development'] = options.mode in [ 'plugin-debug', 'canvas-debug' ]
    context['tz_canvas'] = options.mode in [ 'canvas', 'canvas-debug' ]
    context['tz_hybrid'] = options.hybrid

    return context

############################################################

def inject_js_from_options(options):
    """
    Given the build options, find (if necessary), all includes that
    must be injected for canvas mode to work.  This is done by
    searching for webgl_engine_file in any of the
    template directories, and collecting the list of all .js files
    that reside there.
    """

    inject_list = []

    if options.noinject:
        return inject_list

    mode = options.mode

    # Put debug.js at the top (if in debug mode), and ALWAYS include
    # vmath.js

    if mode in [ 'plugin-debug', 'canvas-debug' ] or not options.stripdebug:
        inject_list.append('jslib/debug.js')
    inject_list.append('jslib/vmath.js')

    # Include webgl includes in canvas mode

    if mode in [ 'canvas', 'canvas-debug' ]:
        LOG.info("Looking for jslib/webgl ...")

        webgl_engine_file = 'jslib/webgl/turbulenzengine.js'
        webgl_engine_dir = os.path.dirname(webgl_engine_file)

        # Find absolute path of webgl_engine_file

        webgl_abs_path = None

        for t in options.templatedirs:
            p = os.path.join(t, webgl_engine_file)
            if os.path.exists(p):
                webgl_abs_path = os.path.dirname(p)
                LOG.info("Found at: %s", webgl_abs_path)
                break

        if webgl_abs_path is None:
            raise ToolsException("No '%s' in any template dir" \
                                     % webgl_engine_file)

        webgl_abs_files = glob.glob(webgl_abs_path + "/*.js")
        inject_list += [ 'jslib/utilities.js',
                         'jslib/aabbtree.js',
                         'jslib/observer.js' ]
        inject_list += \
            [ webgl_engine_dir + "/" + os.path.basename(f) for f in webgl_abs_files ]

    return inject_list

############################################################

def default_add_code(options, context, rendered_js, inc_js):
    """
    Add:
      tz_engine_div
      tz_include_js
      tz_startup_code
    to the context, based on the values of options
    """

    # pylint: disable=W0404
    from turbulenz_tools.version import SDK_VERSION as engine_version
    # pylint: enable=W0404
    engine_version_2 = ".".join(engine_version.split(".")[0:2])

    outfile_dir = os.path.dirname(options.output)
    if options.mode in [ 'plugin', 'canvas' ]:
        codefile_rel = os.path.relpath(options.codefile, outfile_dir).replace('\\', '/')

    #
    # tz_engine_div and tz_engine_2d_div
    #

    tz_engine_div = ""
    if options.mode in [ 'canvas', 'canvas-debug' ]:

        tz_engine_div += """
        <canvas id="turbulenz_game_engine_canvas" moz-opaque="true" tabindex="1">
            Sorry, but your browser does not support WebGL or does not have it
            enabled.  To get a WebGL-enabled browser, please see:<br/>
            <a href="http://www.khronos.org/webgl/wiki/Getting_a_WebGL_Implementation" target="_blank">
                Getting a WebGL Implementation
            </a>
        </canvas>

        <script type="text/javascript">
            var canvasSupported = true;
            (function()
            {
                var contextNames = ["webgl", "experimental-webgl"];
                var context = null;
                var canvas = document.createElement('canvas');

                document.body.appendChild(canvas);

                for (var i = 0; i < contextNames.length; i += 1)
                {
                    try {
                        context = canvas.getContext(contextNames[i]);
                    } catch (e) {}

                    if (context) {
                        break;
                    }
                }
                if (!context)
                {
                    canvasSupported = false;
                    window.alert("Sorry, but your browser does not support WebGL or does not have it enabled.");
                }

                document.body.removeChild(canvas);
            }());
            var TurbulenzEngine = {};
        </script>"""

        tz_engine_2d_div = """
        <canvas id="turbulenz_game_engine_canvas" moz-opaque="true" tabindex="1">
        </canvas>

        <script type="text/javascript">
            var canvasSupported = true;
            (function()
            {
                var canvas = document.createElement("canvas");
                document.body.appendChild(canvas);
                if (!canvas.getContext("2d"))
                {
                    canvasSupported = false;
                    window.alert("Sorry, but your browser does not support 2D Canvas or does not have it enabled.");
                }
                document.body.removeChild(canvas);
            }());
            var TurbulenzEngine = {};
        </script>"""


    if options.mode in [ 'plugin', 'plugin-debug' ] or options.hybrid:

        tz_engine_div += """
        <script type="text/javascript">
            if (window.ActiveXObject)
            {
                document.write('<object id="turbulenz_game_loader_object" classid="CLSID:49AE29B1-3E7D-4f62-B3D2-D6F7C7BEE728" width="100%" height="100%">');
                document.write('<param name="type" value="application/vnd.turbulenz" \/>');
                document.write('<p>You need the Turbulenz Engine for this.');
                document.write('<\/p>');
                document.write('<\/object>');
            }
            else
            {
                // browser supports Netscape Plugin API
                document.write('<object id="turbulenz_game_loader_object" type="application/vnd.turbulenz" width="100%" height="100%">');
                document.write('<p>You need the Turbulenz Engine for this.');
                document.write('<\/p>');
                document.write('<\/object>');
            }"""

        if options.mode == 'plugin-debug':
            tz_engine_div += """
            // If IE
            if (navigator.appName === "Microsoft Internet Explorer")
            {
                window.alert("Sorry, but this sample does not run in development mode in Internet Explorer.");
            }
            var TurbulenzEngine = {
                VMath: null
            };"""

        tz_engine_div += """
        </script>"""

        tz_engine_2d_div = tz_engine_div

    #
    # tz_include_js
    #

    if options.mode in [ 'plugin-debug', 'canvas-debug' ]:
        inc_lines = [ '<script type="text/javascript" src="%s"></script>' % js \
                          for js in inc_js ]
        tz_include_js = "\n".join(inc_lines)
    elif options.mode == 'canvas':
        tz_include_js = '\n<script type="text/javascript" src="%s"></script>' \
            % codefile_rel
    else:
        tz_include_js = "\n"

    #
    # tz_startup_code
    #

    tz_startup_find_best_version_fn = """

            function findBestVersion(request, availableVersions)
            {
                var reqNumbers = request.split(".");
                var candidate;

                for (var vIdx = 0; vIdx < availableVersions.length; vIdx += 1)
                {
                    var ver = availableVersions[vIdx];
                    var verNumbers = ver.split(".");

                    // Check the version has the correct major and minor

                    if ((verNumbers[0] !== reqNumbers[0]) ||
                        (verNumbers[1] !== reqNumbers[1]))
                    {
                        continue;
                    }

                    // If there is already a candidate, compare point and build

                    if (candidate)
                    {
                        if (verNumbers[2] > candidate[2])
                        {
                            candidate = verNumbers;
                            continue;
                        }
                        if ((verNumbers[2] === candidate[2]) &&
                            (verNumbers[3] > candidate[3]))
                        {
                            candidate = verNumbers;
                            continue;
                        }
                    }
                    else
                    {
                        candidate = verNumbers;
                    }
                }

                if (candidate)
                {
                    candidate = candidate.join(".");
                }
                return candidate;
            }"""

    tz_startup_plugin_unload_code = """

            // Engine unload
            var previousOnBeforeUnload = window.onbeforeunload;
            window.onbeforeunload = function ()
            {
                try {
                    loader.unloadEngine();
                } catch (e) {
                }
                if (previousOnBeforeUnload) {
                    previousOnBeforeUnload.call(this);
                }
            };"""

    tz_startup_plugin_check_and_load_code = tz_startup_find_best_version_fn + """

            var now = Date.now || function () { return new Date().valueOf(); };
            var loadDeadline = now() + 5 * 1000;  // 5 seconds
            var loadInterval = 500;               // 0.5 seconds

            var attemptLoad = function attemptLoadFn()
            {
                // Check plugin and load engine
                var err = 0;
                if (!loader) {
                    err = "no loader DOM element";
                }
                if (err === 0 &&
                    !loader.loadEngine &&
                    loader.hasOwnProperty &&
                    !loader.hasOwnProperty('loadEngine')) {
                    err = "loader has no 'loadEngine' property";
                }
                if (err === 0 &&
                    !loader.getAvailableEngines &&
                    !loader.hasOwnProperty('getAvailableEngines')) {
                    err = "no 'getAvailableEngines'. Plugin may be "
                            + "an older version.";
                }

                if (err === 0)
                {
                    var availableEngines = loader.getAvailableEngines();
                    var samplesVersion = '""" + engine_version_2 + """';
                    var requestVersion =
                        findBestVersion(samplesVersion, availableEngines);
                    if (!requestVersion)
                    {
                        err = "No engines installed that are compatible with "
                                + "version " + samplesVersion;
                    }
                    else
                    {
                        config.version = requestVersion;
                    }
                }

                if (err === 0)
                {
                    // Plugin is in place
                    if (!loader.loadEngine(config))
                    {
                        window.alert("Call to loadEngine failed");
                    }
                    return;
                }

                // Continue to wait for the plugin
                if (loadDeadline >= now()) {
                    window.setTimeout(attemptLoad, loadInterval);
                } else {
                    window.alert("No Turbulenz Loader found ("+err+")");
                }
            };
            attemptLoad();"""

    if options.mode == 'plugin-debug':
        tz_startup_code = "\n" + rendered_js.lstrip('\n') + """

        // Engine startup
        window.onload = function ()
        {
            var loader =
                document.getElementById('turbulenz_game_loader_object');
            var appEntry = TurbulenzEngine.onload;
            var appShutdown = TurbulenzEngine.onunload;
            var appMathDevice = TurbulenzEngine.VMath;
            if (!appEntry)
            {
                window.alert("TurbulenzEngine.onload has not been set");
                return;
            }
            var progressCB = function progressCBFn(msg)
            {
                if ('number' !== typeof msg) {
                    window.alert("Error during engine load: " + msg);
                    return;
                }
                // Progress update here
            };
            var config = {
                run: function runFn(engine) {
                    TurbulenzEngine = engine;
                    TurbulenzEngine.onload = appEntry;
                    TurbulenzEngine.onunload = appShutdown;
                    TurbulenzEngine.VMath = appMathDevice;
                    engine.setTimeout(appEntry, 0);
                },
                progress: progressCB
            };""" + tz_startup_plugin_unload_code + """

            """ + tz_startup_plugin_check_and_load_code + """

        };  // window.onload()"""

    elif options.mode == 'plugin':
        tz_startup_code = """

        window.onload = function ()
        {
            var loader = document.getElementById('turbulenz_game_loader_object');
            var config = {
                url: '""" + codefile_rel + """'
            };""" + tz_startup_plugin_unload_code + """

            """ + tz_startup_plugin_check_and_load_code + """

        };  // window.onload()"""

    else:
        tz_startup_code = ""
        if options.hybrid:
            tz_startup_code += """
        var TurbulenzEnginePlugin = null;"""
        if options.mode == 'canvas-debug':
            tz_startup_code += "\n" + rendered_js.lstrip('\n') + "\n"

        tz_startup_code += """
        // Engine startup
        window.onload = function ()
        {
            var appEntry = TurbulenzEngine.onload;
            var appShutdown = TurbulenzEngine.onunload;
            if (!appEntry) {
                window.alert("TurbulenzEngine.onload has not been set");
                return;
            }

            var canvas =
                document.getElementById('turbulenz_game_engine_canvas');"""

        if options.hybrid:
            tz_startup_code += """
            var loader =
                document.getElementById('turbulenz_game_loader_object');"""

        tz_startup_code += """

            var startCanvas = function startCanvasFn()
            {
                if (canvas.getContext && canvasSupported)
                {
                    TurbulenzEngine = WebGLTurbulenzEngine.create({
                        canvas: canvas,
                        fillParent: true
                    });

                    if (!TurbulenzEngine) {
                        window.alert("Failed to init TurbulenzEngine (canvas)");
                        return;
                    }

                    TurbulenzEngine.onload = appEntry;
                    TurbulenzEngine.onunload = appShutdown;
                    appEntry()
                }
            }"""

        # Unloading code

        tz_startup_code += """

            var previousOnBeforeUnload = window.onbeforeunload;
            window.onbeforeunload = function ()
            {
                if (TurbulenzEngine.onunload) {
                    TurbulenzEngine.onunload.call(this);
                }"""
        if options.hybrid:
            tz_startup_code += """
                if (loader.unloadEngine) {
                    loader.unloadEngine();
                }
                if (previousOnBeforeUnload) {
                    previousOnBeforeUnload.call(this);
                }"""
        tz_startup_code += """
            };  // window.beforeunload"""


        # In hybrid mode, nothing can start until the engine is
        # loaded so wrap the canvas startup code in loader calls,
        # otherwise just call it immediately.

        if options.hybrid:
            tz_startup_code += """
            var config = {
                run: function (engine)
                {
                    TurbulenzEnginePlugin = engine;
                    startCanvas();
                },
            };

            if (!loader || !loader.loadEngine || !loader.loadEngine(config))
            {
                window.alert("Failed to load Turbulenz Engine.");
                return;
            }"""

        else:
            tz_startup_code += """

            startCanvas();"""

        tz_startup_code += """
        };  // window.onload()
"""

    context['tz_engine_div'] = tz_engine_div
    context['tz_engine_2d_div'] = tz_engine_2d_div
    context['tz_include_js'] = tz_include_js
    context['tz_startup_code'] = tz_startup_code
    context['tz_sdk_version'] = engine_version

########NEW FILE########
__FILENAME__ = asset2json
# Copyright (c) 2009-2013 Turbulenz Limited
"""
Asset class used to build Turbulenz JSON assets.
"""

import logging
LOG = logging.getLogger('asset')

from itertools import chain as itertools_chain
from simplejson import encoder as json_encoder, dumps as json_dumps, dump as json_dump
from types import StringType

# pylint: disable=W0403
import vmath

from turbulenz_tools.utils.json_utils import float_to_string, metrics
from node import NodeName
from material import Material
# pylint: enable=W0403

__version__ = '1.2.0'
__dependencies__ = ['vmath', 'json2json', 'node', 'material']

#######################################################################################################################

def attach_skins_and_materials(asset, definitions, material_name, default=True):
    """Find all skins in the ``definitions`` asset which remap the material ``material_name``. Attach the found skin
    and references materials to the target ``asset``."""
    skins = definitions.retrieve_skins()
    for skin, materials in skins.iteritems():
        attach_skin = False
        for v, k in materials.iteritems():
            if v == material_name:
                attach_skin = True
                material = definitions.retrieve_material(k, default)
                asset.attach_material(k, raw=material)
        if attach_skin:
            asset.attach_skin(skin, materials)

def remove_unreferenced_images(asset, default=True):
    def _unreference_image(imageName):
        if type(imageName) is StringType:
            # this image is referenced so remove it from the unreferenced list
            if imageName in unreferenced_images:
                unreferenced_images.remove(imageName)

    images = asset.asset['images']
    unreferenced_images = set(asset.asset['images'].iterkeys())
    materials = asset.asset['materials']
    effects = asset.asset['effects']

    for v, _ in effects.iteritems():
        effect = asset.retrieve_effect(v)
        parameters = effect.get('parameters', None)
        if parameters:
            for value in parameters.itervalues():
                _unreference_image(value)

    for v, _ in materials.iteritems():
        material = asset.retrieve_material(v, default)
        parameters = material.get('parameters', None)
        if parameters:
            for value in parameters.itervalues():
                _unreference_image(value)

    # remove the unreferenced images
    for i in unreferenced_images:
        del images[i]

#######################################################################################################################

DEFAULT_IMAGE_FILENAME = 'default.png'
DEFAULT_EFFECT_TYPE = 'lambert'
DEFAULT_EFFECT_NAME = 'effect-0'
DEFAULT_MATERIAL_NAME = 'material-0'
DEFAULT_SHAPE_NAME = 'shape-0'
DEFAULT_SKELETON_NAME = 'skeleton-0'
DEFAULT_LIGHT_NAME = 'light-0'
DEFAULT_INSTANCE_NAME = 'instance-0'
DEFAULT_NODE_NAME = NodeName('node-0')
DEFAULT_TEXTURE_MAP_NAME = 'shape-map1'
DEFAULT_ANIMATION_NAME = 'animation-0'
DEFAULT_ENTITY_DEFINITION_NAME = 'entity_definition-0'
DEFAULT_MODEL_DEFINITION_NAME = 'model_definition-0'
DEFAULT_ENTITY_NAME = 'entity-0'
DEFAULT_PHYSICS_MATERIAL_NAME = 'physics-material-0'
DEFAULT_PHYSICS_NODE_NAME = 'physics-node-0'
DEFAULT_PHYSICS_MODEL_NAME = 'physics-model-0'
DEFAULT_SOUND_NAME = 'sound-0'
DEFAULT_SKIN_NAME = 'skin-0'
DEFAULT_PROCEDURALEFFECT_NAME = 'effect-0'
DEFAULT_APPLICATION_NAME = 'player'

# pylint: disable=R0904
class JsonAsset(object):
    """Contains a JSON asset."""
    SurfaceLines = 0
    SurfaceTriangles = 1
    SurfaceQuads = 2

    def __init__(self, up_axis='Y', v = 1, definitions=None):
        if definitions:
            self.asset = definitions
        else:
            self.asset = { 'version': v,
                           'geometries': { },
                           'skeletons': { },
                           'effects': { },
                           'materials': { },
                           'images': { },
                           'nodes': { },
                           'lights': { },
                           'entitydefinitions': { },
                           'modeldefinitions': { },
                           'entities': { },
                           'animations': { },
                           'camera_animations': { },
                           'physicsmaterials': { },
                           'physicsmodels': { },
                           'physicsnodes': { },
                           'sounds': { },
                           'proceduraleffects': { },
                           'areas': [ ],
                           'bspnodes': [ ],
                           'skins': { },
                           'strings': { },
                           'guis': { },
                           'tables': { },
                           'applications': { }
                         }
        if up_axis == 'X':
            self.default_transform = [ 0, 1, 0, -1, 0,  0, 0, 0, 1, 0, 0, 0 ]
        elif up_axis == 'Y':
            self.default_transform = [ 1, 0, 0,  0, 1,  0, 0, 0, 1, 0, 0, 0 ]
        elif up_axis == 'Z':
            self.default_transform = [ 1, 0, 0,  0, 0, -1, 0, 1, 0, 0, 0, 0 ]

    def json_to_string(self, sort=True, indent=1):
        """Convert the asset to JSON and return it as a string."""
        json_encoder.FLOAT_REPR = float_to_string
        return json_dumps(self.asset, sort_keys=sort, indent=indent)

    def json_to_file(self, target, sort=True, indent=0):
        """Convert the asset to JSON and write it to the file stream."""
        json_encoder.FLOAT_REPR = float_to_string
        if indent > 0:
            return json_dump(self.asset, target, sort_keys=sort, indent=indent)
        else:
            return json_dump(self.asset, target, sort_keys=sort, separators=(',', ':'))

    def clean(self):
        """Remove any toplevel elements which are empty."""
        for k in self.asset.keys():
            if isinstance(self.asset[k], dict) and len(self.asset[k].keys()) == 0:
                del self.asset[k]
            elif isinstance(self.asset[k], list) and len(self.asset[k]) == 0:
                del self.asset[k]

    def log_metrics(self):
        """Output the metrics to the log."""
        m = metrics(self.asset)
        keys = m.keys()
        keys.sort()
        for k in keys:
            LOG.info('json_asset:%s:%s', k, m[k])

#######################################################################################################################

    def __set_source(self, shape, name, stride, min_element=None, max_element=None, data=None):
        """Add a vertex stream source for the specified geometry shape."""
        if data is None:
            data = [ ]
        source = { 'stride': stride, 'data': data }
        if min_element is not None:
            source['min'] = min_element
        if max_element is not None:
            source['max'] = max_element
        LOG.debug("geometries:%s:sources:%s[%i]", shape, name, len(data) / stride)
        self.asset['geometries'][shape]['sources'][name] = source

    def __set_input(self, shape, element, data):
        """Add a vertex stream input for the specified geometry shape."""
        LOG.debug("geometries:%s:inputs:%s:%s offset %i", shape, element, data['source'], data['offset'])
        self.asset['geometries'][shape]['inputs'][element] = data

    def __set_shape(self, shape, key, data, name=None):
        """Add a key and data to the specified geometry shape."""
        if isinstance(data, list):
            LOG.debug("geometries:%s:%s[%i]", shape, key, len(data))
        else:
            LOG.debug("geometries:%s:%s:%i", shape, key, data)
        if name is None:
            self.asset['geometries'][shape][key] = data
        else:
            shape_asset = self.asset['geometries'][shape]
            if 'surfaces' not in shape_asset:
                shape_asset['surfaces'] = { }
            surfaces_asset = shape_asset['surfaces']
            if name not in surfaces_asset:
                surfaces_asset[name] = { }
            surface_asset = surfaces_asset[name]
            surface_asset[key] = data

    def __set_meta(self, shape, data):
        """Add the meta information to the specified geometry shape."""
        self.asset['geometries'][shape]['meta'] = data

    def __set_geometry(self, key, data):
        """Add a key and data to single geometry."""
        LOG.debug("geometries:%s:%s", key, data)
        self.asset['geometries'][key] = data

    def __set_asset(self, key, data):
        """Add a key and data to the asset."""
        LOG.debug("%s:%s", key, data)
        self.asset[key] = data

    def __attach_v1(self, shape, source, name, attribute, offset=0):
        """Attach a single value stream to the JSON representation. Also calculates the min and max range."""
        elements = [ ]
        (min_x) = source[0]
        (max_x) = source[0]
        for x in source:
            elements.append(x)
            min_x = min(x, min_x)
            max_x = max(x, max_x)
        self.__set_source(shape, name, 1, [min_x], [max_x], elements)
        self.__set_input(shape, attribute, { 'source': name, 'offset': offset })

    def __attach_v2(self, shape, source, name, attribute, offset=0):
        """Attach a Tuple[2] stream to the JSON representation. Also calculates the min and max range."""
        elements = [ ]
        (min_x, min_y) = source[0]
        (max_x, max_y) = source[0]
        for (x, y) in source:
            elements.append(x)
            elements.append(y)
            min_x = min(x, min_x)
            min_y = min(y, min_y)
            max_x = max(x, max_x)
            max_y = max(y, max_y)
        self.__set_source(shape, name, 2, [min_x, min_y], [max_x, max_y], elements)
        self.__set_input(shape, attribute, { 'source': name, 'offset': offset })

    def __attach_v3(self, shape, source, name, attribute, offset=0):
        """Attach a Tuple[3] stream to the JSON representation. Also calculates the min and max range."""
        if len(source) > 0:
            elements = [ ]
            (min_x, min_y, min_z) = source[0]
            (max_x, max_y, max_z) = source[0]
            for (x, y, z) in source:
                elements.append(x)
                elements.append(y)
                elements.append(z)
                min_x = min(x, min_x)
                min_y = min(y, min_y)
                min_z = min(z, min_z)
                max_x = max(x, max_x)
                max_y = max(y, max_y)
                max_z = max(z, max_z)
            self.__set_source(shape, name, 3, [min_x, min_y, min_z], [max_x, max_y, max_z], elements)
            self.__set_input(shape, attribute, { 'source': name, 'offset': offset })

    def __attach_v4(self, shape, source, name, attribute, offset=0):
        """Attach a Tuple[4] stream to the JSON representation. Also calculates the min and max range."""
        elements = [ ]
        (min_x, min_y, min_z, min_w) = source[0]
        (max_x, max_y, max_z, max_w) = source[0]
        for (x, y, z, w) in source:
            elements.append(x)
            elements.append(y)
            elements.append(z)
            elements.append(w)
            min_x = min(x, min_x)
            min_y = min(y, min_y)
            min_z = min(z, min_z)
            min_w = min(w, min_w)
            max_x = max(x, max_x)
            max_y = max(y, max_y)
            max_z = max(z, max_z)
            max_w = max(w, max_w)
        self.__set_source(shape, name, 4, [min_x, min_y, min_z, min_w], [max_x, max_y, max_z, max_w], elements)
        self.__set_input(shape, attribute, { 'source': name, 'offset': offset })

    def __retrieve_node(self, name):
        """Find the named node in the node hierarchy."""
        parts = name.hierarchy_names()
        node = self.asset
        for p in parts:
            if 'nodes' not in node:
                node['nodes'] = { }
            nodes = node['nodes']
            if p not in nodes:
                nodes[p] = { }
            node = nodes[p]
        return node

    def __retrieve_shape_instance(self,
                                  name=DEFAULT_NODE_NAME,
                                  shape_instance=DEFAULT_INSTANCE_NAME):
        assert(isinstance(name, NodeName))
        node = self.__retrieve_node(name)
        if 'geometryinstances' in node:
            geometry_instances = node['geometryinstances']
            if shape_instance in geometry_instances:
                instance = geometry_instances[shape_instance]
            else:
                instance = { }
                geometry_instances[shape_instance] = instance
        else:
            geometry_instances = { }
            node['geometryinstances'] = geometry_instances
            instance = { }
            geometry_instances[shape_instance] = instance
        return instance

    def __retrieve_light_instance(self,
                                  name=DEFAULT_NODE_NAME,
                                  light_instance=DEFAULT_INSTANCE_NAME):
        assert(isinstance(name, NodeName))
        node = self.__retrieve_node(name)
        if 'lightinstances' in node:
            light_instances = node['lightinstances']
            if light_instance in light_instances:
                instance = light_instances[light_instance]
            else:
                instance = { }
                light_instances[light_instance] = instance
        else:
            light_instances = { }
            node['lightinstances'] = light_instances
            instance = { }
            light_instances[light_instance] = instance
        return instance

#######################################################################################################################

    def attach_stream(self, source, shape, name, semantic, stride, offset):
        """Missing"""
        if source is not None:
            if isinstance(source[0], tuple) is False:
                self.__attach_v1(shape, source, name, semantic, offset)
            elif len(source[0]) == 2:
                self.__attach_v2(shape, source, name, semantic, offset)
            elif len(source[0]) == 3:
                self.__attach_v3(shape, source, name, semantic, offset)
            elif len(source[0]) == 4:
                self.__attach_v4(shape, source, name, semantic, offset)
        else:
            self.__set_source(shape, name, stride)
            self.__set_input(shape, semantic, { 'source': name, 'offset': offset })

    def attach_uvs(self, uvs, shape=DEFAULT_SHAPE_NAME, name=DEFAULT_TEXTURE_MAP_NAME, semantic="TEXCOORD0"):
        """Attach the vertex UVs to the JSON representation. Also calculates the min and max range."""
        if len(uvs[0]) == 2:
            self.__attach_v2(shape, uvs, name, semantic)
        elif len(uvs[0]) == 3:
            self.__attach_v3(shape, uvs, name, semantic)

    def attach_positions(self, positions, shape=DEFAULT_SHAPE_NAME, name="shape-positions", semantic="POSITION"):
        """Attach the vertex position stream to the JSON representation. Also calculates the min and max range."""
        self.__attach_v3(shape, positions, name, semantic)

    def attach_normals(self, normals, shape=DEFAULT_SHAPE_NAME, name="shape-normals", semantic="NORMAL"):
        """Attach the vertex normal stream to the JSON representation. Also calculates the min and max range."""
        self.__attach_v3(shape, normals, name, semantic)

    # pylint: disable=R0913
    def attach_nbts(self, normals, tangents, binormals, shape=DEFAULT_SHAPE_NAME,
                    normals_name="shape-normals", tangents_name="shape-tangents", binormals_name="shape-binormals",
                    normals_semantic="NORMAL", tangents_semantic="TANGENT", binormals_semantic="BINORMAL"):
        """Attach the vertex nbt streama to the JSON representation. Also calculates the min and max range."""
        self.__attach_v3(shape, normals, normals_name, normals_semantic)
        self.__attach_v3(shape, tangents, tangents_name, tangents_semantic)
        self.__attach_v3(shape, binormals, binormals_name, binormals_semantic)
    # pylint: enable=R0913

    def attach_skinning_data(self, skin_indices, skin_weights, shape=DEFAULT_SHAPE_NAME,
                             skin_indices_name="shape-skinindices", skin_indices_semantic="BLENDINDICES",
                             skin_weights_name="shape-skinweights", skin_weights_semantic="BLENDWEIGHT"):
        """Attach the vertex skinning indices and weights streams to the JSON representation.
        Also calculates the min and max range."""
        self.__attach_v4(shape,  skin_indices, skin_indices_name, skin_indices_semantic)
        self.__attach_v4(shape,  skin_weights, skin_weights_name, skin_weights_semantic)

    def attach_shape(self, shape=DEFAULT_SHAPE_NAME):
        """Attach the shapes to the JSON representation. This should be done before adding any shape streams."""
        self.__set_geometry(shape, { 'sources': { }, 'inputs':  { } })

    def attach_meta(self, meta, shape=DEFAULT_SHAPE_NAME):
        """Attach the meta information to the JSON representation of the shape."""
        self.__set_meta(shape, meta)

    def attach_surface(self, primitives, primitive_type, shape=DEFAULT_SHAPE_NAME, name=None):
        """Attach a surface to the JSON representation. Primitive type should be:
                SurfaceLines = 0
                SurfaceTriangles = 1
                SurfaceQuads = 2
        The primitives will be added to the specified `shape`.

        If a `name` is also specified then the primitives will be put into a named surfaces dictionary."""
        # Collapse the primitives down into a flat index list
        num_primitives = len(primitives)
        indices = [ ]
        for p in primitives:
            indices.extend(p)
        if 0 == len(indices):
            LOG.error('No indices for %s on %s', name, shape)
        if isinstance(indices[0], (tuple, list)):
            indices = list(itertools_chain(*indices))

        self.__set_shape(shape, 'numPrimitives', num_primitives, name)
        if primitive_type == JsonAsset.SurfaceLines:
            self.__set_shape(shape, 'lines', indices, name)
        elif primitive_type == JsonAsset.SurfaceTriangles:
            self.__set_shape(shape, 'triangles', indices, name)
        elif primitive_type == JsonAsset.SurfaceQuads:
            self.__set_shape(shape, 'quads', indices, name)
        else:
            LOG.error('Unsupported primitive type:%i', primitive_type)

    def attach_geometry_skeleton(self, shape=DEFAULT_SHAPE_NAME, skeleton=DEFAULT_SKELETON_NAME):
        """Add a skeleton for the specified geometry shape."""
        LOG.debug("geometries:%s:skeleton added:%s", shape, skeleton)
        self.asset['geometries'][shape]['skeleton'] = skeleton

    def attach_skeleton(self, skeleton, name=DEFAULT_SKELETON_NAME):
        """Add a skeleton object."""
        LOG.debug("%s:skeleton added", name)
        self.asset['skeletons'][name] = skeleton

    def attach_bbox(self, bbox):
        """Attach the bounding box to the top-level geometry of the JSON representation."""
        self.__set_asset('min', bbox['min'])
        self.__set_asset('max', bbox['max'])

    def attach_image(self, filename=DEFAULT_IMAGE_FILENAME, image_link=None):
        """Attach an image to the JSON respresentation."""
        if image_link is None:
            for image_link, image_filename in self.asset['images'].iteritems():
                if image_filename == filename:
                    return image_link
            index = len(self.asset['images'])
            image_link = "file%03i" % index
        self.asset['images'][image_link] = filename
        return image_link

    def attach_effect(self, name=DEFAULT_EFFECT_NAME, effect_type=DEFAULT_EFFECT_TYPE,
                      parameters=None, shader=None, meta=None, raw=None):
        """Attach a new effect to the JSON representation."""
        if raw:
            LOG.debug("effects:%s:elements:%i", name, len(raw.keys()))
            self.asset['effects'][name] = raw
        else:
            if parameters is None:
                parameters = { }
            if name not in self.asset['effects']:
                LOG.debug("effects:%s:type:%s", name, effect_type)
                effect = { 'type': effect_type, 'parameters': parameters }
                if shader is not None:
                    effect['shader'] = shader
                if meta is not None:
                    effect['meta'] = meta
                self.asset['effects'][name] = effect

    def attach_material(self, name=DEFAULT_MATERIAL_NAME, effect=DEFAULT_EFFECT_NAME,
                        technique=None, parameters=None, meta=None, raw=None):
        """Attach a material to the JSON representation."""
        if raw:
            if 'stages' in raw:
                num_stages = len(raw['stages'])
            else:
                num_stages = 0
            LOG.debug("materials:%s:elements:%i:stages:%i", name, len(raw.keys()), num_stages)
            self.asset['materials'][name] = raw
        else:
            LOG.debug("materials:%s:effect:%s", name, effect)
            material = { }
            if effect is not None:
                material['effect'] = effect
            if technique is not None:
                material['technique'] = technique
            if parameters is not None:
                material['parameters'] = parameters
            if meta is not None:
                material['meta'] = meta
            self.asset['materials'][name] = material

    def retrieve_effect(self, name):
        """Return a reference to an effect."""
        if 'effects' in self.asset and name in self.asset['effects']:
            return Material(self.asset['effects'][name])
        return None

    def retrieve_material(self, name=DEFAULT_MATERIAL_NAME, default=True):
        """Return a reference to a material."""
        if name in self.asset['materials']:
            return Material(self.asset['materials'][name])

        if default:
            default_material = { 'effect': 'default',
                                 'parameters': { 'diffuse': 'default' },
                                 'meta': { 'tangents': True } }
            LOG.warning("Material not found:%s", name)
            return Material(default_material)

        return None

    def attach_texture(self, material, stage, filename):
        """Attach an image and linked parameter to the effect of the JSON representation."""
        assert( material in self.asset['materials'] )
        file_link = self.attach_image(filename)
        LOG.debug("material:%s:parameters:%s:%s", material, stage, filename)
        # Override the texture definition to redirect to this new shortcut to the image
        self.asset['materials'][material]['parameters'][stage] = file_link

    def attach_node(self, name=DEFAULT_NODE_NAME, transform=None):
        """Attach a node with a transform to the JSON representation."""
        assert(isinstance(name, NodeName))
        if not transform:
            transform = self.default_transform
        node = self.__retrieve_node(name)
        LOG.debug("nodes:%s:matrix:%s", name, transform)
        if len(transform) == 16:
            transform = vmath.m43from_m44(transform)
        if not vmath.m43is_identity(transform):
            node['matrix'] = transform

    def attach_node_shape_instance(self, name=DEFAULT_NODE_NAME,
                                   shape_instance=DEFAULT_INSTANCE_NAME,
                                   shape=DEFAULT_SHAPE_NAME,
                                   material=DEFAULT_MATERIAL_NAME,
                                   surface=None,
                                   disabled=False):
        """Attach a node connecting a shape, material and transform to the JSON representation."""
        assert(isinstance(name, NodeName))
        assert(shape in self.asset['geometries'])
        LOG.debug("nodes:%s:geometry:%s", name, shape)
        if not material in self.asset['materials']:
            LOG.info("nodes:%s:referencing missing material:%s", name, material)
        else:
            LOG.debug("nodes:%s:material:%s", name, material)
        LOG.debug("nodes:%s:disabled:%s", name, disabled)
        instance = self.__retrieve_shape_instance(name, shape_instance)
        instance['geometry'] = shape
        instance['material'] = material
        if surface is not None:
            instance['surface'] = surface
        if disabled:
            instance['disabled'] = disabled

    def attach_shape_instance_attributes(self,
                                         name=DEFAULT_NODE_NAME,
                                         shape_instance=DEFAULT_INSTANCE_NAME,
                                         attributes=None):
        """Copy the attributes onto the node."""
        assert(isinstance(name, NodeName))
        instance = self.__retrieve_shape_instance(name, shape_instance)

        if attributes:
            for k, v in attributes.iteritems():
                instance[k] = v

    def attach_shape_instance_material(self,
                                       name=DEFAULT_NODE_NAME,
                                       shape_instance=DEFAULT_INSTANCE_NAME,
                                       material=DEFAULT_MATERIAL_NAME):
        """Attach a node connecting a material to the JSON representation."""
        assert(isinstance(name, NodeName))
        if not material in self.asset['materials']:
            LOG.info("nodes:%s:referencing missing material:%s", name, material)
        else:
            LOG.debug("nodes:%s:material:%s", name, material)
        instance = self.__retrieve_shape_instance(name, shape_instance)
        instance['material'] = material

    def attach_node_light_instance(self, name=DEFAULT_NODE_NAME,
                                   light_instance=DEFAULT_INSTANCE_NAME,
                                   light=DEFAULT_LIGHT_NAME,
                                   disabled=False):
        """Attach a node connecting a light and transform to the JSON representation."""
        assert(isinstance(name, NodeName))
        assert(light in self.asset['lights'])
        LOG.debug("nodes:%s:light:%s", name, light)
        instance = self.__retrieve_light_instance(name, light_instance)
        instance['light'] = light
        if disabled:
            instance['disabled'] = disabled

    def attach_node_attributes(self, name=DEFAULT_NODE_NAME, attributes=None):
        """Copy the attributes onto the node."""
        assert(isinstance(name, NodeName))
        node = self.__retrieve_node(name)
        if attributes:
            for k, v in attributes.iteritems():
                node[k] = v

#######################################################################################################################

    def attach_area(self, name):
        """Attach an area targetting a node."""
        area = { 'target': name, 'portals': [ ] }
        if not name in self.asset['nodes']:
            LOG.warning("portal:%s:referencing missing node:%s", name, name)
        self.asset['areas'].append(area)

    def attach_area_portal(self, index, target_index, points):
        """Attach an area portal to the area. This contains a target area, a target node and the portal points."""
        ((min_x, min_y, min_z), (max_x, max_y, max_z)) = vmath.v3s_min_max(points)
        center = ( (max_x + min_x) / 2, (max_y + min_y) / 2, (max_z + min_z) / 2 )
        halfextents = ( (max_x - min_x) / 2, (max_y - min_y) / 2, (max_z - min_z) / 2 )
        portal = { 'area': target_index, 'points': points, 'center': center, 'halfExtents': halfextents }
        self.asset['areas'][index]['portals'].append(portal)

    def attach_bsp_tree_node(self, plane, pos, neg):
        """Attach a bsp tree node."""
        node = { 'plane':plane, 'pos':pos, 'neg':neg }
        self.asset['bspnodes'].append(node)

    def retrieve_light(self, name):
        """Return a reference to a light."""
        if 'lights' in self.asset and name in self.asset['lights']:
            return self.asset['lights'][name]
        return None

    def attach_light(self, name=DEFAULT_LIGHT_NAME, raw=None):
        """Attach a light to the JSON representation."""
        self.asset['lights'][name] = raw

#######################################################################################################################

    def attach_entity_definition(self, name=DEFAULT_ENTITY_DEFINITION_NAME, attributes=None):
        """Attach an entity definition to the JSON representation."""
        if not attributes:
            attributes = { }
        self.asset['entitydefinitions'][name] = attributes

    def attach_model_definition(self, name=DEFAULT_MODEL_DEFINITION_NAME, attributes=None):
        """Attach an model definition to the JSON representation."""
        if not attributes:
            attributes = { }
        self.asset['modeldefinitions'][name] = attributes

    def attach_entity(self, name=DEFAULT_ENTITY_NAME, attributes=None):
        """Attach an entity to the JSON representation."""
        if not attributes:
            attributes = { }
        self.asset['entities'][name] = attributes

    def attach_skin(self, name=DEFAULT_SKIN_NAME, attributes=None):
        """Attach a skin to the JSON representation."""
        if not attributes:
            attributes = { }
        self.asset['skins'][name] = attributes

    def retrieve_skins(self):
        """Return all the skins."""
        return self.asset.get('skins', { })

    def retrieve_skin(self, name=DEFAULT_SKIN_NAME):
        """Return a reference to a skin."""
        skins = self.retrieve_skins()
        if name in skins:
            skin = skins[name]
        else:
            skin = { }
        return skin

#######################################################################################################################

    def attach_animation(self, name=DEFAULT_ANIMATION_NAME, animation=None):
        """Attach an animation to the JSON representation."""
        self.asset['animations'][name] = animation

    def attach_camera_animation(self, name=DEFAULT_ANIMATION_NAME, animation=None):
        """Attach a camera animation to the JSON representation."""
        self.asset['camera_animations'][name] = animation

#######################################################################################################################

    def attach_sound(self, name=DEFAULT_SOUND_NAME, sound=None):
        """Attach a sound to the JSON representation."""
        self.asset['sounds'][name] = sound

    def attach_proceduraleffect(self, name=DEFAULT_PROCEDURALEFFECT_NAME, proceduraleffect=None):
        """Attach a proceduraleffect to the JSON representation."""
        self.asset['proceduraleffects'][name] = proceduraleffect

#######################################################################################################################

    def attach_physics_material(self, physics_material_name=DEFAULT_PHYSICS_MATERIAL_NAME,
                                      physics_material=None):
        self.asset['physicsmaterials'][physics_material_name] = physics_material

    def attach_physics_model(self, physics_model=DEFAULT_PHYSICS_MODEL_NAME,
                                   shape_name=DEFAULT_SHAPE_NAME, model=None, material=None,
                                   shape_type="mesh"):
        """Attach a physics model to the JSON representation."""
        if model is None:
            model = { 'type': "rigid",
                      'shape': shape_type,
                      'geometry': shape_name }
        if material:
            model['material'] = material
        self.asset['physicsmodels'][physics_model] = model

    def attach_physics_node(self, physics_node_name=DEFAULT_PHYSICS_NODE_NAME,
                                  physics_model=DEFAULT_PHYSICS_MODEL_NAME,
                                  node_name=DEFAULT_NODE_NAME,
                                  inline_parameters=None):
        """Attach a physics node to the JSON representation."""
        assert(isinstance(node_name, NodeName))
        physics_node = { 'body': physics_model, 'target': str(node_name) }
        if inline_parameters is not None:
            for k, v in inline_parameters.iteritems():
                physics_node[k] = v
        self.asset['physicsnodes'][physics_node_name] = physics_node

#######################################################################################################################

    def attach_strings(self, name, strings):
        """Attach a named string table."""
        self.asset['strings'][name] = strings

    def attach_guis(self, name, gui):
        """Attach a named window."""
        if name not in self.asset['guis']:
            self.asset['guis'][name] = [ ]
        self.asset['guis'][name].append(gui)

    def attach_table(self, name, table):
        """Attach a table."""
        self.asset['tables'][name] = table

    def retrieve_table(self, name):
        """Retrieve a reference to a table."""
        return self.asset['tables'][name]

    def attach_application(self, name=DEFAULT_APPLICATION_NAME, options=None):
        """Attach options for an application."""
        if options is None:
            options = { }
        self.asset['applications'][name] = options
# pylint: enable=R0904

########NEW FILE########
__FILENAME__ = bmfont2json
#!/usr/bin/python
# Copyright (c) 2011-2013 Turbulenz Limited
"""
Convert Bitmap Font Generator data (.fnt) files into a Turbulenz JSON asset.
http://www.angelcode.com/products/bmfont/
"""

import re
import sys
import logging

from optparse import OptionParser, OptionGroup, TitledHelpFormatter

# pylint: disable=W0403
from stdtool import standard_output_version, standard_json_out
from asset2json import JsonAsset
# pylint: enable=W0403

__version__ = '2.0.0'
__dependencies__ = ['asset2json']


LOG = logging.getLogger('asset')


#######################################################################################################################

class Bmfont2json(object):
    """Parse a .fnt file and generate a Turbulenz JSON geometry asset."""

    bold_re = re.compile(r'bold=(\d+)')
    italic_re = re.compile(r'italic=(\d+)')
    page_width_re = re.compile(r'scaleW=(\d+)')
    page_height_re = re.compile(r'scaleH=(\d+)')
    line_height_re = re.compile(r'lineHeight=(\d+)')
    base_re = re.compile(r'base=(\d+)')
    num_pages_re = re.compile(r'pages=(\d+)')
    page_re = re.compile(r'page\s+id=(\d+)\s+file="(\S+)"')
    num_chars_re = re.compile(r'chars\s+count=(\d+)')
    num_kernings_re = re.compile(r'kernings\s+count=(\d+)')
    kerning_re = re.compile(r'kerning\s+first=(\d+)\s+second=(\d+)\s+amount=([-+]?\d+)')
    # pylint: disable=C0301
    char_re = re.compile(r'char\s+id=(\d+)\s+x=(\d+)\s+y=(\d+)\s+width=(\d+)\s+height=(\d+)\s+xoffset=([-+]?\d+)\s+yoffset=([-+]?\d+)\s+xadvance=([-+]?\d+)\s+page=(\d+)')
    # pylint: enable=C0301

    def __init__(self, texture_prefix):
        self.bold = 0
        self.italic = 0
        self.glyphs = { }
        self.page_width = 0
        self.page_height = 0
        self.baseline = 0
        self.line_height = 0
        self.num_glyphs = 0
        self.min_glyph_index = 256
        self.texture_pages = []
        self.kernings = { }
        self.texture_prefix = texture_prefix

    def __read_page(self, line):
        found = self.page_re.match(line)
        if not found:
            raise Exception('Page information espected, found: ' + line)

        page_index = int(found.group(1))
        page_file = self.texture_prefix + found.group(2)
        self.texture_pages[page_index] = page_file

        LOG.info("texture page: %s", page_file)

    def __read_char(self, line):
        """Parse one glyph descriptor."""
        found = self.char_re.match(line)
        if not found:
            raise Exception('Char information espected, found: ' + line)

        i = int(found.group(1))
        x = float(found.group(2))
        y = float(found.group(3))
        width = int(found.group(4))
        height = int(found.group(5))
        xoffset = int(found.group(6))
        yoffset = int(found.group(7))
        xadvance = int(found.group(8))
        page = int(found.group(9))

        self.glyphs[i] = {
            'width': width,
            'height': height,
            'awidth': xadvance,
            'xoffset': xoffset,
            'yoffset': yoffset,
            'left': x / self.page_width,
            'top': y / self.page_height,
            'right': (x + width) / self.page_width,
            'bottom': (y + height) / self.page_height,
            'page': page
        }

        if self.min_glyph_index > i:
            self.min_glyph_index = i

    def __read_kerning(self, line):
        """Parse one kerning descriptor."""
        found = self.kerning_re.match(line)
        if not found:
            raise Exception('Kerning information espected, found: ' + line)

        first = int(found.group(1))
        second = int(found.group(2))
        amount = int(found.group(3))

        kerning = self.kernings.get(first, None)
        if kerning is None:
            self.kernings[first] = {second: amount}
        else:
            kerning[second] = amount

#######################################################################################################################

    def parse(self, f):
        """Parse a .fnt file stream."""

        line = f.readline()
        line = line.strip()

        if line.startswith('info '):
            found = self.bold_re.search(line)
            if found:
                self.bold = int(found.group(1))

            found = self.italic_re.search(line)
            if found:
                self.italic = int(found.group(1))

            LOG.info("bold: %d", self.bold)
            LOG.info("italic: %d", self.italic)

            line = f.readline()
            line = line.strip()

        # Common
        if not line.startswith('common '):
            raise Exception('Common information espected, found: ' + line)

        found = self.page_width_re.search(line)
        if not found:
            raise Exception('ScaleW espected, found: ' + line)

        self.page_width = int(found.group(1))

        LOG.info("page width: %d", self.page_width)

        found = self.page_height_re.search(line)
        if not found:
            raise Exception('ScaleH espected, found: ' + line)

        self.page_height = int(found.group(1))

        LOG.info("page height: %d", self.page_height)

        found = self.line_height_re.search(line)
        if not found:
            raise Exception('Line Height espected, found: ' + line)

        self.line_height = int(found.group(1))

        LOG.info("line height: %d", self.line_height)

        found = self.base_re.search(line)
        if not found:
            raise Exception('Base espected, found: ' + line)

        self.baseline = int(found.group(1))

        LOG.info("baseline: %d", self.baseline)

        found = self.num_pages_re.search(line)
        if not found:
            raise Exception('Num pages espected, found: ' + line)

        num_pages = int(found.group(1))
        self.texture_pages = [None] * num_pages

        LOG.info("num texture pages: %d", num_pages)

        # Pages
        line = f.readline()
        line = line.strip()
        while line.startswith('page'):
            self.__read_page(line)
            line = f.readline()
            line = line.strip()

        found = self.num_chars_re.search(line)
        if not found:
            raise Exception('Chars count espected, found: ' + line)

        self.num_glyphs = int(found.group(1))
        if self.num_glyphs <= 0:
            raise Exception('No glyphs found!')

        LOG.info("num glyphs: %d", self.num_glyphs)

        line = f.readline()
        line = line.strip()
        while line.startswith('char'):
            self.__read_char(line)
            line = f.readline()
            line = line.strip()

        # Kernings
        found = self.num_kernings_re.search(line)
        if found:
            num_kernings = int(found.group(1))
            if num_kernings > 0:
                line = f.readline()
                line = line.strip()
                while line.startswith('kerning'):
                    self.__read_kerning(line)
                    line = f.readline()
                    line = line.strip()
        else:
            num_kernings = 0

        LOG.info("num kernings: %d", num_kernings)


    def get_definitions(self, filename):
        """Return a fixed asset object."""
        filename = filename.replace('\\', '/')
        asset = {
            'version': 1,
            'bitmapfontlayouts' : {
                filename: {
                    'pagewidth': self.page_width,
                    'pageheight': self.page_height,
                    'baseline': self.baseline,
                    'lineheight': self.line_height,
                    'numglyphs': self.num_glyphs,
                    'minglyphindex': self.min_glyph_index,
                    'glyphs': self.glyphs,
                    'pages': self.texture_pages
                }
            }
        }
        if self.kernings:
            asset['bitmapfontlayouts'][filename]['kernings'] = self.kernings
        if self.bold:
            asset['bitmapfontlayouts'][filename]['bold'] = True
        if self.italic:
            asset['bitmapfontlayouts'][filename]['italic'] = True
        return asset


#######################################################################################################################

def bmfont2json_parser(description, epilog=None):
    """Standard set of parser options."""
    parser = OptionParser(description=description, epilog=epilog,
                          formatter=TitledHelpFormatter())

    parser.add_option("--version", action="store_true", dest="output_version", default=False,
                      help="output version number")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="verbose outout")
    parser.add_option("-s", "--silent", action="store_true", dest="silent", default=False, help="silent running")
    parser.add_option("-m", "--metrics", action="store_true", dest="metrics", default=False,
                      help="output asset metrics")
    parser.add_option("--log", action="store", dest="output_log", default=None, help="write log to file")

    group = OptionGroup(parser, "Asset Generation Options")
    group.add_option("-j", "--json_indent", action="store", dest="json_indent", type="int", default=0, metavar="SIZE",
                     help="json output pretty printing indent size, defaults to 0")
    parser.add_option_group(group)

    group = OptionGroup(parser, "Asset Location Options")
    group.add_option("-p", "--prefix", action="store", dest="texture_prefix", default="textures/", metavar="URL",
                     help="texture URL to prefix to all texture references")
    group.add_option("-a", "--assets", action="store", dest="asset_root", default=".", metavar="PATH",
                     help="PATH of the asset root")
    parser.add_option_group(group)

    group = OptionGroup(parser, "File Options")
    group.add_option("-i", "--input", action="store", dest="input", default=None, metavar="FILE",
                     help="source FILE to process")
    group.add_option("-o", "--output", action="store", dest="output", default="default.json", metavar="FILE",
                     help="output FILE to write to")
    parser.add_option_group(group)

    return parser

def parse(input_filename="default.fontdat", output_filename="default.json", texture_prefix="", asset_root=".",
          options=None):
    """Untility function to convert an .fnt file into a JSON file."""
    with open(input_filename, 'rb') as source:
        asset = Bmfont2json(texture_prefix)
        try:
            asset.parse(source)
            asset_name = input_filename
            if input_filename.startswith(asset_root):
                asset_name = asset_name[(len(asset_root) + 1):-8]
            json_asset = JsonAsset(definitions=asset.get_definitions(asset_name))
            standard_json_out(json_asset, output_filename, options)
            return json_asset
        # pylint: disable=W0703
        except Exception as e:
            LOG.error(str(e))
        # pylint: enable=W0703

def main():
    description = ("Convert Bitmap Font Generator data (.fnt) files into a Turbulenz JSON asset.\n" +
                   "http://www.angelcode.com/products/bmfont/")

    parser = bmfont2json_parser(description)

    (options, args_) = parser.parse_args()

    if options.output_version:
        standard_output_version(__version__, __dependencies__, options.output)
        return

    if options.input is None:
        parser.print_help()
        return

    if options.silent:
        level = logging.CRITICAL
    elif options.verbose or options.metrics:
        level = logging.INFO
    else:
        level = logging.WARNING
    logging.basicConfig(level=level, stream=sys.stdout)

    LOG.info("input: %s", options.input)
    LOG.info("output: %s", options.output)

    if options.texture_prefix != '':
        options.texture_prefix = options.texture_prefix.replace('\\', '/')
        if options.texture_prefix[-1] != '/':
            options.texture_prefix = options.texture_prefix + '/'
        LOG.info("texture URL prefix: %s", options.texture_prefix)

    if options.asset_root != '.':
        LOG.info("root: %s", options.asset_root)

    parse(options.input,
          options.output,
          options.texture_prefix,
          options.asset_root,
          options)

if __name__ == "__main__":
    exit(main())

########NEW FILE########
__FILENAME__ = dae2json
#!/usr/bin/python
# Copyright (c) 2010-2013 Turbulenz Limited
"""
Convert Collada (.dae) files into a Turbulenz JSON asset.
"""

# pylint: disable=C0302
# C0302 - Too many lines in module

import logging
LOG = logging.getLogger('asset')

# pylint: disable=W0404
try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    from xml.etree import ElementTree
# pylint: enable=W0404

from xml.parsers.expat import ExpatError

# pylint: disable=W0403
import sys
import math
import vmath
import subprocess

from stdtool import standard_parser, standard_main, standard_include, standard_json_out
from asset2json import JsonAsset, attach_skins_and_materials, remove_unreferenced_images

from node import NodeName
from mesh import Mesh
# pylint: enable=W0403

__version__ = '1.7.2'
__dependencies__ = ['asset2json', 'node', 'mesh']

def tag(t):
    return str(ElementTree.QName('http://www.collada.org/2005/11/COLLADASchema', t))

def untag(t):
    return t[len('{http://www.collada.org/2005/11/COLLADASchema}'):]

def pack(a, n):
    # Special case components of width 1
    if n == 1:
        return a[:]
    return [ tuple(a[i:i + n]) for i in range(0, len(a), n) ]

def _remove_prefix(line, prefix):
    if line.startswith(prefix):
        return line[len(prefix):]
    return line

#######################################################################################################################

def fix_sid(e, parent_id):
    e_id = e.get('id')
    if e_id:
        parent_id = e_id
    else:
        e_id = e.get('sid')
        if e_id:
            if parent_id:
                e_id = "%s/%s" % (parent_id, e_id)
            else:
                parent_id = e_id
            e.set('id', e_id)
    for child in e:
        fix_sid(child, parent_id)

def find_scoped_name(e_id, parent_id, name_map):
    name = name_map.get(e_id) or (parent_id and name_map.get("%s/%s" % (parent_id, e_id)))
    if name:
        return name
    return e_id

def find_scoped_node(e_id, parent_id, node_map):
    node = node_map.get(e_id) or (parent_id and node_map.get("%s/%s" % (parent_id, e_id)))
    if node:
        return node
    return None

def tidy_name(n, default=None, prefix=None):
    if n is None:
        return default
    if n is not None and n[0] == '#':
        n = n[1:]
    if prefix is not None:
        n = _remove_prefix(n, prefix)
        if n[0] == '-' or n[0] == '_':
            n = n[1:]

    return n

def tidy_value(value_text, value_type):
    if value_type == 'float':
        result = float(value_text)
    elif value_type == 'int':
        result = int(value_text)
    elif value_type == 'bool':
        value_bool = value_text.lower()
        if value_bool == 'true':
            result = True
        else:
            result = False
    elif value_type == 'color':
        result = [ float(x) for x in value_text.split() ]
    elif value_type.startswith('float'):
        result = [ float(x) for x in value_text.split() ]
    else:
        result = value_text.split()

    return result

REMAPPED_SEMANTICS = {
    'BITANGENT': 'BINORMAL',
    'BLEND_WEIGHT': 'BLENDWEIGHT',
    'INV_BIND_MATRIX': 'BLENDINDICES',
    'TEXBINORMAL': 'BINORMAL',
    'TEXTANGENT': 'TANGENT',
    'UV': 'TEXCOORD',
    'VERTEX': 'POSITION',
    'WEIGHT': 'BLENDWEIGHT'
}

def tidy_semantic(s, semantic_set=None):
    # Current runtime supported semantics are in src/semantic.h         #
    # ================================================================= #
    # 0  - ATTR0,               POSITION0,       POSITION               #
    # 1  - ATTR1,               BLENDWEIGHT0,    BLENDWEIGHT            #
    # 2  - ATTR2,               NORMAL0,         NORMAL                 #
    # 3  - ATTR3,               COLOR0,          COLOR                  #
    # 4  - ATTR4,               COLOR1,          SPECULAR               #
    # 5  - ATTR5,                                FOGCOORD, TESSFACTOR   #
    # 6  - ATTR6,               PSIZE0,          PSIZE                  #
    # 7  - ATTR7,               BLENDINDICES0,   BLENDINDICES           #
    # 8  - ATTR8,   TEXCOORD0,                   TEXCOORD               #
    # 9  - ATTR9,   TEXCOORD1                                           #
    # 10 - ATTR10,  TEXCOORD2                                           #
    # 11 - ATTR11,  TEXCOORD3                                           #
    # 12 - ATTR12,  TEXCOORD4                                           #
    # 13 - ATTR13,  TEXCOORD5                                           #
    # 14 - ATTR14,  TEXCOORD6,  TANGENT0,         TANGENT               #
    # 15 - ATTR15,  TEXCOORD7,  BINORMAL0,        BINORMAL              #
    # ================================================================= #
    # If the semantic isn't remapped just return it.
    semantic = REMAPPED_SEMANTICS.get(s, s)
    if semantic_set is not None:
        if semantic_set == '0' and semantic != 'TEXCOORD' and semantic != 'COLOR':
            pass
        elif semantic == 'TANGENT' or semantic == 'BINORMAL':
            pass
        else:
            semantic = semantic + semantic_set
    return semantic

def find_semantic(source_name, mesh_node_e):

    def _test_source(tags):
        if tags:
            for v_e in tags:
                for i in v_e.findall(tag('input')):
                    source = tidy_name(i.get('source'))
                    if (source is not None) and (source == source_name):
                        return tidy_semantic(i.get('semantic'), i.get('set'))
        return None

    semantic = _test_source(mesh_node_e.findall(tag('vertices')))
    if semantic is not None:
        return semantic

    semantic = _test_source(mesh_node_e.findall(tag('triangles')))
    if semantic is not None:
        return semantic

    semantic = _test_source(mesh_node_e.findall(tag('polylist')))
    if semantic is not None:
        return semantic

    semantic = _test_source(mesh_node_e.findall(tag('polygons')))
    if semantic is not None:
        return semantic

    return None

def invert_indices(indices, indices_per_vertex, vertex_per_polygon):
    # If indices_per_vertex = 3 and vertex_per_polygon = 3
    # [ 1, 2, 3, 4, 5, 6, 7, 8, 9 ] -> [ [7, 8, 9], [4, 5, 6], [1, 2, 3] ]
    vertex_indices = pack(indices, indices_per_vertex)
    if vertex_per_polygon == 2:
        polygon_indices = zip(vertex_indices[1::2], vertex_indices[::2])
    elif vertex_per_polygon == 3:
        polygon_indices = zip(vertex_indices[1::3], vertex_indices[2::3], vertex_indices[::3])
    elif vertex_per_polygon == 4:
        polygon_indices = zip(vertex_indices[1::4], vertex_indices[2::4], vertex_indices[3::4], vertex_indices[::4])
    else:
        LOG.error('Vertex per polygon unsupported:%i', vertex_per_polygon)

    return polygon_indices

def get_material_name(instance_e):
    bind_e = instance_e.find(tag('bind_material'))
    if bind_e is not None:
        technique_e = bind_e.find(tag('technique_common'))
        if technique_e is not None:
            material_e = technique_e.find(tag('instance_material'))
            if material_e is not None:
                return material_e.get('target')
    return None

def find_controller(source_name, controllers_e):
    for controller_e in controllers_e.findall(tag('controller')):
        controller_name = tidy_name(controller_e.get('id', controller_e.get('name')))
        if controller_name == source_name:
            return controller_e
    return None

def find_set_param(effect_e, name):
    for set_param_e in effect_e.findall(tag('setparam')):
        ref = set_param_e.get('ref')
        if ref is not None and ref == name:
            return set_param_e
    return None

def find_new_param(profile_e, name):
    for new_param_e in profile_e.findall(tag('newparam')):
        sid = new_param_e.get('sid')
        if sid is not None and sid == name:
            return new_param_e
    return None

def find_node(url, collada_e):
    # This might be better as an XPath of '//*[@id='url'] but the version of ElementTree in python
    # doesn't support attribute selection

    # Remove the # from the url
    if url is not None and url[0] == '#':
        node_id = url[1:]
    else:
        node_id = url
    # Find all nodes in the scene and look for the one with a matching id
    node_iterator = collada_e.getiterator(tag('node'))
    for node_e in node_iterator:
        if node_e.attrib.get('id') == node_id:
            return node_e
    return None

def find_name(name_map, id_name):
    if id_name in name_map:
        return name_map[id_name]
    return id_name


class UrlHandler(object):
    def __init__(self, asset_root, asset_path):
        if asset_root[-1] != '/':
            self.root = asset_root + '/'
        else:
            self.root = asset_root
        self.path = asset_path[:asset_path.rfind('/')]

    def tidy(self, u):
        u = _remove_prefix(u, 'file://')
        u = _remove_prefix(u, 'http://')
        u = _remove_prefix(u, '/')
        if u.startswith('./'):
            u = self.path + u[1:]
        if u.startswith('../'):
            path_index = -1
            u_index = 0
            while u.startswith('../', u_index):
                path_index = self.path.rfind('/', 0, path_index)
                if path_index == -1:
                    LOG.error('Unknown relative path:%s', u)
                    break
                u_index += 3
            u = self.path[:(path_index + 1)] + u[u_index:]
        u = _remove_prefix(u, self.root)
        if u[1] == ':' and u[2] == '/':
            u = u[3:]
        return u


#######################################################################################################################

def build_joint_hierarchy(start_joints, nodes, sid_inputs = False):

    def __find_node(node_name, node, use_sid):
        if use_sid:
            if node_name == node.sid:
                return node
        else:
            if node_name == node.id:
                return node
        for child in node.children:
            result = __find_node(node_name, child, use_sid)
            if result is not None:
                return result
        return None

    def __add_joint_hierarchy(node, parent_index, joints, joint_to_node_map):
        node_index = len(joints)
        if node in joint_to_node_map:
            orig_index = joint_to_node_map.index(node)
        else:
            orig_index = -1
        joints.append( { 'node':node, 'parent': parent_index, 'orig_index': orig_index } )
        for child in node.children:
            __add_joint_hierarchy(child, node_index, joints, joint_to_node_map)

    # Work out all the root nodes parenting any start joints
    hierarchies_affected = []
    joint_to_node_map = [ None ] * len(start_joints)
    for j, node_name in enumerate(start_joints):
        for root_name in nodes:
            node = __find_node(node_name, nodes[root_name], sid_inputs)
            if node is not None:
                joint_to_node_map[j] = node
                if not root_name in hierarchies_affected:
                    hierarchies_affected.append(root_name)

    # Given the hierarchy roots affected we need to build a hierarchical description
    hierarchy = []
    for n in range(0, len(hierarchies_affected)):
        __add_joint_hierarchy(nodes[hierarchies_affected[n]], -1, hierarchy, joint_to_node_map)

    return hierarchy

#######################################################################################################################

class Dae2Geometry(object):

    class Source(object):
        def __init__(self, values, semantic, name='unknown', stride=0, count=0):
            self.values = values
            self.semantic = semantic
            self.name = name
            self.stride = stride
            self.count = count
            self.zero_value = tuple([0] * stride)
            LOG.debug('SOURCE:%s:semantic:%s:stride:%i:count:%i', name, semantic, stride, count)

        def __repr__(self):
            return 'Dae2Geometry.Source<name:%s:semantic:%s:stride:%s:count:%s>' % \
                (self.name, self.semantic, self.stride, self.count)

    class Input(object):
        def __init__(self, semantic, source='unknown', offset=0):
            self.semantic = semantic
            self.source = source
            self.offset = offset
            LOG.debug('INPUT::source:%s:semantic:%s:offset:%i', source, semantic, offset)

        def __repr__(self):
            return 'Dae2Geometry.Input<semantic:%s:source:%s:offset:%s>' % (self.semantic, self.source, self.offset)

    class Surface(object):
        def __init__(self, sources, primitives, primitive_type):
            self.sources = sources
            self.primitives = primitives
            self.type = primitive_type

    def add_input(self, faces_e, shared_sources):
        # Offset N vertex inputs
        max_offset = 0
        sources = shared_sources.copy()
        if faces_e is not None:
            input_e = faces_e.findall(tag('input'))
            for i in input_e:
                semantic = i.get('semantic')
                if semantic != 'VERTEX': # These inputs are all ready pulled from the vertex_inputs
                    semantic = tidy_semantic(semantic, i.get('set'))
                    source = tidy_name(i.get('source'), prefix=self.id)
                    offset = int(i.get('offset', '0'))
                    old_input = self.inputs.get(semantic, None)
                    if old_input:
                        if old_input.source != source or old_input.offset != offset:
                            LOG.error('SEMANTIC "%s" used with different sources (%s:%d) != (%s:%d)',
                                      semantic, source, offset, old_input.source, old_input.offset)
                    else:
                        self.inputs[semantic] = Dae2Geometry.Input(semantic, source, offset)
                    if max_offset < offset:
                        max_offset = offset
                    sources.add(source)

        return max_offset, sources

    # pylint: disable=R0914
    def __init__(self, geometry_e, scale, library_geometries_e, name_map, geometry_names):
        self.name = None
        self.scale = scale
        self.sources = { }
        self.inputs = { }
        self.surfaces = { }
        self.meta = { }
        self.type = 'unknown'

        # Name...
        self.id = geometry_e.get('id', 'unknown')
        self.name = geometry_e.get('name', self.id)
        LOG.debug('GEOMETRY:%s', self.name)
        if self.name in geometry_names:
            LOG.warning('GEOMETRY name clash:%s:replacing with:%s', self.name, self.id)
            geometry_names[self.id] = self.name
            self.name = self.id
        else:
            geometry_names[self.name] = self.name

        name_map[self.id] = self.name

        # Mesh...
        mesh_e = geometry_e.find(tag('mesh'))
        if mesh_e is not None:
            self.type = 'mesh'
        else:
            # !!! Handle 'convex_mesh' correctly
            convex_mesh_e = geometry_e.find(tag('convex_mesh'))
            if convex_mesh_e is not None:
                reference_name = tidy_name(convex_mesh_e.get('convex_hull_of'))

                for reference_node_e in library_geometries_e.findall(tag('geometry')):
                    if reference_node_e.get('id') == reference_name:
                        mesh_e = reference_node_e.find(tag('mesh'))
                        self.type = 'convex_mesh'
                        break

                if mesh_e is None:
                    LOG.error('Unknown reference node:%s', reference_name)
                    return

            if geometry_e.find(tag('spline')):
                LOG.warning('Skipping spline based mesh:%s', self.name)
                self.type = 'spline'
                return

            if mesh_e is None:
                LOG.error('Unknown geometry type:%s', self.name)
                return


        # Sources...
        geometry_source_names = { }
        source_e = mesh_e.findall(tag('source'))
        for s in source_e:
            source_id = s.get('id', 'unknown')
            name = s.get('name', source_id)
            if name in geometry_source_names:
                LOG.warning('SOURCE name clash:%s:replacing with id:%s', name, source_id)
                geometry_source_names[source_id] = name
                name = source_id
            else:
                geometry_source_names[name] = name
            semantic = find_semantic(source_id, mesh_e)
            # We tidy the id after finding the semantic from the sources
            source_id = tidy_name(source_id, prefix=self.id)
            if semantic is not None:
                technique_e = s.find(tag('technique_common'))
                accessor_e = technique_e.find(tag('accessor'))
                stride = int(accessor_e.get('stride', '1'))
                array_e = s.find(tag('float_array'))
                count = int(array_e.get('count', '0'))
                if (0 < count) and (0 < stride):
                    values_text = array_e.text
                    values = [float(x) for x in values_text.split()]
                    if (semantic == 'POSITION') and (scale != 1.0):
                        values = [scale * x for x in values]

                    values = pack(values, stride)
                else:
                    values = None
                self.sources[source_id] = Dae2Geometry.Source(values, semantic, name, stride, count)
            else:
                LOG.warning('SOURCE (unusued):%s:semantic:%s', source_id, semantic)

        # Inputs...
        shared_sources = set()
        vertices_e = mesh_e.find(tag('vertices'))
        if vertices_e is not None:
            for i in vertices_e.findall(tag('input')):
                semantic = tidy_semantic(i.get('semantic'), i.get('set'))
                source = tidy_name(i.get('source'), prefix=self.id)
                # Offset 0 vertex inputs
                self.inputs[semantic] = Dae2Geometry.Input(semantic, source)
                shared_sources.add(source)

        # Mesh can contain:
        #
        # lines         - untested
        # linestrips
        # polygons      - supported (quads [replaced by triangles])
        # polylist      - supported
        # spline
        # triangles     - supported
        # trifans
        # tristrips

        # Triangles...
        for triangles_e in mesh_e.findall(tag('triangles')):
            max_offset, sources = self.add_input(triangles_e, shared_sources)
            if len(triangles_e) == 0:
                LOG.warning('GEOMETRY with no faces:%s', self.name)
                continue
            indices_per_vertex = max_offset + 1
            num_faces = int(triangles_e.get('count', '0'))
            material = triangles_e.get('material')

            indices_e = triangles_e.find(tag('p'))
            if indices_e is not None:
                indices = [int(x) for x in indices_e.text.split()]
                assert(3 * num_faces * indices_per_vertex == len(indices))
                indices = invert_indices(indices, indices_per_vertex, 3)
                self.surfaces[material] = Dae2Geometry.Surface(sources, indices, JsonAsset.SurfaceTriangles)

        # Polylist...
        for polylist_e in mesh_e.findall(tag('polylist')):
            max_offset, sources = self.add_input(polylist_e, shared_sources)
            if len(polylist_e) == 0:
                LOG.warning('GEOMETRY with no faces:%s', self.name)
                continue
            indices_per_vertex = max_offset + 1
            num_faces = int(polylist_e.get('count', '0'))
            material = polylist_e.get('material')

            indices_e = polylist_e.find(tag('p'))
            vertex_count_e = polylist_e.find(tag('vcount'))
            if vertex_count_e is not None:
                vertex_count = [int(x) for x in vertex_count_e.text.split()]
                assert(num_faces == len(vertex_count))

                indices = [int(x) for x in indices_e.text.split()]

                # Add everything as triangles.
                index = 0
                new_indices = [ ]
                for vcount in vertex_count:
                    face_indices = pack(indices[index:index + vcount * indices_per_vertex], indices_per_vertex)
                    index += vcount * indices_per_vertex
                    for t in range(2, vcount):
                        new_indices.append( (face_indices[0], face_indices[t-1], face_indices[t]) )
                self.surfaces[material] = Dae2Geometry.Surface(sources, new_indices, JsonAsset.SurfaceTriangles)

        # Lines...
        for lines_e in mesh_e.findall(tag('lines')):
            max_offset, sources = self.add_input(lines_e, shared_sources)
            if len(lines_e) == 0:
                LOG.warning('GEOMETRY with no faces:%s', self.name)
                continue
            indices_per_vertex = max_offset + 1
            num_faces = int(lines_e.get('count', '0'))
            material = lines_e.get('material')

            indices_e = lines_e.find(tag('p'))
            indices = [int(x) for x in indices_e.text.split()]
            indices = invert_indices(indices, indices_per_vertex, 2)
            self.surfaces[material] = Dae2Geometry.Surface(sources, indices, JsonAsset.SurfaceLines)

        # Polygons...
        for polygons_e in mesh_e.findall(tag('polygons')):
            max_offset, sources = self.add_input(polygons_e, shared_sources)
            if len(polygons_e) == 0:
                LOG.warning('GEOMETRY with no faces:%s', self.name)
                continue
            indices_per_vertex = max_offset + 1
            num_faces = int(polygons_e.get('count', '0'))
            material = polygons_e.get('material')

            indices = [ ]
            for p_e in polygons_e.findall(tag('p')):
                face_indices = pack([int(x) for x in p_e.text.split()], indices_per_vertex)
                vcount = len(face_indices)
                for t in range(2, vcount):
                    indices.append( (face_indices[0], face_indices[t-1], face_indices[t]) )

            if polygons_e.find(tag('ph')):
                LOG.warning('GEOMETRY using polygons with holes, please triangulate when exporting:%s.', self.name)

            if 0 < len(indices):
                self.surfaces[material] = Dae2Geometry.Surface(sources, indices, JsonAsset.SurfaceTriangles)
            else:
                LOG.warning('GEOMETRY without valid primitives:%s.', self.name)
    # pylint: enable=R0914

    # pylint: disable=R0914
    def process(self, definitions_asset, nodes, nvtristrip, materials, effects):
        # Look at the material to check for geometry requirements
        need_normals = False
        need_tangents = False
        generate_normals = False
        generate_tangents = False

        # Assumed to be a graphics geometry
        is_graphics_geometry = True

        if is_graphics_geometry:
            LOG.info('"%s" is assumed to be a graphics geometry. ' \
                     'Check referencing node for physics properties otherwise', self.name)
            self.meta['graphics'] = True

        for mat_name in self.surfaces.iterkeys():
            # Ok, we have a mat_name but this may need to be mapped if the node has an instanced material.
            # So we find the node referencing this geometry, and see if the material has a mapping on it.
            def _find_material_from_instance_on_node(n):
                for instance in n.instance_geometry:
                    if instance.geometry == self.id:
                        for surface, material in instance.materials.iteritems():
                            if surface == mat_name:
                                return material
                for child in n.children:
                    material = _find_material_from_instance_on_node(child)
                    if material is not None:
                        return material
                return None

            for _, node in nodes.iteritems():
                instance_mat_name = _find_material_from_instance_on_node(node)
                if instance_mat_name is not None:
                    LOG.debug('Using instance material:%s to %s', mat_name, instance_mat_name)
                    mat_name = instance_mat_name
                    break

            if mat_name is None:
                mat_name = 'default'

            effect_name = None
            meta = { }

            material = definitions_asset.retrieve_material(mat_name, False)
            if material is not None:
                effect_name = material.get('effect', None)
                if 'meta' in material:
                    meta.update(material['meta'])
            else:
                material = materials.get(mat_name, None)
                if material is not None:
                    effect_name = material.effect_name
                    # Dae2Material has no meta data, everything is on Dae2Effect
                else:
                    continue

            if effect_name is not None:
                effect = definitions_asset.retrieve_effect(effect_name)
                if effect is not None:
                    if 'meta' in effect:
                        meta.update(effect['meta'])
                else:
                    effect = effects.get(effect_name, None)
                    if effect is not None and effect.meta is not None:
                        meta.update(effect.meta)

            if meta.get('normals', False) is True:
                need_normals = True

            if meta.get('tangents', False) is True:
                need_tangents = True

            if meta.get('generate_normals', False) is True:
                generate_normals = True

            if meta.get('generate_tangents', False) is True:
                generate_tangents = True
                break

        if need_normals and 'NORMAL' not in self.inputs:
            generate_normals = True

        if need_tangents and 'TANGENT' not in self.inputs and 'BINORMAL' not in self.inputs:
            generate_tangents = True

        if generate_normals is False and generate_tangents is False and nvtristrip is None:
            return

        # Generate a single vertex pool.
        new_sources = { }
        old_semantics = { }
        old_offsets = { }

        has_uvs = False
        for semantic, input_stream in self.inputs.iteritems():
            new_sources[input_stream.source] = [ ]
            old_offsets[input_stream.source] = input_stream.offset
            old_semantics[semantic] = True
            if semantic == 'TEXCOORD' or semantic == 'TEXCOORD0':
                has_uvs = True

        if generate_tangents:
            if has_uvs is False:
                LOG.warning('Material "%s" requires tangents but geometry "%s" has no UVs', mat_name, self.name)
                return

        for mat_name, surface in self.surfaces.iteritems():
            if surface.type == JsonAsset.SurfaceTriangles:
                if generate_tangents:
                    LOG.info('Process:generate_tangents:geometry:%s:surface:%s', self.name, mat_name)
                elif generate_normals:
                    LOG.info('Process:generate_normals:geometry:%s:surface:%s', self.name, mat_name)
            elif surface.type == JsonAsset.SurfaceQuads:
                triangles = [ ]
                for (q0, q1, q2, q3) in surface.primitives:
                    triangles.append( ( q0, q1, q2) )
                    triangles.append( ( q0, q2, q3) )
                surface.primitives = triangles
                surface.type = JsonAsset.SurfaceTriangles
                LOG.info('Triangulated geometry:%s:surface:%s', self.name, mat_name)
                if generate_tangents:
                    LOG.info('Process:generate_tangents:geometry:%s:surface:%s', self.name, mat_name)
                elif generate_normals:
                    LOG.info('Process:generate_normals:geometry:%s:surface:%s', self.name, mat_name)
            else:
                return

        # For each surface in the geometry...
        new_surfaces = { }

        index = 0
        for mat_name, surface in self.surfaces.iteritems():
            start_index = index
            surface_sources = surface.sources

            # For each primitive within the surface...
            for primitive in surface.primitives:
                index += 1

                if isinstance(primitive[0], (tuple, list)):
                    # For each input source and input offset...
                    for source, offset in old_offsets.iteritems():
                        new_source = new_sources[source]
                        if source in surface_sources:
                            source_values = self.sources[source].values
                            # For each vertex in the primitive (triangle or quad)...
                            for vertex in primitive:
                                new_source.append( source_values[vertex[offset]] )
                        else:
                            zero = self.sources[source].zero_value
                            for vertex in primitive:
                                new_source.append(zero)
                else:
                    # For each input source and input offset...
                    for source in old_offsets.iterkeys():
                        new_source = new_sources[source]
                        if source in surface_sources:
                            source_values = self.sources[source].values
                            # For each vertex in the primitive (triangle or quad)...
                            for vertex in primitive:
                                new_source.append( source_values[vertex] )
                        else:
                            zero = self.sources[source].zero_value
                            for vertex in primitive:
                                new_source.append(zero)

            end_index = index
            new_surfaces[mat_name] = (start_index, end_index)

        mesh = Mesh()
        for semantic, input_stream in self.inputs.iteritems():
            mesh.set_values(new_sources[input_stream.source], semantic)

        mesh.primitives = [ (i, i + 1, i + 2) for i in range(0, index * 3, 3) ]
        #mesh.mirror_in('z')

        if generate_normals:
            mesh.generate_normals()
            mesh.smooth_normals()
            old_semantics['NORMAL'] = True

        if generate_tangents:
            mesh.generate_tangents()
            mesh.normalize_tangents()
            mesh.smooth_tangents()
            mesh.generate_normals_from_tangents()
            mesh.smooth_normals()
            old_semantics['TANGENT'] = True
            old_semantics['BINORMAL'] = True

        def compact_stream(values, semantic):
            """Generate a new value and index stream remapping and removing duplicate elements."""
            new_values = [ ]
            new_values_hash = { }
            new_index = [ ]
            for v in values:
                if v in new_values_hash:
                    new_index.append(new_values_hash[v])
                else:
                    i = len(new_values)
                    new_index.append(i)
                    new_values.append(v)
                    new_values_hash[v] = i

            LOG.info('%s stream compacted from %i to %i elements', semantic, len(values), len(new_values))
            return (new_values, new_index)

        # !!! This should be updated to find index buffers that are similar rather than identical.
        new_indexes = [ ]
        new_offsets = { }
        for semantic in old_semantics.iterkeys():
            values = mesh.get_values(semantic)
            (new_values, new_values_index) = compact_stream(values, semantic)
            mesh.set_values(new_values, semantic)
            for i, indexes in enumerate(new_indexes):
                if indexes == new_values_index:
                    new_offsets[semantic] = i
                    break
            else:
                new_offsets[semantic] = len(new_indexes)
                new_indexes.append(new_values_index)

        indexes = zip(*new_indexes)

        # Use NVTriStrip to generate a vertex cache aware triangle list
        if nvtristrip is not None:
            for (start_index, end_index) in new_surfaces.itervalues():
                reverse_map = {}
                indexes_map = {}
                num_vertices = 0
                for n in xrange(start_index * 3, end_index * 3):
                    index = indexes[n]
                    if index not in indexes_map:
                        indexes_map[index] = num_vertices
                        reverse_map[num_vertices] = index
                        num_vertices += 1
                #LOG.info(num_vertices)

                if num_vertices < 65536:
                    #LOG.info(indexes)
                    try:
                        nvtristrip_proc = subprocess.Popen([nvtristrip],
                                                           stdin = subprocess.PIPE,
                                                           stdout = subprocess.PIPE)

                        stdin_write = nvtristrip_proc.stdin.write
                        for n in xrange(start_index * 3, end_index * 3):
                            index = indexes[n]
                            value = indexes_map[index]
                            stdin_write(str(value) + "\n")
                        stdin_write("-1\n")
                        stdin_write = None
                        indexes_map = None

                        stdout_readline = nvtristrip_proc.stdout.readline
                        try:
                            num_groups = int(stdout_readline())
                            group_type = int(stdout_readline())
                            num_indexes = int(stdout_readline())
                            if num_groups != 1 or group_type != 0 or num_indexes != (end_index - start_index) * 3:
                                LOG.warning("NvTriStripper failed: %d groups, type %d, %d indexes.",
                                            num_groups, group_type, num_indexes)
                            else:
                                n = start_index * 3
                                for value in stdout_readline().split():
                                    value = int(value)
                                    indexes[n] = reverse_map[value]
                                    n += 1
                        except ValueError as e:
                            error_string = str(e).split("'")
                            if 1 < len(error_string):
                                error_string = error_string[1]
                            else:
                                error_string = str(e)
                            LOG.warning("NvTriStripper failed: %s", error_string)
                        stdout_readline = None
                        nvtristrip_proc = None
                        #LOG.info(indexes)

                    except OSError as e:
                        LOG.warning("NvTriStripper failed: " + str(e))
                else:
                    LOG.warning("Too many vertices to use NvTriStrip: %d", num_vertices)
                indexes_map = None
                reverse_map = None

        primitives = [ (indexes[i], indexes[i + 1], indexes[i + 2]) for i in xrange(0, len(indexes), 3) ]

        # Fix up the surfaces...
        for mat_name, (start_index, end_index) in new_surfaces.iteritems():
            self.surfaces[mat_name].primitives = primitives[start_index:end_index]

        # Fix up the inputs...
        for semantic, input_stream in self.inputs.iteritems():
            input_stream.offset = new_offsets[semantic]

        # Fix up the sources...
        for _, source in self.sources.iteritems():
            source.values = mesh.get_values(source.semantic)

        if generate_normals:
            self.inputs['NORMAL'] = Dae2Geometry.Input('NORMAL', 'normals', new_offsets['NORMAL'])
            self.sources['normals'] = Dae2Geometry.Source(mesh.normals, 'NORMAL', 'normals', 3, len(mesh.normals))

        if generate_tangents:
            self.inputs['BINORMAL'] = Dae2Geometry.Input('BINORMAL', 'binormals', new_offsets['BINORMAL'])
            self.inputs['TANGENT'] = Dae2Geometry.Input('TANGENT', 'tangents', new_offsets['TANGENT'])
            self.sources['binormals'] = Dae2Geometry.Source(mesh.binormals,
                                                            'BINORMAL',
                                                            'binormals',
                                                            3,
                                                            len(mesh.binormals))
            self.sources['tangents'] = Dae2Geometry.Source(mesh.tangents,
                                                           'TANGENT',
                                                           'tangents',
                                                           3,
                                                           len(mesh.tangents))
   # pylint: enable=R0914

    def attach(self, json_asset):
        json_asset.attach_shape(self.name)
        json_asset.attach_meta(self.meta, self.name)
        for surface_name, surface in self.surfaces.iteritems():
            json_asset.attach_surface(surface.primitives, surface.type, self.name, surface_name)
        for semantic, i in self.inputs.iteritems():
            source = self.sources[i.source]
            if semantic.startswith('TEXCOORD'):
                mesh = Mesh()
                mesh.uvs[0] = source.values
                mesh.invert_v_texture_map()
                source.values = mesh.uvs[0]
                mesh = None
            json_asset.attach_stream(source.values, self.name, source.name, semantic, source.stride, i.offset)

    def __repr__(self):
        return 'Dae2Geometry<sources:%s:inputs:%s>' % (self.sources, self.inputs)

class Dae2Effect(object):
    def __init__(self, effect_e, url_handler, name_map, effect_names):
        self.shader_path = None
        self.type = None
        self.params = { }
        self.meta = None

        # Name...
        self.id = effect_e.get('id', 'unknown')
        self.name = effect_e.get('name', self.id)
        if self.name in effect_names:
            LOG.warning('EFFECT name clash:%s:replacing with:%s', self.name, self.id)
            effect_names[self.id] = self.name
            self.name = self.id
        else:
            effect_names[self.name] = self.name

        name_map[self.id] = self.name

        for extra_e in effect_e.findall(tag('extra')):
            extra_type = extra_e.get('type')
            if extra_type is not None and extra_type == 'import':
                technique_e = extra_e.find(tag('technique'))
                if technique_e is not None:
                    technique_profile =  technique_e.get('profile')
                    if technique_profile is not None and (technique_profile == 'NV_import' or \
                                                          technique_profile == 'NVIDIA_FXCOMPOSER'):
                        import_e = technique_e.find(tag('import'))
                        if import_e is not None:
                            profile = import_e.get('profile')
                            if profile is not None and profile == 'cgfx':
                                url = import_e.get('url')
                                self.shader_path = url_handler.tidy(url)

        cg_profile = False
        profile_e = effect_e.find(tag('profile_COMMON'))
        if profile_e is None:
            for profile_CG_e in effect_e.findall(tag('profile_CG')):
                platform = profile_CG_e.get('platform')
                if platform is None or platform == 'PC-OGL':
                    cg_profile = True
                    profile_e = profile_CG_e
                    include_e = profile_CG_e.find(tag('include'))
                    if include_e is not None:
                        url = include_e.get('url')
                        if url is not None and 'cgfx' in url:
                            self.shader_path = url_handler.tidy(url)

        if cg_profile:
            self.type = 'cgfx'

        else:
            technique_e = profile_e.find(tag('technique'))
            if technique_e is None:
                return

            type_e = technique_e.getchildren()
            if type_e is None or len(type_e) == 0:
                return
            self.type = untag(type_e[0].tag)

            def _add_texture(param_name, texture_e):
                texture_name = None
                sampler_name = texture_e.get('texture')
                if sampler_name is not None:
                    sampler_e = find_new_param(profile_e, sampler_name)
                    if sampler_e is not None:
                        sampler_type_e = sampler_e[0]
                        if sampler_type_e is not None:
                            source_e = sampler_type_e.find(tag('source'))
                            if source_e is not None:
                                surface_param_e = find_new_param(profile_e, source_e.text)
                                if surface_param_e is not None:
                                    surface_e = surface_param_e.find(tag('surface'))
                                    if surface_e is not None:
                                        image_e = surface_e.find(tag('init_from'))
                                        if image_e is not None:
                                            texture_name = image_e.text
                    else:
                        texture_name = sampler_name

                if texture_name is None:
                    self.params[param_name] = 'null'
                else:
                    self.params[param_name] = find_name(name_map, texture_name)

            for param_e in type_e[0].getchildren():
                param_name = untag(param_e.tag)
                texture_e = param_e.find(tag('texture'))
                if texture_e is not None:
                    _add_texture(param_name, texture_e)
                else:
                    for value_e in param_e.getchildren():
                        value_type = untag(value_e.tag)
                        value_text = value_e.text
                        if value_type == 'param':
                            param_ref = value_e.get('ref')
                            param_ref_e = find_new_param(profile_e, param_ref)
                            if param_ref_e is not None:
                                for ref_value_e in param_ref_e.getchildren():
                                    value_type = untag(ref_value_e.tag)
                                    value_text = ref_value_e.text
                        if value_type == 'color':
                            color = [ float(x) for x in value_text.split() ]
                            if param_name == 'transparent':
                                mode = param_e.get('opaque') or 'A_ONE'
                                if mode == 'A_ONE':
                                    color[0] = color[1] = color[2] = color[3]
                                elif mode == 'A_ZERO':
                                    color[0] = color[1] = color[2] = 1.0 - color[3]
                                elif mode == 'RGB_ZERO':
                                    color[0] = 1.0 - color[0]
                                    color[1] = 1.0 - color[1]
                                    color[2] = 1.0 - color[2]
                            self.params[param_name] = color
                        else:
                            self.params[param_name] = tidy_value(value_text, value_type)

            # Process extensions
            extra_e = technique_e.find(tag('extra'))
            if extra_e is not None:
                extra_techniques = extra_e.findall(tag('technique'))
                if extra_techniques:
                    for extra_technique_e in extra_techniques:
                        bump_e = extra_technique_e.find(tag('bump'))
                        if bump_e is not None:
                            texture_e = bump_e.find(tag('texture'))
                            if texture_e is not None:
                                _add_texture('bump', texture_e)

            tint_color_e = find_new_param(profile_e, '_TintColor')
            if tint_color_e is not None:
                value_e = tint_color_e.find(tag('float4'))
                if value_e is not None:
                    value_text = value_e.text
                    color = [ float(x) for x in value_text.split() ]
                    self.params['TintColor'] = color

            # Convert COLLADA effects to Turbulenz Effects
            if self.type in ['blinn', 'phong', 'lambert']:
                self._patch_type()

    def _patch_type(self):
        if 'TintColor' in self.params:
            material_color = self.params['TintColor']
            del self.params['TintColor']
        else:
            material_color = [1, 1, 1, 1]
        alpha = material_color[3]

        if 'ambient' in self.params:
            del self.params['ambient']

        if 'diffuse' in self.params:
            diffuse = self.params['diffuse']
            if isinstance(diffuse, list):
                material_color = diffuse
                del self.params['diffuse']

        if 'emission' in self.params:
            emission = self.params['emission']
            if not isinstance(emission, list):
                if 'diffuse' in self.params:
                    self.params['light_map'] = emission
                else:
                    self.params['glow_map'] = emission
            del self.params['emission']

        if 'bump' in self.params:
            bump = self.params['bump']
            if not isinstance(bump, list):
                self.params['normal_map'] = bump
            del self.params['bump']

        if 'specular' in self.params:
            specular = self.params['specular']
            if not isinstance(specular, list):
                self.params['specular_map'] = specular
            del self.params['specular']

        if 'reflective' in self.params:
            reflective = self.params['reflective']
            if not isinstance(reflective, list):
                self.params['env_map'] = reflective
            del self.params['reflective']

        if 'transparency' in self.params:
            transparency = self.params['transparency']
            if transparency == 0.0:
                # This is a usual bug on older exporters, it means opaque
                if 'transparent' in self.params:
                    del self.params['transparent']
            else:
                alpha *= transparency
            del self.params['transparency']

        if 'transparent' in self.params:
            transparent = self.params['transparent']
            if not isinstance(transparent, list):
                if transparent == self.params.get('diffuse', None):
                    alpha = 0.9999
            else:
                transparent = min(transparent)
                alpha = min(alpha, transparent)
            del self.params['transparent']

        meta = { }

        if alpha < 1.0:
            self.type = 'blend'
            if alpha > 0.99:
                alpha = 1
            material_color[3] = alpha
            meta['transparent'] = True
            if 'diffuse' not in self.params:
                self.params['diffuse'] = 'white'
        elif 'light_map' in self.params:
            self.type = 'lightmap'
        elif 'normal_map' in self.params:
            self.type = 'normalmap'
            if 'specular_map' in self.params:
                self.type += '_specularmap'
            if 'glow_map' in self.params:
                self.type += '_glowmap'
            meta['normals'] = True
            meta['tangents'] = True
        elif 'glow_map' in self.params:
            self.type = 'glowmap'
        elif 'diffuse' not in self.params:
            self.type = 'constant'
            meta['normals'] = True
        else:
            meta['normals'] = True

        if min(material_color) < 1.0:
            self.params['materialColor'] = material_color

        if meta:
            if self.meta is None:
                self.meta = meta
            else:
                self.meta.update(meta)

    def attach(self, json_asset, definitions_asset):

        def _attach_effect(effect_name):
            effect = definitions_asset.retrieve_effect(effect_name)
            if effect is not None:
                json_asset.attach_effect(self.name, raw=effect)
                return True
            return False

        if definitions_asset is not None:
            if _attach_effect(self.name) or _attach_effect(self.name.lower()):
                return

        # If we did not find an effect in the definitions_asset then we need to add the effect from
        # the Collada asset.
        json_asset.attach_effect(self.name, self.type, self.params, self.shader_path, self.meta)

class Dae2Material(object):
    def __init__(self, material_e, name_map):
        self.effect_name = None
        self.technique_name = None
        self.params = { }

        # Name...
        self.id = material_e.get('id', 'unknown')
        self.name = material_e.get('name', self.id)
        name_map[self.id] = self.name

        # Effect...
        effect_e = material_e.find(tag('instance_effect'))
        self.effect_name = tidy_name(effect_e.get('url'))

        # Technique...
        for technique_hint_e in effect_e.findall(tag('technique_hint')):
            platform = technique_hint_e.get('platform')
            if platform is None or platform == 'PC-OGL':
                self.technique_name = technique_hint_e.get('ref')
                if self.technique_name is not None:
                    break

        # Params...
        for param_e in effect_e.findall(tag('setparam')):
            param_name = param_e.get('ref')
            for value_e in param_e.getchildren():
                value_type = untag(value_e.tag)
                if value_type.startswith('sampler'):
                    texture_name = 'null'
                    source_e = value_e.find(tag('source'))
                    if source_e is not None:
                        surface_param_e = find_set_param(effect_e, source_e.text)
                        if surface_param_e is not None:
                            surface_e = surface_param_e.find(tag('surface'))
                            if surface_e is not None:
                                texture_e = surface_e.find(tag('init_from'))
                                if texture_e is not None:
                                    texture_name = texture_e.text
                    self.params[param_name] = find_name(name_map, texture_name)
                elif value_type != 'surface':
                    value_text = value_e.text
                    self.params[param_name] = tidy_value(value_text, value_type)

    def attach(self, json_asset, definitions_asset, name_map):

        def _attach_materials(mat_name):
            # This attaches any skins and *additional* materials used by the skins.
            attach_skins_and_materials(json_asset, definitions_asset, mat_name, False)
            # This attaches the current material.
            material = definitions_asset.retrieve_material(mat_name, False)
            if material is not None:
                json_asset.attach_material(self.name, raw=material)
                return True
            return False

        # !!! Consider adding options to support Overload and Fallback assets, then the order of assets would be:
        # 1. Overload material
        # 2. Original material
        # 3. Fallback material
        if definitions_asset is not None:
            if _attach_materials(self.name) or _attach_materials(self.name.lower()):
                return

        # If we did not find a material in the definitions_asset then we need to add the material from
        # the Collada asset.
        effect_name = find_name(name_map, self.effect_name)
        if len(self.params) == 0:
            json_asset.attach_material(self.name, effect_name, self.technique_name)
        else:
            json_asset.attach_material(self.name, effect_name, self.technique_name, self.params)

class Dae2Image(object):
    def __init__(self, image_e, url_handler, name_map):
        self.image_path = None

        self.id = image_e.get('id', 'unknown')
        self.name = image_e.get('name', self.id)
        name_map[self.id] = self.name

        from_e = image_e.find(tag('init_from'))
        if from_e is not None and from_e.text is not None:
            self.image_path = url_handler.tidy(from_e.text)

    def attach(self, json_asset):
        json_asset.attach_image(self.image_path, self.name)

class Dae2Light(object):
    def __init__(self, light_e, name_map, light_names):
        self.params = { }

        # Name...
        self.id = light_e.get('id', 'unknown')
        self.name = light_e.get('name', self.id)
        if self.name in light_names:
            LOG.warning('LIGHT name clash:%s:replacing with:%s', self.name, self.id)
            light_names[self.id] = self.name
            self.name = self.id
        else:
            light_names[self.name] = self.name

        name_map[self.id] = self.name

        common_e = light_e.find(tag('technique_common'))
        if common_e is not None:
            type_e = common_e[0]
            self.params['type'] = untag(type_e.tag)

            for param_e in type_e:
                param_name = untag(param_e.tag)
                if param_name == 'color':
                    self.params[param_name] = [float(x) for x in param_e.text.split()]
                else:
                    self.params[param_name] = float(param_e.text)

    def attach(self, json_asset, definitions_asset):

        def _attach_light(light_name):
            light = definitions_asset.retrieve_light(light_name)
            if light is not None:
                json_asset.attach_light(light_name, raw=light)
                if 'material' in light:
                    mat_name = light['material']
                    material = definitions_asset.retrieve_material(mat_name, False)
                    if material is not None:
                        json_asset.attach_material(mat_name, raw=material)
                return True
            return False

        if definitions_asset is not None:
            if _attach_light(self.name) or _attach_light(self.name.lower()):
                return

        # If we did not find a light in the definitions_asset then we need to add the light from
        # the Collada asset.
        constant_atten = 1
        linear_atten = 0
        quadratic_atten = 0
        if 'constant_attenuation' in self.params:
            constant_atten = self.params['constant_attenuation']
            del self.params['constant_attenuation']
        if 'linear_attenuation' in self.params:
            linear_atten = self.params['linear_attenuation']
            del self.params['linear_attenuation']
        if 'quadratic_attenuation' in self.params:
            quadratic_atten = self.params['quadratic_attenuation']
            del self.params['quadratic_attenuation']

        # generate a radius for the light
        # solve quadratic equation for attenuation 1/100
        # att = 1 / (constant_atten + (range * linear_atten) + (range * range * quadratic_atten))
        if quadratic_atten > 0:
            c = (constant_atten - 100)
            b = linear_atten
            a = quadratic_atten
            q = math.sqrt((b * b) - (4 * a * c))
            self.params['radius'] = max( (-b + q) / (2 * a),  (-b - q) / (2 * a))
        elif linear_atten > 0:
            self.params['radius'] = (100 - constant_atten) / linear_atten
        else:
            self.params['global'] = True

        json_asset.attach_light(self.name, self.params)

class Dae2Node(object):

    class InstanceGeometry(object):
        def __init__(self, instance_e):
            self.geometry = tidy_name(instance_e.get('url'))
            self.materials = { }
            bind_e = instance_e.find(tag('bind_material'))
            found_material = False
            if bind_e is not None:
                technique_e = bind_e.find(tag('technique_common'))
                if technique_e is not None:
                    for material_e in technique_e.findall(tag('instance_material')):
                        self.materials[material_e.get('symbol')] = tidy_name(material_e.get('target'))
                        found_material = True
            if not found_material:
                LOG.warning('INSTANCE_GEOMETRY with no material:url:%s:using:default', self.geometry)
                self.materials['default'] = 'default'

        def attach(self, json_asset, name_map, node_name=None):
            for surface, material in self.materials.iteritems():
                geom_name = find_name(name_map, self.geometry)
                mat_name = find_name(name_map, material)

                if len(self.materials) > 1:
                    surface_name = geom_name + '-' + mat_name
                else:
                    surface_name = geom_name

                json_asset.attach_node_shape_instance(node_name, surface_name, geom_name, mat_name, surface)

    class InstanceController(object):

        class Skin(object):
            def __init__(self, skin_e, scale, geometry):
                self.sources = { }
                self.inv_ltms = { }
                self.joint_names = [ ]
                self.joint_parents = { }
                self.joint_bind_poses = { }
                self.geometry = geometry
                self.scale = scale

                bind_matrix_e = skin_e.find(tag('bind_shape_matrix'))
                if bind_matrix_e is not None:
                    transpose = vmath.m44transpose([float(x) for x in bind_matrix_e.text.split()])
                    self.bind_matrix = vmath.m43from_m44(transpose)
                    self.bind_matrix = vmath.m43setpos(self.bind_matrix,
                                                       vmath.v3muls(vmath.m43pos(self.bind_matrix),
                                                       self.scale))
                else:
                    self.bind_matrix = vmath.M43IDENTITY

                source_e = skin_e.findall(tag('source'))
                for s in source_e:
                    technique_e = s.find(tag('technique_common'))
                    accessor_e = technique_e.find(tag('accessor'))
                    param_e = accessor_e.find(tag('param'))
                    param_name = param_e.get('name')
                    param_type = param_e.get('type')
                    if param_type.lower() == 'name' or param_type == 'IDREF':
                        sids = True
                        array_e = s.find(tag('Name_array'))
                        if array_e is None:
                            array_e = s.find(tag('IDREF_array'))
                            sids = False
                        count = int(array_e.get('count', '0'))
                        if (0 < count):
                            values_text = array_e.text
                            self.sources[s.get('id')] = { 'name': param_name,
                                                          'values': values_text.split(),
                                                          'sids': sids }
                    elif param_type == 'float':
                        array_e = s.find(tag('float_array'))
                        count = int(array_e.get('count', '0'))
                        if (0 < count):
                            values_text = array_e.text
                            values = [float(x) for x in values_text.split()]
                            self.sources[s.get('id')] = { 'name': param_name, 'values': values }
                    elif param_type == 'float4x4':
                        array_e = s.find(tag('float_array'))
                        count = int(array_e.get('count', '0'))
                        if (0 < count):
                            values_text = array_e.text
                            float_values = [float(x) for x in values_text.split()]
                            values = [ ]
                            for i in range(0, len(float_values), 16):
                                matrix = vmath.m44transpose(float_values[i:i+16])
                                values.append(vmath.m43from_m44(matrix))
                            self.sources[s.get('id')] = { 'name': param_name, 'values': values }
                    else:
                        LOG.warning('SKIN with unknown param type:%s:ignoring', param_type)
                joints_e = skin_e.find(tag('joints'))
                inputs = joints_e.findall(tag('input'))
                for i in inputs:
                    semantic = i.get('semantic')
                    if semantic == 'JOINT':
                        self.joint_input = tidy_name(i.get('source'))
                    elif semantic == 'INV_BIND_MATRIX':
                        self.inv_ltm_input = tidy_name(i.get('source'))

                vertex_weights_e = skin_e.find(tag('vertex_weights'))
                inputs = vertex_weights_e.findall(tag('input'))
                for i in inputs:
                    semantic = i.get('semantic')
                    if semantic == 'JOINT':
                        self.indices_input = tidy_name(i.get('source'))
                        self.indices_offset = int(i.get('offset'))
                    elif semantic == 'WEIGHT':
                        self.weights_input = tidy_name(i.get('source'))
                        self.weights_offset = int(i.get('offset'))
                weights_per_vertex_e = vertex_weights_e.find(tag('vcount'))
                self.weights_per_vertex = [ int(x) for x in weights_per_vertex_e.text.split() ]
                skin_data_indices_e = vertex_weights_e.find(tag('v'))
                self.skin_data_indices = [ int(x) for x in skin_data_indices_e.text.split() ]

            def process(self, nodes):
                # Build a skeleton for the skinned mesh
                joint_names = self.sources[self.joint_input]['values']
                sid_joints = self.sources[self.joint_input]['sids']
                hierarchy = build_joint_hierarchy(joint_names, nodes, sid_joints)
                for j in hierarchy:
                    node = j['node']
                    parent_index = j['parent']
                    original_joint_index = j['orig_index']
                    if original_joint_index is not -1:
                        inv_bind_ltm = self.sources[self.inv_ltm_input]['values'][original_joint_index]

                        bind_ltm = vmath.m43inverse(inv_bind_ltm)
                        bind_ltm = vmath.m43setpos(bind_ltm,
                                                   vmath.v3muls(vmath.m43pos(bind_ltm),
                                                   self.scale))

                        inv_bind_ltm = vmath.m43setpos(inv_bind_ltm,
                                                       vmath.v3muls(vmath.m43pos(inv_bind_ltm),
                                                       self.scale))
                        inv_bind_ltm = vmath.m43mul(self.bind_matrix, inv_bind_ltm)

                        self.joint_names.append(node.name)
                        self.joint_parents[node.name] = parent_index
                        self.joint_bind_poses[node.name] = bind_ltm
                        self.inv_ltms[node.name] = inv_bind_ltm
                    else:
                        self.joint_names.append(node.name)
                        self.joint_parents[node.name] = parent_index
                        self.joint_bind_poses[node.name] = vmath.M43IDENTITY
                        self.inv_ltms[node.name] = vmath.M43IDENTITY

                # Build a skinning index mapping to the new joints
                skin_index_map = [ -1 ] * len(joint_names)
                for i, j in enumerate(hierarchy):
                    original_joint_index = j['orig_index']
                    if original_joint_index is not -1:
                        skin_index_map[original_joint_index] = i

                # Attach skinning data to the geometry
                g_inputs = self.geometry.inputs
                g_sources = self.geometry.sources
                positions_offset = g_inputs['POSITION'].offset
                count = len(g_sources[g_inputs['POSITION'].source].values)
                g_inputs['BLENDINDICES'] = Dae2Geometry.Input('BLENDINDICES', self.indices_input, positions_offset)
                g_inputs['BLENDWEIGHT'] = Dae2Geometry.Input('BLENDWEIGHT', self.weights_input, positions_offset)

                weight_source_values = self.sources[self.weights_input]['values']
                index_offset = 0
                index_data = []
                weight_data = []
                for wc in self.weights_per_vertex:
                    weights_list = []
                    for i in range(0, wc):
                        index = self.skin_data_indices[index_offset + self.indices_offset]
                        # remap the index
                        index = skin_index_map[index]
                        weight_index = self.skin_data_indices[index_offset + self.weights_offset]
                        weight = weight_source_values[weight_index]
                        index_offset += 2
                        weights_list.append((weight, index))
                    weights_list = sorted(weights_list, key=lambda weight: weight[0], reverse=True)
                    weight_scale = 1
                    if (len(weights_list) > 4):
                        weight_sum = weights_list[0][0] + weights_list[1][0] + weights_list[2][0] + weights_list[3][0]
                        weight_scale = 1 / weight_sum
                    for i in range(0, 4):
                        if i < len(weights_list):
                            (weight, index) = weights_list[i]
                            index_data.append(index)
                            weight_data.append(weight * weight_scale)
                        else:
                            index_data.append(0)
                            weight_data.append(0)

                g_sources[self.indices_input] = Dae2Geometry.Source(pack(index_data, 4), 'BLENDINDICES',
                                                                    'skin-indices', 1, count)
                g_sources[self.weights_input] = Dae2Geometry.Source(pack(weight_data, 4), 'BLENDWEIGHT',
                                                                    'skin-weights', 1, count)

                # update set of sources referenced by each surface
                for surface in self.geometry.surfaces.itervalues():
                    surface.sources.add(self.indices_input)
                    surface.sources.add(self.weights_input)

        def __init__(self, instance_controller_e, scale, controllers_e, child_name, geometries):
            self.skeleton = None
            self.skin = None
            self.geometry = None
            self.materials = { }

            skeleton_e = instance_controller_e.find(tag('skeleton'))
            if skeleton_e is not None:
                self.skeleton_name = tidy_name(skeleton_e.text)

            controller_name = tidy_name(instance_controller_e.get('url'))
            controller_e = find_controller(controller_name, controllers_e)
            if controller_e is not None:
                skin_e = controller_e.find(tag('skin'))
                if skin_e is not None:
                    geometry_id = tidy_name(skin_e.get('source'))
                    if geometry_id in geometries:
                        self.geometry = geometry_id
                        self.skin = Dae2Node.InstanceController.Skin(skin_e, scale, geometries[self.geometry])

            found_material = False
            bind_e = instance_controller_e.find(tag('bind_material'))
            if bind_e is not None:
                technique_e = bind_e.find(tag('technique_common'))
                if technique_e is not None:
                    for material_e in technique_e.findall(tag('instance_material')):
                        self.materials[material_e.get('symbol')] = tidy_name(material_e.get('target'))
                        found_material = True
            if not found_material:
                LOG.warning('INSTANCE_GEOMETRY with no material:url:%s:using:default', self.geometry)
                self.materials['default'] = 'default'

            self.child_name = child_name

        def process(self, nodes):
            if self.skin:
                self.skin.process(nodes)

                # Process a skeleton if we have a skin, note if this is moved to process we should always extract the
                # joint names
                joint_names = [ ]
                joint_parents = [ ]
                joint_bind_poses = [ ]
                inv_ltms = [ ]
                for j in self.skin.joint_names:
                    joint_names.append(j)
                    joint_parents.append(self.skin.joint_parents[j])
                    joint_bind_poses.append(self.skin.joint_bind_poses[j])
                    inv_ltms.append(self.skin.inv_ltms[j])
                self.skeleton = {
                    'numNodes': len(joint_names),
                    'names': joint_names,
                    'parents': joint_parents,
                    'bindPoses': joint_bind_poses,
                    'invBoneLTMs': inv_ltms }

        def attach(self, json_asset, name_map, parent_node_name=None):
            if self.geometry is None:
                LOG.warning('Skipping INSTANCE_CONTROLLER with no geometry attached to %s', parent_node_name)
                return
            if self.child_name is None:
                node_name = parent_node_name
            else:
                node_name = NodeName(self.child_name).add_parent_node(parent_node_name)

            for surface, material in self.materials.iteritems():
                geom_name = find_name(name_map, self.geometry)
                mat_name = find_name(name_map, material)

                if len(self.materials) > 1:
                    surface_name = geom_name + '-' + mat_name
                else:
                    surface_name = geom_name

                json_asset.attach_node_shape_instance(node_name, surface_name, geom_name, mat_name, surface)

                instance_attributes = { }
                node_attributes = { }

                if self.skin is not None:
                    instance_attributes['skinning'] = True
                    node_attributes['dynamic'] = True

                skeleton_name = self.geometry + '-skeleton'
                if hasattr(self , 'skeleton_name'):
                    skeleton_name = self.skeleton_name
                if skeleton_name is not None:
                    json_asset.attach_geometry_skeleton(geom_name, skeleton_name)
                    json_asset.attach_skeleton(self.skeleton, skeleton_name)

                json_asset.attach_shape_instance_attributes(node_name, surface_name, instance_attributes)
                json_asset.attach_node_attributes(node_name, node_attributes)

    def _build_node_path(self):
        path = NodeName(self.name)
        parents = []
        parent = self.parent
        while parent:
            parents.append(parent.name)
            parent = parent.parent
        if parents:
            parents.reverse()
            path.add_parents(parents)
        return path

# pylint: disable=R0913,R0914
    def __init__(self, node_e, global_scale, parent_node, parent_matrix, parent_prefix, controllers_e, collada_e,
                 name_map, node_names, node_map, geometries):
        self.matrix = None

        # !!! Put these in a dictionary??
        self.lights = [ ]
        self.cameras = [ ]
        self.references = [ ]
        self.instance_geometry = [ ]
        self.instance_controller = [ ]
        self.parent = parent_node
        self.children = [ ]
        self.animated = False

        self.element = node_e
        self.id = node_e.get('id', 'unnamed')
        self.sid = node_e.get('sid', None)
        node_name = node_e.get('name', self.id)
        if parent_prefix is not None:
            node_name = parent_prefix + '-' + node_name
        self.name = node_name

        path = self._build_node_path()
        path_str = str(path)
        if path_str in node_names:
            self.name += self.id
            path.name = self.name
            LOG.warning('NODE name clash:%s:replacing with:%s', path_str, str(path))
            path_str = str(path)
        self.path = path

        name_map[self.id] = self.name
        node_names[path_str] = self
        node_map[self.id] = self

        matrix = vmath.M44IDENTITY
        if parent_matrix is not None:
            matrix = parent_matrix # Make sure we get a copy

        for node_param_e in node_e:
            child_type = untag(node_param_e.tag)
            if child_type == 'translate':
                offset = [ float(x) for x in node_param_e.text.split() ]
                translate_matrix = vmath.m43(1.0, 0.0, 0.0,
                                             0.0, 1.0, 0.0,
                                             0.0, 0.0, 1.0,
                                             offset[0], offset[1], offset[2])
                matrix = vmath.m43mulm44(translate_matrix, matrix)

            elif child_type == 'rotate':
                rotate = [ float(x) for x in node_param_e.text.split() ]
                if rotate[3] != 0.0:
                    angle = rotate[3] / 180.0 * math.pi
                    if rotate[0] == 1.0 and rotate[1] == 0.0 and rotate[2] == 0.0:
                        c = math.cos(angle)
                        s = math.sin(angle)
                        rotate_matrix = vmath.m33(1.0, 0.0, 0.0,
                                                  0.0,   c,   s,
                                                  0.0,  -s,   c)
                    elif rotate[0] == 0.0 and rotate[1] == 1.0 and rotate[2] == 0.0:
                        c = math.cos(angle)
                        s = math.sin(angle)
                        rotate_matrix = vmath.m33(  c, 0.0,  -s,
                                                  0.0, 1.0, 0.0,
                                                    s, 0.0,   c)
                    elif rotate[0] == 0.0 and rotate[1] == 0.0 and rotate[2] == 1.0:
                        c = math.cos(angle)
                        s = math.sin(angle)
                        rotate_matrix = vmath.m33(  c,   s, 0.0,
                                                   -s,   c, 0.0,
                                                  0.0, 0.0, 1.0)
                    else:
                        rotate_matrix = vmath.m33from_axis_rotation(rotate[:3], angle)
                    matrix = vmath.m33mulm44(rotate_matrix, matrix)

            elif child_type == 'scale':
                scale = [ float(x) for x in node_param_e.text.split() ]
                scale_matrix = vmath.m33(scale[0],      0.0,      0.0,
                                              0.0, scale[1],      0.0,
                                              0.0,      0.0, scale[2])
                matrix = vmath.m33mulm44(scale_matrix, matrix)

            elif child_type == 'matrix':
                local_matrix = vmath.m44transpose(tuple([ float(x) for x in node_param_e.text.split() ]))
                matrix = vmath.m44mul(local_matrix, matrix)

        # Hard coded scale
        if global_scale != 1.0:
            matrix = vmath.m44setpos(matrix, vmath.v4muls(vmath.m44pos(matrix), global_scale))

        matrix = vmath.tidy(matrix) # Remove tiny values

        if matrix[ 0] != 1.0 or matrix[ 1] != 0.0 or matrix[ 2] != 0.0 or \
           matrix[ 4] != 0.0 or matrix[ 5] != 1.0 or matrix[ 6] != 0.0 or \
           matrix[ 8] != 0.0 or matrix[ 9] != 0.0 or matrix[10] != 1.0 or \
           matrix[12] != 0.0 or matrix[13] != 0.0 or matrix[14] != 0.0:
            self.matrix = matrix
        else:
            self.matrix = None

        geometries_e = node_e.findall(tag('instance_geometry'))

        for geometry_e in geometries_e:
            geometry_url = tidy_name(geometry_e.get('url'))
            if geometry_url in geometries:
                self.instance_geometry.append(Dae2Node.InstanceGeometry(geometry_e))
            else:
                LOG.warning('INSTANCE_GEOMETRY referencing missing or unprocessed geometry:%s', geometry_url)

        # Remove any references to invalid surfaces in the geometry
        for instance_geometry in self.instance_geometry:
            surfaces_to_remove = []
            geometry = geometries[instance_geometry.geometry]
            for material in instance_geometry.materials:
                if material == 'default':
                    if len(geometry.surfaces) != 1:
                        surfaces_to_remove.append(material)
                        LOG.warning('INSTANCE_GEOMETRY referencing default surface but geometry has surfaces:url:%s',
                                    instance_geometry.geometry)
                elif material not in geometry.surfaces:
                    surfaces_to_remove.append(material)
                    LOG.warning('INSTANCE_GEOMETRY referencing surface not present in geometry:surface:%s:url:%s',
                                material, instance_geometry.geometry)
            for surface in surfaces_to_remove:
                del instance_geometry.materials[surface]

        for light_e in node_e.findall(tag('instance_light')):
            self.lights.append(tidy_name(light_e.get('url')))

        for camera_e in node_e.findall(tag('instance_camera')):
            self.cameras.append(tidy_name(camera_e.get('url')))

        for instance_controller_e in node_e.findall(tag('instance_controller')):
            self.instance_controller.append(Dae2Node.InstanceController(instance_controller_e, global_scale,
                                            controllers_e, None, geometries))

        # Instanced nodes, processed like normal children but with custom prefixes
        for instance_node_e in node_e.findall(tag('instance_node')):
            instance_node_url = instance_node_e.get('url')
            if instance_node_url is not None:
                if instance_node_url[0] == '#':
                    instanced_node_e = find_node(instance_node_url, collada_e)
                    if instanced_node_e is not None:
                        self.children.append(Dae2Node(instanced_node_e, global_scale, self, None, node_name,
                                             controllers_e, collada_e, name_map, node_names, node_map, geometries))
                else:
                    self.references.append(instance_node_url)

        # Children...
        for children_e in node_e.findall(tag('node')):
            self.children.append(Dae2Node(children_e, global_scale, self, None, parent_prefix, controllers_e,
                                          collada_e, name_map, node_names, node_map, geometries))
# pylint: enable=R0913,R0914

    def process(self, nodes):
        for instance_controller in self.instance_controller:
            instance_controller.process(nodes)

        for child in self.children:
            child.process(nodes)

    def attach(self, json_asset, url_handler, name_map):
        node_name = self.path

        json_asset.attach_node(node_name, self.matrix)
        if self.animated:
            node_attrib = { 'dynamic': True }
            json_asset.attach_node_attributes(node_name, node_attrib)

        for light in self.lights:
            json_asset.attach_node_light_instance(node_name, light, find_name(name_map, light))

        # Scene runtime code only supports one camera per node
        if len(self.cameras) == 1:
            json_asset.attach_node_attributes(node_name, {'camera': find_name(name_map, self.cameras[0])} )
        else:
            for camera in self.cameras:
                camera_name = NodeName(node_name.leaf_name() + '-' + camera)
                camera_name.add_parent_node(node_name)
                json_asset.attach_node_attributes(camera_name, {'camera': find_name(name_map, camera)} )

        # !!! We only support references to root nodes
        if len(self.references) == 1 and len(self.instance_geometry) == 0:
            reference_parts = self.references[0].split('#')
            file_name = url_handler.tidy(reference_parts[0])
            json_asset.attach_node_attributes(node_name, { 'reference': file_name, 'inplace': True } )
        else:
            for reference in self.references:
                reference_parts = reference.split('#')
                file_name = url_handler.tidy(reference_parts[0])
                reference_name = NodeName(node_name.leaf_name() + '-' + file_name.replace('/', '-'))
                reference_name.add_parent_node(node_name)
                json_asset.attach_node_attributes(reference_name, { 'reference': file_name,
                                                                    'inplace': True } )
        for instance in self.instance_geometry:
            instance.attach(json_asset, name_map, node_name)
        for instance in self.instance_controller:
            instance.attach(json_asset, name_map, node_name)
        for child in self.children:
            child.attach(json_asset, url_handler, name_map)

class Dae2PhysicsMaterial(object):
    def __init__(self, physics_material_e, name_map):
        self.params = { }

        # Name...
        self.id = physics_material_e.get('id', 'unknown')
        self.name = physics_material_e.get('name', self.id)
        name_map[self.id] = self.name

        # Material...
        technique_e = physics_material_e.find(tag('technique_common'))
        for param_e in technique_e.getchildren():
            param_name = untag(param_e.tag)
            param_text = param_e.text
            self.params[param_name] = float(param_text)

    def attach(self, json_asset):
        json_asset.attach_physics_material(self.name, self.params)

class Dae2PhysicsModel(object):
    def __init__(self, physics_model_e, geometries_nodes_e, rigid_body_map, name_map):
        self.rigidbodys = { }

        # Name...
        self.id = physics_model_e.get('id', 'unknown')
        self.name = physics_model_e.get('name', self.id)
        name_map[self.id] = self.name

        # Rigid Body...
        for rigidbody_e in physics_model_e.findall(tag('rigid_body')):
            technique_e = rigidbody_e.find(tag('technique_common'))
            if technique_e is not None:
                rigidbody = { }
                shape_e = technique_e.find(tag('shape'))
                if shape_e is not None:
                    rigidbody['type'] = 'rigid'

                    instance_geometry_e = shape_e.find(tag('instance_geometry'))
                    if instance_geometry_e is not None:
                        geometry_name = tidy_name(instance_geometry_e.get('url'))
                        rigidbody['geometry'] = find_name(name_map, geometry_name)

                        for geometry_e in geometries_nodes_e.findall(tag('geometry')):
                            geometry_id = geometry_e.get('id')
                            if geometry_id == geometry_name:
                                if geometry_e.find(tag('convex_mesh')) is not None:
                                    rigidbody['shape'] = 'convexhull'
                                else:
                                    rigidbody['shape'] = 'mesh'
                                break
                    else:
                        shape_type_e = shape_e[0]
                        shape_type_name = untag(shape_type_e.tag)
                        if shape_type_name == 'tapered_cylinder':
                            rigidbody['shape'] = 'cone'
                        else:
                            rigidbody['shape'] = shape_type_name

                        radius_e = shape_type_e.find(tag('radius'))
                        if radius_e is None:
                            radius_e = shape_type_e.find(tag('radius1'))
                        if radius_e is not None:
                            radius_list = [float(x) for x in radius_e.text.split()]
                            rigidbody['radius'] = radius_list[0] # !!! What about the other values

                        height_e = shape_type_e.find(tag('height'))
                        if height_e is not None:
                            rigidbody['height'] = float(height_e.text)

                        half_extents_e = shape_type_e.find(tag('half_extents'))
                        if half_extents_e is not None:
                            rigidbody['halfExtents'] = [float(x) for x in half_extents_e.text.split()]

                    material_e = shape_e.find(tag('instance_physics_material'))
                    if material_e is not None:
                        material_name = tidy_name(material_e.get('url'))
                        rigidbody['material'] = find_name(name_map, material_name)

                material_e = technique_e.find(tag('instance_physics_material'))
                if material_e is not None:
                    material_name = tidy_name(material_e.get('url'))
                    rigidbody['material'] = find_name(name_map, material_name)

                dynamic_e = technique_e.find(tag('dynamic'))
                if dynamic_e is not None:
                    value = dynamic_e.text.lower()
                    if value == 'true':
                        rigidbody['dynamic'] = True

                        mass_e = technique_e.find(tag('mass'))
                        if mass_e is not None:
                            rigidbody['mass'] = float(mass_e.text)

                        inertia_e = technique_e.find(tag('inertia'))
                        if inertia_e is not None:
                            inertia = [float(x) for x in inertia_e.text.split()]
                            if inertia[0] != 0.0 or inertia[1] != 0.0 or inertia[2] != 0.0:
                                rigidbody['inertia'] = inertia

                if len(rigidbody) > 0:
                    rigidbody_id = rigidbody_e.get('id', 'unknown')
                    rigidbody_name = rigidbody_e.get('name', rigidbody_id)
                    name_map[rigidbody_id] = rigidbody_name
                    rigid_body_map[rigidbody_id] = rigidbody
                    self.rigidbodys[rigidbody_name] = rigidbody

    def attach(self, json_asset):
        for name, rigidbody in self.rigidbodys.iteritems():
            json_asset.attach_physics_model(name, model=rigidbody)

class Dae2InstancePhysicsModel(object):

    class InstanceRigidBody(object):
        def __init__(self, name, body_name, target, params, parent_url):
            self.name = name
            self.body_name = body_name
            self.target = target
            self.params = params
            self.parent_url = parent_url

        def attach(self, json_asset, rigid_body_map, name_map, node_map):
            body_name = find_scoped_name(self.body_name, self.parent_url, name_map)
            body = find_scoped_node(self.body_name, self.parent_url, rigid_body_map)
            if not body:
                LOG.warning('Rigid body instance references an unknown physics model: %s -> %s',
                            self.name, self.body_name)
            target = node_map.get(self.target, None)
            if target:
                target_name = target.path
                # Check for non-root dynamic objects
                target_path = str(target_name)
                if '/' in target_path:
                    if body and body.get('dynamic', False):
                        LOG.error('Dynamic rigid body targets non-root graphics node: %s -> %s',
                                  body_name, target_path)
            else:
                target_name = NodeName(find_name(name_map, self.target))

            params = self.params
            if len(params) > 0:
                if body and 'dynamic' in params and params['dynamic'] != body.get('dynamic', False):
                    body_name = body_name + ':' + self.name
                    LOG.warning('Cloning ridig body because instance has conflicting dynamic properties: ' + body_name)
                    body = dict(body)
                    body['dynamic'] = params['dynamic']
                    del params['dynamic']
                    if 'mass' in params:
                        body['mass'] = params['mass']
                        del params['mass']
                    if 'inertia' in params:
                        body['inertia'] = params['inertia']
                        del params['inertia']
                json_asset.attach_physics_model(body_name, model=body)

                json_asset.attach_physics_node(self.name, body_name, target_name, params)
            else:
                json_asset.attach_physics_node(self.name, body_name, target_name)

    def __init__(self, physics_node_e):
        self.instance_rigidbodys = [ ]

        # Name...
        self.name = tidy_name(physics_node_e.get('url'))

        # Nodes...
        for node_index, rigid_body_e in enumerate(physics_node_e.findall(tag('instance_rigid_body'))):
            if node_index > 0:
                node_name = "%s-%u" % (self.name, node_index)
            else:
                node_name = self.name

            body_name = rigid_body_e.get('body')
            target = tidy_name(rigid_body_e.get('target'))
            params = { }

            technique_e = rigid_body_e.find(tag('technique_common'))
            if technique_e is not None:
                angular_velocity_e = technique_e.find(tag('angular_velocity'))
                if angular_velocity_e is not None:
                    velocity = [float(x) for x in angular_velocity_e.text.split()]
                    if velocity[0] != 0.0 or velocity[1] != 0.0 or velocity[2] != 0.0:
                        params['angularvelocity'] = velocity

                velocity_e = technique_e.find(tag('velocity'))
                if velocity_e is not None:
                    velocity = [float(x) for x in velocity_e.text.split()]
                    if velocity[0] != 0.0 or velocity[1] != 0.0 or velocity[2] != 0.0:
                        params['velocity'] = velocity

                dynamic_e = technique_e.find(tag('dynamic'))
                if dynamic_e is not None:
                    value = dynamic_e.text.lower()
                    if value == 'true':
                        params['dynamic'] = True

                        mass_e = technique_e.find(tag('mass'))
                        if mass_e is not None:
                            params['mass'] = float(mass_e.text)

                        inertia_e = technique_e.find(tag('inertia'))
                        if inertia_e is not None:
                            inertia = [float(x) for x in inertia_e.text.split()]
                            if inertia[0] != 0.0 or inertia[1] != 0.0 or inertia[2] != 0.0:
                                params['inertia'] = inertia

            rigidbody = Dae2InstancePhysicsModel.InstanceRigidBody(node_name, body_name, target, params, self.name)
            self.instance_rigidbodys.append(rigidbody)

    def attach(self, json_asset, physics_models, name_map, node_map):
        for rigidbody in self.instance_rigidbodys:
            rigidbody.attach(json_asset, physics_models, name_map, node_map)

#######################################################################################################################

class Dae2Animation(object):
    def __init__(self, animation_e, library_animations_e, name_map, animations_list):
        self.name = None
        self.sources = { }
        self.samplers = { }
        self.channels = [ ]
        self.children = [ ]

        # Name...
        self.id = animation_e.get('id', 'unknown')
        self.name = animation_e.get('name', self.id)
        LOG.debug('ANIMATION:%s', self.name)
        name_map[self.id] = self.name

        # Animation children
        animation_children_e = animation_e.findall(tag('animation'))
        for a in animation_children_e:
            child = Dae2Animation(a, library_animations_e, name_map, animations_list)
            if child.id != 'unknown':
                animations_list[child.id] = child
            self.children.append(child)

        # Sources...
        source_e = animation_e.findall(tag('source'))
        for s in source_e:
            technique_e = s.find(tag('technique_common'))
            accessor_e = technique_e.find(tag('accessor'))
            param_e = accessor_e.find(tag('param'))
            param_name = param_e.get('name')
            if param_e.get('type').lower() == 'name':
                array_e = s.find(tag('Name_array'))
                count = int(array_e.get('count', '0'))
                if (0 < count):
                    values_text = array_e.text
                    self.sources[s.get('id')] = { 'name': param_name, 'values': values_text.split() }
            else:
                array_e = s.find(tag('float_array'))
                count = int(array_e.get('count', '0'))
                stride = int(accessor_e.get('stride', '1'))
                if (0 < count):
                    values_text = array_e.text
                    float_values = [float(x) for x in values_text.split()]
                    if stride == 1:
                        values = float_values
                    else:
                        values = []
                        for i in range(0, count, stride):
                            values.append(float_values[i:i+stride])
                    self.sources[s.get('id')] = { 'name': param_name, 'values': values }

        sampler_e = animation_e.findall(tag('sampler'))
        for s in sampler_e:
            sampler_id = s.get('id')
            inputs = { }
            inputs_e = s.findall(tag('input'))
            for i in inputs_e:
                inputs[i.get('semantic')] = tidy_name(i.get('source'))
            self.samplers[sampler_id] = { 'inputs': inputs }

        channel_e = animation_e.findall(tag('channel'))
        for c in channel_e:
            sampler = tidy_name(c.get('source'))
            target = c.get('target')
            self.channels.append({ 'sampler': sampler, 'target': target})

        #print self.sources
        #print self.samplers
        #print self.channels

    def evaluate(self, time, sampler_id):
        sampler = self.samplers[sampler_id]
        times = self.sources[sampler['inputs']['INPUT']]['values']
        values = self.sources[sampler['inputs']['OUTPUT']]['values']
        interpolation = self.sources[sampler['inputs']['INTERPOLATION']]['values']

        if len(times) == 0 or len(values) == 0:
            LOG.error('Animation evaluation failed due to missing times or values in:%s', self.name)
        if len(times) != len(values):
            LOG.error('Animation evaluation failed due to mismatch in count of times and values in:%s', self.name)

        if time < times[0]:
            return values[0]
        if time > times[len(times)-1]:
            return values[len(values)-1]
        for i, t in enumerate(times):
            if t == time:
                return values[i]
            elif t > time:
                start_key = i - 1
                end_key = i
                if interpolation[start_key] != 'LINEAR':
                    LOG.warning('Animation evaluation linear sampling non linear keys of type:%s:in animation:%s',
                                interpolation[start_key], self.name)
                start_time = times[start_key]
                end_time = t
                delta = (time - start_time) / (end_time - start_time)
                start_val = values[start_key]
                end_val = values[end_key]
                if type(start_val) is float:
                    return (start_val + delta * (end_val - start_val))
                else:
                    if len(start_val) != len(end_val):
                        LOG.error('Animation evaluation failed in animation:%s:due to mismatched keyframe sizes',
                                  self.name)
                    result = []
                    for v in xrange(0, len(start_val)):
                        val1 = start_val[v]
                        val2 = end_val[v]
                        result.append(val1 + delta * (val2 - val1))
                    return result

        LOG.warning('Animation evaluation failed in animation:%s', self.name)
        return values[0]



#######################################################################################################################

def _decompose_matrix(matrix, node):
    sx = vmath.v3length(vmath.m43right(matrix))
    sy = vmath.v3length(vmath.m43up(matrix))
    sz = vmath.v3length(vmath.m43at(matrix))
    det = vmath.m43determinant(matrix)
    if not vmath.v3equal(vmath.v3create(sx, sy, sz), vmath.v3create(1, 1, 1)) or det < 0:
        if det < 0:
            LOG.warning('Detected negative scale in node "%s", not currently supported', node.name)
            sx *= -1
        if sx != 0:
            matrix = vmath.m43setright(matrix, vmath.v3muls(vmath.m43right(matrix), 1 / sx))
        else:
            matrix = vmath.m43setright(matrix, vmath.V3XAXIS)
        if sy != 0:
            matrix = vmath.m43setup(matrix, vmath.v3muls(vmath.m43up(matrix), 1 / sy))
        else:
            matrix = vmath.m43setup(matrix, vmath.V3YAXIS)
        if sz != 0:
            matrix = vmath.m43setat(matrix, vmath.v3muls(vmath.m43at(matrix), 1 / sz))
        else:
            matrix = vmath.m43setat(matrix, vmath.V3ZAXIS)
    else:
        sx = 1
        sy = 1
        sz = 1
    quat = vmath.quatfrom_m43(matrix)
    pos = vmath.m43pos(matrix)
    scale = vmath.v3create(sx, sy, sz)
    return (quat, pos, scale)

def _evaluate_node(node, time, target_data, global_scale):
    identity_matrix = vmath.M44IDENTITY
    matrix = identity_matrix

    node_e = node.element
    node_id = node_e.get('id')
    for node_param_e in node_e:
        overloads = []
        if target_data:
            if 'sid' in node_param_e.attrib:
                sid = node_param_e.attrib['sid']

                for anim in target_data['anims']:
                    for channel in anim.channels:
                        (target_node_id, _, parameter) = channel['target'].partition('/')
                        (target_sid, _, target_attrib) = parameter.partition('.')
                        if target_node_id == node_id and target_sid == sid:
                            overloads.append((target_attrib, anim.evaluate(time, channel['sampler'])))

        child_type = untag(node_param_e.tag)
        if child_type == 'translate':
            offset = [ float(x) for x in node_param_e.text.split() ]
            for overload_attrib, overload_value in overloads:
                if overload_attrib == 'X':
                    offset[0] = overload_value
                elif overload_attrib == 'Y':
                    offset[1] = overload_value
                elif overload_attrib == 'Z':
                    offset[2] = overload_value
                elif overload_attrib == '':
                    offset = overload_value

            translate_matrix = vmath.m43(1.0, 0.0, 0.0,
                                         0.0, 1.0, 0.0,
                                         0.0, 0.0, 1.0,
                                         offset[0], offset[1], offset[2])
            matrix = vmath.m43mulm44(translate_matrix, matrix)

        elif child_type == 'rotate':
            rotate = [ float(x) for x in node_param_e.text.split() ]
            for overload_attrib, overload_value in overloads:
                if isinstance(overload_value, list):
                    rotate[0] = overload_value[0]
                    rotate[1] = overload_value[1]
                    rotate[2] = overload_value[2]
                    rotate[3] = overload_value[3]
                else:
                    rotate[3] = overload_value
            if rotate[3] != 0.0:
                angle = rotate[3] / 180.0 * math.pi
                if rotate[0] == 1.0 and rotate[1] == 0.0 and rotate[2] == 0.0:
                    c = math.cos(angle)
                    s = math.sin(angle)
                    rotate_matrix = vmath.m33(1.0, 0.0, 0.0,
                                              0.0,   c,   s,
                                              0.0,  -s,   c)
                elif rotate[0] == 0.0 and rotate[1] == 1.0 and rotate[2] == 0.0:
                    c = math.cos(angle)
                    s = math.sin(angle)
                    rotate_matrix = vmath.m33(  c, 0.0,  -s,
                                              0.0, 1.0, 0.0,
                                                s, 0.0,   c)
                elif rotate[0] == 0.0 and rotate[1] == 0.0 and rotate[2] == 1.0:
                    c = math.cos(angle)
                    s = math.sin(angle)
                    rotate_matrix = vmath.m33(  c,   s, 0.0,
                                               -s,   c, 0.0,
                                              0.0, 0.0, 1.0)
                else:
                    rotate_matrix = vmath.m33from_axis_rotation(rotate[:3], angle)
                matrix = vmath.m33mulm44(rotate_matrix, matrix)

        elif child_type == 'scale':
            scale = [ float(x) for x in node_param_e.text.split() ]
            for overload_attrib, overload_value in overloads:
                if overload_attrib == 'X':
                    scale[0] = overload_value
                elif overload_attrib == 'Y':
                    scale[1] = overload_value
                elif overload_attrib == 'Z':
                    scale[2] = overload_value
                elif overload_attrib == '':
                    scale = overload_value
            scale_matrix = vmath.m33(scale[0],      0.0,      0.0,
                                          0.0, scale[1],      0.0,
                                          0.0,      0.0, scale[2])
            matrix = vmath.m33mulm44(scale_matrix, matrix)

        elif child_type == 'matrix':
            if len(overloads) > 1:
                LOG.warning('Found multiple matrices animating a single node')
            if overloads:
                for overload_attrib, overload_value in overloads:
                    local_matrix = vmath.m44transpose(overload_value)
            else:
                local_matrix = vmath.m44transpose([ float(x) for x in node_param_e.text.split() ])
            if matrix != identity_matrix:
                matrix = vmath.m44mul(local_matrix, matrix)
            else:
                matrix = local_matrix

    # Hard coded scale
    if global_scale != 1.0:
        matrix = vmath.m44setpos(matrix, vmath.v4muls(vmath.m44pos(matrix), global_scale))

    matrix = vmath.tidy(matrix) # Remove tiny values

    return vmath.m43from_m44(matrix)

class Dae2AnimationClip(object):
    # pylint: disable=R0914
    def __init__(self, animation_clip_e, global_scale, upaxis_rotate, library_animation_clips_e, name_map, animations,
                 nodes, default_root):
        self.name = None
        self.scale = global_scale
        self.source_anims = [ ]
        self.anim = None

        # Name...
        if not default_root:
            self.id = animation_clip_e.get('id', 'unknown')
            self.name = animation_clip_e.get('name', self.id)
        else:
            name = 'default_' + default_root
            self.id = name
            self.name = name
        LOG.debug('ANIMATION:%s', self.name)
        name_map[self.id] = self.name

        def add_anim_and_children(anim, anim_list):
            anim_list.append(anim)
            for child in anim.children:
                add_anim_and_children(child, anim_list)

        if not default_root:
            for instance_animation_e in animation_clip_e.findall(tag('instance_animation')):
                anim = animations[tidy_name(instance_animation_e.get('url'))]
                if anim is not None:
                    add_anim_and_children(anim, self.source_anims)
        else:
            for anim in animations:
                add_anim_and_children(animations[anim], self.source_anims)

        # TODO: move the following code to process method

        #   { 'num_frames': 2,
        #     'numNodes' : 3,
        #     'frame_rate': 30,
        #     'hiearchy': { 'joints': ['root', -1, [0,0,0,1], [0,0,0]] },
        #     'bounds': [ { 'center': [0,0,0], 'halfExtent': [10,10,10] } ],
        #     'joint_data': [ { 'time': 0, 'rotation': [0,0,0,1], 'translation': [0,0,0] } ]

        global_times = []

        def __find_node_in_dict(node_dict, node_name):

            def __find_node(node_root, node_name):
                if node_root.id == node_name:
                    return node_root

                if node_root.children:
                    for c in node_root.children:
                        result = __find_node(c, node_name)
                        if result:
                            return result
                return None

            for n in node_dict:
                result = __find_node(node_dict[n], node_name)
                if result:
                    return result
            return None

        def __node_root(node_name, nodes):
            node = __find_node_in_dict(nodes, node_name)
            if node is None:
                return None
            while node.parent:
                node = node.parent

            return node.id

        def __is_node(node_name, nodes):
            node = __find_node_in_dict(nodes, node_name)
            return node is not None

        # Work out the list of keyframe times and animations required for each target
        targets = {}
        for anim in self.source_anims:
            for channel in anim.channels:
                target_parts = channel['target'].split('/')
                target = target_parts[0]
                target_channel = target_parts[1]

                if __is_node(target, nodes) and target_channel != 'visibility':
                    # for default animations reject targets which aren't under the same hierarchy
                    if not default_root or default_root == __node_root(target, nodes):
                        sampler = anim.samplers[channel['sampler']]
                        sampler_input = sampler['inputs']['INPUT']
                        if sampler_input in anim.sources:
                            if not target in targets:
                                targets[target] = { 'anims': [], 'keyframe_times': [] }
                            if anim not in targets[target]['anims']:
                                targets[target]['anims'].append(anim)

                            # Find all the keyframe times for the animation
                            times = targets[target]['keyframe_times']
                            time_inputs = anim.sources[sampler_input]
                            if time_inputs['name'] == 'TIME':
                                for t in time_inputs['values']:
                                    if t not in times:
                                        times.append(t)
                                    if t not in global_times:
                                        global_times.append(t)

        if len(targets) == 0:
            return

        # Build a hierarchy from the keys in targets and any intermediate nodes (or nodes in the skin)
        start_joints = targets.keys()
        hierarchy = build_joint_hierarchy(start_joints, nodes)
        runtime_joint_names = [ ]
        runtime_joint_parents = [ ]
        for joint in hierarchy:
            runtime_joint_names.append(joint['node'].name)
            runtime_joint_parents.append(joint['parent'])

        joint_hierarchy = {
            'numNodes': len(runtime_joint_names),
            'names': runtime_joint_names,
            'parents': runtime_joint_parents
            }

        # Work out the start and end time for the animation
        global_times = sorted(global_times)
        start_time = global_times[0]
        end_time = global_times[len(global_times)-1]

        # TODO: reenable when sampling between keys works
        #if not default_root:
        #    start_time = animation_clip_e.get('start', start_time)
        #    end_time = animation_clip_e.get('end', end_time)

        # Work out animation lengths and keyframe counts
        anim_length = end_time - start_time

        # Generate some joint data for the animation
        frames = [ ]

        for j, joint in enumerate(hierarchy):
            orig_index = joint['orig_index']
            if orig_index is not -1:
                target_name = start_joints[orig_index]
            else:
                target_name = None
            node = joint['node']
            node.animated = True
            joint_data = [ ]
            if target_name is not None and target_name in targets:
                target_data = targets[target_name]
                key_times = target_data['keyframe_times']
                key_times = sorted(key_times)
                if key_times[0] > start_time:
                    key_times.insert(0, start_time)
                if key_times[len(key_times) - 1] < end_time:
                    key_times.append(end_time)
                for t in key_times:
                    node_matrix = _evaluate_node(node, t, target_data, global_scale)
                    qps = _decompose_matrix(node_matrix, node)
                    frame_time = t - start_time
                    joint_data.append({'time': frame_time, 'rotation': qps[0], 'translation': qps[1], 'scale': qps[2] })
            else:
                # no targets so we simply add a start key
                node_matrix = _evaluate_node(node, start_time, None, global_scale)
                qps = _decompose_matrix(node_matrix, node)
                joint_data.append({'time': 0, 'rotation': qps[0], 'translation': qps[1], 'scale': qps[2] })

            # TODO: remove translation of [0, 0, 0]
            channels = { 'rotation': True, 'translation': True }
            base_frame = { }
            if len(joint_data) > 1:
                varying_rotation = False
                varying_translation = False
                varying_scale = False
                init_rotation = joint_data[0]['rotation']
                init_translation = joint_data[0]['translation']
                init_scale = joint_data[0]['scale']
                for f in joint_data[1:]:
                    if varying_rotation or f['rotation'] != init_rotation:
                        varying_rotation = True
                    if varying_translation or f['translation'] != init_translation:
                        varying_translation = True
                    if varying_scale or f['scale'] != init_scale:
                        varying_scale = True
                if not varying_rotation:
                    base_frame['rotation'] = init_rotation
                    for f in joint_data:
                        del f['rotation']
                if not varying_translation:
                    base_frame['translation'] = init_translation
                    for f in joint_data:
                        del f['translation']
                if not varying_scale:
                    if not vmath.v3equal(init_scale, vmath.v3create(1, 1, 1)):
                        base_frame['scale'] = init_scale
                        channels['scale'] = True
                    for f in joint_data:
                        del f['scale']
                else:
                    channels['scale'] = True
            elif len(joint_data) == 1:
                init_rotation = joint_data[0]['rotation']
                init_translation = joint_data[0]['translation']
                init_scale = joint_data[0]['scale']
                base_frame = { 'rotation': init_rotation,
                               'translation': init_translation }
                if not vmath.v3equal(init_scale, vmath.v3create(1, 1, 1)):
                    base_frame['scale'] = init_scale
                    channels['scale'] = True
                joint_data = None

            frame_data = { 'channels': channels }
            if joint_data is not None:
                frame_data['keyframes'] = joint_data
            if len(base_frame.keys()):
                frame_data['baseframe'] = base_frame
            frames.append( frame_data )

        # Work out what channels of data are included in the animation
        channel_union = set(frames[0]['channels'].keys())
        uniform_channels = True
        for f in frames[1:]:
            if not uniform_channels or channel_union.symmetric_difference(f['channels'].keys()):
                channel_union = channel_union.union(f['channels'].keys())
                uniform_channels = False

        if uniform_channels:
            # if we have the same channels on all nodes then don't replicate the info
            for f in frames:
                del f['channels']

        # Generate some bounds, for now we calculate the bounds of the root nodes animation and extend them
        # by the length of the joint hierarchy
        maxflt = sys.float_info.max
        bound_min = vmath.v3create(maxflt, maxflt, maxflt)
        bound_max = vmath.v3create(-maxflt, -maxflt, -maxflt)

        joint_lengths = [0] * len(hierarchy)
        for j, joint in enumerate(hierarchy):
            parent_index = joint['parent']
            if parent_index is -1:
                if 'baseframe' in frames[j] and 'translation' in frames[j]['baseframe']:
                    bound_min = vmath.v3min(bound_min, frames[j]['baseframe']['translation'])
                    bound_max = vmath.v3max(bound_max, frames[j]['baseframe']['translation'])
                else:
                    f = frames[j]['keyframes']
                    for frame in f:
                        bound_min = vmath.v3min(bound_min, frame['translation'])
                        bound_max = vmath.v3max(bound_max, frame['translation'])
                joint_lengths[j] = 0
            else:
                if 'baseframe' in frames[j] and 'translation' in frames[j]['baseframe']:
                    bone_length = vmath.v3length(frames[j]['baseframe']['translation'])
                else:
                    bone_length = vmath.v3length(frames[j]['keyframes'][0]['translation'])
                joint_lengths[j] = joint_lengths[parent_index] + bone_length

        max_joint_length = max(joint_lengths)

        bounds = []
        center = vmath.v3muls(vmath.v3add(bound_min, bound_max), 0.5)
        half_extent = vmath.v3sub(center, bound_min)
        half_extent = vmath.v3add(half_extent, vmath.v3create(max_joint_length, max_joint_length, max_joint_length))
        bounds.append({'time': 0, 'center': center, 'halfExtent': half_extent })
        bounds.append({'time': anim_length, 'center': center, 'halfExtent': half_extent })

        self.anim = { 'length': anim_length,
                      'numNodes': len(joint_hierarchy['names']),
                      'hierarchy': joint_hierarchy,
                      'channels': dict.fromkeys(channel_union, True),
                      'nodeData': frames,
                      'bounds': bounds }
    # pylint: enable=R0914

    def attach(self, json_asset, name_map):
        json_asset.attach_animation(self.name, self.anim)

#######################################################################################################################

# pylint: disable=R0914
def parse(input_filename="default.dae", output_filename="default.json", asset_url="", asset_root=".", infiles=None,
          options=None):
    """Untility function to convert a Collada file into a JSON file."""

    definitions_asset = standard_include(infiles)

    animations = { }
    animation_clips = { }
    geometries = { }
    effects = { }
    materials = { }
    images = { }
    lights = { }
    nodes = { }
    physics_materials = { }
    physics_models = { }
    physics_bodies = { }
    physics_nodes = { }

    name_map = { }
    geometry_names = { }
    effect_names = { }
    light_names = { }
    node_names = { }
    node_map = { }

    url_handler = UrlHandler(asset_root, input_filename)

    # DOM stuff from here...
    try:
        collada_e = ElementTree.parse(input_filename).getroot()
    except IOError as e:
        LOG.error('Failed loading: %s', input_filename)
        LOG.error('  >> %s', e)
        exit(1)
    except ExpatError as e:
        LOG.error('Failed processing: %s', input_filename)
        LOG.error('  >> %s', e)
        exit(2)
    else:
        if collada_e is not None:
            fix_sid(collada_e, None)

            # Asset...
            asset_e = collada_e.find(tag('asset'))

            # What is the world scale?
            scale = 1.0
            unit_e = asset_e.find(tag('unit'))
            if unit_e is not None:
                scale = float(unit_e.get('meter', '1.0'))

            # What is the up axis?
            upaxis_rotate = None
            upaxis_e = asset_e.find(tag('up_axis'))
            if upaxis_e is not None:
                if upaxis_e.text == 'X_UP':
                    upaxis_rotate = [ 0.0, 1.0, 0.0, 0.0,
                                     -1.0, 0.0, 0.0, 0.0,
                                      0.0, 0.0, 1.0, 0.0,
                                      0.0, 0.0, 0.0, 1.0 ]
                elif upaxis_e.text == 'Z_UP':
                    upaxis_rotate = [ 1.0, 0.0,  0.0, 0.0,
                                      0.0, 0.0, -1.0, 0.0,
                                      0.0, 1.0,  0.0, 0.0,
                                      0.0, 0.0,  0.0, 1.0 ]
                LOG.info('Up axis:%s', upaxis_e.text)

            # Core COLLADA elements are:
            #
            # library_animation_clips       - not supported
            # library_animations            - not supported
            # instance_animation            - not supported
            # library_cameras               - not supported
            # instance_camera               - supported
            # library_controllers           - not supported
            # instance_controller           - supported
            # library_geometries            - supported
            # instance_geometry             - supported
            # library_lights                - supported
            # instance_light                - supported
            # library_nodes                 - not supported
            # instance_node                 - supported
            # library_visual_scenes         - supported
            # instance_visual_scene         - not supported
            # scene                         - not supported

            geometries_e = collada_e.find(tag('library_geometries'))
            if geometries_e is not None:
                for x in geometries_e.findall(tag('geometry')):
                    g = Dae2Geometry(x, scale, geometries_e, name_map, geometry_names)
                    # For now we only support mesh and convex_mesh
                    if g.type == 'mesh' or g.type == 'convex_mesh':
                        geometries[g.id] = g
            else:
                LOG.warning('Collada file without:library_geometries:%s', input_filename)

            lights_e = collada_e.find(tag('library_lights'))
            if lights_e is not None:
                for x in lights_e.findall(tag('light')):
                    l = Dae2Light(x, name_map, light_names)
                    lights[l.id] = l

            controllers_e = collada_e.find(tag('library_controllers'))
            visual_scenes_e = collada_e.find(tag('library_visual_scenes'))
            if visual_scenes_e is not None:
                visual_scene_e = visual_scenes_e.findall(tag('visual_scene'))
                if visual_scene_e is not None:
                    if len(visual_scene_e) > 1:
                        LOG.warning('Collada file with more than 1:visual_scene:%s', input_filename)
                    node_e = visual_scene_e[0].findall(tag('node'))
                    for n in node_e:
                        n = Dae2Node(n, scale, None, upaxis_rotate, None, controllers_e, collada_e,
                                     name_map, node_names, node_map, geometries)
                        nodes[n.id] = n
                    if len(node_e) == 0:
                        LOG.warning('Collada file without:node:%s', input_filename)
                else:
                    LOG.warning('Collada file without:visual_scene:%s', input_filename)
            else:
                LOG.warning('Collada file without:library_visual_scenes:%s', input_filename)

            animations_e = collada_e.find(tag('library_animations'))
            if animations_e is not None:
                for x in animations_e.findall(tag('animation')):
                    a = Dae2Animation(x, animations_e, name_map, animations)
                    animations[a.id] = a

            animation_clips_e = collada_e.find(tag('library_animation_clips'))
            if animation_clips_e is not None:
                for x in animation_clips_e.findall(tag('animation_clip')):
                    c = Dae2AnimationClip(x, scale, upaxis_rotate, animation_clips_e, name_map, animations, nodes, None)
                    animation_clips[c.id] = c
            else:
                if animations_e is not None:
                    LOG.info('Exporting default animations from:%s', input_filename)
                    for n in nodes:
                        c = Dae2AnimationClip(x, scale, upaxis_rotate, None, name_map, animations, nodes, n)
                        if c.anim:
                            animation_clips[c.id] = c


            # FX COLLADA elements are:
            #
            # library_effects               - supported
            # instance_effect               - supported
            # library_materials             - supported
            # instance_material             - supported
            # library_images                - supported
            # instance_image                - not supported

            # Images have to be read before effects and materials
            images_e = collada_e.find(tag('library_images'))
            if images_e is not None:
                for x in images_e.findall(tag('image')):
                    i = Dae2Image(x, url_handler, name_map)
                    images[i.id] = i

            effects_e = collada_e.find(tag('library_effects'))
            if effects_e is not None:
                for x in effects_e.iter(tag('image')):
                    i = Dae2Image(x, url_handler, name_map)
                    images[i.id] = i

                for x in effects_e.findall(tag('effect')):
                    e = Dae2Effect(x, url_handler, name_map, effect_names)
                    effects[e.id] = e
            else:
                LOG.warning('Collada file without:library_effects:%s', input_filename)
                # json.AddObject("default")
                # json.AddString("type", "lambert")

            materials_e = collada_e.find(tag('library_materials'))
            if materials_e is not None:
                for x in materials_e.findall(tag('material')):
                    m = Dae2Material(x, name_map)
                    materials[m.id] = m
            else:
                LOG.warning('Collada file without:library_materials:%s', input_filename)
                # json.AddObject("default")
                # json.AddString("effect", "default")

            # Physics COLLADA elements are:
            #
            # library_force_fields          - not supported
            # instance_force_field          - not supported
            # library_physics_materials     - supported
            # instance_physics_material     - supported
            # library_physics_models        - supported
            # instance_physics_model        - supported
            # library_physics_scenes        - supported
            # instance_physics_scene        - not supported
            # instance_rigid_body           - supported
            # instance_rigid_constraint     - not supported

            physics_materials_e = collada_e.find(tag('library_physics_materials'))
            if physics_materials_e is not None:
                for x in physics_materials_e.findall(tag('physics_material')):
                    m = Dae2PhysicsMaterial(x, name_map)
                    physics_materials[m.id] = m

            physics_models_e = collada_e.find(tag('library_physics_models'))
            if physics_models_e is not None:
                for x in physics_models_e.findall(tag('physics_model')):
                    m = Dae2PhysicsModel(x, geometries_e, physics_bodies, name_map)
                    physics_models[m.id] = m

            physics_scenes_e = collada_e.find(tag('library_physics_scenes'))
            if physics_scenes_e is not None:
                physics_scene_e = physics_scenes_e.findall(tag('physics_scene'))
                if physics_scene_e is not None:
                    if len(physics_scene_e) > 1:
                        LOG.warning('Collada file with more than 1:physics_scene:%s', input_filename)
                    for x in physics_scene_e[0].findall(tag('instance_physics_model')):
                        i = Dae2InstancePhysicsModel(x)
                        physics_nodes[i.name] = i

            # Drop reference to the etree
            collada_e = None

    # Process asset...
    for _, node in nodes.iteritems():
        node.process(nodes)

    for _, geometry in geometries.iteritems():
        geometry.process(definitions_asset, nodes, options.nvtristrip, materials, effects)

    # Create JSON...
    json_asset = JsonAsset()

    def _attach(asset_type):
        if options.include_types is not None:
            return asset_type in options.include_types
        if options.exclude_types is not None:
            return asset_type not in options.exclude_types
        return True

    # By default attach images map
    if _attach('images'):
        for _, image in images.iteritems():
            image.attach(json_asset)

    if _attach('effects'):
        for _, effect in effects.iteritems():
            effect.attach(json_asset, definitions_asset)

    if _attach('materials'):
        for _, material in materials.iteritems():
            material.attach(json_asset, definitions_asset, name_map)

    if _attach('geometries'):
        for _, geometry in geometries.iteritems():
            geometry.attach(json_asset)

    if _attach('lights'):
        for _, light in lights.iteritems():
            light.attach(json_asset, definitions_asset)

    if _attach('nodes'):
        for _, node in nodes.iteritems():
            node.attach(json_asset, url_handler, name_map)

    if _attach('animations'):
        for _, animation_clip in animation_clips.iteritems():
            animation_clip.attach(json_asset, name_map)

    if _attach('physicsmaterials'):
        for _, physics_material in physics_materials.iteritems():
            physics_material.attach(json_asset)

    if _attach('physicsnodes'):
        for _, physics_node in physics_nodes.iteritems():
            physics_node.attach(json_asset, physics_bodies, name_map, node_map)

    if _attach('physicsmodels'):
        for _, physics_model in physics_models.iteritems():
            physics_model.attach(json_asset)

    if not options.keep_unused_images:
        remove_unreferenced_images(json_asset)

    # Write JSON...
    try:
        standard_json_out(json_asset, output_filename, options)
    except IOError as e:
        LOG.error('Failed processing: %s', output_filename)
        LOG.error('  >> %s', e)
        exit(3)

    return json_asset
# pylint: enable=R0914

def main():
    description = "Convert Collada (.dae) files into a Turbulenz JSON asset."

    parser = standard_parser(description)
    parser.add_option("--nvtristrip", action="store", dest="nvtristrip", default=None,
            help="path to NvTriStripper, setting this enables "
            "vertex cache optimizations")

    standard_main(parse, __version__, description, __dependencies__, parser)

if __name__ == "__main__":
    exit(main())

########NEW FILE########
__FILENAME__ = effect2json
#!/usr/bin/python
# Copyright (c) 2010-2011,2013 Turbulenz Limited
"""
Convert Effect Yaml (.effect) files into a Turbulenz JSON asset.
"""

import logging
LOG = logging.getLogger('asset')

import yaml

# pylint: disable=W0403
from stdtool import standard_main, standard_json_out
from asset2json import JsonAsset
# pylint: enable=W0403

__version__ = '1.0.0'
__dependencies__ = ['asset2json']

#######################################################################################################################

def parse(input_filename="default.effect", output_filename="default.json", asset_url="", asset_root=".", infiles=None,
          options=None):
    """
    Untility function to convert a Effect Yaml (.effect) into a JSON file.
    Known built-in textures are: default, quadratic, white, nofalloff, black, flat
    """
    try:
        with open(input_filename, 'r') as source:
            try:
                effects = yaml.load(source)
            # pylint: disable=E1101
            except yaml.scanner.ScannerError as e:
            # pylint: enable=E1101
                LOG.error('Failed processing: %s', input_filename)
                LOG.error('  >> %s', e)
            else:
                json_asset = JsonAsset()
                for effect_name, effect_parameters in effects.iteritems():
                    effect_type = effect_parameters.pop('type', None)
                    shader = effect_parameters.pop('shader', None)
                    meta = effect_parameters.pop('meta', None)
                    json_asset.attach_effect(effect_name, effect_type, effect_parameters, shader, meta)

                standard_json_out(json_asset, output_filename, options)
                return json_asset
    except IOError as e:
        LOG.error('Failed processing: %s', output_filename)
        LOG.error('  >> %s', e)
        return None

if __name__ == "__main__":
    try:
        standard_main(parse, __version__,
                      "Convert Effect Yaml (.effect) files into a Turbulenz JSON asset.",
                      __dependencies__)
    # pylint: disable=W0703
    except Exception as err:
        LOG.critical('Unexpected exception: %s', err)
        exit(1)
    # pylint: enable=W0703

########NEW FILE########
__FILENAME__ = exportevents
#!/usr/bin/env python
# Copyright (c) 2012-2013 Turbulenz Limited

from logging import basicConfig, CRITICAL, INFO, WARNING

import argparse
from urllib3 import connection_from_url
from urllib3.exceptions import HTTPError, SSLError
from simplejson import loads as json_loads, dump as json_dump
from gzip import GzipFile
from zlib import decompress as zlib_decompress
from time import strptime, strftime, gmtime
from calendar import timegm
from re import compile as re_compile
from sys import stdin, argv
from os import mkdir
from os.path import exists as path_exists, join as path_join, normpath
from getpass import getpass, GetPassWarning
from base64 import urlsafe_b64decode

__version__ = '2.1.2'
__dependencies__ = []


HUB_COOKIE_NAME = 'hub'
HUB_URL = 'https://hub.turbulenz.com/'

DATATYPE_DEFAULT = 'events'
DATATYPE_URL = { 'events': '/dynamic/project/%s/event-log',
                 'users': '/dynamic/project/%s/user-info' }

DAY = 86400
TODAY_START = (timegm(gmtime()) / DAY) * DAY

# pylint: disable=C0301
USERNAME_PATTERN = re_compile('^[a-z0-9]+[a-z0-9-]*$') # usernames
PROJECT_SLUG_PATTERN = re_compile('^[a-zA-Z0-9\-]*$') # game
# pylint: enable=C0301

class DateRange(object):
    """Maintain a time range between two dates. If only a start time is given it will generate a 24 hour period
       starting at that time. Defaults to the start of the current day if no times are given"""
    def __init__(self, start=TODAY_START, end=None):
        self.start = start
        if end:
            self.end = end
        else:
            self.end = start + DAY
        if self.start > self.end:
            raise ValueError('Start date can\'t be greater than the end date')

        def _range_str(t):
            if t % DAY:
                return strftime('%Y-%m-%d %H:%M:%SZ', gmtime(t))
            else:
                return strftime('%Y-%m-%d', gmtime(t))
        self.start_str = _range_str(self.start)
        if self.end % DAY:
            self.end_str = _range_str(self.end)
        else:
            self.end_str = _range_str(self.end - DAY)


    def filename_str(self):
        if self.start_str == self.end_str:
            return self.start_str
        elif int(self.start / DAY) == int(self.end / DAY):
            result = '%s_-_%s' % (strftime('%Y-%m-%d %H:%M:%SZ', gmtime(self.start)),
                                  strftime('%Y-%m-%d %H:%M:%SZ', gmtime(self.end)))
            return result.replace(' ', '_').replace(':', '-')
        else:
            result = '%s_-_%s' % (self.start_str, self.end_str)
            return result.replace(' ', '_').replace(':', '-')

    @staticmethod
    def parse(range_str):
        date_format = '%Y-%m-%d'
        range_parts = range_str.split(':')

        if len(range_parts) < 1:
            error('Date not set')
            exit(1)
        elif len(range_parts) > 2:
            error('Can\'t provide more than two dates for date range')
            exit(1)

        try:
            start = int(timegm(strptime(range_parts[0], date_format)))
            end = None
            if len(range_parts) == 2:
                end = int(timegm(strptime(range_parts[1], date_format))) + DAY
        except ValueError:
            error('Dates must be in the yyyy-mm-dd format')
            exit(1)

        return DateRange(start, end)


def log(message, new_line=True):
    print '\r >> %s' % message,
    if new_line:
        print

def error(message):
    log('[ERROR]   - %s' % message)

def warning(message):
    log('[WARNING] - %s' % message)


def _parse_args():
    parser = argparse.ArgumentParser(description="Export event logs and anonymised user information of a game.")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-s", "--silent", action="store_true", help="silent running")
    parser.add_argument("--version", action='version', version=__version__)

    parser.add_argument("-u", "--user", action="store",
                        help="Hub login username (will be requested if not provided)")
    parser.add_argument("-p", "--password", action="store",
                        help="Hub login password (will be requested if not provided)")

    parser.add_argument("-t", "--type", action="store", default=DATATYPE_DEFAULT,
                        help="type of data to download, either events or users (defaults to " + DATATYPE_DEFAULT + ")")
    parser.add_argument("-d", "--daterange", action="store", default=TODAY_START,
                        help="individual 'yyyy-mm-dd' or range 'yyyy-mm-dd : yyyy-mm-dd' of dates to get the data " \
                             "for (defaults to today)")
    parser.add_argument("-o", "--outputdir", action="store", default="",
                        help="folder to output the downloaded files to (defaults to current directory)")

    parser.add_argument("-w", "--overwrite", action="store_true",
                        help="if a file to be downloaded exists in the output directory, " \
                             "overwrite instead of skipping it")
    parser.add_argument("--indent", action="store_true", help="apply indentation to the JSON output")
    parser.add_argument("--hub", default=HUB_URL, help="Hub url (defaults to https://hub.turbulenz.com/)")

    parser.add_argument("project", metavar='project_slug', help="Slug of Hub project you wish to download from")

    args = parser.parse_args(argv[1:])

    if args.silent:
        basicConfig(level=CRITICAL)
    elif args.verbose:
        basicConfig(level=INFO)
    else:
        basicConfig(level=WARNING)

    if not PROJECT_SLUG_PATTERN.match(args.project):
        error('Incorrect "project" format')
        exit(-1)

    username = args.user
    if not username:
        print 'Username: ',
        username = stdin.readline()
        if not username:
            error('Login information required')
            exit(-1)
        username = username.strip()
        args.user = username

    if not USERNAME_PATTERN.match(username):
        error('Incorrect "username" format')
        exit(-1)

    if not args.password:
        try:
            args.password = getpass()
        except GetPassWarning:
            error('Echo free password entry unsupported. Please provide a --password argument')
            return -1

    if args.type not in ['events', 'users']:
        error('Type must be one of \'events\' or \'users\'')
        exit(1)

    if isinstance(args.daterange, int):
        args.daterange = DateRange(args.daterange)
    else:
        args.daterange = DateRange.parse(args.daterange)

    return args


def login(connection, options):
    username = options.user
    password = options.password

    if not options.silent:
        log('Login as "%s".' % username)

    credentials = {'login': username,
                   'password': password,
                   'source': '/tool'}

    try:
        r = connection.request('POST',
                               '/dynamic/login',
                               fields=credentials,
                               retries=1,
                               redirect=False)
    except (HTTPError, SSLError):
        error('Connection to Hub failed!')
        exit(-1)

    if r.status != 200:
        if r.status == 301:
            redirect_location = r.headers.get('location', '')
            end_domain = redirect_location.find('/dynamic/login')
            error('Login is being redirected to "%s". Please verify the Hub URL.' % redirect_location[:end_domain])
        else:
            error('Wrong user login information!')
        exit(-1)

    cookie = r.headers.get('set-cookie', None)
    login_info = json_loads(r.data)

    # pylint: disable=E1103
    if not cookie or HUB_COOKIE_NAME not in cookie or login_info.get('source') != credentials['source']:
        error('Hub login failed!')
        exit(-1)
    # pylint: enable=E1103

    return cookie


def logout(connection, cookie):
    try:
        connection.request('POST',
                           '/dynamic/logout',
                           headers={'Cookie': cookie},
                           redirect=False)
    except (HTTPError, SSLError) as e:
        error(str(e))


def _request_data(options):
    daterange = options.daterange
    params = { 'start_time': daterange.start,
               'end_time': daterange.end,
               'version': __version__ }

    connection = connection_from_url(options.hub, timeout=8.0)
    cookie = login(connection, options)

    try:
        r = connection.request('GET',
                               DATATYPE_URL[options.type] % options.project,
                               headers={'Cookie': cookie,
                                        'Accept-Encoding': 'gzip'},
                               fields=params,
                               redirect=False)
    except (HTTPError, SSLError) as e:
        error(e)
        exit(-1)

    # pylint: disable=E1103
    r_data = json_loads(r.data)
    if r.status != 200:
        error_msg = 'Wrong Hub answer.'
        if r_data.get('msg', None):
            error_msg += ' ' + r_data['msg']
        if r.status == 403:
            error_msg += ' Make sure the project you\'ve specified exists and you have access to it.'
        error(error_msg)
        exit(-1)
    # pylint: enable=E1103

    if options.verbose:
        log('Data received from the hub')
        log('Logging out')
    logout(connection, cookie)

    return r_data


def write_to_file(options, data, filename=None, output_path=None, force_overwrite=False):
    if not filename:
        filename = '%s-%s-%s.json' % (options.project, options.type, options.daterange.filename_str())

    try:
        if not output_path:
            output_path = normpath(path_join(options.outputdir, filename))

        if path_exists(output_path):
            if options.overwrite or force_overwrite:
                if not options.silent:
                    warning('Overwriting existing file: %s' % output_path)
            elif not options.silent:
                warning('Skipping existing file: %s' % output_path)
                return

        indentation = None
        if options.indent:
            indentation = 4
            if isinstance(data, str):
                data = json_loads(data)

        with open(output_path, 'wb') as fout:
            if isinstance(data, str):
                fout.write(data)
            else:
                json_dump(data, fout, indent=indentation)

        if options.verbose:
            log('Finished writing to: %s' % output_path)

    except (IOError, OSError) as e:
        error(e)
        exit(-1)


try:
    # pylint: disable=F0401
    from Crypto.Cipher.AES import new as aes_new, MODE_CBC
    # pylint: enable=F0401

    def decrypt_data(data, key):
        # Need to use a key of length 32 bytes for AES-256
        if len(key) != 32:
            error('Invalid key length for AES-256')
            exit(-1)

        # IV is last 16 bytes
        iv = data[-16 :]
        data = data[: -16]

        data = aes_new(key, MODE_CBC, iv).decrypt(data)

        # Strip PKCS7 padding required for CBC
        if len(data) % 16:
            error('Corrupted data - invalid length')
            exit(-1)
        num_padding = ord(data[-1])
        if num_padding > 16:
            error('Corrupted data - invalid padding')
            exit(-1)

        return data[: -num_padding]

except ImportError:
    from io import BytesIO
    from subprocess import Popen, STDOUT, PIPE
    from struct import pack

    def decrypt_data(data, key):
        # Need to use a key of length 32 bytes for AES-256
        if len(key) != 32:
            error('Invalid key length for AES-256')
            exit(-1)

        aesdata = BytesIO()
        aesdata.write(key)
        aesdata.write(pack('I', len(data)))
        aesdata.write(data)
        process = Popen('aesdecrypt', stderr=STDOUT, stdout=PIPE, stdin=PIPE, shell=True)
        output, _ = process.communicate(input=aesdata.getvalue())
        retcode = process.poll()
        if retcode != 0:
            error('Failed to run aesdecrypt, check it is on the path or install PyCrypto')
            exit(-1)
        return str(output)


def get_log_files_local(options, files_list, enc_key):

    verbose = options.verbose
    silent = options.silent
    overwrite = options.overwrite
    output_dir = options.outputdir
    filename_prefix = options.project + '-'

    try:
        for filename in files_list:
            if filename.startswith('http'):
                error('Unexpected file to retrieve')
                exit(-1)
            # Format v1: 'eventlogspath/gamefolder/events-yyyy-mm-dd.json.gz'
            # Format v2: 'eventlogspath/gamefolder/events-yyyy-mm-dd.bin'
            # Convert to 'gameslug-events-yyyy-mm-dd.json'
            filename_patched = filename_prefix + filename.rsplit('/', 1)[-1].split('.', 1)[0] + '.json'

            output_path = normpath(path_join(output_dir, filename_patched))
            if not overwrite and path_exists(output_path):
                if not silent:
                    warning('Skipping existing file: %s' % output_path)
                continue

            if verbose:
                log('Retrieving file: %s' % filename_patched)

            if filename.endswith('.bin'):
                with open(filename, 'rb') as fin:
                    file_content = fin.read()
                file_content = decrypt_data(file_content, enc_key)
                file_content = zlib_decompress(file_content)

            else:   # if filename.endswith('.json.gz'):
                gzip_file = GzipFile(filename=filename, mode='rb')
                file_content = gzip_file.read()
                gzip_file.close()
                file_content = decrypt_data(file_content, enc_key)

            write_to_file(options, file_content, filename=filename_patched, output_path=output_path)

    except (IOError, OSError) as e:
        error(e)
        exit(-1)


def get_log_files_s3(options, files_list, enc_key, connection):

    verbose = options.verbose
    silent = options.silent
    overwrite = options.overwrite
    output_dir = options.outputdir
    filename_prefix = options.project + '-'

    try:
        for filename in files_list:
            # Format v1: 'https://bucket.s3.amazonaws.com/gamefolder/events-yyyy-mm-dd.json?AWSAccessKeyId=keyid
            #             &Expires=timestamp&Signature=signature'
            # Format v2: 'https://bucket.s3.amazonaws.com/gamefolder/events-yyyy-mm-dd.bin?AWSAccessKeyId=keyid
            #             &Expires=timestamp&Signature=signature'
            # Convert to 'gameslug-events-yyyy-mm-dd.json'
            filename_cleaned = filename.split('?', 1)[0].rsplit('/', 1)[-1]
            filename_patched = filename_prefix + filename_cleaned.split('.', 1)[0] + '.json'

            output_path = normpath(path_join(output_dir, filename_patched))
            if not overwrite and path_exists(output_path):
                if not silent:
                    warning('Skipping existing file: %s' % output_path)
                continue

            if verbose:
                log('Requesting file: %s' % filename_patched)
            r = connection.request('GET', filename, redirect=False)

            # pylint: disable=E1103
            if r.status != 200:
                error_msg = 'Couldn\'t download %s.' % filename_patched
                if r.data.get('msg', None):
                    error_msg += ' ' + r.data['msg']
                error(str(r.status) + error_msg)
                exit(-1)
            # pylint: enable=E1103

            r_data = decrypt_data(r.data, enc_key)

            if filename_cleaned.endswith('.bin'):
                r_data = zlib_decompress(r_data)
            # Format v1 file gets uncompressed on download so we just decrypt it

            write_to_file(options, r_data, filename=filename_patched, output_path=output_path)

    except (HTTPError, SSLError) as e:
        error(e)
        exit(-1)


def get_objectid_timestamp(objectid):
    return int(str(objectid)[0:8], 16)


def inline_array_events_local(options, today_log, array_files_list, enc_key):

    verbose = options.verbose
    to_sort = set()

    try:
        index = 0
        for index, filename in enumerate(array_files_list):
            # Format: 'eventlogspath/gamefolder/arrayevents/date(seconds)/objectid.bin'
            # The objectid doesn't correspond to a database entry but is used for uniqueness and timestamp
            filename = filename.replace('\\', '/')
            event_objectid = filename.rsplit('/', 1)[-1].split('.', 1)[0]
            timestamp = get_objectid_timestamp(event_objectid)
            formatted_timestamp = strftime('%Y-%m-%d %H:%M:%S', gmtime(timestamp))

            if verbose:
                log('Retrieving events file ' + str(index + 1) + ' submitted at ' + formatted_timestamp)

            with open(filename, 'rb') as fin:
                file_content = fin.read()
            file_content = decrypt_data(file_content, enc_key)
            file_content = json_loads(zlib_decompress(file_content))

            if not isinstance(file_content, list):
                file_content = [file_content]
            for event in file_content:
                slug = event['slug']
                del event['slug']
                event['time'] = strftime('%Y-%m-%d %H:%M:%S', gmtime(event['time']))

                if slug not in today_log:
                    today_log[slug] = { 'playEvents': [], 'customEvents': [] }

                today_log[slug]['customEvents'].append(event)
                # Maintaining a list of slugs to sort the customEvents by date for so that added array events appear in
                # order but we do not unneccesarily sort large lists if an array event wasn't added to it
                to_sort.add(slug)

        for slug in to_sort:
            today_log[slug]['customEvents'].sort(key=lambda k: k['time'])

        return today_log

    except (IOError, OSError) as e:
        error(e)
        exit(-1)


def inline_array_events_s3(options, today_log, array_files_list, enc_key, connection):

    verbose = options.verbose
    to_sort = set()

    try:
        for index, filename in enumerate(array_files_list):
            # Format: 'https://bucket.s3.amazonaws.com/gamefolder/arrayevents/date(seconds)/objectid.bin?
            #          AWSAccessKeyId=keyid&Expires=timestamp&Signature=signature'
            # The objectid doesn't correspond to a database entry but it used for uniqueness and timestamp
            filename_cleaned = filename.split('?', 1)[0].rsplit('/', 1)[-1]
            event_objectid = filename_cleaned.split('.', 1)[0]
            timestamp = get_objectid_timestamp(event_objectid)
            formatted_timestamp = strftime('%Y-%m-%d %H:%M:%S', gmtime(timestamp))

            if verbose:
                log('Requesting events file ' + str(index + 1) + ' submitted at ' + formatted_timestamp)
            r = connection.request('GET', filename, redirect=False)

            # pylint: disable=E1103
            if r.status != 200:
                error_msg = 'Couldn\'t download event %d.' % (index + 1)
                if r.data.get('msg', None):
                    error_msg += ' ' + r.data['msg']
                error(str(r.status) + error_msg)
                exit(-1)
            # pylint: enable=E1103

            r_data = decrypt_data(r.data, enc_key)
            r_data = json_loads(zlib_decompress(r_data))

            if not isinstance(r_data, list):
                r_data = [r_data]

            for event in r_data:
                slug = event['slug']
                del event['slug']
                event['time'] = strftime('%Y-%m-%d %H:%M:%S', gmtime(event['time']))

                if slug not in today_log:
                    today_log[slug] = { 'playEvents': [], 'customEvents': [] }

                today_log[slug]['customEvents'].append(event)
                # Maintaining a list of slugs to sort the customEvents by date for so that added array events appear in
                # order but we do not unneccesarily sort large lists if an array event wasn't added to it
                to_sort.add(slug)

        for slug in to_sort:
            today_log[slug]['customEvents'].sort(key=lambda k: k['time'])

        return today_log

    except (HTTPError, SSLError) as e:
        error(e)
        exit(-1)


def patch_and_write_today_log(options, resp_daterange, today_log, array_files_list, enc_key, connection):
    today_range = DateRange(int(resp_daterange.end / DAY) * DAY, int(resp_daterange.end))
    filename = '%s-%s-%s.json' % (options.project, options.type, today_range.filename_str())

    output_path = normpath(path_join(options.outputdir, filename))
    if not options.overwrite and path_exists(output_path):
        if not options.silent:
            # Confirm skip as does not make sense to request today's data just to skip overwriting it locally
            log('Overwriting is disabled. Are you sure you want to skip overwriting today\'s downloaded log? ' \
                '(Press \'y\' to skip or \'n\' to overwrite)')
            skip_options = ['y', 'n']
            for attempt in xrange(1, 4):  # default to skip after three bad attempts
                log('', new_line=False)
                skip = stdin.readline().strip().lower()
                if skip in skip_options:
                    break
                error('Please answer with \'y\' or \'n\'. (Attempt %d of 3)' % attempt)

            if 'n' != skip:
                warning('Skipping overwriting today\'s downloaded file: %s' % output_path)
                return
            else:
                warning('Overwrite disabled but overwriting today\'s downloaded file: %s' % output_path)
        else:   # Do not ask in silent mode, default to the option passed
            return

    if array_files_list:
        if options.verbose:
            log('Patching today\'s log file to include array events')

        if connection:
            today_log = inline_array_events_s3(options, today_log, array_files_list, enc_key, connection)
        else:
            today_log = inline_array_events_local(options, today_log, array_files_list, enc_key)

    write_to_file(options, today_log, filename=filename, output_path=output_path, force_overwrite=True)


# pylint: disable=E1103
def main():
    options = _parse_args()

    silent = options.silent
    if not silent:
        log('Downloading \'%s\' to %s.' % (options.type, options.outputdir or 'current directory'))

    try:
        r_data = _request_data(options)
        try:
            response_daterange = DateRange(r_data['start_time'], r_data['end_time'])

            datatype = options.type
            if 'users' == datatype:
                user_data = r_data['user_data']
            else: # if 'events' == datatype
                logs_url = r_data['logs_url']
                files_list = r_data['files_list']
                array_files_list = r_data['array_files_list']
                enc_key = r_data['key']
                if enc_key is not None:
                    # enc_key can be a unicode string and we need a stream of ascii bytes
                    enc_key = urlsafe_b64decode(enc_key.encode('ascii'))
                today_log = r_data['today_log']
        except KeyError as e:
            error('Missing information in response: %s' % e)
            exit(-1)
        del r_data

        daterange = options.daterange
        if not silent:
            if response_daterange.start != daterange.start:
                warning('Start date used (%s) not the same as what was specified (%s)' % \
                        (response_daterange.start_str, daterange.start_str))
            if response_daterange.end != daterange.end:
                warning('End date used (%s) not the same as what was specified (%s)' % \
                        (response_daterange.end_str, daterange.end_str))
            options.daterange = response_daterange

        output_dir = options.outputdir
        if output_dir and not path_exists(output_dir):
            # Not allowing creation of nested directories as greater chance of typos and misplaced files
            mkdir(output_dir)

        if 'users' == datatype:
            write_to_file(options, user_data)

        else: # if 'events' == datatype
            connection = None
            if logs_url and (files_list or array_files_list):
                connection = connection_from_url(logs_url, timeout=8.0)

            if files_list:
                if logs_url:
                    get_log_files_s3(options, files_list, enc_key, connection)
                else:
                    get_log_files_local(options, files_list, enc_key)
                del files_list

            if response_daterange.end > TODAY_START:
                # Patch and write, if requested, today's log with the array events downloaded and inlined
                patch_and_write_today_log(options, response_daterange, today_log, array_files_list, enc_key, connection)
                del today_log
                del array_files_list

        if not silent:
            log('Export completed successfully')

    except KeyboardInterrupt:
        if not silent:
            warning('Program stopped by user')
        exit(-1)
    except OSError as e:
        error(str(e))
        exit(-1)
    except Exception as e:
        error(str(e))
        exit(-1)

    return 0
# pylint: enable=E1103


if __name__ == "__main__":
    exit(main())

########NEW FILE########
__FILENAME__ = json2json
#!/usr/bin/python
# Copyright (c) 2009-2013 Turbulenz Limited
"""
Operate on Turbulenz JSON assets.
"""
from optparse import OptionParser, TitledHelpFormatter

import logging
LOG = logging.getLogger('asset')

# pylint: disable=W0403
from stdtool import simple_options
from turbulenz_tools.utils.json_utils import float_to_string, log_metrics, merge_dictionaries
# pylint: enable=W0403

from simplejson import load as json_load, dump as json_dump, encoder as json_encoder

__version__ = '1.0.0'
__dependencies__ = [ ]

#######################################################################################################################

def merge(source_files, output_filename="default.json", output_metrics=True):
    """Utility function to merge JSON assets."""
    LOG.info("%i assets -> %s", len(source_files), output_filename)
    merged = { }
    for i, f in enumerate(source_files):
        LOG.info("Processing:%03i:%s", i + 1, f)
        try:
            with open(f, 'r') as source:
                j = json_load(source)
                if isinstance(j, dict):
                    merged = merge_dictionaries(j, merged)
                else:
                    merged = j
        except IOError as e:
            LOG.error("Failed processing: %s", f)
            LOG.error('  >> %s', e)
    try:
        with open(output_filename, 'w') as target:
            LOG.info("Writing:%s", output_filename)
            json_encoder.FLOAT_REPR = float_to_string
            json_dump(merged, target, sort_keys=True, separators=(',', ':'))
    except IOError as e:
        LOG.error('Failed processing: %s', output_filename)
        LOG.error('  >> %s', e)
    else:
        if output_metrics:
            log_metrics(merged)

def _parser():
    usage = "usage: %prog [options] source.json [ ... ] target.json"
    description = 'Merge JSON asset files'

    parser = OptionParser(description=description, usage=usage, formatter=TitledHelpFormatter())
    parser.add_option("--version", action="store_true", dest="output_version", default=False,
                      help="output version number")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="verbose output")
    parser.add_option("-s", "--silent", action="store_true", dest="silent", default=False, help="silent running")
    parser.add_option("-m", "--metrics", action="store_true", dest="metrics", default=False,
                      help="output asset metrics")

    return parser

def main():
    (options, args, parser_) = simple_options(_parser, __version__, __dependencies__)

    merge(args[:-1], args[-1], options.metrics)

    return 0

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = json2stats
#!/usr/bin/env python
# Copyright (c) 2010-2013 Turbulenz Limited
"""
Report metrics on Turbulenz JSON assets.
"""
import logging

from glob import iglob
from optparse import OptionParser, TitledHelpFormatter

from turbulenz_tools.utils.json_stats import analyse_json
from turbulenz_tools.tools.stdtool import simple_options

__version__ = '1.0.0'
__dependencies__ = ['turbulenz_tools.utils.json_stats']

LOG = logging.getLogger(__name__)

def _parser():
    usage = "usage: %prog [options] asset.json [ ... ]"
    description = """\
Report metrics on JSON asset files.

Metrics are:
"keys": number of bytes used by keys.
"punctuation (punctn)": number of bytes used by JSON punctuation, including '[ ] { } " , :'.
"values": number of bytes used by values. For uncompact JSON files this will also include the white space.
"k%": percentage of total size used by the keys.
"p%": percentage of total size used by the punctuation.
"v%": percentage of total size used by the values (and white space).
"# keys": the total number of keys.
"unique": the number of unique keys.
"total": the total asset size in byte.
"gzip": the asset size after gzip compression.
"ratio": the gzip size as a percentage of the uncompressed total size.
"""
    epilog = 'This tool current assumes the JSON asset is compact with no additional white space.'

    parser = OptionParser(description=description, usage=usage, epilog=epilog, formatter=TitledHelpFormatter())
    parser.add_option("--version", action="store_true", dest="output_version", default=False,
                      help="output version number")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="verbose output")
    parser.add_option("-s", "--silent", action="store_true", dest="silent", default=False, help="silent running")
    parser.add_option("-m", "--metrics", action="store_true", dest="metrics", default=False,
                      help="output asset metrics")

    parser.add_option("-H", "--header", action="store_true", dest="header", default=False,
                      help="generate column header")

    return parser

def main():
    (options, args, parser_) = simple_options(_parser, __version__, __dependencies__)

    divider = "+-------------------------+----------------------+---------------+------------------------+"
    if options.header:
        print divider
        print "|    keys: punctn: values |     k%:    p%:    v% | # keys:unique |   total:   gzip: ratio |"
        print divider

    def vadd(a, b):
        return tuple([x + y for (x, y) in zip(a, b)])

    def log((keys, punctuation, values, key_count, unique_count, total_size, compressed_size), f):
        k_percent = keys * 100.0 / total_size
        p_percent = punctuation * 100.0 / total_size
        v_percent = values * 100.0 / total_size
        c_percent = compressed_size * 100.0 / total_size
        print "| %7i:%7i:%7i | %5.1f%%:%5.1f%%:%5.1f%% | %6i:%6i | %7i:%7i:%5.1f%% | %s" % \
            (keys, punctuation, values, k_percent, p_percent, v_percent, key_count, unique_count, \
             total_size, compressed_size, c_percent, f)

    totals = (0, 0, 0, 0, 0, 0, 0)
    for f in args:
        for g in iglob(f):
            stats = analyse_json(g)
            totals = vadd(totals, stats)
            if options.verbose:
                log(stats, g)
    total_string = 'cumulative total and global ratio'
    if options.verbose:
        print divider

    log(totals, total_string)

    if options.header:
        print divider

    return 0

if __name__ == "__main__":
    exit(main())

########NEW FILE########
__FILENAME__ = json2tar
#!/usr/bin/env python
# Copyright (c) 2010-2013 Turbulenz Limited

import logging
import os
import tarfile
import simplejson as json

from optparse import OptionParser, TitledHelpFormatter

from turbulenz_tools.tools.stdtool import simple_options

__version__ = '1.0.0'
__dependencies__ = [ ]

LOG = logging.getLogger(__name__)

class DependencyTar(object):
    def __init__(self):
        self.paths = [ ]

    def items(self):
        return self.paths

    def add(self, path, name_):
        self.paths.append(path)

    def close(self):
        pass

def images_in_asset(json_asset):
    """Iterator for all images used in a json asset."""
    images = json_asset.get('images', None)
    if images is not None:
        for _, image in images.iteritems():
            yield image, None

    materials = json_asset.get('materials', None)
    if materials is not None:
        texture_maps = { }
        for _, material in materials.iteritems():
            parameters = material.get('parameters', None)
            if parameters is not None:
                for texture_stage, texture_map in parameters.iteritems():
                    if isinstance(texture_map, (str, unicode)):
                        texture_maps[texture_stage] = True
                        yield texture_map, texture_stage
        LOG.info('contains: %s', ', '.join(texture_maps.keys()))

def _parser():
    parser = OptionParser(description='Generate a TAR file for binary assets referenced from a JSON asset.',
                          usage='%prog -i input.json -o output.tar [options]',
                          formatter=TitledHelpFormatter())
    parser.add_option("--version", action="store_true", dest="output_version", default=False,
                      help="output version number")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="verbose output")
    parser.add_option("-s", "--silent", action="store_true", dest="silent", default=False, help="silent running")

    parser.add_option("-i", "--input", action="store", dest="input", help="input file to process")
    parser.add_option("-o", "--output", action="store", dest="output", help="output file to process")
    parser.add_option("-a", "--assets", action="store", dest="asset_root", default=".", metavar="PATH",
                      help="path of the asset root")

    parser.add_option("-M", action="store_true", dest="dependency", default=False, help="output dependencies")
    parser.add_option("--MF", action="store", dest="dependency_file", help="dependencies output to file")

    return parser

def main():
    (options, args_, parser_) = simple_options(_parser, __version__, __dependencies__)

    # Cleanly handle asset location
    asset_root = options.asset_root.replace('\\', '/').rstrip('/')

    def _filename(filename):
        if filename[0] == '/':
            return asset_root + filename
        else:
            return asset_root + '/' + filename

    tar_file = DependencyTar()

    LOG.info('%s %s', __file__, options.input)
    LOG.info('input: %s', options.input)

    try:
        with open(options.input, 'r') as source:
            json_asset = json.load(source)
            if not options.dependency:
                tar_file = tarfile.open(options.output, 'w')
            image_map = { }
            (added, missed, skipped) = (0, 0, 0)
            for image_name, texture_stage_ in images_in_asset(json_asset):
                # This is probably a procedural image - skip it
                if image_name not in image_map:
                    # We used to convert .tga -> .png, .cubemap -> .dds, and support dropping mips from dds files.
                    # Currently this is disabled until we integrate the tool with a build process.
                    # Alternatively we expect this conversion to happen in the image pipeline.
                    try:
                        image_path = _filename(image_name)
                        if os.path.exists(image_path):
                            # Actually do the tar add
                            tar_file.add(image_path, image_name)
                            LOG.info('adding: %s', image_name)
                            image_path = image_path.replace("\\", "/")
                            added += 1
                        else:
                            # We don't mind if files are missing
                            LOG.warning('missing: %s', image_name)
                            missed += 1
                    except OSError:
                        # We don't mind if files are missing
                        LOG.warning('missing: %s', image_name)
                        missed += 1
                    image_map[image_name] = 0
                else:
                    LOG.info('skipping: %s', image_name)
                    skipped += 1
                image_map[image_name] += 1
            tar_file.close()
            LOG.info('output: %s', options.output)
            LOG.info('report: added %i, missing %i, skipped %i', added, missed, skipped)
    except IOError as e:
        LOG.error(e)
        return e.errno
    except Exception as e:
        LOG.critical('Unexpected exception: %s', e)
        return 1

    if options.dependency:
        if options.dependency_file:
            LOG.info('writing dependencies: %s', options.dependency_file)
            dep_file = open(options.dependency_file, 'w')

            for dep in tar_file.items():
                dep_file.write("%s\n" % dep)
            dep_file.close()
        else:
            for dep in tar_file.items():
                print dep
            print

    return 0

if __name__ == "__main__":
    exit(main())

########NEW FILE########
__FILENAME__ = json2txt
#!/usr/bin/env python
# Copyright (c) 2010-2013 Turbulenz Limited

import logging
import simplejson as json

from optparse import OptionParser, TitledHelpFormatter
from fnmatch import fnmatch

from turbulenz_tools.utils.disassembler import Json2htmlRenderer, Json2txtRenderer, Json2txtColourRenderer, Disassembler
from turbulenz_tools.tools.stdtool import simple_options

__version__ = '1.0.0'
__dependencies__ = ['turbulenz_tools.utils.disassembler']

LOG = logging.getLogger(__name__)

def _parser():
    parser = OptionParser(description='Generate a plain text or html output from a JSON asset. (plain text by default)',
                          usage='%prog -i input.json [-o output.html] [options]',
                          formatter=TitledHelpFormatter())
    parser.add_option("--version", action="store_true", dest="output_version", default=False,
                      help="output version number")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="verbose output")
    parser.add_option("-s", "--silent", action="store_true", dest="silent", default=False, help="silent running")

    parser.add_option("-i", "--input", action="store", dest="input", help="input file to process")
    parser.add_option("-o", "--output", action="store", dest="output", help="output file to process")

    parser.add_option("-l", "--listcull", action="store", dest="listcull", type="int", default=3, metavar="NUMBER",
                     help="parameter of the list culling size. 0 - show all (defaults to 3)")
    parser.add_option("-c", "--dictcull", action="store", dest="dictcull", type="int", default=3, metavar="NUMBER",
                     help="parameter of the dictionary culling size. 0 - show all (defaults to 3)")
    parser.add_option("-p", "--path", action="store", dest="path", type="str", default=None,
                     help="path of the required node in the asset tree structure (wildcards allowed)")
    parser.add_option("-d", "--depth", action="store", dest="depth", type="int", default=2, metavar="NUMBER",
                     help="parameter of the dictionary and list rendering depth (defaults to 2).")

    parser.add_option("--html", action="store_true", dest="html", default=False,
                      help="output in html format")
    parser.add_option("--txt", action="store_true", dest="txt", default=False,
                      help="output in plain text format")
    parser.add_option("--color", action="store_true", dest="color", default=False,
                      help="option to turn on the coloured text output")

    return parser

def main():
    (options, args_, parser_) = simple_options(_parser, __version__, __dependencies__)

    source_file = options.input

    LOG.info('%s %s', __file__, source_file)
    LOG.info('input: %s', source_file)

    try:
        with open(source_file, 'r') as source:
            json_asset = json.load(source)

            def find_node(nodes, sub_asset):
                for (k, v) in sub_asset.iteritems():
                    if fnmatch(k, nodes[0]):
                        if len(nodes) == 1:
                            yield (k, sub_asset[k])
                        elif isinstance(v, dict):
                            for n in find_node(nodes[1:], sub_asset[k]):
                                yield n
                            for n in find_node(nodes, sub_asset[k]):
                                yield n

            if options.path:
                node_list = options.path.split('/')

            if options.html:
                renderer = Json2htmlRenderer()
            elif options.color:
                renderer = Json2txtColourRenderer()
            else:
                renderer = Json2txtRenderer()

            disassembler = Disassembler(renderer, options.listcull, options.dictcull, options.depth)
            expand = True

            if options.output:
                with open(options.output, 'w') as target:
                    if options.path:
                        for name, node in find_node(node_list, json_asset):
                            target.write(name + ': ' + disassembler.mark_up_asset({name: node}, expand))
                            target.write('\n')
                    else:
                        target.write(disassembler.mark_up_asset({'root': json_asset}, expand))
                        target.write('\n')
            elif options.color:
                if options.path:
                    for name, node in find_node(node_list, json_asset):
                        print '\033[;31m' + name + '\033[;m' + ': ' + disassembler.mark_up_asset({name: node}, expand),
                else:
                    print disassembler.mark_up_asset({'root': json_asset}, expand)
            else:
                if options.path:
                    for name, node in find_node(node_list, json_asset):
                        print name + ': ' + disassembler.mark_up_asset({name: node}, expand),
                else:
                    print disassembler.mark_up_asset({'root': json_asset}, expand)

    except IOError as e:
        LOG.error(e)
        return e.errno
    except Exception as e:
        LOG.critical('Unexpected exception: %s', e)
        return 1
    return 0

if __name__ == "__main__":
    exit(main())

########NEW FILE########
__FILENAME__ = makehtml
#!/usr/bin/env python
# Copyright (c) 2012-2013 Turbulenz Limited

# Catch "Exception"
# pylint:disable=W0703

from logging import getLogger
from os.path import splitext, basename

from optparse import OptionParser, TitledHelpFormatter

from turbulenz_tools.utils.dependencies import find_dependencies
from turbulenz_tools.utils.dependencies import find_file_in_dirs
from turbulenz_tools.utils.profiler import Profiler

from turbulenz_tools.tools.templates import env_create
from turbulenz_tools.tools.templates import env_load_template
from turbulenz_tools.tools.templates import env_load_templates

from turbulenz_tools.tools.appcodegen import render_js
from turbulenz_tools.tools.appcodegen import context_from_options
from turbulenz_tools.tools.appcodegen import default_add_code
from turbulenz_tools.tools.appcodegen import inject_js_from_options
from turbulenz_tools.tools.appcodegen import default_parser_options
from turbulenz_tools.tools.appcodegen import DEFAULT_HTML_TEMPLATE
from turbulenz_tools.tools.appcodegen import output_dependency_info

from turbulenz_tools.tools.toolsexception import ToolsException
from turbulenz_tools.tools.stdtool import simple_options

__version__ = '1.8.0'
__dependencies__ = ['turbulenz_tools.utils.dependencies', 'turbulenz_tools.tools.appcodegen']

LOG = getLogger(__name__)

############################################################

def _parser():
    parser = OptionParser(description='Generate HTML files from .html and '
                          '.js files. Any options not recognised are '
                          'assumed to be input files.',
                          usage="usage: %prog [options] <input files>",
                          formatter=TitledHelpFormatter())

    default_parser_options(parser)

    parser.add_option("-C", "--code", action="store", dest="codefile",
                      help="release file to be called by the HTML. Does not "
                      "need to exist yet. (release and canvas modes only)")

    # Mode one of [ 'plugin', 'plugin-debug', 'canvas', 'canvas-debug' ]
    parser.add_option("-m", "--mode", action="store", dest="mode",
                      default='plugin-debug',
                      help="build mode: canvas, canvas-debug, plugin, "
                      "plugin-debug (default)")

    parser.add_option("-D", "--dump-default-template", action="store_true",
                      dest="dump_default_template", default=False,
                      help="output the default template to file")

    return parser

############################################################

# TODO : Move into utils
def check_input(input_files):
    """
    Divide up a list of input files into .js and .html files
    """
    js_files = []
    html_files = []
    for f in input_files:
        ext = splitext(f)[1]
        if ext in [ '.js', '.jsinc' ]:
            js_files.append(f)
        elif ext in [ '.html', '.htm' ]:
            html_files.append(f)
        else:
            LOG.error("unrecognised file type: %s", f)
            exit(1)

    return (js_files, html_files)

def load_html_template(env, input_html):
    if 1 == len(input_html):
        return env_load_template(env, input_html[0])

    return env.from_string(DEFAULT_HTML_TEMPLATE)

def dump_default_template(outfile_name):
    if outfile_name is None:
        outfile_name = 'default_template.html'

    with open(outfile_name, "wb") as f:
        f.write(DEFAULT_HTML_TEMPLATE)
    LOG.info("Default template written to: %s", outfile_name)
    return 0

def html_dump_dependencies(env, options, input_js, input_html):
    """
    Dump the dependencies of the html file being output
    """

    # For html, dependencies are:
    # - dev: html template deps, top-level js files
    # - release: html template deps
    # - canvas_dev: html template deps, top-level js files
    # - canvas: html template deps

    outfile_name = options.dependency_file
    if outfile_name is None:
        LOG.error("No dependency output file specified")
        return 1

    # Collect html dependencies (if there are html files available)

    if 1 == len(input_html):
        try:
            deps = find_dependencies(input_html[0], options.templatedirs, env,
                                     [ 'default' ])
        except Exception, e:
            raise ToolsException("dependency error: %s" % str(e))
    else:
        deps = []

    # Collect js dependencies if necessary

    if options.mode in [ 'plugin-debug', 'canvas-debug' ]:
        deps += [ find_file_in_dirs(js, options.templatedirs) for js in input_js ]

    # Write dependency info

    output_dependency_info(outfile_name, options.output, deps)

    return 0

def html_generate(env, options, input_js, input_html):
    """
    Generate html based on the templates and build mode.
    """

    # - dev, canvas_dev:
    #     render top-level js files into a temporary file
    #     collect the .js files that need to be included
    #     setup includes, startup code and the js render result into variables
    #     render html template
    #
    # - release, canvas:
    #     need to know name of output js file
    #     setup startup code to point to .tzjs or .js file
    #     render html template

    # Load templates (using default html template if not specified)

    Profiler.start('load_templates')

    template_html = load_html_template(env, input_html)
    if template_html is None:
        LOG.error("failed to load file %s from template dirs", input_html[0])
        exit(1)

    # Get context

    if len(input_js) > 0:
        title = input_js[0]
    elif options.codefile:
        title = options.codefile
    elif len(input_html) > 0:
        title = input_html[0]
    else:
        title = "Unknown"
    title = splitext(basename(title))[0]

    context = context_from_options(options, title)

    Profiler.stop('load_templates')
    Profiler.start('code_gen')

    # In development modes, render the JS code that needs embedding

    rendered_js = ""
    inc_js = []

    if options.mode in [ 'plugin-debug', 'canvas-debug' ]:
        inject_js = inject_js_from_options(options)

        Profiler.start('load_js_templates')
        templates_js = env_load_templates(env, input_js)
        Profiler.stop('load_js_templates')

        (rendered_js, inc_js) = render_js(context, options, templates_js,
                                          inject_js)

    # Add the HTML and JS code into the tz_* variables

    default_add_code(options, context, rendered_js, inc_js)

    Profiler.stop('code_gen')
    Profiler.start('html_render')

    # Render the template and write it out

    try:
        res = template_html.render(context)
    except Exception, e:
        raise ToolsException("Error in '%s': %s %s" \
                                 % (input_html, e.__class__.__name__, str(e)))

    try:
        with open(options.output, "wb") as f:
            f.write(res.encode('utf-8'))
    except IOError:
        raise ToolsException("failed to create file: %s" % options.output)

    Profiler.stop('html_render')

    return 0

############################################################

def main():

    (options, args, parser) = simple_options(_parser, __version__,
                                             __dependencies__, input_required=False)

    Profiler.start('main')
    Profiler.start('startup')

    input_files = args

    # Check that if dump-default-template is set then output and exit

    if options.dump_default_template:
        exit(dump_default_template(options.output))
    elif 0 == len(args):
        LOG.error('No input files specified')
        parser.print_help()
        exit(1)

    LOG.info("options: %s", options)
    LOG.info("args: %s", args)
    LOG.info("parser: %s", parser)
    LOG.info("templatedirs: %s", options.templatedirs)

    if options.output is None:
        LOG.error("no output file specified (required in dependency mode)")
        parser.print_help()
        exit(1)

    # Check mode

    if options.mode not in [ 'plugin-debug', 'plugin', 'canvas-debug', 'canvas' ]:
        LOG.error('Unrecognised mode: %s', options.mode)
        parser.print_help()
        exit(1)

    # Check a release source name is given if mode is one of release
    # or canvas

    if options.mode in [ 'plugin', 'canvas' ] and \
            not options.dependency and \
            not options.codefile:
        LOG.error('Missing code file name.  Use --code to specify.')
        parser.print_usage()
        exit(1)

    # Check input files and split them into (ordered) js and html

    (input_js, input_html) = check_input(input_files)

    LOG.info("js files: %s", input_js)
    LOG.info("html files: %s", input_html)

    # In debug and canvas-debug we need a .js input file

    if 0 == len(input_js):
        if options.mode in [ 'debug', 'canvas-debug' ]:
            LOG.error('Missing input .js file')
            parser.print_usage()
            exit(1)
    if 1 < len(input_html):
        LOG.error('Multiple html files specified: %s', input_html)
        exit(1)

    # Create a jinja2 env

    env = env_create(options, DEFAULT_HTML_TEMPLATE)

    Profiler.stop('startup')
    Profiler.start('run')

    # Execute

    retval = 1
    try:

        if options.dependency:
            LOG.info("generating dependencies")
            retval = html_dump_dependencies(env, options, input_js, input_html)
            LOG.info("done generating dependencies")

        else:
            retval = html_generate(env, options, input_js, input_html)

    except ToolsException, e:
        #traceback.print_exc()
        LOG.error("%s", str(e))

    Profiler.stop('run')
    Profiler.stop('main')
    Profiler.dump_data()

    return retval

############################################################

if __name__ == "__main__":
    exit(main())

########NEW FILE########
__FILENAME__ = maketzjs
#!/usr/bin/env python
# Copyright (c) 2012-2013 Turbulenz Limited

from turbulenz_tools.utils.dependencies import find_dependencies
from turbulenz_tools.utils.subproc import SubProc
from turbulenz_tools.utils.profiler import Profiler

from turbulenz_tools.tools.templates import env_create
from turbulenz_tools.tools.templates import env_load_templates

from turbulenz_tools.tools.appcodegen import render_js
from turbulenz_tools.tools.appcodegen import render_js_extract_includes
from turbulenz_tools.tools.appcodegen import inject_js_from_options
from turbulenz_tools.tools.appcodegen import context_from_options
from turbulenz_tools.tools.appcodegen import default_parser_options
from turbulenz_tools.tools.appcodegen import output_dependency_info

from turbulenz_tools.tools.toolsexception import ToolsException
from turbulenz_tools.tools.stdtool import simple_options

from logging import getLogger
from os import remove
from os.path import relpath, abspath, normpath
from tempfile import NamedTemporaryFile
from optparse import OptionParser, TitledHelpFormatter

import subprocess

__version__ = '1.2.0'
__dependencies__ = ['turbulenz_tools.utils.subproc', 'turbulenz_tools.utils.dependencies',
                    'turbulenz_tools.tools.appcodegen']

LOG = getLogger(__name__)

############################################################

def _parser():
    parser = OptionParser(description='Convert a JavaScript file into a .tzjs'
                          ' or .canvas.js file. Any options not recognised are'
                          ' assumed to be input files.',
                          usage="usage: %prog [options] <input files>",
                          formatter=TitledHelpFormatter())

    default_parser_options(parser)

    # Mode one of [ 'plugin', 'canvas' ]
    parser.add_option("-m", "--mode", action="store", dest="mode",
                      default='plugin', help="build mode: canvas, "
                      "plugin(default)")

    parser.add_option("--ignore-input-extension", action="store_true",
                      dest="ignore_ext_check", default=False,
                      help="allow input files with an extension other than .js")

    # Compacting
    parser.add_option("-y", "--yui", action="store", dest="yui", default=None,
                      help="path to the YUI compressor, setting this enables "
                      "compacting with the YUI compressor")
    parser.add_option("-c", "--closure", action="store", dest="closure",
                      default=None, help="path to the Closure compiler, setting "
                      "this enables the compacting with the Closure compiler "
                      "(EXPERIMENTAL)")
    parser.add_option("-u", "--uglifyjs", action="store", dest="uglifyjs",
                      default=None, help="path to the UglifyJS application, "
                      "setting this enables the compacting with the UglifyJS "
                      "compiler. This option assumes node.js is executable "
                      "from the path.")
    parser.add_option("--uglify", action="store", dest="uglifyjs",
                      default=None, help="Deprecated - Please use --uglifyjs")

    # Strip-debug
    parser.add_option("--no-strip-debug", action="store_false",
                      dest="stripdebug", default=True,
                      help="don't remove calls to debug.* methods")
    parser.add_option("--strip-debug", action="store",
                      dest="stripdebugpath", default=None,
                      help="set the path to the strip-debug application")
    parser.add_option("--strip-namespace", action="append", default=[],
                      dest="stripnamespaces", help="add namespace to strip "
                      "(see strip-debug --namespace flag)")
    parser.add_option("--strip-var", action="append", dest="stripvars",
                      help="define a global bool var for static code stripping "
                      "(see strip-debug -D flag)", default=[])

    parser.add_option("--ignore-errors", action="store_true",
                      dest="ignoreerrors", default=False,
                      help="ignore any syntax errors found while parsing")

    # Line length
    parser.add_option("-l", "--line-break", action="store", type="int",
                      dest="length", default=1000, help="split line length")

    return parser

############################################################

def tzjs_dump_dependencies(env, options, input_js):
    """
    Lists all the dependencies of the .js file.  We attempt to retain
    some kind of order with the leaves of the dependency tree at the
    top of the list.
    """

    # The set of files to be injected

    injects = inject_js_from_options(options)

    LOG.info("files to inject:")
    _ = [ LOG.info(" - %s", i) for i in injects ]

    # Do a full parse with a correct context, and extract the
    # javascript includes

    context = context_from_options(options, input_js[0])

    deps = render_js_extract_includes(context, options,
                                      env_load_templates(env, input_js),
                                      injects)

    # TODO : Do we need this find_dependencies stage?  It doesn't pick
    # up any javascript tags.

    for i in input_js:
        deps += find_dependencies(i, options.templatedirs, env)

    # Write dependency data

    # LOG.info("deps are: %s" % deps)
    output_dependency_info(options.dependency_file, options.output, deps)

    return 0

############################################################

def tzjs_compact(options, infile, outfile):

    LOG.info("compacting from %s to %s", infile, outfile)

    if options.yui is not None:
        command = ['java', '-jar', options.yui,
                           '--line-break', str(options.length),
                           '--type', 'js',
                           '-o', outfile, infile]

    elif options.closure is not None:
        command = ['java', '-jar', options.closure,
                           '--js_output_file=' + outfile,
                           '--js=' + infile]

    elif options.uglifyjs is not None:
        # For nodejs on win32 we need posix style paths for the js
        # module, so convert to relative path
        uglify_rel_path = relpath(options.uglifyjs).replace('\\', '/')
        command = ['node', uglify_rel_path, '-o', outfile, infile]

    LOG.info("  CMD: %s", command)
    subproc = SubProc(command)
    error_code = subproc.time_popen()

    if 0 != error_code:
        raise ToolsException("compactor command returned error code %d: %s " \
                                 % (error_code, " ".join(command)))

############################################################

def tzjs_generate(env, options, input_js):

    # The set of files to be injected

    Profiler.start('find_inject_code')
    inject_js = inject_js_from_options(options)
    Profiler.stop('find_inject_code')

    if 0 < len(inject_js):
        LOG.info("Files to inject:")
        for i in inject_js:
            LOG.info(" - '%s'", i)

    # Create a context and render the template

    Profiler.start('load_templates')
    context = context_from_options(options, input_js[0])
    templates_js = env_load_templates(env, input_js)
    Profiler.stop('load_templates')

    Profiler.start('render_js')
    (rendered_js, inc_js) = render_js(context, options, templates_js,
                                      inject_js)
    Profiler.stop('render_js')

    if 0 != len(inc_js):
        raise ToolsException("internal error")

    # If required, remove all calls to 'debug.*' methods BEFORE
    # compacting

    if options.stripdebug:

        strip_path = "strip-debug"
        if options.stripdebugpath:
            strip_path = normpath(abspath(options.stripdebugpath))

        LOG.info("Stripping debug method calls ...")

        # Check we can actually run strip debug, with the given path
        p = subprocess.Popen('%s -h' % strip_path, stdout=subprocess.PIPE,
                                                   stderr=subprocess.STDOUT,
                                                   shell=True)
        p.communicate()
        if p.returncode != 0:
            raise ToolsException( \
                "\n\tstrip-debug tool could not be found, check it's on your path\n"
                "\tor supply the path with --strip-debug <path>. To run maketzjs\n"
                "\twithout stripping debug code run with --no-strip-debug." )

        Profiler.start('strip_debug')

        strip_debug_flags = "-Ddebug=false"

        # Add the default flags first, in case the custom flags
        # override them.

        if options.verbose:
            strip_debug_flags += " -v"
        for s in options.stripnamespaces:
            strip_debug_flags += " --namespace %s" % s
        for v in options.stripvars:
            strip_debug_flags += " -D %s" % v
        if options.ignoreerrors:
            strip_debug_flags += " --ignore-errors"

        # Launch the strip command and pass in the full script via
        # streams.

        strip_cmd = "%s %s" % (strip_path, strip_debug_flags)
        LOG.info("Strip cmd: %s", strip_cmd)
        p = subprocess.Popen(strip_cmd, shell=True,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        (stripped_js, err) = p.communicate(rendered_js.encode('utf-8'))
        strip_retval = p.wait()

        if 0 != strip_retval:
            with NamedTemporaryFile(delete = False) as t:
                t.write(rendered_js)

            raise ToolsException( \
                "strip-debug tool exited with code %d and stderr:\n\n%s\n"
                "The (merged) input probably contains a syntax error.  It has "
                "been written to:\n  %s\nfor inspection." \
                    % (strip_retval, err, t.name))

        if not err is None and len(err) > 0:
            print "error output from strip-debug tool:"
            print "%s" % err


        rendered_js = stripped_js

        Profiler.stop('strip_debug')

    # If required, compact the JS via a temporary file, otherwise just
    # write out directly to the output file.

    if options.yui or options.closure or options.uglifyjs:

        Profiler.start('compact')

        with NamedTemporaryFile(delete = False) as t:
            LOG.info("Writing temp JS to '%s'", t.name)
            t.write(rendered_js)

        LOG.info("Compacting temp JS to '%s'", options.output)
        tzjs_compact(options, t.name, options.output)
        remove(t.name)
        Profiler.stop('compact')

    else:

        LOG.info("Writing JS to '%s'", options.output)
        Profiler.start('write_out')
        try:
            with open(options.output, 'wb') as f:
                f.write(rendered_js)
                LOG.info("Succeeded")
        except IOError:
            raise ToolsException("failed to write file: %s" % options.output)
        Profiler.stop('write_out')

    return 0

############################################################

def main():
    (options, args, parser) = simple_options(_parser, __version__,
                                             __dependencies__)

    Profiler.start('main')
    Profiler.start('startup')

    # Sanity checks

    if 0 == len(args):
        LOG.error("no input files specified")
        parser.print_help()
        exit(1)

    if options.mode not in [ 'plugin', 'canvas' ]:
        LOG.error("invalid mode %s", options.mode)
        parser.print_help()
        exit(1)

    if options.output is None:
        LOG.error("no output file specified (required in dependency mode)")
        parser.print_help()
        exit(1)

    # Create a jinja2 env

    env = env_create(options)
    input_js = args

    LOG.info("input files: %s", input_js)

    Profiler.stop('startup')
    Profiler.start('run')

    # Execute

    retval = 1
    try:

        if options.dependency:
            LOG.info("dependency generation selected")
            retval = tzjs_dump_dependencies(env, options, input_js)
        else:
            LOG.info("rendering tzjs")
            retval = tzjs_generate(env, options, input_js)

    except ToolsException, e:
        LOG.error(str(e))
        exit(1)

    Profiler.stop('run')
    Profiler.stop('main')
    Profiler.dump_data()

    return retval

if __name__ == "__main__":
    exit(main())

########NEW FILE########
__FILENAME__ = material
# Copyright (c) 2009-2011,2013 Turbulenz Limited
"""
Utility for manipluating Materials.
"""

__version__ = '1.0.0'

def clean_material_name(material_name):
    """Make sure the material name is consistent."""
    return material_name.lower().replace('\\', '/')

def is_material_collidable(material):
    """Check whether a material has meta suggesting we need collision meshes"""
    collision_filter = material.meta('collisionFilter')
    return (not collision_filter) or (len(collision_filter) > 0)

# pylint: disable=R0904
class Material(dict):
    """Material class to provide safe meta and parameter attribute access."""

    def __init__(self, source_material=None):
        if source_material is None:
            source_material = { }
        super(Material, self).__init__(source_material)
        for k, v in source_material.iteritems():
            if isinstance(v, dict):
                self[k] = v.copy()
            else:
                self[k] = v

    def meta(self, key):
        """Return a meta attribute. Returns None if the attribute is missing."""
        if 'meta' in self:
            if key in self['meta']:
                return self['meta'][key]
        return None

    def param(self, key, value=None):
        """Returns a parameter attribute. Returns None if the attribute is missing."""
        if value is None:
            if 'parameters' in self:
                if key in self['parameters']:
                    return self['parameters'][key]
            return None
        else:
            if 'parameters' not in self:
                self['parameters'] = { }
            self['parameters'][key] = value

    def pop_param(self, key, default=None):
        """Pop a parameter attribute."""
        params = self.get('parameters', None)
        if params:
            return params.pop(key, default)
        else:
            return default

    def remove(self, key):
        """Delete an attribute from the material."""
        if key in self:
            del(self[key])
# pylint: enable=R0904

########NEW FILE########
__FILENAME__ = material2json
#!/usr/bin/python
# Copyright (c) 2010-2011,2013 Turbulenz Limited
"""
Convert Material Yaml (.material) files into a Turbulenz JSON asset.
"""

import logging
LOG = logging.getLogger('asset')

import yaml

# pylint: disable=W0403
from stdtool import standard_main, standard_json_out
from asset2json import JsonAsset
# pylint: enable=W0403

__version__ = '1.0.0'
__dependencies__ = ['asset2json']

#######################################################################################################################

def parse(input_filename="default.material", output_filename="default.json", asset_url="", asset_root=".",
          infiles=None, options=None):
    """
    Utility function to convert a Material Yaml (.material) into a JSON file.
    Known built-in textures are: default, quadratic, white, nofalloff, black, flat

    Example:

        # Example material
        material:
            effect: lambert
            diffuse: textures/wallstone.jpg
            color: [1.0, 0.5, 0.1]
            meta: &id1
                collision: True
                collisionFilter: ["ALL"]

        material2:
            diffuse: textures/wall.jpg
            meta:
                <<: *id1
                collision: False

        material3:
            diffuse: textures/stone.jpg
            meta: *id1
    """
    try:
        with open(input_filename, 'r') as source:
            try:
                materials = yaml.load(source)
            # pylint: disable=E1101
            except yaml.scanner.ScannerError as e:
            # pylint: enable=E1101
                LOG.error('Failed processing:%s', input_filename)
                LOG.error('  >> %s', e)
            else:
                json_asset = JsonAsset()
                for mat_name, material in materials.iteritems():
                    effect = material.pop('effect', None)
                    technique = material.pop('technique', None)
                    meta = material.pop('meta', None)
                    json_asset.attach_material(mat_name, effect, technique, material, meta)

                standard_json_out(json_asset, output_filename, options)
                return json_asset
    except IOError as e:
        LOG.error('Failed processing: %s', output_filename)
        LOG.error('  >> %s', e)
        return None

if __name__ == "__main__":
    try:
        standard_main(parse, __version__,
                      "Convert Material Yaml (.material) files into a Turbulenz JSON asset.",
                      __dependencies__)
    # pylint: disable=W0703
    except Exception as err:
        LOG.critical('Unexpected exception: %s', err)
        exit(1)
    # pylint: enable=W0703

########NEW FILE########
__FILENAME__ = mesh
# Copyright (c) 2009-2013 Turbulenz Limited
"""
Mesh class used to hold and process vertex streams.

Supports generating NBTs.
"""

import math
import logging
LOG = logging.getLogger('asset')

# pylint: disable=W0403
import vmath
import pointmap
# pylint: enable=W0403

__version__ = '1.1.0'
__dependencies__ = ['pointmap', 'vmath']

#######################################################################################################################

# cos( 1 pi / 8 ) = 0.923879 ~ cos 22.5 degrees
# cos( 2 pi / 8 ) = 0.707106 ~ cos 45   degrees
# cos( 2 pi / 6 ) = 0.5      ~ cos 60   degress
# cos( 3 pi / 8 ) = 0.382683 ~ cos 67.5 degrees
DEFAULT_POSITION_TOLERANCE = 1e-6
DEFAULT_NORMAL_SMOOTH_TOLERANCE = 0.5 # 0.707106
DEFAULT_TANGENT_SPLIT_TOLERANCE = 0.5 # 0.382683
DEFAULT_ZERO_TOLERANCE = 1e-6
DEFAULT_DONT_NORMALIZE_TOLERANCE = 1e-3
DEFAULT_UV_TOLERANCE = 1e-6
DEFAULT_PLANAR_TOLERANCE = 1e-6
DEFAULT_TANGENT_PROJECTION_TOLERANCE = 1e-10
DEFAULT_COLLINEAR_TOLERANCE = 1e-10
DEFAULT_COPLANAR_TOLERANCE = 1e-16
DEFAULT_PLANAR_HULL_VERTEX_THRESHOLD = 5

def similar_positions(major, positions, pos_tol=DEFAULT_POSITION_TOLERANCE):
    """Iterator to return the index of similar positions."""
    # pos_tol currently unused - using vmath default.
    for i, p in enumerate(positions):
        if vmath.v3equal(major, p):
            yield i

#######################################################################################################################

# pylint: disable=R0902
# pylint: disable=R0904
class Mesh(object):
    """Generate a mesh geometry."""

    class Stream(object):
        """Contains a single stream of vertex attributes."""
        def __init__(self, values, semantic, name, stride, offset):
            """
            ``values`` - array of stream tuples
            ``semantic`` - name of the stream semantic
            ``name`` - human readable name of the stream
            ``stride`` - length of each vertex in the stream
            ``offset`` - offset in the index buffer for this stream
            """
            self.values = values
            self.semantic = semantic
            self.name = name
            self.stride = stride
            self.offset = offset

    def __init__(self, mesh=None):
        # Positions, normals, uvs, skin_indices, skin_weights, primitives
        self.kdtree = None
        if mesh is not None:
            self.positions = mesh.positions[:]
            self.uvs = [ uvs[:] for uvs in mesh.uvs ]
            self.normals = mesh.normals[:]
            self.tangents = mesh.tangents[:]
            self.binormals = mesh.binormals[:]
            self.colors = mesh.colors[:]
            self.skin_indices = mesh.skin_indices[:]
            self.skin_weights = mesh.skin_weights[:]
            self.primitives = mesh.primitives[:]
            self.bbox = mesh.bbox.copy()
        else:
            self.positions = [ ]
            self.uvs = [ [] ]
            self.normals = [ ]
            self.tangents = [ ]
            self.binormals = [ ]
            self.colors = [ ]
            self.skin_indices = [ ]
            self.skin_weights = [ ]
            self.primitives = [ ]
            self.bbox = { }

    ###################################################################################################################

    def set_values(self, values, semantic):
        """Replace the mesh values for a specified semantic."""
        if semantic == 'POSITION':
            self.positions = values
        elif semantic.startswith('TEXCOORD'):
            if semantic == 'TEXCOORD' or semantic == 'TEXCOORD0':
                self.uvs[0] = values
            else:
                index = int(semantic[8:])
                while index >= len(self.uvs):
                    self.uvs.append([])
                self.uvs[index] = values
        elif semantic == 'NORMAL' or semantic == 'NORMAL0':
            self.normals = values
        elif semantic == 'TANGENT':
            self.tangents = values
        elif semantic == 'BINORMAL':
            self.binormals = values
        elif semantic == 'COLOR' or semantic == 'COLOR0':
            self.colors = values
        elif semantic == 'BLENDINDICES':
            self.skin_indices = values
        elif semantic == 'BLENDWEIGHT':
            self.skin_weights = values
        else:
            LOG.warning('Unknown semantic:%s', semantic)

    def get_values(self, semantic):
        """Retrieve the mesh values for a specified semantic."""
        if semantic == 'POSITION':
            values = self.positions
        elif semantic.startswith('TEXCOORD'):
            if semantic == 'TEXCOORD' or semantic == 'TEXCOORD0':
                values = self.uvs[0]
            else:
                index = int(semantic[8:])
                if index >= len(self.uvs):
                    values = []
                else:
                    values = self.uvs[index]
        elif semantic == 'NORMAL' or semantic == 'NORMAL0':
            values = self.normals
        elif semantic == 'TANGENT':
            values = self.tangents
        elif semantic == 'BINORMAL':
            values = self.binormals
        elif semantic == 'COLOR' or semantic == 'COLOR0':
            values = self.colors
        elif semantic == 'BLENDINDICES':
            values = self.skin_indices
        elif semantic == 'BLENDWEIGHT':
            values = self.skin_weights
        else:
            values = None
            LOG.warning('Unknown semantic:%s', semantic)
        return values

    ###################################################################################################################

    def transform(self, transform):
        """Transform the vertexes."""
        self.positions = [ vmath.m43transformp(transform, v) for v in self.positions ]
        self.normals = [ vmath.m43transformn(transform, v) for v in self.normals ]
        self.tangents = [ vmath.m43transformn(transform, v) for v in self.tangents ]
        self.binormals = [ vmath.m43transformn(transform, v) for v in self.binormals ]

    def rotate(self, transform):
        """Rotate the vertexes."""
        self.positions = [ vmath.v3mulm33(v, transform) for v in self.positions ]
        self.normals = [ vmath.v3mulm33(v, transform) for v in self.normals ]
        self.tangents = [ vmath.v3mulm33(v, transform) for v in self.tangents ]
        self.binormals = [ vmath.v3mulm33(v, transform) for v in self.binormals ]

    def invert_v_texture_map(self, uvs=None):
        """Invert the v texture mapping."""
        if not uvs:
            uvs = self.uvs[0]
        if len(uvs) > 0:
            if len(uvs[0]) == 2:
                elements = [ ]
                (_, min_v) = uvs[0]
                (_, max_v) = uvs[0]
                for (_, v) in uvs:
                    min_v = min(v, min_v)
                    max_v = max(v, max_v)
                midV = 2 * ((math.ceil(max_v) + math.floor(min_v)) * 0.5)
                for (u, v) in uvs:
                    elements.append( (u, midV - v) )
                self.uvs[0] = elements
            elif len(uvs[0]) == 3:
                elements = [ ]
                (_, min_v, _) = uvs[0]
                (_, max_v, _) = uvs[0]
                for (_, v, _) in uvs:
                    min_v = min(v, min_v)
                    max_v = max(v, max_v)
                midV = 2 * ((math.ceil(max_v) + math.floor(min_v)) * 0.5)
                for (u, v, w) in uvs:
                    elements.append( (u, midV - v, w) )
                self.uvs[0] = elements

    def generate_vertex_with_new_uv(self, pindex, vindex, new_uv):
        """Create a new vertex for a primitive with a new uv."""
        new_vindex = len(self.positions)                        # Get the new vindex
        while len(self.uvs[0]) < new_vindex:                       # Make sure the UVs and Positions are the same size
            self.uvs[0].append( (0, 0) )
        self.positions.append(self.positions[vindex])           # Clone the position
        self.uvs[0].append(new_uv)                                 # Create a new UV
        (ci1, ci2, ci3) = self.primitives[pindex]               # Update the primitive to use the new vindex
        if (ci1 == vindex):
            self.primitives[pindex] = (new_vindex, ci2, ci3)
        elif (ci2 == vindex):
            self.primitives[pindex] = (ci1, new_vindex, ci3)
        elif (ci3 == vindex):
            self.primitives[pindex] = (ci1, ci2, new_vindex)
        else:
            LOG.error("Didn't find vertex:%i used on primitive:%i", vindex, pindex)

    def generate_primitives(self, indexes):
        """Generate a list of primitives from a list of indexes."""
        # Make triangles out of each sequence of 3 indices.
        self.primitives = zip(indexes[0::3], indexes[1::3], indexes[2::3])

    def generate_bbox(self):
        """Generate a bounding box for the mesh."""
        # Assumes that the positions have at least one element, or the bbox will be nonsensical
        self.bbox['min'] = (float('inf'), float('inf'), float('inf'))
        self.bbox['max'] = (float('-inf'), float('-inf'), float('-inf'))
        for pos in self.positions:
            self.bbox['min'] = vmath.v3min(self.bbox['min'], pos)
            self.bbox['max'] = vmath.v3max(self.bbox['max'], pos)

    def remove_degenerate_primitives(self, remove_zero_length_edges=True,
                                     edge_length_tol=DEFAULT_POSITION_TOLERANCE):
        """Remove degenerate triangles with duplicated indices and optionally
           zero length edges."""
        def _is_degenerate(prim):
            """ Test if a prim is degenerate """
            (i1, i2, i3) = prim
            if i1 == i2 or i1 == i3 or i2 == i3:
                return True
            elif remove_zero_length_edges:
                (v1, v2, v3) = (self.positions[i1], self.positions[i2], self.positions[i3])
                return (vmath.v3is_zero(vmath.v3sub(v2, v1), edge_length_tol) or
                        vmath.v3is_zero(vmath.v3sub(v3, v1), edge_length_tol) or
                        vmath.v3is_zero(vmath.v3sub(v3, v2), edge_length_tol))
            else:
                return False

        self.primitives = [ prim for prim in self.primitives if not _is_degenerate(prim) ]

    ###################################################################################################################

    def generate_smooth_nbts(self):
        """Helper method to generate and smooth the normals, binormals and tangents."""
        if not len(self.normals):
            # Generate the initial normals if there are none.
            self.generate_normals()
        self.generate_tangents()
        self.normalize_tangents()
        self.smooth_tangents()
        self.generate_normals_from_tangents()
        self.smooth_normals()

    def _generate_normal(self, i1, i2, i3, pos_tol):
        """Generate a normal for 3 indexes."""
        (v1, v2, v3) = (self.positions[i1], self.positions[i2], self.positions[i3])
        e1 = vmath.v3sub(v2, v1)
        e2 = vmath.v3sub(v3, v1)
        e_other = vmath.v3sub(v3, v2)
        if (vmath.v3is_zero(e1, pos_tol) or vmath.v3is_zero(e2, pos_tol) or vmath.v3is_zero(e_other, pos_tol)):
            LOG.warning("%s: Found degenerate primitive:%s with edge length < position tolerance[%g]:[%s,%s,%s]",
                        "generate_normals", (i1, i2, i3), pos_tol, e1, e2, e_other)
            return (0, 0, 0)
        return vmath.v3normalize(vmath.v3cross(e1, e2))

    def generate_normals(self, pos_tol=DEFAULT_POSITION_TOLERANCE,
                               dont_norm_tol=DEFAULT_DONT_NORMALIZE_TOLERANCE):
        """Generate a normal per vertex as an average of face normals the primitive is part of."""
        zero = (0, 0, 0)
        self.normals = [zero] * len(self.positions)
        for (i1, i2, i3) in self.primitives:
            n = self._generate_normal(i1, i2, i3, pos_tol)
            self.normals[i1] = vmath.v3add(self.normals[i1], n)
            self.normals[i2] = vmath.v3add(self.normals[i2], n)
            self.normals[i3] = vmath.v3add(self.normals[i3], n)
        for i, n in enumerate(self.normals):
            lsq = vmath.v3lengthsq(n)
            if (lsq > dont_norm_tol): # Ensure normal isn't tiny before normalizing it.
                lr = 1.0 / math.sqrt(lsq)
                self.normals[i] = vmath.v3muls(n, lr)
            else:
                self.normals[i] = zero
                LOG.warning("%s: Found vertex[%i] with normal < normalizable tolerance[%g]:%s",
                            "generate_normals", i, dont_norm_tol, n)

    def smooth_normals(self, include_uv_tol=False,
                             root_node=None,
                             pos_tol=DEFAULT_POSITION_TOLERANCE,
                             nor_smooth_tol=DEFAULT_NORMAL_SMOOTH_TOLERANCE,
                             uv_tol=DEFAULT_UV_TOLERANCE):
        """Smooth normals within a certain position range and normal divergence limit."""

        if not root_node:
            if not self.kdtree:
                # Create a kd-tree to optimize the smoothing performance
                self.kdtree = pointmap.build_kdtree(self.positions)
            root_node = self.kdtree

        uvs = self.uvs[0]
        for i, p in enumerate(self.positions):
            original_normal = self.normals[i]
            accumulate_normal = (0, 0, 0)
            accumulated_indexes = [ ]

            # Generate a list of indexes for the positions close to the evaluation vertex.
            if include_uv_tol:
                uv = uvs[i]
                similiar_positions_indexes = root_node.points_within_uv_distance(self.positions, p, pos_tol,
                                                                                 uvs, uv, uv_tol)
            else:
                similiar_positions_indexes = root_node.points_within_distance(self.positions, p, pos_tol)

            for i in similiar_positions_indexes:
                this_normal = self.normals[i]
                if vmath.v3is_similar(this_normal, original_normal, nor_smooth_tol):
                    accumulate_normal = vmath.v3add(accumulate_normal, this_normal)
                    accumulated_indexes.append(i)
            smooth_normal = vmath.v3unitcube_clamp(vmath.v3normalize(accumulate_normal))
            for i in accumulated_indexes:
                self.normals[i] = smooth_normal

    ###################################################################################################################

    def _clone_vertex_with_new_tangents(self, prim_index, vertex_index, tangent, binormal):
        """Create a new vertex clone all attributes. Then set the new tangent and binormal."""
        clone_index = len(self.positions)
        self.positions.append(self.positions[vertex_index])
        self.normals.append(self.normals[vertex_index])
        for uvs in self.uvs:
            if len(uvs) > vertex_index:
                uvs.append(uvs[vertex_index])
        self.tangents.append(tangent)
        self.binormals.append(binormal)
        if len(self.colors) > vertex_index:
            self.colors.append(self.colors[vertex_index])
        if len(self.skin_indices) > vertex_index:
            self.skin_indices.append(self.skin_indices[vertex_index])
        if len(self.skin_weights) > vertex_index:
            self.skin_weights.append(self.skin_weights[vertex_index])
        return clone_index

    def _split_vertex_with_new_tangents(self, vertex_index, prim_index, split_map, tangent, binormal, tan_split_tol_sq):
        """Split the vertex if the tangents are outside of the accumulation tolerance."""

        def update_primitive_vertexes(primitives, prim_index, source_index, target_index):
            """Update the primitive for a cloned set of vertexes."""
            (p1, p2, p3) = primitives[prim_index]
            if p1 == source_index:
                p1 = target_index
            if p2 == source_index:
                p2 = target_index
            if p3 == source_index:
                p3 = target_index
            primitives[prim_index] = (p1, p2, p3)

        def tangents_within_tolerance(t1, b1, t2, b2, tan_split_tol_sq):
            """Test if the tangents and binormals are within tolerance."""
            tangent_within_tolerance = vmath.v3is_within_tolerance(t1, t2, tan_split_tol_sq)
            binormal_within_tolerance = vmath.v3is_within_tolerance(b1, b2, tan_split_tol_sq)
            return tangent_within_tolerance and binormal_within_tolerance

        def potential_accumulation_vertexes(vertex_index, split_map):
            """Iterator to consider all potential accumulation vertexes."""
            yield (vertex_index, vertex_index)
            for (original_index, clone_index) in split_map:
                if original_index == vertex_index:
                    yield (original_index, clone_index)

        for (original_index, index) in potential_accumulation_vertexes(vertex_index, split_map):
            if tangents_within_tolerance(self.tangents[index], self.binormals[index],
                                         tangent, binormal, tan_split_tol_sq):
                self.tangents[index] = vmath.v3add(self.tangents[index], tangent)
                self.binormals[index] = vmath.v3add(self.binormals[index], binormal)
                update_primitive_vertexes(self.primitives, prim_index, original_index, index)
                break
        else:
            # We need to split the vertex to start accumulating a different set of tangents.
            clone_index = self._clone_vertex_with_new_tangents(prim_index, vertex_index, tangent, binormal)
            update_primitive_vertexes(self.primitives, prim_index, vertex_index, clone_index)
            split_map.append( (vertex_index, clone_index) )
            LOG.debug("Splitting vertex:%i --> %i primitive[%i] is now:%s", vertex_index, clone_index, prim_index,
                      self.primitives[prim_index])
            LOG.debug("N:%s B:%s T:%s", self.normals[clone_index], self.binormals[clone_index],
                      self.tangents[clone_index])

    # pylint: disable=R0914
    def _generate_tangents_for_triangle(self, prim, pos_tol, zero_tol):
        """Generate binormals and tangents for a primitive."""
        du = [0, 0, 0]
        dv = [0, 0, 0]
        (i1, i2, i3) = prim                                                                     # Primitive indexes
        (v1, v2, v3) = (self.positions[i1], self.positions[i2], self.positions[i3])             # Vertex positions
        uvs = self.uvs[0]
        (uv1, uv2, uv3) = (uvs[i1], uvs[i2], uvs[i3])                                           # Vertex UVs
        (e21, e31, e32) = (vmath.v3sub(v2, v1), vmath.v3sub(v3, v1), vmath.v3sub(v3, v2))       # Generate edges
        # Ignore degenerates
        if (vmath.v3is_zero(e21, pos_tol) or vmath.v3is_zero(e31, pos_tol) or vmath.v3is_zero(e32, pos_tol)):
            LOG.warning("%s: Found degenerate triangle:%s", "_generate_tangents_for_triangle", (i1, i2, i3))
        else:
            # Calculate tangent and binormal
            edge1 = [e21[0], uv2[0] - uv1[0], uv2[1] - uv1[1]]
            edge2 = [e31[0], uv3[0] - uv1[0], uv3[1] - uv1[1]]
            cp = vmath.v3cross(edge1, edge2)
            if not vmath.iszero(cp[0], zero_tol):
                du[0] = -cp[1] / cp[0]
                dv[0] = -cp[2] / cp[0]
            edge1[0] = e21[1] # y, s, t
            edge2[0] = e31[1]
            cp = vmath.v3cross(edge1, edge2)
            if not vmath.iszero(cp[0], zero_tol):
                du[1] = -cp[1] / cp[0]
                dv[1] = -cp[2] / cp[0]
            edge1[0] = e21[2] # z, s, t
            edge2[0] = e31[2]
            cp = vmath.v3cross(edge1, edge2)
            if not vmath.iszero(cp[0], zero_tol):
                du[2] = -cp[1]/cp[0]
                dv[2] = -cp[2]/cp[0]
        return (du, dv)
    # pylint: enable=R0914

    def generate_tangents(self, pos_tol=DEFAULT_POSITION_TOLERANCE,
                                zero_tol=DEFAULT_ZERO_TOLERANCE,
                                tan_split_tol=DEFAULT_TANGENT_SPLIT_TOLERANCE):
        """Generate a NBT per vertex."""
        if 0 == len(self.uvs[0]): # We can't generate nbts without uvs
            LOG.debug("Can't generate nbts without uvs:%i", len(self.uvs[0]))
            return
        num_vertices = len(self.positions)
        self.tangents = [ (0, 0, 0) ] * num_vertices
        self.binormals = [ (0, 0, 0) ] * num_vertices

        # Split map for recording pairs of integers that represent which vertexes have been split.
        partition_vertices = True
        split_map = [ ]
        tan_split_tol_sq = (tan_split_tol * tan_split_tol)

        for prim_index, prim in enumerate(self.primitives):
            (tangent, binormal) = self._generate_tangents_for_triangle(prim, pos_tol, zero_tol)
            (i1, i2, i3) = prim
            if partition_vertices:
                self._split_vertex_with_new_tangents(i1, prim_index, split_map, tangent, binormal, tan_split_tol_sq)
                self._split_vertex_with_new_tangents(i2, prim_index, split_map, tangent, binormal, tan_split_tol_sq)
                self._split_vertex_with_new_tangents(i3, prim_index, split_map, tangent, binormal, tan_split_tol_sq)
            else:
                # Accumulate tangent and binormal
                self.tangents[i1] = vmath.v3add(self.tangents[i1], tangent)
                self.tangents[i2] = vmath.v3add(self.tangents[i2], tangent)
                self.tangents[i3] = vmath.v3add(self.tangents[i3], tangent)
                self.binormals[i1] = vmath.v3add(self.binormals[i1], binormal)
                self.binormals[i2] = vmath.v3add(self.binormals[i2], binormal)
                self.binormals[i3] = vmath.v3add(self.binormals[i3], binormal)

    def normalize_tangents(self, dont_norm_tol=DEFAULT_DONT_NORMALIZE_TOLERANCE):
        """Normalize and clamp the new tangents and binormals."""
        zero = (0, 0, 0)

        tangents = [ ]
        for i, t in enumerate(self.tangents):
            if (vmath.v3lengthsq(t) > dont_norm_tol): # Ensure the tangent isn't tiny before normalizing it.
                tangents.append(vmath.v3unitcube_clamp(vmath.v3normalize(t)))
            else:
                LOG.warning("%s: Found vertex[%i] with tangent < normalizable tolerance[%g]:%s",
                            "normalize_tangents", i, dont_norm_tol, t)
                tangents.append(zero)
        self.tangents = tangents

        binormals = [ ]
        for i, b in enumerate(self.binormals):
            if (vmath.v3lengthsq(b) > dont_norm_tol):
                binormals.append(vmath.v3unitcube_clamp(vmath.v3normalize(b)))
            else:
                LOG.warning("%s: Found vertex[%i] with binormal < normalizable tolerance[%g]:%s",
                            "normalize_tangents", i, dont_norm_tol, b)
                binormals.append(zero)
        self.binormals = binormals

    def smooth_tangents(self, include_uv_tol=False,
                              root_node=None,
                              pos_tol=DEFAULT_POSITION_TOLERANCE,
                              nor_smooth_tol=DEFAULT_NORMAL_SMOOTH_TOLERANCE,
                              uv_tol=DEFAULT_UV_TOLERANCE):
        """Smooth the tangents of vertices with similar positions."""
        def tangents_are_similar(t1, t2, b1, b2, nor_smooth_tol):
            """Test if both the tangents and binormals are similar."""
            tangent_similar = vmath.v3is_similar(t1, t2, nor_smooth_tol)
            binormal_similar = vmath.v3is_similar(b1, b2, nor_smooth_tol)
            return tangent_similar and binormal_similar

        if not root_node:
            if not self.kdtree:
                # Create a kd-tree to optimize the smoothing performance
                self.kdtree = pointmap.build_kdtree(self.positions)
            root_node = self.kdtree

        uvs = self.uvs[0]
        for i, p in enumerate(self.positions):
            original_tangent = self.tangents[i]
            original_binormal = self.binormals[i]
            accumulate_tangent = (0, 0, 0)
            accumulate_binormal = (0, 0, 0)
            accumulated_indexes = [ ]

            # Generate a list of indexes for the positions close to the evaluation vertex.
            if include_uv_tol:
                uv = uvs[i]
                similiar_positions_indexes = root_node.points_within_uv_distance(self.positions, p, pos_tol,
                                                                                 uvs, uv, uv_tol)
            else:
                similiar_positions_indexes = root_node.points_within_distance(self.positions, p, pos_tol)

            for i in similiar_positions_indexes:
                this_tangent = self.tangents[i]
                this_binormal = self.binormals[i]
                if tangents_are_similar(this_tangent, original_tangent,
                                        this_binormal, original_binormal, nor_smooth_tol):
                    accumulate_tangent = vmath.v3add(accumulate_tangent, this_tangent)
                    accumulate_binormal = vmath.v3add(accumulate_binormal, this_binormal)
                    accumulated_indexes.append(i)
            smooth_tangent = vmath.v3unitcube_clamp(vmath.v3normalize(accumulate_tangent))
            smooth_binormal = vmath.v3unitcube_clamp(vmath.v3normalize(accumulate_binormal))
            for i in accumulated_indexes:
                self.tangents[i] = smooth_tangent
                self.binormals[i] = smooth_binormal

    def generate_normals_from_tangents(self, zero_tol=DEFAULT_ZERO_TOLERANCE,
                                             dont_norm_tol=DEFAULT_DONT_NORMALIZE_TOLERANCE):
        """Create a new normal from the tangent and binormals."""
        if not len(self.tangents) or not len(self.binormals): # We can't generate normals without nbts
            LOG.debug("Can't generate normals from nbts without tangets:%i and binormals:%i",
                      len(self.tangents), len(self.binormals))
            return
        num_vertices = len(self.normals)
        assert(num_vertices == len(self.tangents))
        assert(num_vertices == len(self.binormals))
        # Regenerate the vertex normals from the new tangents and binormals
        for i in range(num_vertices):
            normal = self.normals[i]
            cp = vmath.v3cross(self.tangents[i], self.binormals[i])
            # Keep vertex normal if the tangent and the binormal are paralel
            if (vmath.v3lengthsq(cp) > dont_norm_tol):
                cp = vmath.v3normalize(cp)
                # Keep vertex normal if new normal is *somehow* in the primitive plane
                cosangle = vmath.v3dot(cp, normal)
                if not vmath.iszero(cosangle, zero_tol):
                    if cosangle < 0:
                        self.normals[i] = vmath.v3neg(cp)
                    else:
                        self.normals[i] = cp

    def flip_primitives(self):
        """Change winding order"""
        self.primitives = [ (i1, i3, i2) for (i1, i2, i3) in self.primitives ]

    def mirror_in(self, axis="x", flip=True):
        """Flip geometry in axis."""
        if axis == "x":
            self.positions = [ (-x, y, z) for (x, y, z) in self.positions ]
            self.normals = [ (-x, y, z) for (x, y, z) in self.normals ]
        elif axis == "y":
            self.positions = [ (x, -y, z) for (x, y, z) in self.positions ]
            self.normals = [ (x, -y, z) for (x, y, z) in self.normals ]
        elif axis == "z":
            self.positions = [ (x, y, -z) for (x, y, z) in self.positions ]
            self.normals = [ (x, y, -z) for (x, y, z) in self.normals ]
        if flip:
            self.flip_primitives()

    ###################################################################################################################

    def remove_redundant_vertexes(self):
        """Remove redundant vertex indexes from the element streams if unused by the primitives."""
        mapping = { }
        new_index = 0
        for (i1, i2, i3) in self.primitives:
            if i1 not in mapping:
                mapping[i1] = new_index
                new_index += 1
            if i2 not in mapping:
                mapping[i2] = new_index
                new_index += 1
            if i3 not in mapping:
                mapping[i3] = new_index
                new_index += 1
        old_index = len(self.positions)
        if old_index != new_index:
            LOG.info("Remapping:remapping vertexes from %i to %i", old_index, new_index)

        def __remap_stream(source, size, mapping):
            """Remap vertex attribute stream."""
            if len(source) > 0:
                target = [0] * size
                for k, v in mapping.items():
                    target[v] = source[k]
                return target
            return [ ]

        self.positions = __remap_stream(self.positions, new_index, mapping)
        for uvs in self.uvs:
            uvs[:] = __remap_stream(uvs, new_index, mapping)
        self.normals = __remap_stream(self.normals, new_index, mapping)
        self.tangents = __remap_stream(self.tangents, new_index, mapping)
        self.binormals = __remap_stream(self.binormals, new_index, mapping)
        self.colors = __remap_stream(self.colors, new_index, mapping)
        self.skin_indices = __remap_stream(self.skin_indices, new_index, mapping)
        self.skin_weights = __remap_stream(self.skin_weights, new_index, mapping)

        primitives = [ ]
        for (i1, i2, i3) in self.primitives:
            primitives.append( (mapping[i1], mapping[i2], mapping[i3]) )
        self.primitives = primitives

    ###################################################################################################################

    def stitch_vertices(self):
        """Combine equal vertices together, adjusting indices of primitives where appropriate
           Any other vertex data like normals, tangents, colors are ignored"""

        num_points = len(self.positions)
        points = sorted(enumerate(self.positions), key=lambda (_, x): x)

        mapping = [0] * num_points
        new_index = -1
        prev_p = None
        for (index, p) in points:
            if p != prev_p:
                new_index += 1
                prev_p = p
            mapping[index] = new_index

        self.primitives = [(mapping[i1], mapping[i2], mapping[i3]) for (i1, i2, i3) in self.primitives]
        new_positions = [0] * (new_index + 1)
        for (i, to) in enumerate(mapping):
            new_positions[to] = self.positions[i]
        self.positions = new_positions

    ###################################################################################################################

    def is_convex(self, positions=None, primitives=None):
        """Check if a mesh is convex by validating no vertices lie in front of the planes defined by its faces."""
        positions = positions or self.positions
        primitives = primitives or self.primitives
        for (i1, i2, i3) in primitives:
            v1 = positions[i1]
            v2 = positions[i2]
            v3 = positions[i3]

            edge1 = vmath.v3sub(v1, v3)
            edge2 = vmath.v3sub(v2, v3)
            normal = vmath.v3normalize(vmath.v3cross(edge1, edge2))

            for p in positions:
                dist = vmath.v3dot(vmath.v3sub(p, v1), normal)
                if dist > vmath.PRECISION:
                    return False
        return True

    def simply_closed(self, primitives=None):
        """Determine if a connected mesh is closed defined by triangle indexes
           in sense that it defines the boundary of a closed region of space without any
           possible dangling triangles on boundary.

           We assume that the triangle mesh does not have any ugly self intersections."""
        primitives = primitives or self.primitives
        # We do this by counting the number of triangles on each triangle edge
        # Specifically check that this value is exactly 2 for every edge.1
        edges = { }
        def _inc(a, b):
            """Increment edge count for vertex indices a, b.
               Return True if edge count has exceeded 2"""
            if a > b:
                return _inc(b, a)
            if (a, b) in edges:
                edges[(a, b)] += 1
            else:
                edges[(a, b)] = 1
            return edges[(a, b)] > 2

        for (i1, i2, i3) in primitives:
            if _inc(i1, i2):
                return False
            if _inc(i2, i3):
                return False
            if _inc(i3, i1):
                return False

        for (_, v) in edges.items():
            if v != 2:
                return False

        return True

    def is_planar(self, positions=None, tolerance=DEFAULT_PLANAR_TOLERANCE):
        """Determine if mesh is planar; that all vertices lie in the same plane.
           If positions argument is not supplied, then self.positions is used"""
        positions = positions or self.positions
        if len(positions) <= 3:
            return True

        p0 = positions[0]
        edge1 = vmath.v3sub(positions[1], p0)
        edge2 = vmath.v3sub(positions[2], p0)
        normal = vmath.v3normalize(vmath.v3cross(edge1, edge2))

        for p in positions:
            distance = vmath.v3dot(vmath.v3sub(p, p0), normal)
            if (distance * distance) > tolerance:
                return False

        return True

    def is_convex_planar(self, positions=None):
        """Determine if a planar mesh is convex; taking virtual edge normals into account"""
        positions = positions or self.positions
        if len(positions) <= 3:
            return True

        p0 = positions[0]
        edge1 = vmath.v3sub(positions[1], p0)
        edge2 = vmath.v3sub(positions[2], p0)
        normal = vmath.v3normalize(vmath.v3cross(edge1, edge2))

        for (i, p) in enumerate(positions):
            j = (i + 1) if (i < len(positions) - 1) else 0
            q = positions[j]

            edge3 = vmath.v3sub(q, p)
            edge_normal = vmath.v3cross(normal, edge3)

            for w in positions:
                if vmath.v3dot(vmath.v3sub(w, p), edge_normal) < -vmath.PRECISION:
                    return False

        return True

    def connected_components(self):
        """Determine connected components of mesh, returning list of set of vertices and primitives."""
        # Perform this algorithm with a disjoint set forest.
        # Initialise components: [index, parent_index, rank, component]
        components = [[i, 0] for i in range(len(self.positions))]

        def _find(x):
            """Find root note in disjoint set forest, compressing path to root."""
            if components[x][0] == x:
                return x
            else:
                root = x
                stack = [ ]
                while components[root][0] != root:
                    stack.append(root)
                    root = components[root][0]
                for y in stack:
                    components[y][0] = root
                return root

        def _unify(x, y):
            """Unify two components in disjoint set forest by rank."""
            x_root = _find(x)
            y_root = _find(y)
            if x_root != y_root:
                xc = components[x_root]
                yc = components[y_root]
                if xc[1] < yc[1]:
                    xc[0] = y_root
                elif xc[1] > yc[1]:
                    yc[0] = x_root
                else:
                    yc[0] = x_root
                    xc[1] += 1

        # Unify components based on adjacency information inferred through shared vertices in primitives
        for (i1, i2, i3) in self.primitives:
            _unify(i1, i2)
            _unify(i2, i3)

        # Return list of all components associated with each root.
        ret = [ ]
        for c in [y for y in range(len(self.positions)) if _find(y) == y]:
            m = Mesh()
            m.positions = self.positions[:]
            m.primitives = [(i1, i2, i3) for (i1, i2, i3) in self.primitives if _find(i1) == c]

            m.remove_redundant_vertexes()
            ret.append((m.positions, m.primitives))

        return ret

    # pylint: disable=R0914
    def make_planar_convex_hull(self, positions=None, tangent_tolerance=DEFAULT_TANGENT_PROJECTION_TOLERANCE):
        """Convert set of co-planar positions into a minimal set of positions required to form their convex
           hull, together with a set of primitives representing one side of the hulls' surface as a
           new Mesh"""
        positions = positions or self.positions
        # Use a 2D Graham Scan with projections of positions onto their maximal plane.
        # Time complexity: O(nh) for n positions and h out positions.

        # Determine maximal plane for projection.
        edge1 = vmath.v3sub(positions[1], positions[0])
        edge2 = vmath.v3sub(positions[2], positions[0])
        (n0, _, n2) = n = vmath.v3cross(edge1, edge2)

        # compute plane tangents.
        # epsilon chosen with experiment
        if (n0 * n0) + (n2 * n2) < tangent_tolerance:
            t = (1, 0, 0)
        else:
            t = (-n2, 0, n0)
        u = vmath.v3cross(n, t)

        # Project to tangents
        projs = [(vmath.v3dot(p, t), vmath.v3dot(p, u)) for p in positions]

        # Find first vertex on hull as minimal lexicographically ordered projection
        i0 = 0
        minp = projs[0]
        for i in range(1, len(projs)):
            if projs[i] < minp:
                i0 = i
                minp = projs[i]

        # Map from old vertex indices to new index for those vertices used by hull
        outv = { i0: 0 }
        new_index = 1

        # List of output triangles.
        outtriangles = [ ]
        fsti = i0
        (p0x, p0y) = minp
        while True:
            i1 = -1
            for i in range(len(projs)):
                if i == i0:
                    continue

                (px, py) = projs[i]
                plsq = ((px - p0x) * (px - p0x)) + ((py - p0y) * (py - p0y))
                if i1 == -1:
                    i1 = i
                    maxp = (px, py)
                    maxplsq = plsq
                    continue

                # If this is not the first vertex tested, determine if new vertex makes
                # A right turn looking in direction of edge, or is further in same direction.
                (qx, qy) = maxp
                turn = ((qx - p0x) * (py - p0y)) - ((qy - p0y) * (px - p0x))
                if turn < 0 or (turn == 0 and plsq > maxplsq):
                    i1 = i
                    maxp = (px, py)
                    maxplsq = plsq

            # Append i1 vertex to hull
            if i1 in outv:
                break

            outv[i1] = new_index
            new_index += 1

            # Form triangle (fsti, i0, i1)
            # If i0 != fsti
            if i0 != fsti:
                outtriangles.append((fsti, i0, i1))

            i0 = i1
            (p0x, p0y) = projs[i1]

        # Compute output hull.
        mesh = Mesh()
        mesh.positions = [0] * len(outv.items())
        for i, j in outv.items():
            mesh.positions[j] = positions[i]
        mesh.primitives = [(outv[i1], outv[i2], outv[i3]) for (i1, i2, i3) in outtriangles]

        return mesh
    # pylint: enable=R0914

    # pylint: disable=R0914
    def make_convex_hull(self, positions=None, collinear_tolerance=DEFAULT_COLLINEAR_TOLERANCE,
                               coplanar_tolerance=DEFAULT_COPLANAR_TOLERANCE):
        """Convert set of positions into a minimal set of positions required to form their convex hull
           Together with a set of primitives representing a triangulation of the hull's surface as a
           new Mesh"""
        positions = positions or self.positions
        # Use a 3D generalisation of a Graham Scan to facilitate a triangulation of the hull in generation.
        # Time complexity: O(nh) for n positions, and h out-positions.

        # Find first vertex on hull as minimal lexicographically ordered position
        i0 = 0
        minp = positions[0]
        for i in range(1, len(positions)):
            if positions[i] < minp:
                i0 = i
                minp = positions[i]

        # Find second vertex by performing a 2D graham scan step on the xy-plane projections of positions.
        i1 = -1
        (cos1, lsq1) = (-2, 0) # will always be overriden as cos(theta) > -2
        (p0x, p0y, _) = minp
        for i in range(len(positions)):
            if i == i0:
                continue

            (px, py, _) = positions[i]
            dx = px - p0x
            dy = py - p0y
            lsq = (dx * dx) + (dy * dy)
            if lsq == 0:
                if i1 == -1:
                    i1 = i
                continue

            cos = dy / math.sqrt(lsq)
            if cos > cos1 or (cos == cos1 and lsq > lsq1):
                cos1 = cos
                lsq1 = lsq
                i1 = i

        # Dictionary of visited edges to avoid duplicates
        # List of open edges to be visited by graham scan
        closedset = set()
        openset = [ (i0, i1), (i1, i0) ]

        # Mapping from old vertex index to new index for those vertices used by hull.
        outv = { i0: 0, i1: 1 }
        new_index = 2

        # Output triangles for hull
        outtriangles = [ ]

        while len(openset) > 0:
            (i0, i1) = openset.pop()
            if (i0, i1) in closedset:
                continue

            # Find next vertex on hull to form triangle with.
            i2 = -1

            p0 = positions[i0]
            edge = vmath.v3sub(positions[i1], p0)
            isq = 1.0 / vmath.v3lengthsq(edge)

            for i in range(len(positions)):
                if i == i0 or i == i1:
                    continue

                p = positions[i]
                # Find closest point on line containing the edge to determine vector to p
                # Perpendicular to edge, this is not necessary for computing the turn
                # since the value of 'turn' computed is actually the same whether we do this
                # or not, however it is needed to be able to sort equal turn vertices
                # by distance.
                t = vmath.v3dot(vmath.v3sub(p, p0), edge) * isq
                pedge = vmath.v3sub(p, vmath.v3add(p0, vmath.v3muls(edge, t)))

                # Ignore vertex if |pedge| = 0, thus ignoring vertices on the edge itself
                # And so avoid generating degenerate triangles.
                #
                # epsilon chosen by experiment
                plsq = vmath.v3lengthsq(pedge)
                if plsq <= collinear_tolerance:
                    continue

                if i2 == -1:
                    i2 = i
                    maxpedge = pedge
                    maxplsq = plsq
                    maxt = t
                    continue

                # If this is not the first vertex tested, determine if new vertex makes
                # A right turn looking in direction of edge, or is further in same direction.
                #
                # We require a special case when pedge, and maxpedge are coplanar with edge
                # As the computed turn will be 0 and we must check if the cross product
                # Is facing into the hull or outside to determine left/right instead.
                axis = vmath.v3cross(pedge, maxpedge)
                coplanar = vmath.v3dot(pedge, vmath.v3cross(edge, maxpedge))
                # epsilon chosen by experiment
                if (coplanar * coplanar) <= coplanar_tolerance:
                    # Special case for coplanar pedge, maxpedge, edge
                    #
                    # if edges are in same direction, base on distance.
                    if vmath.v3dot(pedge, maxpedge) >= 0:
                        if plsq > maxplsq or (plsq == maxplsq and t > maxt):
                            i2 = i
                            maxpedge = pedge
                            maxplsq = plsq
                            maxt = t
                    else:
                        axis = vmath.v3cross(vmath.v3sub(p, p0), edge)
                        # Check if axis points into the hull.
                        internal = True
                        for p in positions:
                            if vmath.v3dot(axis, vmath.v3sub(p, p0)) < 0:
                                internal = False
                                break

                        if internal:
                            i2 = i
                            maxpedge = pedge
                            maxplsq = plsq
                            maxt = t
                else:
                    turn = vmath.v3dot(axis, edge)
                    # epsilon chosen by experiment
                    if turn < 0 or (turn <= collinear_tolerance and plsq > maxplsq):
                        i2 = i
                        maxpedge = pedge
                        maxplsq = plsq
                        maxt = t

            # Append i2 vertex to hull
            if i2 not in outv:
                outv[i2] = new_index
                new_index += 1

            # Form triangle iff no edge is closed.
            if ((i0, i1) not in closedset and
                (i1, i2) not in closedset and
                (i2, i0) not in closedset):

                outtriangles.append((i0, i1, i2))
                # Mark visited edges. Open new edges.
                closedset.add((i0, i1))
                closedset.add((i1, i2))
                closedset.add((i2, i0))

                openset.append((i2, i1))
                openset.append((i0, i2))

        # cnt does not 'need' to be len(positions) for convex hull to have succeeded
        #   but numerical issues with not using say fixed point means that we cannot
        #   be sure of success if it is not equal.
        # Obvious side effect is input mesh must already be a convex hull with no
        #   unnecessary vertices.
        cnt = len(outv.items())
        if cnt != len(positions):
            return None

        # Compute output mesh.
        mesh = Mesh()
        mesh.positions = [0] * cnt
        for (i, j) in outv.items():
            mesh.positions[j] = positions[i]
        mesh.primitives = [(outv[i1], outv[i2], outv[i3]) for (i1, i2, i3) in outtriangles]

        # Ensure algorithm has not failed!
        if not mesh.is_convex() or not mesh.simply_closed():
            return None

        return mesh
    # pylint: enable=R0914

    def extend_mesh(self, positions, primitives):
        """Extend mesh with extra set of positions and primitives defiend relative to positions"""
        offset = len(self.positions)
        self.positions.extend(positions)
        self.primitives.extend([(i1 + offset, i2 + offset, i3 + offset) for (i1, i2, i3) in primitives])

    def convex_hulls(self, max_components=-1, allow_non_hulls=False,
                           planar_vertex_count=DEFAULT_PLANAR_HULL_VERTEX_THRESHOLD):
        """Split triangle mesh into set of unconnected convex hulls.

           If max_components != -1, then None will be returned should the number
           of connected components exceed this value.

           If allow_non_hulls is False, and any component of the mesh was not able
           to be converted then None will be returned.

           No other vertex data is assumed to exist, and mesh is permitted to be
           mutated.

           The return value is a tuple ([Mesh], Mesh) for the list of convex hulls
           computed, and an additional mesh representing the remainder of the mesh
           which could not be converted (If allow_non_hulls is False, then this
           additional mesh will always be None, otherwise it may still be None
           if all of the mesh was able to be converted)."""
        self.stitch_vertices()
        self.remove_degenerate_primitives()
        self.remove_redundant_vertexes()

        components = self.connected_components()
        if max_components != -1 and len(components) > max_components:
            return None

        if allow_non_hulls:
            triangles = Mesh()
            triangles.positions = [ ]
            triangles.primitives = [ ]

        ret = [ ]
        for (vertices, primitives) in components:
            convex = self.is_convex(vertices, primitives)
            closed = self.simply_closed(primitives)
            planar = self.is_planar(vertices)

            if convex and planar:
                if self.is_convex_planar(vertices) and len(vertices) >= planar_vertex_count:
                    print "Converted to planar convex hull!"
                    ret.append(self.make_planar_convex_hull(vertices))
                else:
                    if allow_non_hulls:
                        triangles.extend_mesh(vertices, primitives)
                    else:
                        return None

            elif convex and closed:
                mesh = self.make_convex_hull(vertices)
                if mesh == None:
                    if allow_non_hulls:
                        print "Failed to turn convex closed mesh into convex hull!"
                        triangles.extend_mesh(vertices, primitives)
                    else:
                        return None
                else:
                    # Ensure that convex hull can be re-computed correctly as this will be performed
                    # By WebGL physics device.
                    if mesh.make_convex_hull() == None:
                        if allow_non_hulls:
                            print "Convex hull failed to be re-computed!"
                            triangles.extend_mesh(vertices, primitives)
                        else:
                            return None
                    else:
                        print "Converted to convex hull!"
                        ret.append(mesh)

            else:
                # Cannot convert component to a convex hull.
                if allow_non_hulls:
                    triangles.extend_mesh(vertices, primitives)
                else:
                    return None

        if len(triangles.positions) == 0:
            triangles = None

        return (ret, triangles)

# pylint: enable=R0902
# pylint: enable=R0904

#######################################################################################################################

# pylint: disable=C0111
def __generate_test_square(json_asset):

    def __generate_square_t():
        mesh = Mesh()
        mesh.positions.extend( [ (0, 0, 0), (1, 0, 0), (1, 1, 1), (0, 1, 1), (2, 0, 0), (2, 1, 1) ] )
        mesh.uvs[0].extend( [ (0, 0), (1, 0), (1, 1), (0, 1), (0, 0), (0, 1) ] )
        indexes = [ ]
        indexes.extend( [ 0, 1, 2, 0, 2, 3, 1, 4, 5, 1, 5, 2 ] )
        return (mesh, indexes)

    def __generate_square_b():
        mesh = Mesh()
        mesh.positions.extend( [ (0, 2, 2), (1, 2, 2), (1, 3, 3), (0, 3, 3), (2, 2, 2), (2, 3, 3) ] )
        mesh.uvs[0].extend( [ (0, 0), (0, 1), (1, 1), (1, 0), (0, 0), (1, 0) ] )
        indexes = [ ]
        indexes.extend( [ 0, 1, 2, 0, 2, 3, 1, 4, 5, 1, 5, 2 ] )
        return (mesh, indexes)

    def __generate_split_square_t():
        mesh = Mesh()
        mesh.positions.extend( [ (0, 4, 4), (1, 4, 4), (1, 5, 5), (0, 5, 5), (2, 4, 4), (2, 5, 5),
                                 (1, 4, 4), (1, 5, 5) ] )
        mesh.uvs[0].extend( [ (0, 0), (1, 0), (1, 1), (0, 1), (0, 0), (0, 1),
                              (1, 0), (1, 1) ] )
        indexes = [ ]
        indexes.extend( [ 0, 1, 2, 0, 2, 3, 6, 4, 5, 6, 5, 7 ] )
        return (mesh, indexes)

    def __generate_split_square_b():
        mesh = Mesh()
        mesh.positions.extend( [ (0, 6, 6), (1, 6, 6), (1, 7, 7), (0, 7, 7), (2, 6, 6), (2, 7, 7),
                                 (1, 6, 6), (1, 7, 7) ] )
        mesh.uvs[0].extend( [ (0, 0), (0, 1), (1, 1), (1, 0), (0, 0), (1, 0),
                              (0, 1), (1, 1) ] )
        indexes = [ ]
        indexes.extend( [ 0, 1, 2, 0, 2, 3, 6, 4, 5, 6, 5, 7 ] )
        return (mesh, indexes)

    def __generate_control_square_t():
        r2 = 1 / math.sqrt(2)
        mesh = Mesh()
        mesh.positions.extend( [ (0, 8, 8), (1, 8, 8), (1, 9, 9), (0, 9, 9),
                                 (1, 8, 8), (2, 8, 8), (2, 9, 9), (1, 9, 9) ] )
        mesh.uvs[0].extend( [ (0, 0), (1, 0), (1, 1), (0, 1),
                              (1, 0), (0, 0), (0, 1), (1, 1) ] )
        mesh.tangents.extend( [ (1, 0, 0), (1, 0, 0), (1, 0, 0), (1, 0, 0),
                                (-1, 0, 0), (-1, 0, 0), (-1, 0, 0), (-1, 0, 0) ] )
        mesh.binormals.extend( [ (0, r2, r2), (0, r2, r2), (0, r2, r2), (0, r2, r2),
                                 (0, r2, r2), (0, r2, r2), (0, r2, r2), (0, r2, r2) ] )
        indexes = [ ]
        indexes.extend( [ 0, 1, 2, 0, 2, 3, 4, 5, 6, 4, 6, 7 ] )
        return (mesh, indexes)

    def __generate_control_square_b():
        r2 = 1 / math.sqrt(2)
        mesh = Mesh()
        mesh.positions.extend( [ (0, 10, 10), (1, 10, 10), (1, 11, 11), (0, 11, 11),
                                 (1, 10, 10), (2, 10, 10), (2, 11, 11), (1, 11, 11) ] )
        mesh.uvs[0].extend( [ (0, 0), (0, 1), (1, 1), (1, 0),
                              (0, 1), (0, 0), (1, 0), (1, 1) ] )
        mesh.tangents.extend( [ (0, r2, r2), (0, r2, r2), (0, r2, r2), (0, r2, r2),
                                (0, r2, r2), (0, r2, r2), (0, r2, r2), (0, r2, r2) ] )
        mesh.binormals.extend( [ (1, 0, 0), (1, 0, 0), (1, 0, 0), (1, 0, 0),
                                 (-1, 0, 0), (-1, 0, 0), (-1, 0, 0), (-1, 0, 0) ] )
        indexes = [ ]
        indexes.extend( [ 0, 1, 2, 0, 2, 3, 4, 5, 6, 4, 6, 7 ] )
        return (mesh, indexes)

    def __generate_square((a, i), (s, n), j):
        a.generate_primitives(i)
        a.generate_normals()
        if len(a.tangents) == 0:
            a.generate_smooth_nbts()
        j.attach_shape(s)
        n = NodeName(n)
        j.attach_node(n)
        j.attach_node_shape_instance(n, s, s, m)
        j.attach_positions(a.positions, s)
        j.attach_nbts(a.normals, a.tangents, a.binormals, s)
        j.attach_uvs(a.uvs[0], s)
        j.attach_surface(a.primitives, JsonAsset.SurfaceTriangles, s)

    m = 'material-0'
    e = 'effect-0'
    json_asset.attach_effect(e, 'normalmap')
    json_asset.attach_material(m, e)
    json_asset.attach_texture(m, 'diffuse', '/assets/checker.png')
    json_asset.attach_texture(m, 'normal_map', '/assets/monkey.png')
    __generate_square(__generate_square_t(), ('shape-0', 'node-0'), json_asset)
    __generate_square(__generate_square_b(), ('shape-1', 'node-1'), json_asset)
    __generate_square(__generate_split_square_t(), ('shape-2', 'node-2'), json_asset)
    __generate_square(__generate_split_square_b(), ('shape-3', 'node-3'), json_asset)
    __generate_square(__generate_control_square_t(), ('shape-4', 'node-4'), json_asset)
    __generate_square(__generate_control_square_b(), ('shape-5', 'node-5'), json_asset)

def __generate_test_cube():
    def add_quad_face(v, m, primitives):
        """Append a two triangle quad to the mesh."""
        offset = len(m.positions)
        m.positions.extend( [ v[0], v[1], v[2], v[3] ] )
        m.uvs[0].extend( [ (1, 1), (0, 1), (0, 0), (1, 0) ] )
        primitives.extend( [offset, offset + 2, offset + 1, offset, offset + 3, offset + 2] )

    indexes = [ ]
    mesh = Mesh()
    v = [ (-1, -1, -1), (-1, -1,  1), (-1,  1,  1), (-1,  1, -1),
          ( 1, -1, -1), ( 1, -1,  1), ( 1,  1,  1), ( 1,  1, -1) ]
    add_quad_face( [ v[0], v[1], v[2], v[3] ], mesh, indexes)
    add_quad_face( [ v[4], v[0], v[3], v[7] ], mesh, indexes)
    add_quad_face( [ v[5], v[4], v[7], v[6] ], mesh, indexes)
    add_quad_face( [ v[1], v[5], v[6], v[2] ], mesh, indexes)
    add_quad_face( [ v[7], v[3], v[2], v[6] ], mesh, indexes)
    add_quad_face( [ v[1], v[0], v[4], v[5] ], mesh, indexes)

    mesh.generate_primitives(indexes)
    return mesh

# pylint: enable=C0111

if __name__ == "__main__":
    # pylint: disable=W0403
    from asset2json import JsonAsset
    from node import NodeName
    # pylint: enable=W0403
    logging.basicConfig(level=logging.INFO)

    J = JsonAsset()
    __generate_test_square(J)
    J.clean()
    JSON = J.json_to_string()
    with open("mesh.json", 'w') as output:
        output.write(JSON)
    print JSON
    J.log_metrics()

########NEW FILE########
__FILENAME__ = node
# Copyright (c) 2009-2011,2013 Turbulenz Limited
"""
Utility for manipluating Nodes.
"""

__version__ = '1.0.0'

class NodeName(object):
    """Node class to consistent name ."""

    def __init__(self, name):
        self.name = name
        self.path = [ ]

    def add_parent(self, parent):
        """Add the name for a parent node."""
        self.path.append(parent)

    def add_parents(self, parents):
        """Add a list of names for the parent nodes."""
        self.path.extend(parents)

    def add_parent_node(self, parent_node):
        """Add a parent node as a parent."""
        self.add_parents(parent_node.hierarchy_names())
        return self

    def add_path(self, path):
        """Add a path for the parent nodes which is split by '/'."""
        self.path = path.split('/')

    def leaf_name(self):
        """Return the leaf node name."""
        return self.name

    def hierarchy_names(self):
        """Return a list of all the node names."""
        return self.path + [self.name]

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        if len(self.path) > 0:
            return '/'.join(self.path) + '/' + self.name
        else:
            return self.name

########NEW FILE########
__FILENAME__ = obj2json
#!/usr/bin/python
# Copyright (c) 2009-2013 Turbulenz Limited
"""
Convert LightWave (.obj) OBJ2 files into a Turbulenz JSON asset.

Supports generating NBTs.
"""

import logging
LOG = logging.getLogger('asset')

# pylint: disable=W0403
from stdtool import standard_main, standard_json_out, standard_include
from asset2json import JsonAsset
from mesh import Mesh
from node import NodeName
from os.path import basename
# pylint: enable=W0403

__version__ = '1.2.2'
__dependencies__ = ['asset2json', 'mesh', 'node', 'vmath']


DEFAULT_EFFECT_NAME = 'lambert'

# Note:
# * Does not have support for .mtl files yet, but expects any relevant materials
#   to be declared in a .material file and included as a dependancy in deps.yaml
# * This script sets the default node name of the asset parsed to be the file name (without the path),
#   unless anything else is supplied. This could lead to clashes with other nodes with the same name.
# * Each surface is assumed to only have a single material. A new surface will be made upon requiring a new material.

#######################################################################################################################

def _increment_name(name):
    """Returns a name similar to the inputted name

        If the inputted name ends with a hyphen and then a number,
        then the outputted name has that number incremented.
        Otherwise, the outputted name has a hyphen and the number '1' appended to it.
    """
    index = name.rfind('-')
    if index == -1:
        # The is not already followed by a number, so just append -1
        return name + '-1'
    else:
        # The number is already followed by a number, so increment the number
        value = int(name[index+1:])
        return name[:index+1] + str(value+1)

def purge_empty(dictionary, recurseOnce = False):
    """Removes all elements of a dictionary which return true for elem.is_empty().

        If recurseOnce is True, then it will call element.purge_empty()
        for any remaining elements in the dictionary. This will not recurse further."""
    names_empty = []
    for name, elem in dictionary.iteritems():
        if elem.is_empty():
            names_empty.append(name)
    # Need to compile the list of names of empty elements in a separate loop above,
    # to avoid changing dictionary during iteration over it directly.
    for name in names_empty:
        del dictionary[name]
    if recurseOnce:
        for elem in dictionary.itervalues():
            # Note that it is here assumed that the element has a method purge_empty
            elem.purge_empty()


#######################################################################################################################

class Surface(object):
    """Represents a surface (a.k.a. group) as parsed from the .obj file into .json format

        Contains a material, and indices into the Obj2json.primitives list
        to identify which polygons belong to this surface."""
    def __init__(self, first, material):
        # first refers to initial index of triangles parsed
        # count refers to number of triangles parsed
        self.first = first
        self.count = 0
        self.material_name = material
    def is_empty(self):
        return self.count == 0

class Shape(object):
    """Represents a shape (a.k.a. object) as parsed from the .obj file into .json format

        Contains a dictionary of names -> surfaces."""
    # NB: Do not pass in Null for the surfaces parameter, all shapes are assumed to
    #     contain a dictionary with at least one surface, even if it is a default one.
    def __init__(self, surfaces):
        # Dictionary of names -> surfaces
        self.surfaces = surfaces
    def is_empty(self):
        empty = True
        for surface in self.surfaces.itervalues():
            # If a single surface is non-empty, empty will be false
            empty = empty and surface.is_empty()
        return empty
    def purge_empty(self):
        purge_empty(self.surfaces)

#######################################################################################################################

# pylint: disable=R0904
class Obj2json(Mesh):
    """Parse a OBJ file and generate a Turbulenz JSON geometry asset."""
    # TODO: Probably some more information should be moved from the Obj2json class to the Shape class.

    def __init__(self, obj_file_name):
        self.default_shape_name = obj_file_name or 'initial_shape'
        self.default_surface_name = 'initial_surface'
        self.default_material_name = 'default'

        # Name of the shape/surface/material from the most recently parsed 'o'/'g'/'usemtl' line respectively
        self.curr_shape_name = self.default_shape_name
        self.curr_surf_name = self.default_surface_name
        self.curr_mtl_name = self.default_material_name

        # To keep of track of number of polygons parsed so far
        self.next_polygon_index = 0
        # A tuple of indices per vertex element
        self.indices = [ ]

        # Shortcut to be able to access the current surface in fewer characters and lookups
        self.curr_surf = Surface(0, self.default_material_name)
        # Dictionary of names -> shapes. Initialise to a default shape with a default surface
        self.shapes = { self.default_shape_name : Shape({ self.default_surface_name : self.curr_surf }) }
        Mesh.__init__(self)

    def __read_object_name(self, data):
        """Parse the 'o' line. This line contains the mesh name."""
        LOG.debug("object name:%s", data)
        # Remove any shapes with no surfaces (e.g. the default shape if a named one is given)
        purge_empty(self.shapes)
        # If a shape with this name has already been declared, do not change it,
        # append the following faces to the current shape in stead
        if data not in self.shapes:
            self.curr_shape_name = data
            self.curr_surf = Surface(self.next_polygon_index, self.curr_mtl_name)
            self.shapes[data] = Shape({self.curr_surf_name : self.curr_surf})

    def __read_group_name(self, data):
        """Parse the 'g' line. This indicates the start of a group (surface)."""
        # Remove leading/trailing whitespace
        data = data.strip()
        LOG.debug("group name:%s", data)
        # Note: Don't purge empty shapes/surfaces here, you might remove a new surface
        #       created by a preceding 'usemtl' line. Purging happens after parsing.
        self.curr_surf_name = data
        # Use most recently specified material (unless overridden later)
        self.curr_surf = Surface(self.next_polygon_index, self.curr_mtl_name)
        self.shapes[self.curr_shape_name].surfaces[data] = self.curr_surf

    def __read_material(self, data):
        """Parse the 'usemtl' line. This references a material."""
        data = data.strip()
        LOG.debug("material name:%s", data)
        self.curr_mtl_name = data
        if self.curr_surf.is_empty():
            # No polygons (yet) in the current surface, so just set its material
            self.curr_surf.material_name = data
        elif self.curr_surf.material_name != data:
            # Current surface already has a number of faces of a different material
            # so create a new surface for this new material
            self.curr_surf = Surface(self.next_polygon_index, data)
            self.curr_surf_name = _increment_name(self.curr_surf_name)
            self.shapes[self.curr_shape_name].surfaces[self.curr_surf_name] = self.curr_surf

    def __read_vertex_position(self, data):
        """Parse the 'v' line. This line contains the vertex position."""
        sv = data.split(' ')
        position = (float(sv[0]), float(sv[1]), float(sv[2]))
        self.positions.append(position)
        # Do not calculate the bounding box here, as some unused vertices may later be removed

    def __read_vertex_uvs(self, data):
        """Parse the 'vt' line. This line contains the vertex uvs."""
        # Texture coordinates
        sv = data.split(' ')
        if len(sv) == 2:
            uvs = (float(sv[0]), float(sv[1]))
        else:
            uvs = (float(sv[0]), float(sv[1]), float(sv[2]))
        self.uvs[0].append(uvs)

    def __read_vertex_normal(self, data):
        """Parse the 'vn' line. This line contains the vertex normals."""
        (sv0, sv1, sv2) = data.split(' ')
        normal = (float(sv0), float(sv1), -float(sv2))
        self.normals.append(normal)

    def __read_face(self, data):
        """Parse the 'f' line. This line contains a face.

            Constructs a tri-fan if face has more than 3 edges."""
        def __extract_indices(si):
            """Add a tuple of indices."""
            # Vertex index / Texture index / Normal index
            # Subtract 1 to count indices from 0, not from 1.
            s = si.split('/')
            if len(s) == 1:
                return [int(s[0]) - 1]
            if len(s) == 2:
                return (int(s[0]) - 1, int(s[1]) - 1)
            else:
                if len(s[1]) == 0:
                    return (int(s[0]) - 1, int(s[2]) - 1)
                else:
                    return (int(s[0]) - 1, int(s[1]) - 1, int(s[2]) - 1)

        # Split string into list of vertices
        si = data.split()
        indices = self.indices
        # Construct a tri-fan of all the vertices supplied (no support for quadrilaterals or polygons)
        # Origin vertex of fan
        i0 = __extract_indices(si[0])
        prevInd = __extract_indices(si[1])
        for i in xrange(2, len(si)):
            currInd = __extract_indices(si[i])
            indices.append(i0)
            indices.append(prevInd)
            indices.append(currInd)
            prevInd = currInd
        num_triangles = len(si) - 2
        self.next_polygon_index += num_triangles
        self.curr_surf.count += num_triangles

    def __ignore_comments(self, data):
        """Ignore comments."""

#######################################################################################################################

    def parse(self, f, prefix = ""):
        """Parse an OBJ file stream."""
        chunks_with_data = { 'v': Obj2json.__read_vertex_position,
                             'vt': Obj2json.__read_vertex_uvs,
                             'vn': Obj2json.__read_vertex_normal,
                             'f': Obj2json.__read_face,
                             'o': Obj2json.__read_object_name,
                             'g': Obj2json.__read_group_name,
                             'usemtl': Obj2json.__read_material,
                             '#': Obj2json.__ignore_comments}
        for lineNumber, line in enumerate(f):
            # The middle of the tuple is just whitespace
            (command, _, data) = line.partition(' ')
            if len(data) > 0:
                data = data[:-1]
                while len(data) > 0 and data[0] == ' ':
                    data = data[1:]
                if len(data) > 0:
                    # After stripping away excess whitespace
                    address_string = "(%d) %s%s" % (lineNumber, prefix, command)
                    if command in chunks_with_data:
                        LOG.debug(address_string)
                        # Parse data depending on its type
                        chunks_with_data[command](self, data)
                    else:
                        LOG.warning(address_string + " *unsupported*")

    def unpack_vertices(self):
        """Unpack the vertices."""
        # Consecutive list of nodes making up faces (specifically, triangles)
        indices = []

        num_components = 1
        if 0 < len(self.uvs[0]):
            num_components += 1
        if 0 < len(self.normals):
            num_components += 1

        # A node of a face definition consists of a vertex index, and optional
        # texture coord index and an optional normal vector index
        # Thus, the length of an element of self.indices can be 1, 2 or 3.
        if num_components == 1:
            # No texture coordinates (uv) or normal vector specified.
            indices = [x[0] for x in self.indices]
        else:
            old_positions = self.positions
            old_uvs = self.uvs[0]
            old_normals = self.normals
            positions = []  # Vertex position
            uvs = []        # Texture coordinate
            normals = []
            mapping = {}
            if num_components == 2:
                for indx in self.indices:
                    i0 = indx[0]
                    if len(indx) >= 2:
                        i1 = indx[1]
                    else:
                        i1 = 0
                    hash_string = "%x:%x" % (i0, i1)
                    if hash_string in mapping:
                        indices.append(mapping[hash_string])
                    else:
                        newindx = len(positions)
                        mapping[hash_string] = newindx
                        indices.append(newindx)
                        positions.append(old_positions[i0])
                        # Figure out whether 2nd value is uv or normal
                        if len(old_uvs) != 0:
                            uvs.append(old_uvs[i1])
                        else:
                            normals.append(old_normals[i1])
            else:
                for indx in self.indices:
                    i0 = indx[0]
                    if len(indx) >= 2:
                        i1 = indx[1]
                    else:
                        i1 = 0
                    if len(indx) >= 3:
                        i2 = indx[2]
                    else:
                        i2 = 0
                    hash_string = "%x:%x:%x" % (i0, i1, i2)
                    if hash_string in mapping:
                        indices.append(mapping[hash_string])
                    else:
                        newindx = len(positions)
                        mapping[hash_string] = newindx
                        indices.append(newindx)
                        positions.append(old_positions[i0])
                        uvs.append(old_uvs[i1])
                        normals.append(old_normals[i2])
            # Reassign the vertex positions, texture coordinates and normals, so
            # that they coincide with the indices defining the triangles.
            self.positions = positions
            self.uvs[0] = uvs
            self.normals = normals
        self.generate_primitives(indices)

    def extract_nbt_options(self, definitions_asset):
        """Returns whether normals and tangents/binormals are needed, and whether they should be generated.

            Loops over each material and checks their meta attributes to extract this information."""
        # Record the whether normals/tangents need to be generated, and which shapes require these options
        generate_normals  = False
        generate_tangents = False
        need_normals      = set()
        need_tangents     = set()
        for shape_name in self.shapes.iterkeys():
            for surface_name in self.shapes[shape_name].surfaces.iterkeys():
                material_name = self.shapes[shape_name].surfaces[surface_name].material_name
                material = definitions_asset.retrieve_material(material_name, default = True)
                effect = definitions_asset.retrieve_effect(material['effect'])

                # Rules used: Generating tangents implies needing tangents
                #             Needing tangents implies needing normals
                #             Needing tangents/normals implies generating them if they aren't present
                if material.meta('generate_tangents') or effect is not None and effect.meta('generate_tangents'):
                    generate_tangents = True
                    need_tangents.add(shape_name)
                elif material.meta('tangents') or effect is not None and effect.meta('tangents'):
                    need_tangents.add(shape_name)
                    # Generate tangents if any material needs tangents and you haven't parsed any,
                    # or if any materials ask you to generate tangents
                    generate_tangents = generate_tangents or not len(self.tangents) or not len(self.binormals)
                if material.meta('generate_normals') or effect is not None and effect.meta('generate_normals'):
                    generate_normals = True
                    need_normals.add(shape_name)
                elif material.meta('normals') or effect is not None and effect.meta('normals'):
                    need_normals.add(shape_name)
                    # Same reasoning as with generating tangents
                    generate_normals = generate_normals or not len(self.normals)
        if generate_tangents and 0 == len(self.uvs[0]):
            LOG.debug("Can't generate nbts without uvs:%i", len(self.uvs[0]))
            generate_tangents = False
            need_tangents     = set()
        return (need_normals, generate_normals, need_tangents, generate_tangents)
# pylint: enable=R0904

#######################################################################################################################

def parse(input_filename="default.obj", output_filename="default.json", asset_url="", asset_root=".",
          infiles=None, options=None):
    """Utility function to convert an OBJ file into a JSON file."""
    definitions_asset = standard_include(infiles)
    with open(input_filename, 'r') as source:
        asset = Obj2json(basename(input_filename))
        asset.parse(source)
        # Remove any and all unused (e.g. default) shapes and surfaces
        purge_empty(asset.shapes, recurseOnce = True)
        # Generate primitives
        asset.unpack_vertices()
        # Remove any degenerate primitives unless they're requested to be kept
        keep_degenerates = True
        for shape in asset.shapes:
            for _, surface in asset.shapes[shape].surfaces.iteritems():
                material = definitions_asset.retrieve_material(surface.material_name)
                if material.meta('keep_degenerates'):
                    keep_degenerates = True
        if not keep_degenerates:
            asset.remove_degenerate_primitives()
        # Remove any unused vertices and calculate a bounding box
        asset.remove_redundant_vertexes()
        asset.generate_bbox()
        # Generate normals/tangents if required
        (need_normals, generate_normals,
         need_tangents, generate_tangents) = asset.extract_nbt_options(definitions_asset)
        if generate_tangents:
            if generate_normals:
                asset.generate_normals()
            asset.generate_smooth_nbts()
            asset.invert_v_texture_map()
        elif generate_normals:
            asset.generate_normals()
            asset.smooth_normals()
        json_asset = JsonAsset()
        for shape_name in asset.shapes.iterkeys():
            json_asset.attach_shape(shape_name)
            node_name = NodeName("node-%s" % shape_name)
            json_asset.attach_node(node_name)
            #TODO: Should the following be divided into separate shapes?
            json_asset.attach_positions(asset.positions, shape_name)
            # Attach texture map, normals and tangents/binormals if required
            if len(asset.uvs[0]) != 0:
                json_asset.attach_uvs(asset.uvs[0], shape_name)
            if shape_name in need_tangents:
                if len(asset.tangents):
                    # Needing tangents implies needing normals and binormals
                    json_asset.attach_nbts(asset.normals, asset.tangents, asset.binormals, shape_name)
                else:
                    LOG.error('tangents requested for shape %s, but no tangents or uvs available!', shape_name)
            elif shape_name in need_normals:
                json_asset.attach_normals(asset.normals, shape_name)
            for surface_name, surface in asset.shapes[shape_name].surfaces.iteritems():
                material = definitions_asset.retrieve_material(surface.material_name)
                effect = material.get('effect', DEFAULT_EFFECT_NAME)
                effect_name = "effect-%s" % shape_name
                material_name = "material-%s" % surface.material_name
                instance_name = "instance-%s-%s" % (shape_name, surface_name)
                json_asset.attach_effect(effect_name, effect)
                mat_params = material.get('parameters', None)
                json_asset.attach_material(material_name, effect=effect, parameters=mat_params)
                def textures(mat_params):
                    for k, v in mat_params.iteritems():
                        # If a paramater of a material has a string value, it is assumed to be a texture definition
                        if isinstance(v, basestring):
                            # Return the type of the texture (e.g. 'diffuse')
                            yield k
                for t_type in textures(mat_params):
                    json_asset.attach_texture(material_name, t_type, mat_params[t_type])
                first = surface.first
                last = first + surface.count
                json_asset.attach_surface(asset.primitives[first:last], JsonAsset.SurfaceTriangles,
                                          shape_name, name=surface_name)
                json_asset.attach_node_shape_instance(node_name, instance_name, shape_name,
                                                      material_name, surface=surface_name)
        json_asset.attach_bbox(asset.bbox)
        standard_json_out(json_asset, output_filename, options)
        return json_asset

if __name__ == "__main__":
    standard_main(parse, __version__,
                  "Convert LightWave (.obj) OBJ2 files into a Turbulenz JSON asset. Supports generating NBTs.",
                  __dependencies__)

########NEW FILE########
__FILENAME__ = pointmap
# Copyright (c) 2009-2011,2013 Turbulenz Limited
"""
Point map structure similar to a kd-tree but with points on each internal node which allows for fast neighbours lookup.
It takes (N*log N) to build and (N*log N) to query.
"""

# pylint: disable=W0403
import vmath
# pylint: enable=W0403

__version__ = '1.0.0'
__dependencies__ = ['vmath']

#######################################################################################################################

class Node(object):
    """kd-tree node."""

    def __init__(self, vertex_index, split_axis):
        self.vertex_index = vertex_index
        self.split_axis = split_axis
        self.left_child = None
        self.right_child = None

    def points_within_uv_distance(self, positions, position, position_tolerance, uvs, uv, uv_tolerance):
        """Build a list of indexes which are within distance of the point and vertex."""

        def __points_within_distance(node, results):
            """Build a list of indexes which are within distance of the point and vertex."""
            if not node:
                return

            vertex_index = node.vertex_index
            this_position = positions[vertex_index]
            this_uv = uvs[vertex_index]

            if vmath.v3equal(this_position, position, position_tolerance) and vmath.v2equal(this_uv, uv, uv_tolerance):
                results.append(vertex_index)

            split_axis = node.split_axis
            v_axis = this_position[split_axis]
            p_axis = position[split_axis]

            if (p_axis + position_tolerance) < v_axis:
                __points_within_distance(node.left_child, results)
            elif (p_axis - position_tolerance) > v_axis:
                __points_within_distance(node.right_child, results)
            else:
                __points_within_distance(node.left_child, results)
                __points_within_distance(node.right_child, results)

        results = [ ]
        __points_within_distance(self, results)
        return results

    def points_within_distance(self, vertexes, point, distance):
        """Build a list of indexes which are within distance of the point and vertex."""

        def __points_within_distance(node, results):
            """Build a list of indexes which are within distance of the point and vertex."""
            if not node:
                return

            vertex_index = node.vertex_index
            vertex = vertexes[vertex_index]

            if vmath.v3equal(point, vertex, distance):
                results.append(vertex_index)

            split_axis = node.split_axis
            v_axis = vertex[split_axis]
            p_axis = point[split_axis]

            if (p_axis + distance) < v_axis:
                __points_within_distance(node.left_child, results)
            elif (p_axis - distance) > v_axis:
                __points_within_distance(node.right_child, results)
            else:
                __points_within_distance(node.left_child, results)
                __points_within_distance(node.right_child, results)

        results = [ ]
        __points_within_distance(self, results)
        return results

def build_kdtree(vertexes):
    """Build a kd-tree for the vertexes and indexes."""
    return build_kdtree_nodes(vertexes, range(len(vertexes)))

def build_kdtree_nodes(vertexes, indexes, depth=0):
    """Build a kd-tree for the vertexes and indexes."""
    if not indexes:
        return

    # Select axis based on depth so that axis cycles through all valid values
    split_axis = depth % 3

    # Sort point list and choose median as pivot element
    indexes.sort(key=lambda v: vertexes[v][split_axis])
    median = len(indexes) / 2 # choose median

    # Create node and construct subtrees
    node = Node(indexes[median], split_axis)
    node.left_child = build_kdtree_nodes(vertexes, indexes[0:median], depth + 1)
    node.right_child = build_kdtree_nodes(vertexes, indexes[median+1:], depth + 1)

    return node

#######################################################################################################################

if __name__ == "__main__":
    import random
    NUM = 1000
    VERTEXES = [ (random.random(), random.random(), random.random()) for x in range(NUM) ]
    ROOT = build_kdtree(VERTEXES)
    POINT = (0.25, 0.5, 0.75)
    DISTANCE = 0.1
    RESULTS = ROOT.points_within_distance(VERTEXES, POINT, DISTANCE)
    RESULTS.sort()
    for r in RESULTS:
        print "Result: %i %s is close to %s." % (r, VERTEXES[r], POINT)
    print "=" * 80
    for i, x in enumerate(VERTEXES):
        if vmath.v3equal(x, POINT, DISTANCE):
            print "Result: %i %s is close to %s." % (i, x, POINT)

########NEW FILE########
__FILENAME__ = stdtool
# Copyright (c) 2009-2013 Turbulenz Limited
"""
Utilities to simplify building a standard translater.
"""

import sys
import logging
LOG = logging.getLogger('asset')

from os.path import basename as path_basename, exists as path_exists
from simplejson import load as json_load
from optparse import OptionParser, OptionGroup, TitledHelpFormatter

# pylint: disable=W0403
from asset2json import JsonAsset
from turbulenz_tools.utils.json_utils import merge_dictionaries
# pylint: enable=W0403

#######################################################################################################################


#######################################################################################################################

def standard_output_version(version, dependencies, output_file=None):
    main_module_name = path_basename(sys.argv[0])
    version_string = None
    if dependencies:
        deps = { }

        def get_dependencies_set(this_module_name, deps_list):
            for module_name in deps_list:
                if module_name not in deps:
                    m = None
                    try:
                        m = __import__(module_name, globals(), locals(),
                                       ['__version__', '__dependencies__'])
                    except ImportError:
                        print "Failed to import %s, listed in dependencies " \
                            "for %s" % (module_name, this_module_name)
                        exit(1)
                    else:
                        # Test is the module actually has a version attribute
                        try:
                            version_ = m.__version__
                        except AttributeError as e:
                            print 'No __version__ attribute for tool %s' \
                                % m.__name__
                            print ' >> %s' % str(e)
                        else:
                            deps[module_name] = m

                    if m is not None:
                        try:
                            get_dependencies_set(module_name,
                                                 m.__dependencies__)
                        except AttributeError:
                            pass

        get_dependencies_set(main_module_name, dependencies)

        module_names = deps.keys()
        module_names.sort()

        module_list = ', '.join(['%s %s' % (deps[m].__name__, deps[m].__version__) for m in module_names])
        version_string = '%s %s (%s)' % (main_module_name, version, module_list)
    else:
        version_string = '%s %s' % (main_module_name, version)

    # If we are given an output file, write the versions info there if
    # either:
    #   the file doesn't exist already, or
    #   the file contains different data
    # If we are given no output file, just write to stdout.

    print version_string
    if output_file is not None:
        if path_exists(output_file):
            with open(output_file, "rb") as f:
                old_version = f.read()
            if old_version == version_string:
                return
        with open(output_file, "wb") as f:
            f.write(version_string)

def standard_include(infiles):
    """Load and merge all the ``infiles``."""
    if infiles:
        definitions = { }
        for infile in infiles:
            if path_exists(infile):
                with open(infile, 'r') as infile_file:
                    infile_json = json_load(infile_file)
                    definitions = merge_dictionaries(infile_json, definitions)
            else:
                LOG.error('Missing file: %s', infile)
        return JsonAsset(definitions=definitions)
    else:
        return JsonAsset()
    return None

def standard_parser(description, epilog=None, per_file_options=True):
    """Standard set of parser options."""
    parser = OptionParser(description=description, epilog=epilog,
                          formatter=TitledHelpFormatter())
    parser.add_option("--version", action="store_true", dest="output_version",
                      default=False, help="output version number to output "
                      "file, or stdout if no output file is given")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      default=False, help="verbose outout")
    parser.add_option("-s", "--silent", action="store_true", dest="silent",
                      default=False, help="silent running")
    if per_file_options:
        parser.add_option("-m", "--metrics", action="store_true",
                          dest="metrics", default=False, help="output asset "
                          "metrics")
    parser.add_option("--log", action="store", dest="output_log", default=None,
                      help="write log to file")

    group = OptionGroup(parser, "Asset Generation Options")
    group.add_option("-j", "--json_indent", action="store", dest="json_indent",
                     type="int", default=0, metavar="SIZE",
                     help="json output pretty printing indent size, defaults "
                     "to 0")

    # TODO - Asset Generation Options currently disabled
    #
    #group.add_option("-6", "--base64-encoding", action="store_true", dest="b64_encoding", default=False,
    #                 help=("encode long float and int attributes in base64, defaults to disabled %s" %
    #                        "- [ currently unsupported ]"))
    #group.add_option("-c", "--force-collision", action="store_true", dest="force_collision", default=False,
    #                 help="force collision generation - [ currently unsupported ]")
    #group.add_option("-r", "--force-render", action="store_true", dest="force_render", default=False,
    #                 help="force rendering generation - [ currently unsupported ]")

    group.add_option("--keep-unused-images", action="store_true", dest="keep_unused_images", default=False,
                     help="keep images with no references to them")

    group.add_option("-I", "--include-type", action="append", dest="include_types", default=None, metavar="TYPE",
                     help="only include objects of class TYPE in export.")
    group.add_option("-E", "--exclude-type", action="append", dest="exclude_types", default=None, metavar="TYPE",
                     help="exclude objects of class TYPE from export. "
                          "Classes currently supported for include and exclude: "
                          "geometries, nodes, animations, images, effects, materials, lights, "
                          "physicsmaterials, physicsmodels and physicsnodes. "
                          "CAUTION using these options can create incomplete assets which require fixup at runtime. ")
    parser.add_option_group(group)

    group = OptionGroup(parser, "Asset Location Options")
    group.add_option("-u", "--url", action="store", dest="asset_url", default="", metavar="URL",
                     help="asset URL to prefix to all asset references")
    group.add_option("-a", "--assets", action="store", dest="asset_root", default=".", metavar="PATH",
                     help="PATH of the asset root")
    group.add_option("-d", "--definitions", action="append", dest="definitions", default=None, metavar="JSON_FILE",
                     help="definition JSON_FILE to include in build, this option can be used repeatedly for multiple "
                          "files")
    parser.add_option_group(group)

    if per_file_options:
        group = OptionGroup(parser, "File Options")
        group.add_option("-i", "--input", action="store", dest="input", default=None, metavar="FILE",
                         help="source FILE to process")
        group.add_option("-o", "--output", action="store", dest="output", default="default.json", metavar="FILE",
                         help="output FILE to write to")
        parser.add_option_group(group)

    # TODO - Database Options are currently disabled
    #
    #group = OptionGroup(parser, "Database Options")
    #group.add_option("-A", "--authority", action="store", dest="authority", default=None,
    #                 metavar="HOST:PORT",
    #                 help=("Authority of the database in the form HOST:PORT. %s" %s
    #                       "If undefined, database export is disabled."))
    #group.add_option("-D", "--database", action="store", dest="database", default="default",
    #                 metavar="NAME", help="NAME of the document database")
    #group.add_option("-P", "--put-post", action="store_true", dest="put_post", default=False,
    #                 help="put or post the asset to the authority database")
    #group.add_option("-O", "--document", action="store", dest="document", default="default.asset",
    #                 metavar="NAME", help="NAME of the document")
    #parser.add_option_group(group)

    return parser

def standard_main(parse, version, description, dependencies, parser = None):
    """Provide a consistent wrapper for standalone translation.
       When parser is not supplied, standard_parser(description) is used."""

    parser = parser or standard_parser(description)
    (options, args_) = parser.parse_args()

    if options.output_version:
        standard_output_version(version, dependencies, options.output)
        return

    if options.input is None:
        parser.print_help()
        return

    if options.silent:
        logging.basicConfig(level=logging.CRITICAL, stream=sys.stdout)
    elif options.verbose or options.metrics:
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    else:
        logging.basicConfig(level=logging.WARNING, stream=sys.stdout)

    LOG.info("input: %s", options.input)
    LOG.info("output: %s", options.output)

    if options.asset_url != '':
        LOG.info("url: %s", options.asset_url)

    if options.asset_root != '.':
        LOG.info("root: %s", options.asset_root)

    if options.definitions:
        for inc in options.definitions:
            LOG.info("inc: %s", inc)

    # TODO - Database Options are currently disabled
    #
    #if options.put_post:
    #    LOG.info("## authority: %s" % (options.authority))

    json_asset_ = parse(options.input, options.output,
                        options.asset_url, options.asset_root, options.definitions,
                        options)

    # TODO - Database Options are currently disabled
    #
    #if options.put_post:
    #    try:
    #        from couchdbkit import Server
    #        from couchdbkit.resource import PreconditionFailed
    #        database_supported = True
    #    except ImportError:
    #        database_supported = False
    #
    #    if database_supported and json_asset and options.put_post:
    #        server_uri = 'http://' + options.authority + '/'
    #        server = Server(uri=server_uri)
    #        try:
    #            database = server.get_or_create_db(options.database)
    #        except PreconditionFailed:
    #            database = server[options.database]
    #        if database.doc_exist(options.document):
    #            pass
    #        else:
    #            database[options.document] = json_asset.asset

def standard_json_out(json_asset, output_filename, options=None):
    """Provide a consistent output of the JSON assets."""

    indent = 0
    if options is not None:
        indent = options.json_indent

    metrics = False
    if options is not None:
        metrics = options.metrics

    json_asset.clean()
    if metrics:
        json_asset.log_metrics()

    with open(output_filename, 'w') as target:
        json_asset.json_to_file(target, True, indent)
        target.write('\n')

#######################################################################################################################

def simple_options(parser_fn, version, dependencies, input_required=True):
    parser = parser_fn()
    (options, args) = parser.parse_args()

    if options.output_version:
        standard_output_version(version, dependencies, getattr(options, 'output', None))
        exit(0)

    if input_required:
        # Not all tools have an input file, so we print help for no args as well.
        try:
            if options.input is None:
                print "ERROR: no input files specified"
                parser.print_help()
                exit(1)
        except AttributeError:
            if len(args) == 0:
                print "ERROR: no input files specified"
                parser.print_help()
                exit(1)

    # Not all tools have a metrics option.
    try:
        metrics = options.metrics
    except AttributeError:
        metrics = False

    if options.silent:
        logging.basicConfig(level=logging.CRITICAL)
    elif options.verbose or metrics:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    return (options, args, parser)

########NEW FILE########
__FILENAME__ = templates
# Copyright (c) 2012-2013 Turbulenz Limited

from jinja2 import Environment, FileSystemLoader, ChoiceLoader
from jinja2 import TemplateNotFound, TemplateSyntaxError, BaseLoader
from logging import getLogger

from turbulenz_tools.tools.toolsexception import ToolsException

import os
import re

LOG = getLogger(__name__)
LF_RE = re.compile(r".?\r.?", re.DOTALL)

############################################################

class DefaultTemplateLoader(BaseLoader):
    """
    Class that loads a named template from memory
    """

    def __init__(self, name, template):
        BaseLoader.__init__(self)
        self.name = name
        self.template = template

    def get_source(self, env, template):
        if template == self.name:
            LOG.info("Request for template '%s'.  Using default registered", template)
            return self.template, None, lambda: True
        raise TemplateNotFound(template)

class UTF8FileSystemLoader(FileSystemLoader):
    """
    Class that loads a template from a given path, removing any utf8
    BOMs.
    """

    def __init__(self, searchpath):
        FileSystemLoader.__init__(self, searchpath)
        self._path = searchpath

    def get_source(self, env, name):
        fn = os.path.join(self._path, name)
        if not os.path.exists(fn):
            raise TemplateNotFound(name)

        d = read_file_utf8(fn)
        return d, None, lambda: True

############################################################

def _sanitize_crlf(m):
    v = m.group(0)
    if 3 == len(v):
        if '\n' == v[0]:
            return '\n' + v[2]
        if '\n' == v[2]:
            return v[0] + '\n'
    elif 2 == len(v):
        if '\n' in v:
            return '\n'
    return v.replace('\r', '\n')

# Read a file, handling any utf8 BOM
def read_file_utf8(filename):
    with open(filename, 'rb') as f:
        text = f.read().decode('utf-8-sig')

        # This is unpleasant, but it is thorough.  This is the
        # single-pass equivalent of:
        # return (in_data.replace('\r\n', '\n').replace('\n\r', '\n'))\
        #     .replace('\r', '\n');
        return LF_RE.sub(_sanitize_crlf, text)

############################################################

def env_create(options, default_template=None):
    """
    Setup a jinja env based on the tool options
    """

    LOG.info("Template dirs:")
    for t in options.templatedirs:
        LOG.info(" - '%s'", t)

    loaders = [ UTF8FileSystemLoader(t) for t in options.templatedirs ]
    if default_template is not None:
        loaders.append(DefaultTemplateLoader('default', default_template))

    _loader = ChoiceLoader(loaders)
    env = Environment(loader = _loader,
                      block_start_string = '/*{%',
                      block_end_string = '%}*/',
                      variable_start_string = '/*{{',
                      variable_end_string = '}}*/',
                      comment_start_string = '/*{#',
                      comment_end_string = '#}*/')
    return env

############################################################

def env_load_template(env, in_file):
    """
    Load a single template into the environment, handling the
    appropriate errors.  Returns the loaded template
    """

    try:
        return env.get_template(in_file)
    except TemplateNotFound as e:
        raise ToolsException('template not found: %s' % str(e))
    except TemplateSyntaxError as e:
        raise ToolsException('template syntax error: %s' % str(e))

############################################################

def env_load_templates(env, inputs):
    """
    Load an array of templates into the environment.  Returns the
    loaded templates as a list
    """

    return [env_load_template(env, i) for i in inputs]

########NEW FILE########
__FILENAME__ = toolsexception
# Copyright (c) 2012-2013 Turbulenz Limited

# For utils to use to send error messages
class ToolsException(Exception):
    pass


########NEW FILE########
__FILENAME__ = vmath
#!/usr/bin/python
# Copyright (c) 2009-2013 Turbulenz Limited
"""
Collection of math functions.
"""

import math

__version__ = '1.0.0'

# pylint: disable=C0302,C0111,R0914,R0913
# C0111 - Missing docstring
# C0302 - Too many lines in module
# R0914 - Too many local variables
# R0913 - Too many arguments

#######################################################################################################################

PRECISION = 1e-6

def tidy(m, tolerance=PRECISION):
    def __tidy(x, tolerance):
        if abs(x) < tolerance:
            return 0
        return x
    return tuple([__tidy(x, tolerance) for x in m])

#######################################################################################################################

def select(m, a, b):
    if m:
        return a
    return b

def rcp(a):
    if (a != 0.0):
        return 1 / a
    return 0.0

def iszero(a, tolerance=PRECISION):
    return (abs(a) < tolerance)


#######################################################################################################################

def v2equal(a, b, tolerance=PRECISION):
    (a0, a1) = a
    (b0, b1) = b
    return (abs(a0 - b0) <= tolerance and abs(a1 - b1) <= tolerance)

#######################################################################################################################

V3ZERO = (0.0, 0.0, 0.0)
V3HALF = (0.5, 0.5, 0.5)
V3ONE = (1.0, 1.0, 1.0)
V3TWO = (2.0, 2.0, 2.0)

V3XAXIS = (1.0, 0.0, 0.0)
V3YAXIS = (0.0, 1.0, 0.0)
V3ZAXIS = (0.0, 0.0, 1.0)

#######################################################################################################################

def v3create(a, b, c):
    return (a, b, c)

def v3neg(a):
    (a0, a1, a2) = a
    return (-a0, -a1, -a2)

def v3add(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((a0 + b0), (a1 + b1), (a2 + b2))

def v3add3(a, b, c):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    (c0, c1, c2) = c
    return ((a0 + b0 + c0), (a1 + b1 + c1), (a2 + b2 + c2))

def v3add4(a, b, c, d):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    (c0, c1, c2) = c
    (d0, d1, d2) = d
    return ((a0 + b0 + c0 + d0), (a1 + b1 + c1 + d1), (a2 + b2 + c2 + d2))

def v3sub(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((a0 - b0), (a1 - b1), (a2 - b2))

def v3mul(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((a0 * b0), (a1 * b1), (a2 * b2))

def v3madd(a, b, c):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    (c0, c1, c2) = c
    return (((a0 * b0) + c0), ((a1 * b1) + c1), ((a2 * b2) + c2))

def v3dot(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((a0 * b0) + (a1 * b1) + (a2 * b2))

def v3cross(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((a1 * b2) - (a2 * b1), (a2 * b0) - (a0 * b2), (a0 * b1) - (a1 * b0))

def v3lengthsq(a):
    (a0, a1, a2) = a
    return ((a0 * a0) + (a1 * a1) + (a2 * a2))

def v3length(a):
    (a0, a1, a2) = a
    return math.sqrt((a0 * a0) + (a1 * a1) + (a2 * a2))

def v3distancesq(a, b):
    return v3lengthsq(v3sub(a, b))

def v3recp(a):
    (a0, a1, a2) = a
    return (rcp(a0), rcp(a1), rcp(a2))

def v3normalize(a):
    (a0, a1, a2) = a
    lsq = ((a0 * a0) + (a1 * a1) + (a2 * a2))
    if (lsq > 0.0):
        lr = 1.0 / math.sqrt(lsq)
        return ((a0 * lr), (a1 * lr), (a2 * lr))
    return V3ZERO

def v3abs(a):
    (a0, a1, a2) = a
    return (abs(a0), abs(a1), abs(a2))

def v3max(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return (max(a0, b0), max(a1, b1), max(a2, b2))

def v3max3(a, b, c):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    (c0, c1, c2) = c
    return (max(max(a0, b0), c0), max(max(a1, b1), c1), max(max(a2, b2), c2))

def v3max4(a, b, c, d):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    (c0, c1, c2) = c
    (d0, d1, d2) = d
    return (max(max(a0, b0), max(c0, d0)),
            max(max(a1, b1), max(c1, d1)),
            max(max(a2, b2), max(c2, d2)))

def v3min(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return (min(a0, b0), min(a1, b1), min(a2, b2))

def v3min3(a, b, c):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    (c0, c1, c2) = c
    return (min(min(a0, b0), c0), min(min(a1, b1), c1), min(min(a2, b2), c2))

def v3min4(a, b, c, d):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    (c0, c1, c2) = c
    (d0, d1, d2) = d
    return (min(min(a0, b0), min(c0, d0)),
            min(min(a1, b1), min(c1, d1)),
            min(min(a2, b2), min(c2, d2)))

def v3equal(a, b, tolerance=PRECISION):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return (abs(a0 - b0) <= tolerance and abs(a1 - b1) <= tolerance and abs(a2 - b2) <= tolerance)

def v3mulm33(a, m):
    (a0, a1, a2) = a
    return v3add3( v3muls(m33right(m), a0),
                   v3muls(m33up(m),    a1),
                   v3muls(m33at(m),    a2) )

def v3mequal(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((abs(a0 - b0) <= PRECISION), (abs(a1 - b1) <= PRECISION), (abs(a2 - b2) <= PRECISION))

def v3mless(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((a0 < b0), (a1 < b1), (a2 < b2))

def v3mgreater(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((a0 > b0), (a1 > b1), (a2 > b2))

def v3mgreatereq(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((a0 >= b0), (a1 >= b1), (a2 >= b2))

def v3mnot(a):
    (a0, a1, a2) = a
    return (not a0, not a1, not a2)

def v3mor(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((a0 or b0), (a1 or b1), (a2 or b2))

def v3mand(a, b):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((a0 and b0), (a1 and b1), (a2 and b2))

def v3select(m, a, b):
    (m0, m1, m2) = m
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return (select(m0, a0, b0), select(m1, a1, b1), select(m2, a2, b2))

def v3creates(a):
    return (a, a, a)

def v3maxs(a, b):
    (a0, a1, a2) = a
    return (max(a0, b), max(a1, b), max(a2, b))

def v3mins(a, b):
    (a0, a1, a2) = a
    return (min(a0, b), min(a1, b), min(a2, b))

def v3adds(a, b):
    (a0, a1, a2) = a
    return ((a0 + b), (a1 + b), (a2 + b))

def v3subs(a, b):
    (a0, a1, a2) = a
    return ((a0 - b), (a1 - b), (a2 - b))

def v3muls(a, b):
    (a0, a1, a2) = a
    if (b == 0):
        return V3ZERO
    return ((a0 * b), (a1 * b), (a2 * b))

def v3equals(a, b):
    (a0, a1, a2) = a
    return (abs(a0 - b) <= PRECISION and abs(a1 - b) <= PRECISION and abs(a2 - b) <= PRECISION)

def v3equalsm(a, b):
    (a0, a1, a2) = a
    return ((abs(a0 - b) <= PRECISION), (abs(a1 - b) <= PRECISION), (abs(a2 - b) <= PRECISION))

def v3lesssm(a, b):
    (a0, a1, a2) = a
    return ((a0 > b), (a1 > b), (a2 > b))

def v3greatersm(a, b):
    (a0, a1, a2) = a
    return ((a0 > b), (a1 > b), (a2 > b))

def v3greatereqsm(a, b):
    (a0, a1, a2) = a
    return ((a0 >= b), (a1 >= b), (a2 >= b))

def v3lerp(a, b, t):
    (a0, a1, a2) = a
    (b0, b1, b2) = b
    return ((a0 + (b0 - a0) * t), (a1 + (b1 - a1) * t), (a2 + (b2 - a2) * t))

def v3is_zero(a, tolerance=PRECISION):
    return (abs(v3lengthsq(a)) < (tolerance * tolerance))

def v3is_similar(a, b, tolerance=PRECISION):
    return (v3dot(a, b) > tolerance)

def v3is_within_tolerance(a, b, tolerance):
    """The tolerance must be defined as the square of the cosine angle tolerated. Returns True is 'a' is zero."""
    if v3is_zero(a): # Should we test b is_zero as well?
        return True
    dot = v3dot(a, b)
    if dot < 0:
        return False
    if (dot * dot) < (v3lengthsq(a) * v3lengthsq(b) * tolerance):
        return False
    return True

def v3unitcube_clamp(a):
    (a0, a1, a2) = a
    if (a0 > 1.0):
        a0 = 1.0
    elif (a0 < -1.0):
        a0 = -1.0
    if (a1 > 1.0):
        a1 = 1.0
    elif (a1 < -1.0):
        a1 = -1.0
    if (a2 > 1.0):
        a2 = 1.0
    elif (a2 < -1.0):
        a2 = -.10
    return (a0, a1, a2)

#######################################################################################################################

def v3s_min_max(points):
    (min_x, min_y, min_z) = points[0]
    (max_x, max_y, max_z) = points[0]
    for (x, y, z) in points:
        min_x = min(x, min_x)
        min_y = min(y, min_y)
        min_z = min(z, min_z)
        max_x = max(x, max_x)
        max_y = max(y, max_y)
        max_z = max(z, max_z)
    return ((min_x, min_y, min_z), (max_x, max_y, max_z))

#######################################################################################################################

V4ZERO = (0.0, 0.0, 0.0, 0.0)
V4HALF = (0.5, 0.5, 0.5, 0.5)
V4ONE  = (1.0, 1.0, 1.0, 1.0)
V4TWO  = (2.0, 2.0, 2.0, 2.0)

#######################################################################################################################

def v4create(a, b, c, d):
    return (a, b, c, d)

def v4neg(a):
    (a0, a1, a2, a3) = a
    return (-a0, -a1, -a2, -a3)

def v4add(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return ((a0 + b0), (a1 + b1), (a2 + b2), (a3 + b3))

def v4add3(a, b, c):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    (c0, c1, c2, c3) = c
    return ((a0 + b0 + c0), (a1 + b1 + c1), (a2 + b2 + c2), (a3 + b3 + c3))

def v4add4(a, b, c, d):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    (c0, c1, c2, c3) = c
    (d0, d1, d2, d3) = d
    return ((a0 + b0 + c0 + d0), (a1 + b1 + c1 + d1), (a2 + b2 + c2 + d2), (a3 + b3 + c3 + d3))

def v4sub(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return ((a0 - b0), (a1 - b1), (a2 - b2), (a3 - b3))

def v4mul(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return ((a0 * b0), (a1 * b1), (a2 * b2), (a3 * b3))

def v4madd(a, b, c):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    (c0, c1, c2, c3) = c
    return (((a0 * b0) + c0), ((a1 * b1) + c1), ((a2 * b2) + c2), ((a3 * b3) + c3))

def v4dot(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return ((a0 * b0) + (a1 * b1) + (a2 * b2) + (a3 * b3))

def v4lengthsq(a):
    (a0, a1, a2, a3) = a
    return ((a0 * a0) + (a1 * a1) + (a2 * a2) + (a3 * a3))

def v4length(a):
    (a0, a1, a2, a3) = a
    return math.sqrt((a0 * a0) + (a1 * a1) + (a2 * a2) + (a3 * a3))

def v4recp(a):
    (a0, a1, a2, a3) = a
    return (rcp(a0), rcp(a1), rcp(a2), rcp(a3))

def v4normalize(a):
    (a0, a1, a2, a3) = a
    lsq = ((a0 * a0) + (a1 * a1) + (a2 * a2) + (a3 * a3))
    if (lsq > 0.0):
        lr = 1.0 / math.sqrt(lsq)
        return ((a0 * lr), (a1 * lr), (a2 * lr), (a3 * lr))
    return V4ZERO

def v4abs(a):
    (a0, a1, a2, a3) = a
    return (abs(a0), abs(a1), abs(a2), abs(a3))

def v4max(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return (max(a0, b0), max(a1, b1), max(a2, b2), max(a3, b3))

def v4max3(a, b, c):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    (c0, c1, c2, c3) = c
    return (max(max(a0, b0), c0),
            max(max(a1, b1), c1),
            max(max(a2, b2), c2),
            max(max(a3, b3), c3))

def v4max4(a, b, c, d):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    (c0, c1, c2, c3) = c
    (d0, d1, d2, d3) = d
    return (max(max(a0, b0), max(c0, d0)),
            max(max(a1, b1), max(c1, d1)),
            max(max(a2, b2), max(c2, d2)),
            max(max(a3, b3), max(c3, d3)))

def v4min(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return (min(a0, b0), min(a1, b1), min(a2, b2), min(a3, b3))

def v4min3(a, b, c):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    (c0, c1, c2, c3) = c
    return (min(min(a0, b0), c0),
            min(min(a1, b1), c1),
            min(min(a2, b2), c2),
            min(min(a3, b3), c3))

def v4min4(a, b, c, d):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    (c0, c1, c2, c3) = c
    (d0, d1, d2, d3) = d
    return (min(min(a0, b0), min(c0, d0)),
            min(min(a1, b1), min(c1, d1)),
            min(min(a2, b2), min(c2, d2)),
            min(min(a3, b3), min(c3, d3)))

def v4equal(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return (abs(a0 - b0) <= PRECISION and
            abs(a1 - b1) <= PRECISION and
            abs(a2 - b2) <= PRECISION and
            abs(a3 - b3) <= PRECISION)

def v4mulm44(v, m):
    (v0, v1, v2, v3) = v
    return v4add4(v4muls(m44right(m), v0),
                  v4muls(m44up(m),    v1),
                  v4muls(m44at(m),    v2),
                  v4muls(m44pos(m),   v3))

def v4mequal(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return ((abs(a0 - b0) <= PRECISION),
            (abs(a1 - b1) <= PRECISION),
            (abs(a2 - b2) <= PRECISION),
            (abs(a3 - b3) <= PRECISION))

def v4mless(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return ((a0 < b0), (a1 < b1), (a2 < b2), (a3 < b3))

def v4mgreater(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return ((a0 > b0), (a1 > b1), (a2 > b2), (a3 > b3))

def v4mgreatereq(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return ((a0 >= b0), (a1 >= b1), (a2 >= b2), (a3 >= b3))

def v4mnot(a):
    (a0, a1, a2, a3) = a
    return ( not a0, not a1, not a2, not a3)

def v4mor(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return ((a0 or b0), (a1 or b1), (a2 or b2), (a3 or b3))

def v4mand(a, b):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return ((a0 and b0), (a1 and b1), (a2 and b2), (a3 and b3))

def v4many(m):
    (m0, m1, m2, m3) = m
    return (m0 or m1 or m2 or m3)

def v4mall(m):
    (m0, m1, m2, m3) = m
    return (m0 and m1 and m2 and m3)

def v4select(m, a, b):
    (m0, m1, m2, m3) = m
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return (select(m0, a0, b0), select(m1, a1, b1), select(m2, a2, b2), select(m3, a3, b3))

def v4creates(a):
    return (a, a, a, a)

def v4maxs(a, b):
    (a0, a1, a2, a3) = a
    return (max(a0, b), max(a1, b), max(a2, b), max(a3, b))

def v4mins(a, b):
    (a0, a1, a2, a3) = a
    return (min(a0, b), min(a1, b), min(a2, b), min(a3, b))

def v4adds(a, b):
    (a0, a1, a2, a3) = a
    return ((a0 + b), (a1 + b), (a2 + b), (a3 + b))

def v4subs(a, b):
    (a0, a1, a2, a3) = a
    return ((a0 - b), (a1 - b), (a2 - b), (a3 - b))

def v4muls(a, b):
    if (b == 0):
        return V4ZERO
    else:
        (a0, a1, a2, a3) = a
        return ((a0 * b), (a1 * b), (a2 * b), (a3 * b))

def v4equals(a, b):
    (a0, a1, a2, a3) = a
    return (abs(a0 - b) <= PRECISION and
            abs(a1 - b) <= PRECISION and
            abs(a2 - b) <= PRECISION and
            abs(a3 - b) <= PRECISION)

def v4equalsm(a, b):
    (a0, a1, a2, a3) = a
    return ((abs(a0 - b) <= PRECISION),
            (abs(a1 - b) <= PRECISION),
            (abs(a2 - b) <= PRECISION),
            (abs(a3 - b) <= PRECISION))

def v4lesssm(a, b):
    (a0, a1, a2, a3) = a
    return ((a0 < b), (a1 < b), (a2 < b), (a3 < b))

def v4greatersm(a, b):
    (a0, a1, a2, a3) = a
    return ((a0 > b), (a1 > b), (a2 > b), (a3 > b))

def v4greatereqsm(a, b):
    (a0, a1, a2, a3) = a
    return ((a0 >= b), (a1 >= b), (a2 >= b), (a3 >= b))

def v4lerp(a, b, t):
    (a0, a1, a2, a3) = a
    (b0, b1, b2, b3) = b
    return ((a0 + (b0 - a0) * t), (a1 + (b1 - a1) * t), (a2 + (b2 - a2) * t), (a3 + (b3 - a3) * t))

#######################################################################################################################

M33IDENTITY = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
M43IDENTITY = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)
M44IDENTITY = (1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0)

#######################################################################################################################

def m33(r0, r1, r2, u0, u1, u2, a0, a1, a2):
    return (r0, r1, r2, u0, u1, u2, a0, a1, a2)

def m33create(r, u, a):
    (r0, r1, r2) = r
    (u0, u1, u2) = u
    (a0, a1, a2) = a
    return (r0, r1, r2, u0, u1, u2, a0, a1, a2)

def m33is_identity(m):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8) = m
    return (m0 == 1 and m1 == 0 and m2 == 0 and
            m3 == 0 and m4 == 1 and m5 == 0 and
            m6 == 0 and m7 == 0 and m8 == 1)

def m33from_axis_rotation(axis, angle):
    s = math.sin(angle)
    c = math.cos(angle)
    t = 1.0 - c
    (axisX, axisY, axisZ) = axis
    tx = t * axisX
    ty = t * axisY
    tz = t * axisZ
    sx = s * axisX
    sy = s * axisY
    sz = s * axisZ

    return (tx * axisX + c, tx * axisY + sz, tx * axisZ - sy,
            ty * axisX - sz, ty * axisY + c, ty * axisZ + sx,
            tz * axisX + sy, tz * axisY - sx, tz * axisZ + c)

def m33right(m):
    return m[:3]

def m33up(m):
    return m[3:6]

def m33at(m):
    return m[6:]

def m33setright(m, v):
    (_, _, _, m3, m4, m5, m6, m7, m8) = m
    (v0, v1, v2) = v
    return (v0, v1, v2, m3, m4, m5, m6, m7, m8)

def m33setup(m, v):
    (m0, m1, m2, _, _, _, m6, m7, m8) = m
    (v0, v1, v2) = v
    return (m0, m1, m2, v0, v1, v2, m6, m7, m8)

def m33setat(m, v):
    (m0, m1, m2, m3, m4, m5, _, _, _) = m
    (v0, v1, v2) = v
    return (m0, m1, m2, m3, m4, m5, v0, v1, v2)

def m33transpose(m):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8) = m
    return (m0, m3, m6, m1, m4, m7, m2, m5, m8)

def m33determinant(m):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8) = m
    return (m0 * (m4 * m8 - m5 * m7) + m1 * (m5 * m6 - m3 * m8) + m2 * (m3 * m7 - m4 * m6))

def m33inverse(m):
    det = m33determinant(m)
    if (det == 0.0):
        return ( )
    else:
        (m0, m1, m2, m3, m4, m5, m6, m7, m8) = m
        detrecp = 1.0 / det
        return (((m4 * m8 + m5 * (-m7)) * detrecp),
                ((m7 * m2 + m8 * (-m1)) * detrecp),
                ((m1 * m5 - m2 *   m4)  * detrecp),
                ((m5 * m6 + m3 * (-m8)) * detrecp),
                ((m8 * m0 + m6 * (-m2)) * detrecp),
                ((m3 * m2 - m0 *   m5)  * detrecp),
                ((m3 * m7 + m4 * (-m6)) * detrecp),
                ((m6 * m1 + m7 * (-m0)) * detrecp),
                ((m0 * m4 - m3 *   m1)  * detrecp))

def m33inversetranspose(m):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8) = m
    det = (m0 * (m4 * m8 - m5 * m7) +
           m1 * (m5 * m6 - m3 * m8) +
           m2 * (m3 * m7 - m4 * m6))
    if (det == 0.0):
        return ( )
    else:
        detrecp = 1.0 / det
        r0 = ((m4 * m8 + m5 * (-m7)) * detrecp)
        r1 = ((m7 * m2 + m8 * (-m1)) * detrecp)
        r2 = ((m1 * m5 - m2 *   m4)  * detrecp)
        r3 = ((m5 * m6 + m3 * (-m8)) * detrecp)
        r4 = ((m8 * m0 + m6 * (-m2)) * detrecp)
        r5 = ((m3 * m2 - m0 *   m5)  * detrecp)
        r6 = ((m3 * m7 + m4 * (-m6)) * detrecp)
        r7 = ((m6 * m1 + m7 * (-m0)) * detrecp)
        r8 = ((m0 * m4 - m3 *   m1)  * detrecp)
        return (r0, r3, r6,
                r1, r4, r7,
                r2, r5, r8)

def m33mul(a, b):
    (a0, a1, a2, a3, a4, a5, a6, a7, a8) = a
    (b0, b1, b2, b3, b4, b5, b6, b7, b8) = b
    return ( (b0 * a0 + b3 * a1 + b6 * a2),
             (b1 * a0 + b4 * a1 + b7 * a2),
             (b2 * a0 + b5 * a1 + b8 * a2),

             (b0 * a3 + b3 * a4 + b6 * a5),
             (b1 * a3 + b4 * a4 + b7 * a5),
             (b2 * a3 + b5 * a4 + b8 * a5),

             (b0 * a6 + b3 * a7 + b6 * a8),
             (b1 * a6 + b4 * a7 + b7 * a8),
             (b2 * a6 + b5 * a7 + b8 * a8) )

def m33mulm43(a, b):
    (a0, a1, a2, a3, a4, a5, a6, a7, a8) = a
    (b0, b1, b2, b3, b4, b5, b6, b7, b8, b9, b10, b11) = b
    return ( (b0 * a0 + b3 * a1 + b6 * a2),
             (b1 * a0 + b4 * a1 + b7 * a2),
             (b2 * a0 + b5 * a1 + b8 * a2),

             (b0 * a3 + b3 * a4 + b6 * a5),
             (b1 * a3 + b4 * a4 + b7 * a5),
             (b2 * a3 + b5 * a4 + b8 * a5),

             (b0 * a6 + b3 * a7 + b6 * a8),
             (b1 * a6 + b4 * a7 + b7 * a8),
             (b2 * a6 + b5 * a7 + b8 * a8),

             b9, b10, b11 )

def m33mulm44(a, b):
    (a0, a1, a2, a3, a4, a5, a6, a7, a8) = a
    (b0, b1, b2, b3, b4, b5, b6, b7, b8, b9, b10, b11, b12, b13, b14, b15) = b
    return ( (b0 * a0 + b4 * a1 + b8  * a2),
             (b1 * a0 + b5 * a1 + b9  * a2),
             (b2 * a0 + b6 * a1 + b10 * a2),
             (b3 * a0 + b7 * a1 + b11 * a2),

             (b0 * a3 + b4 * a4 + b8  * a5),
             (b1 * a3 + b5 * a4 + b9  * a5),
             (b2 * a3 + b6 * a4 + b10 * a5),
             (b3 * a3 + b7 * a4 + b11 * a5),

             (b0 * a6 + b4 * a7 + b8  * a8),
             (b1 * a6 + b5 * a7 + b9  * a8),
             (b2 * a6 + b6 * a7 + b10 * a8),
             (b3 * a6 + b7 * a7 + b11 * a8),

             b12, b13, b14, b15 )

def m33adds(m, s):
    return tuple([ m[n] + s for n in range(9) ])

def m33subs(m, s):
    return tuple([ m[n] - s for n in range(9) ])

def m33muls(m, s):
    return tuple([ m[n] * s for n in range(9) ])

#######################################################################################################################

def m43(r0, r1, r2, u0, u1, u2, a0, a1, a2, p0, p1, p2):
    return (r0, r1, r2, u0, u1, u2, a0, a1, a2, p0, p1, p2)

def m43create(r, u, a, p):
    (r0, r1, r2) = r
    (u0, u1, u2) = u
    (a0, a1, a2) = a
    (p0, p1, p2) = p
    return (r0, r1, r2, u0, u1, u2, a0, a1, a2, p0, p1, p2)

def m43from_m44(m):
    return m43create(m[0:3], m[4:7], m[8:11], m[12:15])

def m43is_identity(m):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11) = m
    return (m0 == 1 and m1 == 0 and m2 == 0 and
            m3 == 0 and m4 == 1 and m5 == 0 and
            m6 == 0 and m7 == 0 and m8 == 1 and
            m9 == 0 and m10 == 0 and m11 == 0)

def m43from_axis_rotation(axis, angle):
    s = math.sin(angle)
    c = math.cos(angle)
    t = 1.0 - c
    (axisX, axisY, axisZ) = axis
    tx = t * axisX
    ty = t * axisY
    tz = t * axisZ
    sx = s * axisX
    sy = s * axisY
    sz = s * axisZ

    return (tx * axisX + c,
            tx * axisY + sz,
            tx * axisZ - sy,
            ty * axisX - sz,
            ty * axisY + c,
            ty * axisZ + sx,
            tz * axisX + sy,
            tz * axisY - sx,
            tz * axisZ + c,
            0.0,
            0.0,
            0.0)

def m43right(m):
    return m[:3]

def m43up(m):
    return m[3:6]

def m43at(m):
    return m[6:9]

def m43pos(m):
    return m[9:]

def m43setright(m, v):
    (_, _, _, m3, m4, m5, m6, m7, m8, m9, m10, m11) = m
    (v0, v1, v2) = v
    return (v0, v1, v2, m3, m4, m5, m6, m7, m8, m9, m10, m11)

def m43setup(m, v):
    (m0, m1, m2, _, _, _, m6, m7, m8, m9, m10, m11) = m
    (v0, v1, v2) = v
    return (m0, m1, m2, v0, v1, v2, m6, m7, m8, m9, m10, m11)

def m43setat(m, v):
    (m0, m1, m2, m3, m4, m5, _, _, _, m9, m10, m11) = m
    (v0, v1, v2) = v
    return (m0, m1, m2, m3, m4, m5, v0, v1, v2, m9, m10, m11)

def m43setpos(m, v):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, _, _, _) = m
    (v0, v1, v2) = v
    return (m0, m1, m2, m3, m4, m5, m6, m7, m8, v0, v1, v2)

def m43translate(m, v):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11) = m
    (v0, v1, v2) = v
    return (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9 + v0, m10 + v1, m11 + v2)

def m43inverse_orthonormal(m):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, px, py, pz) = m
    return ( m0, m3, m6,
             m1, m4, m7,
             m2, m5, m8,
             -((px * m0) + (py * m1) + (pz * m2)),
             -((px * m3) + (py * m4) + (pz * m5)),
             -((px * m6) + (py * m7) + (pz * m8)) )

def m43ortho_normalize(m):
    right = m43right(m)
    up    = m43up(m)
    at    = m43at(m)
    pos   = m43pos(m)

    innerX = v3length(right)
    innerY = v3length(up)
    innerZ = v3length(at)

    right = v3normalize(right)
    up    = v3normalize(up)
    at    = v3normalize(at)

    if (innerX > 0.0):
        if (innerY > 0.0):
            if (innerZ > 0.0):
                outerX = abs(v3dot(up, at))
                outerY = abs(v3dot(at, right))
                outerZ = abs(v3dot(right, up))
                if (outerX < outerY):
                    if (outerX < outerZ):
                        vpU = up
                        vpV = at
                        vpW = right
                    else:
                        vpU = right
                        vpV = up
                        vpW = at
                else:
                    if (outerY < outerZ):
                        vpU = at
                        vpV = right
                        vpW = up
                    else:
                        vpU = right
                        vpV = up
                        vpW = at
            else:
                vpU = right
                vpV = up
                vpW = at
        else:
            vpU = at
            vpV = right
            vpW = up
    else:
        vpU = up
        vpV = at
        vpW = right
    vpW = v3normalize(v3cross(vpV, vpU))
    vpV = v3normalize(v3cross(vpU, vpW))
    return m43create(right, up, at, pos)

def m43determinant(m):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, _m9, _m10, _m11) = m
    return (m0 * (m4 * m8 - m5 * m7) +
            m1 * (m5 * m6 - m3 * m8) +
            m2 * (m3 * m7 - m4 * m6))

def m43inverse(m):
    det = m43determinant(m)
    if (det == 0.0):
        return ( )
    else:
        (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11) = m
        detrecp = 1.0 / det
        return (((m4 * m8 + m5 * (-m7)) * detrecp),
                ((m7 * m2 + m8 * (-m1)) * detrecp),
                ((m1 * m5 - m2 *   m4)  * detrecp),
                ((m5 * m6 + m3 * (-m8)) * detrecp),
                ((m8 * m0 + m6 * (-m2)) * detrecp),
                ((m3 * m2 - m0 *   m5)  * detrecp),
                ((m3 * m7 + m4 * (-m6)) * detrecp),
                ((m6 * m1 + m7 * (-m0)) * detrecp),
                ((m0 * m4 - m3 *   m1)  * detrecp),
                ((m3 * (m10 * m8  - m7 * m11) + m4  * (m6 * m11 - m9 * m8) + m5  * (m9 * m7 - m6 * m10)) * detrecp),
                ((m6 * (m2  * m10 - m1 * m11) + m7  * (m0 * m11 - m9 * m2) + m8  * (m9 * m1 - m0 * m10)) * detrecp),
                ((m9 * (m2  * m4  - m1 * m5)  + m10 * (m0 * m5  - m3 * m2) + m11 * (m3 * m1 - m0 * m4))  * detrecp))

def m43transformn(m, v):
    (v0, v1, v2) = v
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, _m9, _m10, _m11) = m
    return ( (m0 * v0 + m3 * v1 + m6 * v2),
             (m1 * v0 + m4 * v1 + m7 * v2),
             (m2 * v0 + m5 * v1 + m8 * v2) )

def m43transformp(m, v):
    (v0, v1, v2) = v
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11) = m
    return ( (m0 * v0 + m3 * v1 + m6 * v2 + m9),
             (m1 * v0 + m4 * v1 + m7 * v2 + m10),
             (m2 * v0 + m5 * v1 + m8 * v2 + m11) )

def m43mul(a, b):
    (a0, a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11) = a
    (b0, b1, b2, b3, b4, b5, b6, b7, b8, b9, b10, b11) = b
    return ( (b0 * a0 + b3 * a1 + b6 * a2),
             (b1 * a0 + b4 * a1 + b7 * a2),
             (b2 * a0 + b5 * a1 + b8 * a2),
             (b0 * a3 + b3 * a4 + b6 * a5),
             (b1 * a3 + b4 * a4 + b7 * a5),
             (b2 * a3 + b5 * a4 + b8 * a5),
             (b0 * a6 + b3 * a7 + b6 * a8),
             (b1 * a6 + b4 * a7 + b7 * a8),
             (b2 * a6 + b5 * a7 + b8 * a8),
             (b0 * a9 + b3 * a10 + b6 * a11 + b9),
             (b1 * a9 + b4 * a10 + b7 * a11 + b10),
             (b2 * a9 + b5 * a10 + b8 * a11 + b11) )

def m43mulm44(a, b):
    (a0, a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11) = a
    (b0, b1, b2, b3, b4, b5, b6, b7, b8, b9, b10, b11, b12, b13, b14, b15) = b
    return ( (b0 * a0 + b4 * a1 + b8  * a2),
             (b1 * a0 + b5 * a1 + b9  * a2),
             (b2 * a0 + b6 * a1 + b10 * a2),
             (b3 * a0 + b7 * a1 + b11 * a2),
             (b0 * a3 + b4 * a4 + b8  * a5),
             (b1 * a3 + b5 * a4 + b9  * a5),
             (b2 * a3 + b6 * a4 + b10 * a5),
             (b3 * a3 + b7 * a4 + b11 * a5),
             (b0 * a6 + b4 * a7 + b8  * a8),
             (b1 * a6 + b5 * a7 + b9  * a8),
             (b2 * a6 + b6 * a7 + b10 * a8),
             (b3 * a6 + b7 * a7 + b11 * a8),
             (b0 * a9 + b4 * a10 + b8  * a11 + b12),
             (b1 * a9 + b5 * a10 + b9  * a11 + b13),
             (b2 * a9 + b6 * a10 + b10 * a11 + b14),
             (b3 * a9 + b7 * a10 + b11 * a11 + b15) )

def m43transpose(m):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11) = m
    return (m0, m3, m6, m9,
            m1, m4, m7, m10,
            m2, m5, m8, m11)

def m43adds(m, s):
    return tuple([ m[n] + s for n in range(12) ])

def m43subs(m, s):
    return tuple([ m[n] - s for n in range(12) ])

def m43muls(m, s):
    return tuple([ m[n] * s for n in range(12) ])

#######################################################################################################################

def m44(r0, r1, r2, r3,
        u0, u1, u2, u3,
        a0, a1, a2, a3,
        p0, p1, p2, p3):
    return (r0, r1, r2, r3,
            u0, u1, u2, u3,
            a0, a1, a2, a3,
            p0, p1, p2, p3)

def m44create(r, u, a, p):
    (r0, r1, r2, r3) = r
    (u0, u1, u2, u3) = u
    (a0, a1, a2, a3) = a
    (p0, p1, p2, p3) = p
    return (r0, r1, r2, r3,
            u0, u1, u2, u3,
            a0, a1, a2, a3,
            p0, p1, p2, p3)

def m44is_identity(m):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13, m14, m15) = m
    return (m0 == 1 and m1 == 0 and m2 == 0 and m3 == 0 and
            m4 == 0 and m5 == 1 and m6 == 0 and m7 == 0 and
            m8 == 0 and m9 == 0 and m10 == 1 and m11 == 0 and
            m12 == 0 and m13 == 0 and m14 == 0 and m15 == 1)

def m44right(m):
    return m[:4]

def m44up(m):
    return m[4:8]

def m44at(m):
    return m[8:12]

def m44pos(m):
    return m[12:]

def m44setright(m, v):
    (_, _, _, _, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13, m14, m15) = m
    (v0, v1, v2, v3) = v
    return (v0, v1, v2, v3, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13, m14, m15)

def m44setup(m, v):
    (m0, m1, m2, m3, _, _, _, _, m8, m9, m10, m11, m12, m13, m14, m15) = m
    (v0, v1, v2, v3) = v
    return (m0, m1, m2, m3, v0, v1, v2, v3, m8, m9, m10, m11, m12, m13, m14, m15)

def m44setat(m, v):
    (m0, m1, m2, m3, m4, m5, m6, m7, _, _, _, _, m12, m13, m14, m15) = m
    (v0, v1, v2, v3) = v
    return (m0, m1, m2, m3, m4, m5, m6, m7, v0, v1, v2, v3, m12, m13, m14, m15)

def m44setpos(m, v):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, _, _, _, _) = m
    (v0, v1, v2, v3) = v
    return (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, v0, v1, v2, v3)

def m44translate(m, v):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13, m14, m15) = m
    (v0, v1, v2, v3) = v
    return (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12 + v0, m13 + v1, m14 + v2, m15 + v3)

def m44transformn(m, v):
    (v0, v1, v2) = v
    return v4add3(v4muls(m44right(m), v0),
                  v4muls(m44up(m),    v1),
                  v4muls(m44at(m),    v2))

def m44transformp(m, v):
    (v0, v1, v2) = v
    return v4add4(v4muls(m44right(m), v0),
                  v4muls(m44up(m),    v1),
                  v4muls(m44at(m),    v2),
                  m44pos(m))

def m44mul(a, b):
    return m44create(v4mulm44(m44right(a), b),
                     v4mulm44(m44up(a),    b),
                     v4mulm44(m44at(a),    b),
                     v4mulm44(m44pos(a),   b))

def m44transpose(m):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13, m14, m15) = m
    return (m0, m4, m8,  m12,
            m1, m5, m9,  m13,
            m2, m6, m10, m14,
            m3, m7, m11, m15)

def m44adds(m, s):
    return tuple([ m[n] + s for n in range(16) ])

def m44subs(m, s):
    return tuple([ m[n] - s for n in range(16) ])

def m44muls(m, s):
    return tuple([ m[n] * s for n in range(16) ])

#######################################################################################################################

def is_visible_box(center, halfDimensions, vpm):
    (c0, c1, c2) = center
    (h0, h1, h2) = halfDimensions
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13, m14, m15) = vpm

    i0 = (m0  * h0)
    i1 = (m1  * h0)
    i2 = (m2  * h0)
    i3 = (m3  * h0)
    j0 = (m4  * h1)
    j1 = (m5  * h1)
    j2 = (m6  * h1)
    j3 = (m7  * h1)
    k0 = (m8  * h2)
    k1 = (m9  * h2)
    k2 = (m10 * h2)
    k3 = (m11 * h2)

    t0 = (m0 * c0 + m4 * c1 + m8  * c2 + m12)
    t1 = (m1 * c0 + m5 * c1 + m9  * c2 + m13)
    t2 = (m2 * c0 + m6 * c1 + m10 * c2 + m14)
    t3 = (m3 * c0 + m7 * c1 + m11 * c2 + m15)

    return not (((t0 - t3) >  (abs(i0 - i3) + abs(j0 - j3) + abs(k0 - k3))) or
                ((t0 + t3) < -(abs(i0 + i3) + abs(j0 + j3) + abs(k0 + k3))) or
                ((t1 - t3) >  (abs(i1 - i3) + abs(j1 - j3) + abs(k1 - k3))) or
                ((t1 + t3) < -(abs(i1 + i3) + abs(j1 + j3) + abs(k1 + k3))) or
                ((t2 - t3) >  (abs(i2 - i3) + abs(j2 - j3) + abs(k2 - k3))) or
                ((t2 + t3) < -(abs(i2 + i3) + abs(j2 + j3) + abs(k2 + k3))) or
               #((t3 - t3) >  (abs(i3 - i3) + abs(j3 - j3) + abs(k3 - k3))) or
                ((t3 + t3) < -(abs(i3 + i3) + abs(j3 + j3) + abs(k3 + k3))))

def is_visible_box_origin(halfDimensions, vpm):
    (h0, h1, h2) = halfDimensions
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13, m14, m15) = vpm

    i0 = (m0  * h0)
    i1 = (m1  * h0)
    i2 = (m2  * h0)
    i3 = (m3  * h0)
    j0 = (m4  * h1)
    j1 = (m5  * h1)
    j2 = (m6  * h1)
    j3 = (m7  * h1)
    k0 = (m8  * h2)
    k1 = (m9  * h2)
    k2 = (m10 * h2)
    k3 = (m11 * h2)
    t0 = m12
    t1 = m13
    t2 = m14
    t3 = m15

    return not (((t0 - t3) >  (abs(i0 - i3) + abs(j0 - j3) + abs(k0 - k3))) or
                ((t0 + t3) < -(abs(i0 + i3) + abs(j0 + j3) + abs(k0 + k3))) or
                ((t1 - t3) >  (abs(i1 - i3) + abs(j1 - j3) + abs(k1 - k3))) or
                ((t1 + t3) < -(abs(i1 + i3) + abs(j1 + j3) + abs(k1 + k3))) or
                ((t2 - t3) >  (abs(i2 - i3) + abs(j2 - j3) + abs(k2 - k3))) or
                ((t2 + t3) < -(abs(i2 + i3) + abs(j2 + j3) + abs(k2 + k3))) or
               #((t3 - t3) >  (abs(i3 - i3) + abs(j3 - j3) + abs(k3 - k3))) or
                ((t3 + t3) < -(abs(i3 + i3) + abs(j3 + j3) + abs(k3 + k3))))

def is_visible_sphere(center, radius, vpm):
    (c0, c1, c2) = center
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13, m14, m15) = vpm

    i0 = m0
    i1 = m1
    i2 = m2
    i3 = m3
    j0 = m4
    j1 = m5
    j2 = m6
    j3 = m7
    k0 = m8
    k1 = m9
    k2 = m10
    k3 = m11

    t0 = (m0 * c0 + m4 * c1 + m8  * c2 + m12)
    t1 = (m1 * c0 + m5 * c1 + m9  * c2 + m13)
    t2 = (m2 * c0 + m6 * c1 + m10 * c2 + m14)
    t3 = (m3 * c0 + m7 * c1 + m11 * c2 + m15)

    nradius = -radius

    return not (((t0 - t3) >  radius * (abs(i0 - i3) + abs(j0 - j3) + abs(k0 - k3))) or
                ((t0 + t3) < nradius * (abs(i0 + i3) + abs(j0 + j3) + abs(k0 + k3))) or
                ((t1 - t3) >  radius * (abs(i1 - i3) + abs(j1 - j3) + abs(k1 - k3))) or
                ((t1 + t3) < nradius * (abs(i1 + i3) + abs(j1 + j3) + abs(k1 + k3))) or
                ((t2 - t3) >  radius * (abs(i2 - i3) + abs(j2 - j3) + abs(k2 - k3))) or
                ((t2 + t3) < nradius * (abs(i2 + i3) + abs(j2 + j3) + abs(k2 + k3))) or
               #((t3 - t3) >  radius * (abs(i3 - i3) + abs(j3 - j3) + abs(k3 - k3))) or
                ((t3 + t3) < nradius * (abs(i3 + i3) + abs(j3 + j3) + abs(k3 + k3))))

def is_visible_sphere_origin(radius, vpm):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13, m14, m15) = vpm

    i0 = m0
    i1 = m1
    i2 = m2
    i3 = m3
    j0 = m4
    j1 = m5
    j2 = m6
    j3 = m7
    k0 = m8
    k1 = m9
    k2 = m10
    k3 = m11
    t0 = m12
    t1 = m13
    t2 = m14
    t3 = m15

    nradius = -radius

    return not (((t0 - t3) >  radius * (abs(i0 - i3) + abs(j0 - j3) + abs(k0 - k3))) or
                ((t0 + t3) < nradius * (abs(i0 + i3) + abs(j0 + j3) + abs(k0 + k3))) or
                ((t1 - t3) >  radius * (abs(i1 - i3) + abs(j1 - j3) + abs(k1 - k3))) or
                ((t1 + t3) < nradius * (abs(i1 + i3) + abs(j1 + j3) + abs(k1 + k3))) or
                ((t2 - t3) >  radius * (abs(i2 - i3) + abs(j2 - j3) + abs(k2 - k3))) or
                ((t2 + t3) < nradius * (abs(i2 + i3) + abs(j2 + j3) + abs(k2 + k3))) or
               #((t3 - t3) >  radius * (abs(i3 - i3) + abs(j3 - j3) + abs(k3 - k3))) or
                ((t3 + t3) < nradius * (abs(i3 + i3) + abs(j3 + j3) + abs(k3 + k3))))

def is_visible_sphere_unit(vpm):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13, m14, m15) = vpm

    i0 = m0
    i1 = m1
    i2 = m2
    i3 = m3
    j0 = m4
    j1 = m5
    j2 = m6
    j3 = m7
    k0 = m8
    k1 = m9
    k2 = m10
    k3 = m11
    t0 = m12
    t1 = m13
    t2 = m14
    t3 = m15

    return not (((t0 - t3) >  (abs(i0 - i3) + abs(j0 - j3) + abs(k0 - k3))) or
                ((t0 + t3) < -(abs(i0 + i3) + abs(j0 + j3) + abs(k0 + k3))) or
                ((t1 - t3) >  (abs(i1 - i3) + abs(j1 - j3) + abs(k1 - k3))) or
                ((t1 + t3) < -(abs(i1 + i3) + abs(j1 + j3) + abs(k1 + k3))) or
                ((t2 - t3) >  (abs(i2 - i3) + abs(j2 - j3) + abs(k2 - k3))) or
                ((t2 + t3) < -(abs(i2 + i3) + abs(j2 + j3) + abs(k2 + k3))) or
               #((t3 - t3) >  (abs(i3 - i3) + abs(j3 - j3) + abs(k3 - k3))) or
                ((t3 + t3) < -(abs(i3 + i3) + abs(j3 + j3) + abs(k3 + k3))))

def transform_box(center, halfExtents, matrix):
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11) = matrix
    (c0, c1, c2) = center
    (h0, h1, h2) = halfExtents

    return { center : ((m0 * c0 + m3 * c1 + m6 * c2 + m9),
                       (m1 * c0 + m4 * c1 + m7 * c2 + m10),
                       (m2 * c0 + m5 * c1 + m8 * c2 + m11)),
             halfExtents : ((abs(m0) * h0 + abs(m3) * h1 + abs(m6) * h2),
                            (abs(m1) * h0 + abs(m4) * h1 + abs(m7) * h2),
                            (abs(m2) * h0 + abs(m5) * h1 + abs(m8) * h2)) }

def plane_normalize(plane):
    (a, b, c, d) = plane
    lsq = ((a * a) + (b * b) + (c * c))
    if (lsq > 0.0):
        lr = 1.0 / math.sqrt(lsq)
        return ((a * lr), (b * lr), (c * lr), (d * lr))
    return V4ZERO

#######################################################################################################################

def quat(qx, qy, qz, qw):
    return (qx, qy, qz, qw)

def quatis_similar(q1, q2):
    # this compares for similar rotations not raw data
    (_, _, _, w1) = q1
    (_, _, _, w2) = q2
    if (w1 * w2 < 0.0):
        # quaternions in opposing hemispheres, negate one
        q1 = v4mul((-1, -1, -1, -1), q1)

    mag_sqrd = v4lengthsq(v4sub(q1, q2))
    epsilon_sqrd = (PRECISION * PRECISION)
    return mag_sqrd < epsilon_sqrd

def quatlength(q):
    return v4length(q)

def quatdot(q1, q2):
    return v4dot(q1, q2)

# Note quaternion multiplication is the opposite way around from our matrix multiplication
def quatmul(q1, q2):
    (v2, w2) = (q1[:3], q1[3])
    (v1, w1) = (q2[:3], q2[3])

    imag = v3add3(v3muls(v2, w1), v3muls(v1, w2), v3cross(v2, v1))
    real = (w1 * w2) - v3dot(v1, v2)

    (i0, i1, i2) = imag
    return (i0, i1, i2, real)

def quatnormalize(q):
    norme = math.sqrt(quatdot(q, q))

    if (norme == 0.0):
        return V4ZERO
    else:
        recip = 1.0 / norme
        return v4muls(q, recip)

def quatconjugate(q):
    (x, y, z, w) = q
    return (-x, -y, -z, w)

def quatlerp(q1, q2, t):
    if (v4dot(q1, q2) > 0.0):
        return v4add(v4muls(v4sub(q2, q1), t), q1)
    else:
        return v4add(v4muls(v4sub(q2, q1), -t), q1)

def quatslerp(q1, q2, t):
    cosom = quatdot(q1, q2)

    if (cosom < 0.0):
        q1 = v4muls(q1, -1.0)
        cosom = -cosom

    if(cosom > math.cos(math.pi / 180.0)):  # use a lerp for angles <= 1 degree
        return quatnormalize(quatlerp(q1, q2, t))

    omega = math.acos(cosom)
    sin_omega = math.sin(omega)

    q1 = v4muls(q1, math.sin((1.0-t)*omega)/sin_omega)

    return v4add(q1, v4muls(q2, math.sin(t*omega)/sin_omega))


def quatfrom_axis_rotation(axis, angle):
    omega = 0.5 * angle
    s = math.sin(omega)
    c = math.cos(omega)
    (a0, a1, a2) = axis
    q = (a0 * s, a1 * s, a2 * s, c)
    return quatnormalize(q)

def quatto_axis_rotation(q):
    angle = math.acos(q[3]) * 2.0

    sin_sqrd = 1.0 - q[3] * q[3]
    if sin_sqrd < PRECISION:
        # we can return any axis
        return ( (1.0, 0.0, 0.0), angle )
    else:
        scale = 1.0 / math.sqrt(sin_sqrd)
        axis = v3muls(q[:3], scale)
        return ( axis, angle )

def quattransformv(q, v):
    (qx, qy, qz, qw) = q
    qimaginary = (qx, qy, qz)

    s = (qw * qw) - v3dot(qimaginary, qimaginary)

    r = v3muls(v, s)

    s = v3dot(qimaginary, v)
    r = v3add(r, v3muls(qimaginary, s + s))
    r = v3add(r, v3muls(v3cross(qimaginary, v), qw + qw))
    return r

def quatto_m43(q):
    """Convert a quaternion to a matrix43."""
    (q0, q1, q2, q3) = q

    xx = 2.0 * q0 * q0
    yy = 2.0 * q1 * q1
    zz = 2.0 * q2 * q2
    xy = 2.0 * q0 * q1
    zw = 2.0 * q2 * q3
    xz = 2.0 * q0 * q2
    yw = 2.0 * q1 * q3
    yz = 2.0 * q1 * q2
    xw = 2.0 * q0 * q3

    return m43(1.0 - yy - zz, xy - zw,       xz + yw,
               xy + zw,       1.0 - xx - zz, yz - xw,
               xz - yw,       yz + xw,       1.0 - xx - yy,
               0.0,           0.0,           0.0)

def quatfrom_m33(m):
    """Convert the top of an m33 matrix into a quaternion."""
    (m0, m1, m2, m3, m4, m5, m6, m7, m8) = m
    trace = m0 + m4 + m8 + 1
    if trace > PRECISION:
        w = math.sqrt(trace) / 2
        x = (m5 - m7) / (4*w)
        y = (m6 - m2) / (4*w)
        z = (m1 - m3) / (4*w)
    else:
        if ((m0 > m4) and (m0 > m8)):
            s = math.sqrt( 1.0 + m0 - m4 - m8 ) * 2 # S=4*qx
            w = (m5 - m7) / s
            x = 0.25 * s
            y = (m3 + m1) / s
            z = (m6 + m2) / s
        elif (m4 > m8):
            s = math.sqrt( 1.0 + m4 - m0 - m8 ) * 2 # S=4*qy
            w = (m6 - m2) / s
            x = (m3 + m1) / s
            y = 0.25 * s
            z = (m7 + m5) / s
        else:
            s = math.sqrt( 1.0 + m8 - m0 - m4 ) * 2 # S=4*qz
            w = (m1 - m3) / s
            x = (m6 + m2) / s
            y = (m7 + m5) / s
            z = 0.25 * s

    return quatnormalize((-x, -y, -z, w))

def quatfrom_m43(m):
    """ Convert the top of an m33 matrix into a quaternion."""
    (m0, m1, m2, m3, m4, m5, m6, m7, m8, _, _, _) = m
    trace = m0 + m4 + m8 + 1
    if trace > PRECISION:
        w = math.sqrt(trace) / 2
        x = (m5 - m7) / (4*w)
        y = (m6 - m2) / (4*w)
        z = (m1 - m3) / (4*w)
    else:
        if ((m0 > m4) and (m0 > m8)):
            s = math.sqrt( 1.0 + m0 - m4 - m8 ) * 2 # S=4*qx
            w = (m5 - m7) / s
            x = 0.25 * s
            y = (m3 + m1) / s
            z = (m6 + m2) / s
        elif (m4 > m8):
            s = math.sqrt( 1.0 + m4 - m0 - m8 ) * 2 # S=4*qy
            w = (m6 - m2) / s
            x = (m3 + m1) / s
            y = 0.25 * s
            z = (m7 + m5) / s
        else:
            s = math.sqrt( 1.0 + m8 - m0 - m4 ) * 2 # S=4*qz
            w = (m1 - m3) / s
            x = (m6 + m2) / s
            y = (m7 + m5) / s
            z = 0.25 * s

    return quatnormalize((-x, -y, -z, w))

def quatpos(qx, qy, qz, qw, px, py, pz):
    return ( (qx, qy, qz, qw), (px, py, pz) )

def quatpostransformn(qp, n):
    (q, _) = qp

    return quattransformv(q, n)

def quatpostransformp(qp, p):
    (q, v) = qp

    rotated_p = quattransformv(q, p)
    return v3add(rotated_p, v)

# Note quaternion multiplication is the opposite way around from our matrix multiplication
def quatposmul(qp1, qp2):
    (q1, _) = qp1
    (q2, v2) = qp2

    qr = quatmul(q1, q2)
    pr = quatpostransformp(v2, qp1)

    return (qr, pr)

def quat_from_qx_qy_qz(qx, qy, qz):
    """Calculate the w field of a quaternion."""
    qw = 1.0 - ((qx * qx) + (qy * qy) + (qz * qz))
    if (qw < 0.0):
        qw = 0.0
    else:
        qw = -math.sqrt(qw)
    return (qx, qy, qz, qw)

#######################################################################################################################

########NEW FILE########
__FILENAME__ = xml2json
#!/usr/bin/env python
# Copyright (c) 2010-2013 Turbulenz Limited

import logging

from re import sub
from optparse import OptionParser, OptionGroup, TitledHelpFormatter

from turbulenz_tools.utils.xml_json import xml2json
from turbulenz_tools.tools.stdtool import simple_options

__version__ = '1.0.0'
__dependencies__ = ['turbulenz_tools.utils.xml_json']

LOG = logging.getLogger(__name__)

def _parser():
    usage = "usage: %prog [options] -i source.xml -o output.json"
    description = "Convert XML assets into a structured JSON asset."

    parser = OptionParser(description=description, usage=usage, formatter=TitledHelpFormatter())
    parser.add_option("--version", action="store_true", dest="output_version", default=False,
                      help="output version number")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="verbose output")
    parser.add_option("-s", "--silent", action="store_true", dest="silent", default=False, help="silent running")
    parser.add_option("-m", "--metrics", action="store_true", dest="metrics", default=False,
                      help="output asset metrics")

    parser.add_option("-i", "--input", action="store", dest="input", help="input XML file to process")
    parser.add_option("-o", "--output", action="store", dest="output", help="output JSON file to process")

    group = OptionGroup(parser, "Asset Generation Options")
    group.add_option("-j", "--json-indent", action="store", dest="json_indent", type="int", default=0, metavar="SIZE",
                     help="json output pretty printing indent size, defaults to 0")
    group.add_option("-n", "--namespace", action="store_true", dest="namespace", default=False,
                     help="maintain XML xmlns namespace in JSON asset keys.")
    group.add_option("-c", "--convert-types", action="store_true", dest="convert_types", default=False,
                     help="attempt to convert values to ints, floats and lists.")

    parser.add_option_group(group)

    return parser

def main():
    (options, args_, parser_) = simple_options(_parser, __version__, __dependencies__)

    try:
        with open(options.input) as xml_file:
            xml_string = xml_file.read()

            # At the moment there doesn't seem to be an obvious way to extract the xmlns from the asset.
            # For now, we'll attempt to just remove it before transforming it into a Python object.

            # <COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
            #   ==>
            # <COLLADA version="1.4.1">
            if options.namespace is False:
                xml_string = sub(' xmlns="[^"]*"', '', xml_string)

            json_string = xml2json(xml_string, indent=options.json_indent, convert_types=options.convert_types)
            if options.output:
                with open(options.output, 'w') as target:
                    target.write(json_string)
                    target.write('\n')
            else:
                print json_string

    except IOError as e:
        LOG.error(e)
        return e.errno
    except Exception as e:
        LOG.critical('Unexpected exception: %s', e)
        return 1

if __name__ == "__main__":
    exit(main())

########NEW FILE########
__FILENAME__ = coloured_writer
# Copyright (c) 2009-2011,2013 Turbulenz Limited
"""Utility module to colour highlight the output form tools."""

import sys
import re

# pylint: disable=R0903
class ColouredWriterBase(object):
    """Colour th Django server output."""
    colors = {  'endc': '\033[0m',              # black
                'fail': '\033[91m',             # red
                'okgreen': '\033[32m',          # green
                'unknown': '\033[33m',          # yellow
                'okblue': '\033[34m',           # blue
                'warning': '\033[95m',          # magenta
                'build': '\033[97m\033[40m' }   # white

    status_code_text = {
            100: 'CONTINUE',
            101: 'SWITCHING PROTOCOLS',
            200: 'OK',
            201: 'CREATED',
            202: 'ACCEPTED',
            203: 'NON-AUTHORITATIVE INFORMATION',
            204: 'NO CONTENT',
            205: 'RESET CONTENT',
            206: 'PARTIAL CONTENT',
            300: 'MULTIPLE CHOICES',
            301: 'MOVED PERMANENTLY',
            302: 'FOUND',
            303: 'SEE OTHER',
            304: 'NOT MODIFIED',
            305: 'USE PROXY',
            306: 'RESERVED',
            307: 'TEMPORARY REDIRECT',
            400: 'BAD REQUEST',
            401: 'UNAUTHORIZED',
            402: 'PAYMENT REQUIRED',
            403: 'FORBIDDEN',
            404: 'NOT FOUND',
            405: 'METHOD NOT ALLOWED',
            406: 'NOT ACCEPTABLE',
            407: 'PROXY AUTHENTICATION REQUIRED',
            408: 'REQUEST TIMEOUT',
            409: 'CONFLICT',
            410: 'GONE',
            411: 'LENGTH REQUIRED',
            412: 'PRECONDITION FAILED',
            413: 'REQUEST ENTITY TOO LARGE',
            414: 'REQUEST-URI TOO LONG',
            415: 'UNSUPPORTED MEDIA TYPE',
            416: 'REQUESTED RANGE NOT SATISFIABLE',
            417: 'EXPECTATION FAILED',
            500: 'INTERNAL SERVER ERROR',
            501: 'NOT IMPLEMENTED',
            502: 'BAD GATEWAY',
            503: 'SERVICE UNAVAILABLE',
            504: 'GATEWAY TIMEOUT',
            505: 'HTTP VERSION NOT SUPPORTED',
        }

    def __init__(self, stdout, stderr):
        self.stdout = stdout
        self.stderr = stderr

    def flush(self):
        """Flush method."""
        self.stdout.flush()
        self.stderr.flush()

if sys.platform == "win32":

    from ctypes import windll, Structure, c_short, c_ushort, byref

    SHORT = c_short
    WORD = c_ushort

    class Coord(Structure):
        """struct in wincon.h."""
        _fields_ = [
            ("X", SHORT),
            ("Y", SHORT)]

    class SmallRect(Structure):
        """struct in wincon.h."""
        _fields_ = [
            ("Left", SHORT),
            ("Top", SHORT),
            ("Right", SHORT),
            ("Bottom", SHORT)]

    class ConsoleScreenBufferInfo(Structure):
        """struct in wincon.h."""
        _fields_ = [
            ("dwSize", Coord),
            ("dwCursorPosition", Coord),
            ("wAttributes", WORD),
            ("srWindow", SmallRect),
            ("dwMaximumWindowSize", Coord)]

    # winbase.h
    STD_INPUT_HANDLE = -10
    STD_OUTPUT_HANDLE = -11
    STD_ERROR_HANDLE = -12

    # wincon.h
    FOREGROUND_BLACK     = 0x0000
    FOREGROUND_BLUE      = 0x0001
    FOREGROUND_GREEN     = 0x0002
    FOREGROUND_CYAN      = 0x0003
    FOREGROUND_RED       = 0x0004
    FOREGROUND_MAGENTA   = 0x0005
    FOREGROUND_YELLOW    = 0x0006
    FOREGROUND_GREY      = 0x0007
    FOREGROUND_INTENSITY = 0x0008 # foreground color is intensified.

    BACKGROUND_BLACK     = 0x0000
    BACKGROUND_BLUE      = 0x0010
    BACKGROUND_GREEN     = 0x0020
    BACKGROUND_CYAN      = 0x0030
    BACKGROUND_RED       = 0x0040
    BACKGROUND_MAGENTA   = 0x0050
    BACKGROUND_YELLOW    = 0x0060
    BACKGROUND_GREY      = 0x0070
    BACKGROUND_INTENSITY = 0x0080 # background color is intensified.

    STDOUT_HANDLE = windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    SETCONSOLETEXTATTRIBUTE = windll.kernel32.SetConsoleTextAttribute
    GETCONSOLESCREENBUFFERINFO = windll.kernel32.GetConsoleScreenBufferInfo

    def get_text_attr():
        """Returns the character attributes (colors) of the console screen buffer."""
        csbi = ConsoleScreenBufferInfo()
        GETCONSOLESCREENBUFFERINFO(STDOUT_HANDLE, byref(csbi))
        return csbi.wAttributes

    def set_text_attr(color):
        """Sets the character attributes (colors) of the console screen buffer. Color is a combination of foreground
        and background color, foreground and background intensity."""
        SETCONSOLETEXTATTRIBUTE(STDOUT_HANDLE, color)

    class ColouredWriter(ColouredWriterBase):
        """Colour the Django server output."""
        colors = {  'endc': FOREGROUND_BLACK | FOREGROUND_INTENSITY,        # white
                    'fail': FOREGROUND_RED,                                 # red
                    'okgreen': FOREGROUND_GREEN,                            # green
                    'unknown': FOREGROUND_YELLOW,                           # yellow
                    'okblue': FOREGROUND_BLUE | FOREGROUND_INTENSITY,       # blue
                    'warning':FOREGROUND_MAGENTA | FOREGROUND_INTENSITY,    # magenta
                    'build': BACKGROUND_BLACK | BACKGROUND_INTENSITY | FOREGROUND_BLACK } # white

        #[14/Jul/2009 18:57:31] "GET /assets/maps/mp/q4ctf1.proc HTTP/1.1" 302 0
        line_re = re.compile('^(\[.*\]) (".*") (\d*) (\d*)$')
        build_re = re.compile("^(\[.*\]) ('.*')$")

        def __init__(self, stdout, stderr):
            ColouredWriterBase.__init__(self, stdout, stderr)
            self.default_colors = get_text_attr()
            self.default_bg = self.default_colors & 0x0070

        def write(self, line):
            """Write method."""
            line_m = ColouredWriter.line_re.match(line)
            if line_m:
                time = line_m.group(1)
                request = line_m.group(2)
                code = int(line_m.group(3))
                size = int(line_m.group(4))
                if code >= 500:
                    command = ColouredWriter.colors['fail']
                elif code >= 400:
                    command = ColouredWriter.colors['warning']
                elif code == 301:
                    command = ColouredWriter.colors['fail'] # We don't want any 301s from our links...
                elif code >= 300:
                    command = ColouredWriter.colors['okgreen']
                elif code >= 200:
                    command = ColouredWriter.colors['okblue']
                else:
                    command = ColouredWriter.colors['unknown']

                if code in ColouredWriter.status_code_text:
                    meaning = ColouredWriter.status_code_text[code]
                else:
                    meaning = "*unknown*"

                self.stdout.write(time)
                set_text_attr(command | self.default_bg)
                self.stdout.write(" " + request)
                set_text_attr(self.default_colors)
                self.stdout.write(" %i %i (%s)\n" % (code, size, meaning))
            else:
                build_m = ColouredWriter.build_re.match(line)
                if build_m:
                    time = build_m.group(1)
                    request = build_m.group(2)
                    self.stdout.write(time + ' ')
                    if request[1:].startswith("FAILED"):
                        set_text_attr(ColouredWriter.colors['fail'])
                    else:
                        set_text_attr(ColouredWriter.colors['build'] | self.default_bg)
                    self.stdout.write("%s" % (request))
                    set_text_attr(self.default_colors)
                    self.stdout.write("\n")
                else:
                    self.stdout.write(line)

else:

    class ColouredWriter(ColouredWriterBase):
        """Colour the Django server output."""
        colors = {  'endc': '\033[0m',               # black
                    'fail': '\033[91m',              # red
                    'okgreen': '\033[32m',           # green
                    'unknown': '\033[33m',           # yellow
                    'okblue': '\033[34m',            # blue
                    'warning': '\033[95m',           # magenta
                    'buildfail': '\033[91m\033[40m', # red on black
                    'buildmsg': '\033[32m\033[40m',  # green on black
                    'build': '\033[97m\033[40m' }    # white on black

        #[14/Jul/2009 18:57:31] "GET /assets/maps/mp/q4ctf1.proc HTTP/1.1" 302 0
        line_re = re.compile('^(\[.*\]) (".*") (\d*) (\d*)$')
        build_re = re.compile("^(\[.*\]) ('.*')$")

        # 127.0.0.1 0.0.0.0:8000 - [06/Sep/2009:21:40:00 +0100]
        #    "GET /assets/models/mapobjects/multiplayer/acceleration_pad/acceleration_pad_d.dds HTTP/1.1" 200 87125
        #    "http://0.0.0.0:8000/play/maps/mp/q4ctf1.map"
        #    "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6; en-us) AppleWebKit/532.0+ (KHTML, like Gecko) \
        #        Version/4.0.3 Safari/531.9"
        access_re = re.compile('^([\d\.]*) ([\w\.:-]*) - (\[.*\]) (".*") (\d*) (\d*) (".*") (".*")$')

        @classmethod
        def coloured_access(cls, time, request, code, size, server, who=None):
            """Generate a consistent coloured response."""
            if code >= 500:
                command = ColouredWriter.colors['fail']
            elif code >= 400:
                command = ColouredWriter.colors['warning']
            elif code == 301:
                command = ColouredWriter.colors['fail'] # We don't want any 301s from our links...
            elif code >= 300:
                command = ColouredWriter.colors['okgreen']
            elif code >= 200:
                command = ColouredWriter.colors['okblue']
            else:
                command = ColouredWriter.colors['unknown']

            if code in ColouredWriter.status_code_text:
                meaning = ColouredWriter.status_code_text[code]
            else:
                meaning = "*unknown*"

            endc = ColouredWriter.colors['endc']
            if who is None:
                line = "%s %s %s%s%s %i %i (%s)\n" % (server[:3], time, command, request, endc, code, size, meaning)
            else:
                line = "%s %s %s %s%s%s %i %i (%s)\n" % \
                    (server[:3], time, who, command, request, endc, code, size, meaning)
            return line

        def write(self, line):
            """Write method."""
            access_m = ColouredWriter.access_re.match(line)
            line_m = ColouredWriter.line_re.match(line)
            build_m = ColouredWriter.build_re.match(line)
            if access_m:
                server = "LIGHTTPD"
                time = access_m.group(3)
                who = access_m.group(1)
                request = access_m.group(4)
                code = int(access_m.group(5))
                size = int(access_m.group(6))
                line = ColouredWriter.coloured_access(time, request, code, size, server, who)
            elif line_m:
                server = "PYTHON"
                time = line_m.group(1)
                request = line_m.group(2)
                code = int(line_m.group(3))
                size = int(line_m.group(4))
                line = ColouredWriter.coloured_access(time, request, code, size, server)
            elif build_m:
                server = "BUILD"
                time = build_m.group(1)
                request = build_m.group(2)
                if request[1:].startswith("FAILED"):
                    build = ColouredWriter.colors['buildfail']
                elif request[1:].startswith("MSG"):
                    build = ColouredWriter.colors['buildmsg']
                else:
                    build = ColouredWriter.colors['build']
                endc = ColouredWriter.colors['endc']
                line = "%s %s %s%s%s\n" % (server[:3], time, build, request, endc)

            self.stdout.write(line)
            self.stdout.flush()

if __name__ == "__main__":
    CONVERTER = ColouredWriter(sys.stdout, sys.stderr)
    while True:
        L = sys.stdin.readline()
        CONVERTER.write(L)

########NEW FILE########
__FILENAME__ = dependencies
# Copyright (c) 2010-2013 Turbulenz Limited
"""
Utility functions for finding and outputing dependencies
"""

from os.path import join, exists, abspath
from jinja2 import meta

__version__ = '1.0.0'

def find_file_in_dirs(filename, dirs, error_on_multiple = False):
    found = []
    for d in dirs:
        fn = join(d, filename)
        if exists(fn):
            if error_on_multiple:
                if fn not in found:
                    found.append(fn)
            else:
                return abspath(fn)
    if error_on_multiple:
        if len(found) > 1:
            raise Exception("File '%s' matched several locations: %s" % found)
        if len(found) == 1:
            return abspath(found[0])
    return None

# pylint: disable=W0102
def find_dependencies(input_file, templatedirs, env, exceptions=[]):
    """
    Find jinja2 dependency list.  Files listed in 'exceptions' do not
    generate exceptions if not found.
    """

    total_set = set()

    def find_dependencies_recurse(file_path):
        new_deps = []

        # Parse the file and extract the list of references

        with open(file_path, "r") as f:
            ast = env.parse(f.read().decode('utf-8'))

            # For each reference, find the absolute path.  If no file
            # is found and the reference was not listed in exceptions,
            # throw an error.

            for reference in meta.find_referenced_templates(ast):
                reference_path = find_file_in_dirs(reference, templatedirs)
                if reference_path is None:
                    if reference in exceptions:
                        continue
                    raise Exception("cannot find file '%s' referenced in "
                                    "'%s'" % (reference, file_path))
                new_deps.append(reference_path)

        for dep in new_deps:
            # Make sure we don't have a circular reference
            if dep not in total_set:
                total_set.add(dep)
                find_dependencies_recurse(dep)
        return

    top_file = find_file_in_dirs(input_file, templatedirs)
    if top_file is None:
        raise Exception("cannot find file '%s'" % input_file)
    total_set.add(top_file)
    find_dependencies_recurse(top_file)

    sorted_total = []
    for x in total_set:
        sorted_total.append(x)

    sorted_total.sort()
    return sorted_total
# pylint: enable=W0102

########NEW FILE########
__FILENAME__ = disassembler
# Copyright (c) 2010-2011,2013 Turbulenz Limited
"""
Python module that handles JSON asset disassembling into HTML.
"""

#######################################################################################################################

def ordered(d):
    keys = d.keys()
    keys.sort()
    for k in keys:
        yield(k, d[k])

# pylint: disable=R0201
class Json2txtRenderer(object):

    def __init__(self):
        pass

    def span(self, string, span_class=None):
        return string

    def key(self, string):
        return string

    def comment(self, string):
        return string

    ###################################

    def expand(self, node_path_string, expand_all=True):
        return '...'

    def collapse(self):
        return ''

    def node_span(self, node_path_string):
        return ''

    def close_span(self):
        return ''

    ###################################

    def expand_link(self, num, is_list, node_path_string, parent):
        """Creates a link span to expand a dictionary or a list."""
        return '%s%s%s%s%s\n%s' % ( self.node_span(node_path_string),
                                    '[ ' if is_list else '{ ',
                                    self.expand(node_path_string, False),
                                    self.comment(' (%i %s)' % (num, parent)),
                                    ' ]' if is_list else ' }',
                                    self.close_span() )

    def string(self, value, link_prefix=None, link=False):
        asset = unicode(value)
        return asset


class Json2txtColourRenderer(Json2txtRenderer):

    def __init__(self):
        Json2txtRenderer.__init__(self)

    def span(self, string, span_class=None):
        return string

    def key(self, string):
        return '\033[31m%s\033[0m' % string

    def comment(self, string):
        return '\033[34m%s\33[0m' % string

    def string(self, value, link_prefix=None, link=False):
        return '\033[32m"%s"\033[0m' % unicode(value)

    def expand(self, node_path_string, expand_all=True):
        return '\033[34m...\033[0m'


class Json2htmlRenderer(Json2txtRenderer):

    def __init__(self):
        Json2txtRenderer.__init__(self)

    def span(self, string, span_class=None):
        if span_class:
            return '<span class="%s">%s</span>' % (span_class, string)
        else:
            return '<span>%s</span>' % string

    def key(self, string):
        return self.span(string)

    def comment(self, string):
        return self.span(string, 'c')

    ###################################

    def expand(self, node_path_string, expand_all=True):
        c = 'expand c all' if expand_all else 'expand c'
        return '<a class="%s">more</a>' % c

    def collapse(self):
        return '<a class="collapse c">less</a>'

    def node_span(self, node_path_string):
        return '<span class="node" id="node=%s">' % node_path_string

    def close_span(self):
        return '</span>'

    ###################################

    def string(self, value, link_prefix=None, link=False):
        asset = unicode(value)
        if link_prefix and (link or '/' in value):
            return '"<a href="%s/%s">%s</a>"' % (link_prefix, asset, asset)
        else:
            return '"%s"' % asset
# pylint: enable=R0201

#######################################################################################################################

class Disassembler(object):
    """Convert JSON to HTML."""

    def __init__(self, renderer, list_cull=3, dict_cull=3, depth=2, link_prefix='',
                 single_line_string_length=200, auto_expand_child_lenght=500, limit_list_length=1000):
        self.renderer = renderer
        self.list_cull = list_cull
        self.dict_cull = dict_cull
        self.depth = depth

        self.single_line_string_length = single_line_string_length
        self.auto_expand_child_lenght = auto_expand_child_lenght
        self.limit_list_length = limit_list_length

        self.link_prefix = link_prefix

        self.current_node_path = [ ]
        self.node_path_string = ''
        self.current_depth = 0

    def _update_node_path_string(self):
        self.node_path_string = ','.join([str(x) for x in self.current_node_path])

    def _push(self, index):
        self.current_node_path.append(index)
        self._update_node_path_string()
        self.current_depth += 1

    def _pop(self):
        self.current_node_path = self.current_node_path[:-1]
        self._update_node_path_string()
        self.current_depth -= 1

    def _has_more_depth(self):
        return self.current_depth <= self.depth

    def _indents(self):
        return ('  ' * len(self.current_node_path), '  ' * (len(self.current_node_path) - 1))

    ###################################################################################################################

    # This function can render the list on multiple lines.
    def mark_up_list_items(self, output, element, start_element, count):
        """Iterate through the list or its slice and mark up its elements."""
        (indent, minor_indent) = self._indents()
        r = self.renderer

        def _expand_link(length, is_list):
            return r.expand_link(length, is_list, self.node_path_string, 'items' if is_list else 'elements')

        sub_list = element[start_element:start_element + count]
        for i, l in enumerate(sub_list):
            if i < (len(sub_list) - 1):
                comma = ','
                line_indent = indent
            else:
                comma = ''
                line_indent = minor_indent

            self._push(i + start_element)
            if isinstance(l, dict):
                if self._has_more_depth():
                    self.mark_up_dict(output, l)
                else:
                    child_output = [ ]
                    self.mark_up_dict(child_output, l)
                    child_len = reduce(lambda a, b: a + len(b), child_output, 0)
                    if child_len < self.auto_expand_child_lenght:
                        output.extend(child_output)
                    else:
                        output.append(_expand_link(len(l), False))
            elif isinstance(l, (list, tuple)):
                if self._has_more_depth():
                    self.mark_up_list(output, l)
                else:
                    child_output = [ ]
                    self.mark_up_list(child_output, l)
                    child_len = reduce(lambda a, b: a + len(b), child_output, 0)
                    if child_len < self.auto_expand_child_lenght:
                        output.extend(child_output)
                    else:
                        output.append(_expand_link(len(l), True))
            elif isinstance(l, (str, unicode)):
                output.append('%s%s\n' % (r.string(l, self.link_prefix), comma))
            elif isinstance(l, bool):
                output.append('%s%s\n' % ('true' if l else 'false', comma))
            elif l is None:
                output.append('null%s\n' % comma)
            else:
                output.append('%s%s\n' % (str(l), comma))
            output.append(line_indent)
            self._pop()

    def mark_up_single_line_list_items(self, output, element, start_element, count):
        # This function can render on a single line the list.
        (indent, _) = self._indents()
        r = self.renderer
        limit_list_length = self.limit_list_length

        current_length = 0
        for i, x in enumerate(element[start_element:start_element + count]):
            if isinstance(x, (str, unicode)):
                o = r.string(x, self.link_prefix)
            elif isinstance(x, bool):
                o = 'true' if x else 'false'
            elif x is None:
                o = 'null'
            else:
                o = str(x)

            output.append(o)
            if i < (count - 1):
                output.append(', ')

            # We count the size of the element and an extra 2 for the comma and space.
            current_length += len(o) + 2
            if current_length > limit_list_length:
                output.append('\n%s' % indent)
                current_length = 0

    def mark_up_list(self, output, element, parent=None, expand=False):
        (indent, _) = self._indents()
        r = self.renderer

        num_values = len(element)
        over_size_limit = num_values > 2 * self.list_cull

        parent = parent or 'items'

        # Test the list to see if we can render it onto a single line.
        # If we find a dict or list we exit and fall back onto rendering each item on a single line.
        total_length = 0
        for x in element:
            if isinstance(x, (dict, list, tuple)):
                break
            elif isinstance(x, (str, unicode)):
                total_length += len(x)
        else:
            # We got to the end of the list without finding any complicated items.
            # If the total length of strings too large also fall back onto multi line rendering.
            if total_length < self.single_line_string_length:
                if not expand and over_size_limit:
                    output.append('%s[' % r.node_span(self.node_path_string))
                    self.mark_up_single_line_list_items(output, element, 0, self.list_cull)
                    output.append(', %s ' % r.expand(self.node_path_string))
                    self.mark_up_single_line_list_items(output, element, num_values - self.list_cull, self.list_cull)
                    output.append(']%s\n%s' % (r.comment(' (%i of %i %s)' % (self.list_cull * 2, num_values, parent)),
                                               r.close_span()))
                else:
                    output.append('%s[' % ((r.collapse() + ' ') if over_size_limit else ''))
                    self.mark_up_single_line_list_items(output, element, 0, num_values)
                    output.append(']\n%s' % (r.close_span() if over_size_limit else ''))

                # Early out as we've followed a special case.
                return

        # If we get this far we render each item on it's own line.
        if not expand and over_size_limit:
            # display start and end of the list
            output.append('%s[\n%s' % (r.node_span(self.node_path_string), indent))
            self.mark_up_list_items(output, element, 0, self.list_cull)
            output.append('%s\n%s' % (r.expand(self.node_path_string), indent))
            self.mark_up_list_items(output, element, num_values - self.list_cull, self.list_cull)
            output.append(']%s\n%s' % (r.comment(' (%i of %i %s)' % (self.list_cull * 2, num_values, parent)),
                                       r.close_span()))
        else:
            output.append('%s[\n%s' % ((r.collapse() + ' ') if over_size_limit else '', indent))
            self.mark_up_list_items(output, element, 0, num_values)
            output.append(']\n')

    def mark_up_element(self, output, k, v, i=0):
        """Mark up the element of a node."""
        (indent, _) = self._indents()
        r = self.renderer

        def _expand_link(is_list):
            return r.expand_link(len(v), is_list, self.node_path_string, k)

        self._push(i)
        output.append('%s%s: ' % (indent, r.key(k)) if k is not None else '')
        if isinstance(v, dict):
            if self._has_more_depth():
                self.mark_up_dict(output, v, k)
            else:
                child_output = [ ]
                self.mark_up_dict(child_output, v, k)
                child_len = reduce(lambda a, b: a + len(b), child_output, 0)
                if child_len < self.auto_expand_child_lenght:
                    output.extend(child_output)
                else:
                    output.append(_expand_link(False))
        elif isinstance(v, (list, tuple)):
            if self._has_more_depth():
                self.mark_up_list(output, v, k)
            else:
                child_output = [ ]
                self.mark_up_list(child_output, v, k)
                child_len = reduce(lambda a, b: a + len(b), child_output, 0)
                if child_len < self.auto_expand_child_lenght:
                    output.extend(child_output)
                else:
                    output.append(_expand_link(True))
        elif isinstance(v, (str, unicode)):
            output.append('%s\n' % r.string(v, self.link_prefix, (k == 'reference')))
        elif isinstance(v, (bool)):
            output.append('true\n' if v is True else 'false\n')
        elif v is None:
            output.append('none\n')
        else:
            output.append('%s\n' % str(v))
        self._pop()

    def mark_up_dict(self, output, element, parent=None, expand=False):
        """Mark up the node element accordingly to its type into HTML and return as a string."""
        (indent, minor_indent) = self._indents()
        r = self.renderer

        num_values = len(element)
        over_size_limit = num_values > self.dict_cull

        parent = parent or 'elements'

        if not expand and over_size_limit:
            output.append('%s{\n' % r.node_span(self.node_path_string))

            for i, (k, v) in enumerate(ordered(element)):
                if i == self.dict_cull:
                    break
                self.mark_up_element(output, k, v, i)

            output.append('%s%s %s\n%s}\n%s' % (indent,
                                               r.expand(self.node_path_string),
                                               r.comment('(%i of %i %s)' % (self.dict_cull, num_values, parent)),
                                               minor_indent,
                                               r.close_span()))

        else:
            output.append('%s{\n' % ((r.collapse() + ' ') if over_size_limit else ''))
            for i, (k, v) in enumerate(ordered(element)):
                self.mark_up_element(output, k, v, i)
            output.append('%s}\n' % minor_indent)

    def find_node(self, output, json_asset, node_list, expand=False):
        """Find the element in the node list from the json_asset, return marked up in HTML."""

        def _values(elements):
            if isinstance(json_asset, dict):
                for k, v in ordered(json_asset):
                    yield (k, v)
            elif isinstance(json_asset, list):
                for v in json_asset:
                    yield (None, v)

        for i, (k, v) in enumerate(_values(json_asset)):
            if i == node_list[0]:
                self._push(i)
                if (len(node_list) == 1):
                    if isinstance(v, dict):
                        self.mark_up_dict(output, v, k, expand)
                    elif isinstance(v, list):
                        self.mark_up_list(output, v, k, expand)
                    else:
                        # Potentially this should handle the other types correct.
                        # Maybe we could refactor this out of the dict or list methods.
                        output.append('%s\n' % str(v))
                else:
                    self.find_node(output, v, node_list[1:], expand)
                self._pop()

    def mark_up_asset(self, json_asset, expand=False, node=None):
        """Mark up element on HTTP Request."""
        if node is None:
            node_list = [0]
        else:
            node_list = [int(x) for x in node.split(',')]

        output = [ ]
        self.find_node(output, json_asset, node_list, expand)
        return ''.join(output)

########NEW FILE########
__FILENAME__ = hash
# Copyright (c) 2010-2011,2013 Turbulenz Limited

from hashlib import md5, sha256
from base64 import urlsafe_b64encode

def hash_file_sha256_md5(file_path):
    file_obj = open(file_path, 'rb')
    ctx_sha256 = sha256()
    ctx_md5 = md5()
    x = file_obj.read(65536)
    while x:
        ctx_sha256.update(x)
        ctx_md5.update(x)
        x = None
        x = file_obj.read(65536)
    file_obj.close()
    file_sha256 = urlsafe_b64encode(ctx_sha256.digest()).rstrip('=')
    file_md5 = ctx_md5.hexdigest()
    return file_sha256, file_md5

def hash_file_sha256(file_path):
    file_obj = open(file_path, 'rb')
    ctx = sha256()
    x = file_obj.read(65536)
    while x:
        ctx.update(x)
        x = None
        x = file_obj.read(65536)
    file_obj.close()
    return urlsafe_b64encode(ctx.digest()).rstrip('=')

def hash_file_md5(file_path):
    file_obj = open(file_path, 'rb')
    ctx_md5 = md5()
    x = file_obj.read(65536)
    while x:
        ctx_md5.update(x)
        x = None
        x = file_obj.read(65536)
    file_obj.close()
    return ctx_md5.hexdigest()

def hash_for_file(file_name):
    return urlsafe_b64encode(hash_file_md5(file_name)).strip('=')

def hash_for_string(string):
    return urlsafe_b64encode(md5(string).digest()).strip('=')

########NEW FILE########
__FILENAME__ = htmlmin
# Copyright (c) 2010-2011,2013 Turbulenz Limited

import re
import logging

from HTMLParser import HTMLParser

# pylint: disable=W0403
from jsmin import jsmin
# pylint: enable=W0403

LOG = logging.getLogger(__name__)

# pylint: disable=R0904
class HTMLMinifier(HTMLParser):
    """An HTML minifier."""

    REMOVE_WHITESPACE = re.compile(r'\s{2,}').sub

    def __init__(self, output, compact_script=True):
        """output: This callback function will be called when there is data to output.
        A good candidate to use is sys.stdout.write."""
        HTMLParser.__init__(self)
        self.output = output
        self.compact_script = compact_script
        self.pre_count = 0
        self.inside_script = False

    def error(self, message):
        LOG.warning('Warning: %s', message)

    def handle_starttag(self, tag, attributes):
        if 'pre' == tag:
            self.pre_count += 1
        elif 'script' == tag:
            script_type = None
            for (key, value) in attributes:
                if key == 'type':
                    script_type = value
                    break
            if script_type != 'text/html':
                self.inside_script = True
        # This is no longer required as the controller can now signal the middleware to not compact the response.
        #elif 'html' == tag:
        #    # If the request doesn't contain an html tag - we can't assume it isn't inserted within a pre tag (this
        #    # happens in the disassembler.) So we only 'enable' white space removal if we see the html tag.
        #    self.pre_count = 0

        data = self.REMOVE_WHITESPACE(' ', self.get_starttag_text())
        self.output(data)

    def handle_startendtag(self, tag, attributes):
        #self.handle_starttag(tag, attributes)
        #self.handle_endtag(tag)
        data = self.REMOVE_WHITESPACE(' ', self.get_starttag_text())
        self.output(data)

    def handle_endtag(self, tag):
        if 'pre' == tag:
            self.pre_count -= 1
        elif 'script' == tag:
            self.inside_script = False
        self.output('</%s>' % tag)

    def handle_data(self, data):
        if self.inside_script:
            if self.compact_script:
                data = jsmin(data)
        elif self.pre_count == 0:
            data = self.REMOVE_WHITESPACE(' ', data)
            if data == ' ':
                return
        self.output(data)

    def handle_charref(self, name):
        self.output('&#%s;' % name)

    def handle_entityref(self, name):
        self.output('&%s;' % name)

    def handle_comment(self, data):
        return

    def handle_decl(self, data):
        self.output('<!%s>' % data)
        return

    def handle_pi(self, data):
        return
# pylint: enable=R0904

########NEW FILE########
__FILENAME__ = json_stats
# Copyright (c) 2009-2011,2013 Turbulenz Limited

from os.path import getsize as path_getsize
from zlib import compress as zlib_compress
from simplejson import loads as json_loads

__version__ = '1.0.0'

def analyse_json(filename):
    """Utility to return the ratio of key size, punctuation size, and leaf value size."""

    unique_keys = { }

    def __get_size(j):
        """Recurse to generate size."""
        (keys, punctuation, key_count) = (0, 0, 0)
        if isinstance(j, list):
            punctuation += 1 # [
            punctuation += (len(j) - 1) # ,
            for v in j:
                sub_k, sub_p, sub_count = __get_size(v)
                keys += sub_k
                punctuation += sub_p
                key_count += sub_count
            punctuation += 1 # ]
        elif isinstance(j, dict):
            punctuation += 1 # {
            if len(j.keys()) > 1:
                punctuation += (len(j.keys()) - 1) # ,
            for k, v in j.iteritems():
                if k not in unique_keys:
                    unique_keys[k] = True
                key_count += 1
                punctuation += 1 # "
                keys += len(k)
                punctuation += 1 # "
                punctuation += 1 # :
                sub_k, sub_p, sub_count = __get_size(v)
                keys += sub_k
                punctuation += sub_p
                key_count += sub_count
            punctuation += 1 # }
        elif isinstance(j, (str, unicode)):
            punctuation += 1 # "
            punctuation += 1 # "
        return (keys, punctuation, key_count)

    total_size = path_getsize(filename)
    with open(filename, 'r') as f:
        data = f.read()
        j = json_loads(data)

        (keys, punctuation, key_count) = __get_size(j)
        values = total_size - (keys + punctuation)
        unique_count = len(unique_keys.keys())
        compressed_size = len(zlib_compress(data, 6))

        return (keys, punctuation, values, key_count, unique_count, total_size, compressed_size)

########NEW FILE########
__FILENAME__ = json_utils
# Copyright (c) 2009-2013 Turbulenz Limited
"""
Utilities to manipulate JSON data.
"""

import logging
LOG = logging.getLogger('asset')

def merge_dictionaries(outof, into, prefix='\t'):
    """Merge the dictionary 'outof' into the dictionary 'into'. If matching keys are found and the value is a
    dictionary, then the sub dictionary is merged."""
    for k in outof.keys():
        if k in into:
            if isinstance(outof[k], dict):
                LOG.debug("%sMerging:%s", prefix, k)
                into[k] = merge_dictionaries(outof[k], into[k], prefix + '\t')
            else:
                LOG.debug("%sSkipping:%s", prefix, k)
        else:
            into[k] = outof[k]
    return into

def float_to_string(f):
    """Unitiliy float encoding which clamps floats close to 0 and 1 and uses %g instead of repr()."""
    if abs(f) < 1e-6:
        return "0"
    elif abs(1 - f) < 1e-6:
        return "1"
    return "%g" % (f)

def metrics(asset):
    """Generate a collection of simple size metrics about the asset."""
    def __approximate_size(num):
        """Convert a file size to human-readable form."""
        for x in [' bytes', 'KB', 'MB', 'GB', 'TB']:
            if num < 1024.0:
                return "%3.1f%s" % (num, x)
            num /= 1024.0

    def __count_nodes(nodes):
        """Recursively count the nodes."""
        num_nodes = len(nodes)
        for n in nodes.itervalues():
            if 'nodes' in n:
                num_nodes += __count_nodes(n['nodes'])
        return num_nodes

    m = { }
    for k in asset.keys():
        if isinstance(asset[k], dict):
            m['num_' + k] = len(asset[k])
        elif isinstance(asset[k], list):
            m['num_' + k] = len(asset[k])
    if 'nodes' in asset:
        m['num_nodes_recurse'] = __count_nodes(asset['nodes'])
    if 'num_geometries' in m and m['num_geometries']:
        m['total_primitives'] = 0
        m['total_positions'] = 0
        m['approximate_size'] = 0
        for _, shape in asset['geometries'].items():
            if 'surfaces' in shape:
                for _, surface in shape['surfaces'].items():
                    m['total_primitives'] += int(surface['numPrimitives'])
            else:
                if 'numPrimitives' in shape:
                    m['total_primitives'] += int(shape['numPrimitives'])
            if 'POSITION' in shape['inputs']:
                position_source = shape['inputs']['POSITION']['source']
                if position_source in shape['sources']:
                    positions = shape['sources'][position_source]
                    m['total_positions'] += len(positions['data']) / positions['stride']
            for _, source in shape['sources'].items():
                m['approximate_size'] += len(source['data']) * 4      # Assume float per vertex element attribute
            if 'triangles' in shape:
                m['approximate_size'] += len(shape['triangles']) * 2  # Assume short per index
            elif 'quads' in shape:
                m['approximate_size'] += len(shape['quads']) * 2      # Assume short per index
        m['average_primitives'] = m['total_primitives'] / m['num_geometries']
        m['average_positions'] = m['total_positions'] / m['num_geometries']
        m['approximate_readable_size'] = __approximate_size(m['approximate_size'])
    return m

def log_metrics(asset):
    """Output the metrics to the log."""
    m = metrics(asset)
    keys = m.keys()
    keys.sort()
    for k in keys:
        LOG.info('%s:%s', k, m[k])

########NEW FILE########
__FILENAME__ = profiler
# Copyright (c) 2012-2013 Turbulenz Limited
"""
Keep track of the cost of various points in code
"""

import time

############################################################

class ResultNode(object):
    def __init__(self, node_name):
        self.name = node_name
        self.duration = -1
        self.children = []

        self._start = time.time()

    def stop(self):
        self.duration = time.time() - self._start

    def add_child(self, child_result):
        if -1 != self.duration:
            raise Exception("section '%s' already stopped when trying to add "
                            "child '%s'" % (self.name, child_result.name))
        self.children.append(child_result)

############################################################

class ProfilerDummyImpl(object):
    @classmethod
    def __init__(cls):
        return
    @classmethod
    def start(cls, _):
        return
    @classmethod
    def stop(cls, _):
        return
    @classmethod
    def get_root_nodes(cls):
        return []
    @classmethod
    def dump_data(cls):
        return

############################################################

class ProfilerImpl(object):

    def __init__(self):
        self._root = ResultNode('__')
        self._current_node = self._root
        self._current_stack = []

    def start(self, section_name):
        new_child = ResultNode(section_name)
        self._current_node.add_child(new_child)

        self._current_stack.append(self._current_node)
        self._current_node = new_child

    def stop(self, section_name):

        # Unwind stack until we find the section
        while section_name != self._current_node.name:
            if len(self._current_stack) == 0:
                raise Exception("Cannot find section '%s' to stop it" \
                                    % section_name)

            self._current_node = self._current_stack.pop()

        self._current_node.stop()
        self._current_node = self._current_stack.pop()

    def get_root_nodes(self):
        return self._root.children

    def dump_data(self):

        if 0 == len(self._root.children):
            return

        def _dump_node(node, _indent = 2):
            if node.duration == -1:
                duration = "(unterminated)"
            else:
                duration = node.duration
            _indent_string = " "*_indent
            print "%s%-16s - %s%.6f" % (_indent_string, node.name, _indent_string,
                                    duration)
            for c in node.children:
                _dump_node(c, _indent+2)

        print "TimingData: "
        for r in self._root.children:
            _dump_node(r)

############################################################

class Profiler(object):

    _profiler_impl = ProfilerDummyImpl()

    @classmethod
    def enable(cls):
        if not isinstance(cls._profiler_impl, ProfilerDummyImpl):
            raise Exception("Profiler.enable_profiler() called twice")
        cls._profiler_impl = ProfilerImpl()

    @classmethod
    def start(cls, section_name):
        cls._profiler_impl.start(section_name)

    @classmethod
    def stop(cls, section_name):
        cls._profiler_impl.stop(section_name)

    @classmethod
    def get_root_nodes(cls):
        return cls._profiler_impl.get_root_nodes()

    @classmethod
    def dump_data(cls):
        cls._profiler_impl.dump_data()

############################################################

def _profiler_test():

    ##################################################

    p = ProfilerImpl()
    p.start('section1')
    p.stop('section1')
    roots = p.get_root_nodes()
    assert(1 == len(roots))
    x = roots[0]
    assert('section1' == x.name)
    assert(x.duration > 0)
    assert(0 == len(x.children))

    ##################################################

    p = ProfilerImpl()
    p.start('section1')
    p.start('section1.1')
    p.start('section1.1.1')   # unterminated
    p.start('section1.1.2')
    p.stop ('section1.1.2')
    p.stop ('section1.1')
    p.stop ('section1')
    p.start('section2')
    p.start('section2.1')
    p.stop ('section2.1')
    p.start('section2.2')
    p.stop ('section2.2')
    p.start('section2.3')
    p.stop ('section2.3')
    p.start('section2.4')
    p.stop ('section2.4')
    p.start('section2.5')
    p.stop ('section2.5')
    p.start('section2.6')
    p.stop ('section2.6')
    p.stop ('section2')

    roots = p.get_root_nodes()
    assert(2 == len(roots))

    s1 = roots[0]
    assert('section1' == s1.name)
    assert(s1.duration > 0)
    assert(1 == len(s1.children) > 0)

    s11 = s1.children[0]
    assert('section1.1' == s11.name)
    assert(1 == len(s11.children))

    s111 = s11.children[0]
    assert('section1.1.1' == s111.name)
    assert(-1 == s111.duration)
    assert(1 == len(s111.children))

    s112 = s111.children[0]
    assert('section1.1.2' == s112.name)
    assert(0 < s112.duration)
    assert(0 == len(s112.children))

    s2 = roots[1]
    assert('section2' == s2.name)
    assert(0 < s2.duration)
    assert(6 == len(s2.children))

    p.dump_data()

if __name__ == "__main__":
    exit(_profiler_test())

########NEW FILE########
__FILENAME__ = subproc
# Copyright (c) 2009-2011,2013 Turbulenz Limited

"""
Collection of utility functions for handling subprocess execution.
"""

import datetime
import subprocess

__version__ = '1.0.0'

class SubProc(object):
    """Encapsulation for running subprocesses, capturing the output and processing to return in a response."""
    def __init__(self, command, cwd=None):
        self.command = command
        self.cwd = cwd
        self.retcode = 0
        self.time_delta = datetime.timedelta()
        self.stdout_report, self.stderr_report = ('','')

    def update_command(self, command, cwd=None, env=None):
        """Set the command to execute and optionally the path to execute form."""
        self.command = command
        self.cwd = cwd

    def time_popen(self):
        """Time a subprocess command and return process retcode. This method will block until the process completes."""
        time_start = datetime.datetime.now()

        proc = subprocess.Popen(self.command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self.cwd)
        stdout_report, stderr_report = proc.communicate()
        self.retcode = proc.wait()

        time_end = datetime.datetime.now()
        time_delta = time_end - time_start

        self.time_delta += time_delta
        self.stdout_report += stdout_report
        self.stderr_report += stderr_report

        return self.retcode

    def command_str(self):
        """Generate the command string."""
        return ' '.join(self.command)

########NEW FILE########
__FILENAME__ = xml_json
# This code is based on an xml2json.py script found at:
# https://gist.github.com/raw/434945/2a0615b2bd07ece2248a968609284b3ba0d5e466/xml2json.py
#
# It has been modified to fit our package style and asset types.
# Also supports stripping out namespaces and converting values to native types.
#
# All modifications are:
# Copyright (c) 2010-2011,2013 Turbulenz Limited

from simplejson import loads as json_loads, dumps as json_dumps, encoder as json_encoder

# pylint: disable=W0404
try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    from xml.etree import ElementTree
# pylint: enable=W0404

from turbulenz_tools.tools.json2json import float_to_string

__version__ = '1.0.0'
__dependencies__ = ['turbulenz_tools.tools.json2json']

#######################################################################################################################

def to_native(a):
    """Parse the string into native types."""
    if a is None:
        return None

    try:
        int_number = int(a)
    except ValueError:
        pass
    else:
        return int_number

    try:
        float_number = float(a)
    except ValueError:
        pass
    else:
        return float_number

    parts = a.split()

    try:
        int_list = [int(x) for x in parts]
    except ValueError:
        pass
    else:
        return int_list

    try:
        float_list = [float(x) for x in parts]
    except ValueError:
        pass
    else:
        return float_list

    return a

def elem2internal(elem, strip=True, convert_types=False):
    """Convert an Element into an internal dictionary (not JSON!)."""
    if convert_types:
        _prepare = to_native
    else:
        _prepare = lambda a: a

    def _elem2internal(elem):
        d = { }
        for key, value in elem.attrib.items():
            d['@'+key] = _prepare(value)

        # loop over subelements to merge them
        for subelem in elem:
            v = _elem2internal(subelem)
            tag = subelem.tag
            value = v[tag]
            try:
                # add to existing list for this tag
                d[tag].append(value)
            except AttributeError:
                # turn existing entry into a list
                d[tag] = [d[tag], value]
            except KeyError:
                # add a new non-list entry
                d[tag] = value
        text = elem.text
        tail = elem.tail
        if strip:
            # ignore leading and trailing whitespace
            if text:
                text = text.strip()
            if tail:
                tail = tail.strip()
        text = _prepare(text)
        tail = _prepare(tail)

        if tail:
            d['#tail'] = tail

        if d:
            # use #text element if other attributes exist
            if text:
                d["#text"] = text
        else:
            # text is the value if no attributes

            # The following line used to read:
            #  >> d = text or None
            # But we now convert '0' to 0 and this resulted in None instead of 0.
            # So it has been updated to:
            d = text
        return { elem.tag: d }

    return _elem2internal(elem)

def internal2elem(pfsh, factory=ElementTree.Element):
    """Convert an internal dictionary (not JSON!) into an Element."""
    attribs = { }
    text = None
    tail = None
    sublist = [ ]
    tag = pfsh.keys()
    if len(tag) != 1:
        raise ValueError("Illegal structure with multiple tags: %s" % tag)
    tag = tag[0]
    value = pfsh[tag]
    if isinstance(value, dict):
        for k, v in value.items():
            if k[:1] == "@":
                attribs[k[1:]] = v
            elif k == "#text":
                text = v
            elif k == "#tail":
                tail = v
            elif isinstance(v, list):
                for v2 in v:
                    sublist.append(internal2elem({k:v2}, factory=factory))
            else:
                sublist.append(internal2elem({k:v}, factory=factory))
    else:
        text = value
    e = factory(tag, attribs)
    for sub in sublist:
        e.append(sub)
    e.text = text
    e.tail = tail
    return e

def elem2json(elem, strip=True, indent=0, convert_types=False):
    """Convert an ElementTree or Element into a JSON string."""
    if hasattr(elem, 'getroot'):
        elem = elem.getroot()

    internal = elem2internal(elem, strip=strip, convert_types=convert_types)

    # Module 'simplejson' has no 'encoder' member
    # pylint: disable=E1101
    json_encoder.FLOAT_REPR = float_to_string
    # pylint: enable=E1101
    if indent > 0:
        output = json_dumps(internal, sort_keys=True, indent=indent)
    else:
        output = json_dumps(internal, sort_keys=True, separators=(',', ':'))

    return output

def json2elem(json_string, factory=ElementTree.Element):
    """Convert a JSON string into an Element."""
    return internal2elem(json_loads(json_string), factory)

def xml2json(xml_string, strip=True, indent=0, convert_types=False):
    """Convert an XML string into a JSON string."""
    elem = ElementTree.fromstring(xml_string)
    return elem2json(elem, strip=strip, indent=indent, convert_types=convert_types)

def json2xml(json_string, factory=ElementTree.Element):
    """Convert a JSON string into an XML string."""
    elem = internal2elem(json_loads(json_string), factory)
    return ElementTree.tostring(elem)

########NEW FILE########
__FILENAME__ = version
# Copyright (c) 2012-2013 Turbulenz Limited

# Must be kept in sync with the version in the plugin and webgl engine
# code.  Python tools use this to stamp build products and to generate
# version checking code.
SDK_VERSION = "0.28.0.0"

########NEW FILE########
