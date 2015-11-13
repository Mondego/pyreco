__FILENAME__ = app
# Copyright (c) 2010-2011 Joshua Harlan Lifton.
# See LICENSE.txt for details.

# TODO: unit test this module

"""Configuration, initialization, and control of the Plover steno pipeline.

This module's single class, StenoEngine, encapsulates the configuration,
initialization, and control (starting and stopping) of a complete stenographic
processing pipeline, from reading stroke keys from a stenotype machine to
outputting translated English text to the screen. Configuration parameters are
read from a user-editable configuration file. In addition, application log files
are maintained by this module. This module does not provide a graphical user
interface.

"""


# Import plover modules.
import plover.config as conf
import plover.formatting as formatting
import plover.oslayer.keyboardcontrol as keyboardcontrol
import plover.steno as steno
import plover.machine.base
import plover.machine.sidewinder
import plover.steno_dictionary as steno_dictionary
import plover.steno as steno
import plover.translation as translation
from plover.dictionary.base import load_dictionary
from plover.exception import InvalidConfigurationError,DictionaryLoaderException
import plover.dictionary.json_dict as json_dict
import plover.dictionary.rtfcre_dict as rtfcre_dict
from plover.machine.registry import machine_registry, NoSuchMachineException
from plover.logger import Logger
from plover.dictionary.loading_manager import manager as dict_manager

# Because 2.7 doesn't have this yet.
class SimpleNamespace(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def __repr__(self):
        keys = sorted(self.__dict__)
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in keys)
        return "{}({})".format(type(self).__name__, ", ".join(items))


def init_engine(engine, config):
    """Initialize a StenoEngine from a config object."""
    reset_machine(engine, config)
    
    dictionary_file_names = config.get_dictionary_file_names()
    try:
        dicts = dict_manager.load(dictionary_file_names)
    except DictionaryLoaderException as e:
        raise InvalidConfigurationError(unicode(e))
    engine.get_dictionary().set_dicts(dicts)

    log_file_name = config.get_log_file_name()
    if log_file_name:
        engine.set_log_file_name(log_file_name)

    engine.enable_stroke_logging(config.get_enable_stroke_logging())
    engine.enable_translation_logging(config.get_enable_translation_logging())
    engine.set_space_placement(config.get_space_placement())
    
    engine.set_is_running(config.get_auto_start())

def reset_machine(engine, config):
    """Set the machine on the engine based on config."""
    machine_type = config.get_machine_type()
    machine_options = config.get_machine_specific_options(machine_type)
    try:
        instance = machine_registry.get(machine_type)(machine_options)
    except NoSuchMachineException as e:
        raise InvalidConfigurationError(unicode(e))
    engine.set_machine(instance)

def update_engine(engine, old, new):
    """Modify a StenoEngine using a before and after config object.
    
    Using the before and after allows this function to not make unnecessary 
    changes.
    """
    machine_type = new.get_machine_type()
    machine_options = new.get_machine_specific_options(machine_type)
    if (old.get_machine_type() != machine_type or 
        old.get_machine_specific_options(machine_type) != machine_options):
        try:
            machine_class = machine_registry.get(machine_type)
        except NoSuchMachineException as e:
            raise InvalidConfigurationError(unicode(e))
        engine.set_machine(machine_class(machine_options))

    dictionary_file_names = new.get_dictionary_file_names()
    if old.get_dictionary_file_names() != dictionary_file_names:
        try:
            dicts = dict_manager.load(dictionary_file_names)
        except DictionaryLoaderException as e:
            raise InvalidConfigurationError(unicode(e))
        engine.get_dictionary().set_dicts(dicts)

    log_file_name = new.get_log_file_name()
    if old.get_log_file_name() != log_file_name:
        engine.set_log_file_name(log_file_name)

    enable_stroke_logging = new.get_enable_stroke_logging()
    if old.get_enable_stroke_logging() != enable_stroke_logging:
        engine.enable_stroke_logging(enable_stroke_logging)

    enable_translation_logging = new.get_enable_translation_logging()
    if old.get_enable_translation_logging() != enable_translation_logging:
        engine.enable_translation_logging(enable_translation_logging)

    space_placement = new.get_space_placement()
    if old.get_space_placement() != space_placement:
        engine.set_space_placement(space_placement)

def same_thread_hook(fn, *args):
    fn(*args)

class StenoEngine(object):
    """Top-level class for using a stenotype machine for text input.

    This class combines all the non-GUI pieces needed to use a stenotype machine
    as a general purpose text entry device. The pipeline consists of the 
    following elements:

    machine: An instance of the Stenotype class from one of the submodules of 
    plover.machine. This object is responsible for monitoring a particular type 
    of hardware for stenotype output and passing that output on to the 
    translator.

    translator: An instance of the plover.steno.Translator class. This object 
    converts raw steno keys into strokes and strokes into translations. The 
    translation objects are then passed on to the formatter.

    formatter: An instance of the plover.formatting.Formatter class. This object 
    converts translation objects into printable text that can be displayed to 
    the user. Orthographic and lexical rules, such as capitalization at the 
    beginning of a sentence and pluralizing a word, are taken care of here. The 
    formatted text is then passed on to the output.

    output: An instance of plover.oslayer.keyboardcontrol.KeyboardEmulation 
    class plus a hook to the application allows output to the screen and control
    of the app with steno strokes.

    In addition to the above pieces, a logger records timestamped strokes and
    translations.

    """

    def __init__(self, thread_hook=same_thread_hook):
        """Creates and configures a single steno pipeline."""
        self.subscribers = []
        self.stroke_listeners = []
        self.is_running = False
        self.machine = None
        self.thread_hook = thread_hook

        self.translator = translation.Translator()
        self.formatter = formatting.Formatter()
        self.logger = Logger()
        self.translator.add_listener(self.logger.log_translation)
        self.translator.add_listener(self.formatter.format)
        # This seems like a reasonable number. If this becomes a problem it can
        # be parameterized.
        self.translator.set_min_undo_length(10)

        self.full_output = SimpleNamespace()
        self.command_only_output = SimpleNamespace()
        self.running_state = self.translator.get_state()
        self.set_is_running(False)

    def set_machine(self, machine):
        if self.machine:
            self.machine.remove_state_callback(self._machine_state_callback)
            self.machine.remove_stroke_callback(
                self._translator_machine_callback)
            self.machine.remove_stroke_callback(self.logger.log_stroke)
            self.machine.stop_capture()
        self.machine = machine
        if self.machine:
            self.machine.add_state_callback(self._machine_state_callback)
            self.machine.add_stroke_callback(self.logger.log_stroke)
            self.machine.add_stroke_callback(self._translator_machine_callback)
            self.machine.start_capture()
            self.set_is_running(self.is_running)
        else:
            self.set_is_running(False)

    def set_dictionary(self, d):
        self.translator.set_dictionary(d)

    def get_dictionary(self):
        return self.translator.get_dictionary()

    def set_is_running(self, value):
        self.is_running = value
        if self.is_running:
            self.translator.set_state(self.running_state)
            self.formatter.set_output(self.full_output)
        else:
            self.translator.clear_state()
            self.formatter.set_output(self.command_only_output)
        if isinstance(self.machine, plover.machine.sidewinder.Stenotype):
            self.machine.suppress_keyboard(self.is_running)
        for callback in self.subscribers:
            callback(None)

    def set_output(self, o):
        self.full_output.send_backspaces = o.send_backspaces
        self.full_output.send_string = o.send_string
        self.full_output.send_key_combination = o.send_key_combination
        self.full_output.send_engine_command = o.send_engine_command
        self.command_only_output.send_engine_command = o.send_engine_command

    def destroy(self):
        """Halts the stenography capture-translate-format-display pipeline.

        Calling this method causes all worker threads involved to terminate.
        This method should be called at least once if the start method had been
        previously called. Calling this method more than once or before the
        start method has been called has no effect.

        """
        if self.machine:
            self.machine.stop_capture()
        self.is_running = False

    def add_callback(self, callback):
        """Subscribes a function to receive changes of the is_running state.

        Arguments:

        callback -- A function that takes no arguments.

        """
        self.subscribers.append(callback)
        
    def set_log_file_name(self, filename):
        """Set the file name for log output."""
        self.logger.set_filename(filename)

    def enable_stroke_logging(self, b):
        """Turn stroke logging on or off."""
        self.logger.enable_stroke_logging(b)

    def set_space_placement(self, s):
        """Set whether spaces will be inserted before the output or after the output."""
        self.formatter.set_space_placement(s)
        
    def enable_translation_logging(self, b):
        """Turn translation logging on or off."""
        self.logger.enable_translation_logging(b)

    def add_stroke_listener(self, listener):
        self.stroke_listeners.append(listener)
        
    def remove_stroke_listener(self, listener):
        self.stroke_listeners.remove(listener)

    def _translate_stroke(self, s):
        stroke = steno.Stroke(s)
        self.translator.translate(stroke)
        for listener in self.stroke_listeners:
            listener(stroke)

    def _translator_machine_callback(self, s):
        self.thread_hook(self._translate_stroke, s)

    def _notify_listeners(self, s):
        for callback in self.subscribers:
            callback(s)

    def _machine_state_callback(self, s):
        self.thread_hook(self._notify_listeners, s)



########NEW FILE########
__FILENAME__ = config
# Copyright (c) 2010-2011 Joshua Harlan Lifton.
# See LICENSE.txt for details.

"""Configuration management."""

import ConfigParser
from ConfigParser import RawConfigParser
import os
import shutil
from cStringIO import StringIO
from plover.exception import InvalidConfigurationError
from plover.machine.registry import machine_registry
from plover.oslayer.config import ASSETS_DIR, CONFIG_DIR

SPINNER_FILE = os.path.join(ASSETS_DIR, 'spinner.gif')

# Config path.
CONFIG_FILE = os.path.join(CONFIG_DIR, 'plover.cfg')

# General configuration sections, options and defaults.
MACHINE_CONFIG_SECTION = 'Machine Configuration'
MACHINE_TYPE_OPTION = 'machine_type'
DEFAULT_MACHINE_TYPE = 'NKRO Keyboard'
MACHINE_AUTO_START_OPTION = 'auto_start'
DEFAULT_MACHINE_AUTO_START = False

DICTIONARY_CONFIG_SECTION = 'Dictionary Configuration'
DICTIONARY_FILE_OPTION = 'dictionary_file'
DEFAULT_DICTIONARY_FILE = os.path.join(CONFIG_DIR, 'dict.json')

LOGGING_CONFIG_SECTION = 'Logging Configuration'
LOG_FILE_OPTION = 'log_file'
DEFAULT_LOG_FILE = os.path.join(CONFIG_DIR, 'plover.log')
ENABLE_STROKE_LOGGING_OPTION = 'enable_stroke_logging'
DEFAULT_ENABLE_STROKE_LOGGING = True
ENABLE_TRANSLATION_LOGGING_OPTION = 'enable_translation_logging'
DEFAULT_ENABLE_TRANSLATION_LOGGING = True

STROKE_DISPLAY_SECTION = 'Stroke Display'
STROKE_DISPLAY_SHOW_OPTION = 'show'
DEFAULT_STROKE_DISPLAY_SHOW = False
STROKE_DISPLAY_ON_TOP_OPTION = 'on_top'
DEFAULT_STROKE_DISPLAY_ON_TOP = True
STROKE_DISPLAY_STYLE_OPTION = 'style'
DEFAULT_STROKE_DISPLAY_STYLE = 'Paper'
STROKE_DISPLAY_X_OPTION = 'x'
DEFAULT_STROKE_DISPLAY_X = -1
STROKE_DISPLAY_Y_OPTION = 'y'
DEFAULT_STROKE_DISPLAY_Y = -1

OUTPUT_CONFIG_SECTION = 'Output Configuration'
OUTPUT_CONFIG_SPACE_PLACEMENT_OPTION = 'space_placement'
DEFAULT_OUTPUT_CONFIG_SPACE_PLACEMENT = 'Before Output'

CONFIG_FRAME_SECTION = 'Config Frame'
CONFIG_FRAME_X_OPTION = 'x'
DEFAULT_CONFIG_FRAME_X = -1
CONFIG_FRAME_Y_OPTION = 'y'
DEFAULT_CONFIG_FRAME_Y = -1
CONFIG_FRAME_WIDTH_OPTION = 'width'
DEFAULT_CONFIG_FRAME_WIDTH = -1
CONFIG_FRAME_HEIGHT_OPTION = 'height'
DEFAULT_CONFIG_FRAME_HEIGHT = -1

MAIN_FRAME_SECTION = 'Main Frame'
MAIN_FRAME_X_OPTION = 'x'
DEFAULT_MAIN_FRAME_X = -1
MAIN_FRAME_Y_OPTION = 'y'
DEFAULT_MAIN_FRAME_Y = -1

TRANSLATION_FRAME_SECTION = 'Translation Frame'
TRANSLATION_FRAME_X_OPTION = 'x'
DEFAULT_TRANSLATION_FRAME_X = -1
TRANSLATION_FRAME_Y_OPTION = 'y'
DEFAULT_TRANSLATION_FRAME_Y = -1

LOOKUP_FRAME_SECTION = 'Lookup Frame'
LOOKUP_FRAME_X_OPTION = 'x'
DEFAULT_LOOKUP_FRAME_X = -1
LOOKUP_FRAME_Y_OPTION = 'y'
DEFAULT_LOOKUP_FRAME_Y = -1

DICTIONARY_EDITOR_FRAME_SECTION = 'Dictionary Editor Frame'
DICTIONARY_EDITOR_FRAME_X_OPTION = 'x'
DEFAULT_DICTIONARY_EDITOR_FRAME_X = -1
DICTIONARY_EDITOR_FRAME_Y_OPTION = 'y'
DEFAULT_DICTIONARY_EDITOR_FRAME_Y = -1

SERIAL_CONFIG_FRAME_SECTION = 'Serial Config Frame'
SERIAL_CONFIG_FRAME_X_OPTION = 'x'
DEFAULT_SERIAL_CONFIG_FRAME_X = -1
SERIAL_CONFIG_FRAME_Y_OPTION = 'y'
DEFAULT_SERIAL_CONFIG_FRAME_Y = -1

KEYBOARD_CONFIG_FRAME_SECTION = 'Keyboard Config Frame'
KEYBOARD_CONFIG_FRAME_X_OPTION = 'x'
DEFAULT_KEYBOARD_CONFIG_FRAME_X = -1
KEYBOARD_CONFIG_FRAME_Y_OPTION = 'y'
DEFAULT_KEYBOARD_CONFIG_FRAME_Y = -1

# Dictionary constants.
JSON_EXTENSION = '.json'
RTF_EXTENSION = '.rtf'

# Logging constants.
LOG_EXTENSION = '.log'

# TODO: Unit test this class

class Config(object):

    def __init__(self):
        self._config = RawConfigParser()
        # A convenient place for other code to store a file name.
        self.target_file = None

    def load(self, fp):
        self._config = RawConfigParser()
        try:
            self._config.readfp(fp)
        except ConfigParser.Error as e:
            raise InvalidConfigurationError(str(e))

    def clear(self):
        self._config = RawConfigParser()

    def save(self, fp):
        self._config.write(fp)

    def clone(self):
        f = StringIO()
        self.save(f)
        c = Config()
        f.seek(0, 0)
        c.load(f)
        return c

    def set_machine_type(self, machine_type):
        self._set(MACHINE_CONFIG_SECTION, MACHINE_TYPE_OPTION, 
                         machine_type)

    def get_machine_type(self):
        return self._get(MACHINE_CONFIG_SECTION, MACHINE_TYPE_OPTION, 
                         DEFAULT_MACHINE_TYPE)

    def set_machine_specific_options(self, machine_name, options):
        if self._config.has_section(machine_name):
            self._config.remove_section(machine_name)
        self._config.add_section(machine_name)
        for k, v in options.items():
            self._config.set(machine_name, k, str(v))

    def get_machine_specific_options(self, machine_name):
        def convert(p, v):
            try:
                return p[1](v)
            except ValueError:
                return p[0]
        machine = machine_registry.get(machine_name)
        info = machine.get_option_info()
        defaults = {k: v[0] for k, v in info.items()}
        if self._config.has_section(machine_name):
            options = {o: self._config.get(machine_name, o) 
                       for o in self._config.options(machine_name)
                       if o in info}
            options = {k: convert(info[k], v) for k, v in options.items()}
            defaults.update(options)
        return defaults

    def set_dictionary_file_names(self, filenames):
        if self._config.has_section(DICTIONARY_CONFIG_SECTION):
            self._config.remove_section(DICTIONARY_CONFIG_SECTION)
        self._config.add_section(DICTIONARY_CONFIG_SECTION)
        for ordinal, filename in enumerate(filenames, start=1):
            option = DICTIONARY_FILE_OPTION + str(ordinal)
            self._config.set(DICTIONARY_CONFIG_SECTION, option, filename)

    def get_dictionary_file_names(self):
        filenames = []
        if self._config.has_section(DICTIONARY_CONFIG_SECTION):
            options = filter(lambda x: x.startswith(DICTIONARY_FILE_OPTION),
                             self._config.options(DICTIONARY_CONFIG_SECTION))
            options.sort(key=_dict_entry_key)
            filenames = [self._config.get(DICTIONARY_CONFIG_SECTION, o) 
                         for o in options]
        if not filenames or filenames == ['dict.json']:
            filenames = [DEFAULT_DICTIONARY_FILE]
        return filenames

    def set_log_file_name(self, filename):
        self._set(LOGGING_CONFIG_SECTION, LOG_FILE_OPTION, filename)

    def get_log_file_name(self):
        return self._get(LOGGING_CONFIG_SECTION, LOG_FILE_OPTION, 
                         DEFAULT_LOG_FILE)

    def set_enable_stroke_logging(self, log):
        self._set(LOGGING_CONFIG_SECTION, ENABLE_STROKE_LOGGING_OPTION, log)

    def get_enable_stroke_logging(self):
        return self._get_bool(LOGGING_CONFIG_SECTION, 
                              ENABLE_STROKE_LOGGING_OPTION, 
                              DEFAULT_ENABLE_STROKE_LOGGING)

    def set_enable_translation_logging(self, log):
      self._set(LOGGING_CONFIG_SECTION, ENABLE_TRANSLATION_LOGGING_OPTION, log)

    def get_enable_translation_logging(self):
        return self._get_bool(LOGGING_CONFIG_SECTION, 
                              ENABLE_TRANSLATION_LOGGING_OPTION, 
                              DEFAULT_ENABLE_TRANSLATION_LOGGING)

    def set_auto_start(self, b):
        self._set(MACHINE_CONFIG_SECTION, MACHINE_AUTO_START_OPTION, b)

    def get_auto_start(self):
        return self._get_bool(MACHINE_CONFIG_SECTION, MACHINE_AUTO_START_OPTION, 
                              DEFAULT_MACHINE_AUTO_START)

    def set_show_stroke_display(self, b):
        self._set(STROKE_DISPLAY_SECTION, STROKE_DISPLAY_SHOW_OPTION, b)

    def get_show_stroke_display(self):
        return self._get_bool(STROKE_DISPLAY_SECTION, 
            STROKE_DISPLAY_SHOW_OPTION, DEFAULT_STROKE_DISPLAY_SHOW)

    def get_space_placement(self):
        return self._get(OUTPUT_CONFIG_SECTION, OUTPUT_CONFIG_SPACE_PLACEMENT_OPTION, 
                         DEFAULT_OUTPUT_CONFIG_SPACE_PLACEMENT)

    def set_space_placement(self, s):
        self._set(OUTPUT_CONFIG_SECTION, OUTPUT_CONFIG_SPACE_PLACEMENT_OPTION, s)

    def set_stroke_display_on_top(self, b):
        self._set(STROKE_DISPLAY_SECTION, STROKE_DISPLAY_ON_TOP_OPTION, b)

    def get_stroke_display_on_top(self):
        return self._get_bool(STROKE_DISPLAY_SECTION, 
            STROKE_DISPLAY_ON_TOP_OPTION, DEFAULT_STROKE_DISPLAY_ON_TOP)

    def set_stroke_display_style(self, s):
        self._set(STROKE_DISPLAY_SECTION, STROKE_DISPLAY_STYLE_OPTION, s)

    def get_stroke_display_style(self):
        return self._get(STROKE_DISPLAY_SECTION, STROKE_DISPLAY_STYLE_OPTION, 
                         DEFAULT_STROKE_DISPLAY_STYLE)

    def set_stroke_display_x(self, x):
        self._set(STROKE_DISPLAY_SECTION, STROKE_DISPLAY_X_OPTION, x)

    def get_stroke_display_x(self):
        return self._get_int(STROKE_DISPLAY_SECTION, STROKE_DISPLAY_X_OPTION, 
                             DEFAULT_STROKE_DISPLAY_X)

    def set_stroke_display_y(self, y):
        self._set(STROKE_DISPLAY_SECTION, STROKE_DISPLAY_Y_OPTION, y)

    def get_stroke_display_y(self):
        return self._get_int(STROKE_DISPLAY_SECTION, STROKE_DISPLAY_Y_OPTION, 
                             DEFAULT_STROKE_DISPLAY_Y)

    def set_config_frame_x(self, x):
        self._set(CONFIG_FRAME_SECTION, CONFIG_FRAME_X_OPTION, x)
        
    def get_config_frame_x(self):
        return self._get_int(CONFIG_FRAME_SECTION, CONFIG_FRAME_X_OPTION,
                             DEFAULT_CONFIG_FRAME_X)

    def set_config_frame_y(self, y):
        self._set(CONFIG_FRAME_SECTION, CONFIG_FRAME_Y_OPTION, y)
    
    def get_config_frame_y(self):
        return self._get_int(CONFIG_FRAME_SECTION, CONFIG_FRAME_Y_OPTION,
                             DEFAULT_CONFIG_FRAME_Y)

    def set_config_frame_width(self, width):
        self._set(CONFIG_FRAME_SECTION, CONFIG_FRAME_WIDTH_OPTION, width)

    def get_config_frame_width(self):
        return self._get_int(CONFIG_FRAME_SECTION, CONFIG_FRAME_WIDTH_OPTION,
                             DEFAULT_CONFIG_FRAME_WIDTH)

    def set_config_frame_height(self, height):
        self._set(CONFIG_FRAME_SECTION, CONFIG_FRAME_HEIGHT_OPTION, height)

    def get_config_frame_height(self):
        return self._get_int(CONFIG_FRAME_SECTION, CONFIG_FRAME_HEIGHT_OPTION,
                             DEFAULT_CONFIG_FRAME_HEIGHT)

    def set_main_frame_x(self, x):
        self._set(MAIN_FRAME_SECTION, MAIN_FRAME_X_OPTION, x)
    
    def get_main_frame_x(self):
        return self._get_int(MAIN_FRAME_SECTION, MAIN_FRAME_X_OPTION,
                             DEFAULT_MAIN_FRAME_X)

    def set_main_frame_y(self, y):
        self._set(MAIN_FRAME_SECTION, MAIN_FRAME_Y_OPTION, y)

    def get_main_frame_y(self):
        return self._get_int(MAIN_FRAME_SECTION, MAIN_FRAME_Y_OPTION,
                             DEFAULT_MAIN_FRAME_Y)

    def set_translation_frame_x(self, x):
        self._set(TRANSLATION_FRAME_SECTION, TRANSLATION_FRAME_X_OPTION, x)
    
    def get_translation_frame_x(self):
        return self._get_int(TRANSLATION_FRAME_SECTION, 
                             TRANSLATION_FRAME_X_OPTION,
                             DEFAULT_TRANSLATION_FRAME_X)

    def set_translation_frame_y(self, y):
        self._set(TRANSLATION_FRAME_SECTION, TRANSLATION_FRAME_Y_OPTION, y)

    def get_translation_frame_y(self):
        return self._get_int(TRANSLATION_FRAME_SECTION, 
                             TRANSLATION_FRAME_Y_OPTION,
                             DEFAULT_TRANSLATION_FRAME_Y)
                             
    def set_lookup_frame_x(self, x):
        self._set(LOOKUP_FRAME_SECTION, LOOKUP_FRAME_X_OPTION, x)
    
    def get_lookup_frame_x(self):
        return self._get_int(LOOKUP_FRAME_SECTION, 
                             LOOKUP_FRAME_X_OPTION,
                             DEFAULT_LOOKUP_FRAME_X)

    def set_lookup_frame_y(self, y):
        self._set(LOOKUP_FRAME_SECTION, LOOKUP_FRAME_Y_OPTION, y)

    def get_lookup_frame_y(self):
        return self._get_int(LOOKUP_FRAME_SECTION, 
                             LOOKUP_FRAME_Y_OPTION,
                             DEFAULT_LOOKUP_FRAME_Y)

    def set_dictionary_editor_frame_x(self, x):
        self._set(DICTIONARY_EDITOR_FRAME_SECTION, DICTIONARY_EDITOR_FRAME_X_OPTION, x)

    def get_dictionary_editor_frame_x(self):
        return self._get_int(DICTIONARY_EDITOR_FRAME_SECTION,
                             DICTIONARY_EDITOR_FRAME_X_OPTION,
                             DEFAULT_DICTIONARY_EDITOR_FRAME_X)

    def set_dictionary_editor_frame_y(self, y):
        self._set(DICTIONARY_EDITOR_FRAME_SECTION, DICTIONARY_EDITOR_FRAME_Y_OPTION, y)

    def get_dictionary_editor_frame_y(self):
        return self._get_int(DICTIONARY_EDITOR_FRAME_SECTION,
                             DICTIONARY_EDITOR_FRAME_Y_OPTION,
                             DEFAULT_DICTIONARY_EDITOR_FRAME_Y)
    
    def set_serial_config_frame_x(self, x):
        self._set(SERIAL_CONFIG_FRAME_SECTION, SERIAL_CONFIG_FRAME_X_OPTION, x)
    
    def get_serial_config_frame_x(self):
        return self._get_int(SERIAL_CONFIG_FRAME_SECTION, 
                             SERIAL_CONFIG_FRAME_X_OPTION,
                             DEFAULT_SERIAL_CONFIG_FRAME_X)

    def set_serial_config_frame_y(self, y):
        self._set(SERIAL_CONFIG_FRAME_SECTION, SERIAL_CONFIG_FRAME_Y_OPTION, y)

    def get_serial_config_frame_y(self):
        return self._get_int(SERIAL_CONFIG_FRAME_SECTION, 
                             SERIAL_CONFIG_FRAME_Y_OPTION,
                             DEFAULT_SERIAL_CONFIG_FRAME_Y)

    def set_keyboard_config_frame_x(self, x):
        self._set(KEYBOARD_CONFIG_FRAME_SECTION, KEYBOARD_CONFIG_FRAME_X_OPTION, 
                  x)
    
    def get_keyboard_config_frame_x(self):
        return self._get_int(KEYBOARD_CONFIG_FRAME_SECTION, 
                             KEYBOARD_CONFIG_FRAME_X_OPTION,
                             DEFAULT_KEYBOARD_CONFIG_FRAME_X)

    def set_keyboard_config_frame_y(self, y):
        self._set(KEYBOARD_CONFIG_FRAME_SECTION, KEYBOARD_CONFIG_FRAME_Y_OPTION, 
                  y)

    def get_keyboard_config_frame_y(self):
        return self._get_int(KEYBOARD_CONFIG_FRAME_SECTION, 
                             KEYBOARD_CONFIG_FRAME_Y_OPTION,
                             DEFAULT_KEYBOARD_CONFIG_FRAME_Y)

    def _set(self, section, option, value):
        if not self._config.has_section(section):
            self._config.add_section(section)
        self._config.set(section, option, str(value))

    def _get(self, section, option, default):
        if self._config.has_option(section, option):
            return self._config.get(section, option)
        return default

    def _get_bool(self, section, option, default):
        try:
            if self._config.has_option(section, option):
                return self._config.getboolean(section, option)
        except ValueError:
            pass
        return default

    def _get_int(self, section, option, default):
        try:
            if self._config.has_option(section, option):
                return self._config.getint(section, option)
        except ValueError:
            pass
        return default
        

def _dict_entry_key(s):
    try:
        return int(s[len(DICTIONARY_FILE_OPTION):])
    except ValueError:
        return -1

########NEW FILE########
__FILENAME__ = base
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

# TODO: maybe move this code into the StenoDictionary itself. The current saver 
# structure is odd and awkward.
# TODO: write tests for this file

"""Common elements to all dictionary formats."""

from os.path import splitext
import shutil
import threading

import plover.dictionary.json_dict as json_dict
import plover.dictionary.rtfcre_dict as rtfcre_dict
from plover.config import JSON_EXTENSION, RTF_EXTENSION, CONFIG_DIR
from plover.exception import DictionaryLoaderException

dictionaries = {
    JSON_EXTENSION.lower(): json_dict,
    RTF_EXTENSION.lower(): rtfcre_dict,
}

def load_dictionary(filename):
    """Load a dictionary from a file."""
    extension = splitext(filename)[1].lower()
    
    try:
        dict_type = dictionaries[extension]
    except KeyError:
        raise DictionaryLoaderException(
            'Unsupported extension for dictionary: %s. Supported extensions: %s' %
            (extension, ', '.join(dictionaries.keys())))

    loader = dict_type.load_dictionary

    try:
        with open(filename, 'rb') as f:
            d = loader(f.read())
    except IOError as e:
        raise DictionaryLoaderException(unicode(e))
        
    d.save = ThreadedSaver(d, filename, dict_type.save_dictionary)
    return d

def save_dictionary(d, filename, saver):
    # Write the new file to a temp location.
    tmp = filename + '.tmp'
    with open(tmp, 'wb') as fp:
        saver(d, fp)

    # Then move the new file to the final location.
    shutil.move(tmp, filename)
    
class ThreadedSaver(object):
    """A callable that saves a dictionary in the background.
    
    Also makes sure that there is only one active call at a time.
    """
    def __init__(self, d, filename, saver):
        self.d = d
        self.filename = filename
        self.saver = saver
        self.lock = threading.Lock()
        
    def __call__(self):
        t = threading.Thread(target=self.save)
        t.start()
        
    def save(self):
        with self.lock:
            save_dictionary(self.d, self.filename, self.saver)

########NEW FILE########
__FILENAME__ = json_dict
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

"""Parsing a json formatted dictionary.

"""

from plover.steno_dictionary import StenoDictionary
from plover.steno import normalize_steno
from plover.exception import DictionaryLoaderException

try:
    import simplejson as json
except ImportError:
    import json
    

def load_dictionary(data):
    """Load a json dictionary from a string."""

    def h(pairs):
        return StenoDictionary((normalize_steno(x[0]), x[1]) for x in pairs)

    try:
        try:
            return json.loads(data, object_pairs_hook=h)
        except UnicodeDecodeError:
            return json.loads(data, 'latin-1', object_pairs_hook=h)
    except ValueError:
        raise DictionaryLoaderException('Dictionary is not valid json.')
        
# TODO: test this
def save_dictionary(d, fp):
    d = dict(('/'.join(k), v) for k, v in d.iteritems())
    json.dump(d, fp, sort_keys=True, indent=0, separators=(',', ': '))

########NEW FILE########
__FILENAME__ = loading_manager
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

"""Centralized place for dictionary loading operation."""

import threading
from plover.dictionary.base import load_dictionary
from plover.exception import DictionaryLoaderException

class DictionaryLoadingManager(object):
    def __init__(self):
        self.dictionaries = {}
        
    def start_loading(self, filename):
        if filename in self.dictionaries:
            return self.dictionaries[filename]
        op = DictionaryLoadingOperation(filename)
        self.dictionaries[filename] = op
        return op
        
    def load(self, filenames):
        self.dictionaries = {f: self.start_loading(f) for f in filenames}
        # Result must be in order given so can't just use values().
        ops = [self.dictionaries[f] for f in filenames]
        results = [op.get() for op in ops]
        dicts = []
        for d, e in results:
            if e:
                raise e
            dicts.append(d)
        return dicts
        
        
class DictionaryLoadingOperation(object):
    def __init__(self, filename):
        self.loading_thread = threading.Thread(target=self.load)
        self.filename = filename
        self.exception = None
        self.dictionary = None
        self.loading_thread.start()
        
    def load(self):
        try:
            self.dictionary = load_dictionary(self.filename)
            self.dictionary.set_path(self.filename)
        except DictionaryLoaderException as e:
            self.exception = e
        
    def get(self):
        self.loading_thread.join()
        return self.dictionary, self.exception

manager = DictionaryLoadingManager()

########NEW FILE########
__FILENAME__ = rtfcre_dict
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.
#
# TODO: Convert non-ascii characters to UTF8
# TODO: What does ^ mean in Eclipse?
# TODO: What does #N mean in Eclipse?
# TODO: convert supported commands from Eclipse

"""Parsing an RTF/CRE dictionary.

RTF/CRE spec:
http://www.legalxml.org/workgroups/substantive/transcripts/cre-spec.htm

"""

import inspect
import re
from plover.steno import normalize_steno
from plover.steno_dictionary import StenoDictionary
# TODO: Move dictionary format somewhere more caninical than formatting.
from plover.formatting import META_RE

# A regular expression to capture an individual entry in the dictionary.
DICT_ENTRY_PATTERN = re.compile(r'(?s)(?<!\\){\\\*\\cxs (?P<steno>[^}]+)}' + 
                                r'(?P<translation>.*?)(?:(?<!\\)(?:\r\n|\n))*?'+
                                r'(?=(?:(?<!\\){\\\*\\cxs [^}]+})|' +
                                r'(?:(?:(?<!\\)(?:\r\n|\n)\s*)*}\s*\Z))')

class TranslationConverter(object):
    """Convert an RTF/CRE translation into plover's internal format."""
    
    def __init__(self, styles={}):
        self.styles = styles
        
        def linenumber(f):
            return f[1].im_func.func_code.co_firstlineno
        
        handler_funcs = inspect.getmembers(self, inspect.ismethod)
        handler_funcs.sort(key=linenumber)
        handlers = [self._make_re_handler(f.__doc__, f)
                    for name, f in handler_funcs 
                    if name.startswith('_re_handle_')]
        handlers.append(self._match_nested_command_group)
        def handler(s, pos):
            for handler in handlers:
                result = handler(s, pos)
                if result:
                    return result
            return None
        self._handler = handler
        self._command_pattern = re.compile(
            r'(\\\*)?\\([a-z]+)(-?[0-9]+)?[ ]?')
        self._multiple_whitespace_pattern = re.compile(r'([ ]{2,})')
        # This poorly named variable indicates whether the current context is
        # one where commands can be inserted (True) or not (False).
        self._whitespace = True
    
    def _make_re_handler(self, pattern, f):
        pattern = re.compile(pattern)
        def handler(s, pos):
            match = pattern.match(s, pos)
            if match:
                newpos = match.end()
                result = f(match)
                return (newpos, result)
            return None
        return handler

    def _re_handle_escapedchar(self, m):
        r'\\([-\\{}])'
        return m.group(1)
        
    def _re_handle_hardspace(self, m):
        r'\\~'
        return '{^ ^}'
        
    def _re_handle_dash(self, m):
        r'\\_'
        return '-'
        
    def _re_handle_escaped_newline(self, m):
        r'\\\r|\\\n'
        return '{#Return}{#Return}'
        
    def _re_handle_infix(self, m):
        r'\\cxds ([^{}\\\r\n]+)\\cxds ?'
        return '{^%s^}' % m.group(1)
        
    def _re_handle_suffix(self, m):
        r'\\cxds ([^{}\\\r\n ]+)'
        return '{^%s}' % m.group(1)

    def _re_handle_prefix(self, m):
        r'([^{}\\\r\n ]+)\\cxds ?'
        return '{%s^}' % m.group(1)

    def _re_handle_commands(self, m):
        r'(\\\*)?\\([a-z]+)(-?[0-9]+)? ?'
        
        ignore = bool(m.group(1))
        command = m.group(2)
        arg = m.group(3)
        if arg:
            arg = int(arg)
        
        if command == 'cxds':
            return '{^}'
        
        if command == 'cxfc':
            return '{-|}'

        if command == 'cxfl':
            return '{>}'

        if command == 'par':
            self.seen_par = True
            return '{#Return}{#Return}'
            
        if command == 's':
            result = []
            if not self.seen_par:
                result.append('{#Return}{#Return}')
            style_name = self.styles.get(arg, '')
            if style_name.startswith('Contin'):
                result.append('{^    ^}')
            return ''.join(result)

        # Unrecognized commands are ignored.
        return ''

    def _re_handle_simple_command_group(self, m):
        r'{(\\\*)?\\([a-z]+)(-?[0-9]+)?[ ]?([^{}]*)}'
        
        ignore = bool(m.group(1))
        command = m.group(2)
        contents = m.group(4)
        if contents is None:
            contents = ''

        if command == 'cxstit':
            # Plover doesn't support stitching.
            return self(contents)
        
        if command == 'cxfing':
            prev = self._whitespace
            self._whitespace = False
            result = '{&' + contents + '}'
            self._whitespace = prev
            return result
            
        if command == 'cxp':
            prev = self._whitespace
            self._whitespace = False
            contents = self(contents)
            if contents is None:
                return None
            self._whitespace = prev
            stripped = contents.strip()
            if stripped in ['.', '!', '?', ',', ';', ':']:
                return '{' + stripped + '}'
            if stripped == "'":
                return "{^'}"
            if stripped in ['-', '/']:
                return '{^' + contents + '^}'
            # Show unknown punctuation as given.
            return '{^' + contents + '^}'
        
        if command == 'cxsvatdictflags' and 'N' in contents:
            return '{-|}'
        
        # unrecognized commands
        if ignore:
            return ''
        else:
            return self(contents)

    def _re_handle_eclipse_command(self, m):
        r'({[^\\][^{}]*})'
        return m.group()

    # caseCATalyst doesn't put punctuation in \cxp so we will treat any 
    # isolated punctuation at the beginning of the translation as special.
    def _re_handle_punctuation(self, m):
        r'^([.?!:;,])(?=\s|$)'
        if self._whitespace:
            result = '{%s}' % m.group(1)
        else:
            result = m.group(1)
        return result

    def _re_handle_text(self, m):
        r'[^{}\\\r\n]+'
        text = m.group()
        if self._whitespace:
            text = self._multiple_whitespace_pattern.sub(r'{^\1^}', text)
        return text

    def _get_matching_bracket(self, s, pos):
        if s[pos] != '{':
            return None
        end = len(s)
        depth = 1
        startpos = pos
        pos += 1
        while pos != end:
            c = s[pos]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
            if depth == 0:
                break
            pos += 1
        if pos < end and s[pos] == '}':
            return pos
        return None

    def _get_command(self, s, pos):
        return self._command_pattern.match(s, pos)

    def _match_nested_command_group(self, s, pos):
        startpos = pos
        endpos = self._get_matching_bracket(s, pos)
        if endpos is None:
            return None

        command_match = self._get_command(s, startpos + 1)
        if command_match is None:
            return None

        ignore = bool(command_match.group(1))
        command = command_match.group(2)
        
        if command == 'cxconf':
            pos = command_match.end()
            last = ''
            while pos < endpos:
                if s[pos] in ['[', '|', ']']:
                    pos += 1
                    continue
                if s[pos] == '{':
                    command_match = self._get_command(s, pos + 1)
                    if command_match is None:
                        return None
                    if command_match.group(2) != 'cxc':
                        return None
                    cxc_end = self._get_matching_bracket(s, pos)
                    if cxc_end is None:
                        return None
                    last = s[command_match.end():cxc_end]
                    pos = cxc_end + 1
                    continue
                return None
            return (endpos + 1, self(last))
            
        if ignore:
            return (endpos + 1, '')
        else:
            return (endpos + 1, self(s[command_match.end():endpos]))

    def __call__(self, s):
        self.seen_par = False
        
        pos = 0
        tokens = []
        handler = self._handler
        end = len(s)
        while pos != end:
            result = handler(s, pos)
            if result is None:
                return None
            pos = result[0]
            token = result[1]
            if token is None:
                return None
            tokens.append(token)
        return ''.join(tokens)

STYLESHEET_RE = re.compile(r'(?s){\\s([0-9]+).*?((?:\b\w+\b\s*)+);}')

def load_stylesheet(s):
    """Returns a dictionary mapping a number to a style name."""
    return dict((int(k), v) for k, v in STYLESHEET_RE.findall(s))

def load_dictionary(s):
    """Load an RTF/CRE dictionary."""
    styles = load_stylesheet(s)
    d = {}
    converter = TranslationConverter(styles)
    for m in DICT_ENTRY_PATTERN.finditer(s):
        steno = normalize_steno(m.group('steno'))
        translation = m.group('translation')
        converted = converter(translation)
        if converted is not None:
            d[steno] = converted
    return StenoDictionary(d)


HEADER = ("{\\rtf1\\ansi{\\*\\cxrev100}\\cxdict{\\*\\cxsystem Plover}" +
          "{\\stylesheet{\\s0 Normal;}}\r\n")

def format_translation(t):
    t = ' '.join([x.strip() for x in META_RE.findall(t) if x.strip()])
    
    t = re.sub(r'{\.}', '{\\cxp. }', t)
    t = re.sub(r'{!}', '{\\cxp! }', t)
    t = re.sub(r'{\?}', '{\\cxp? }', t)
    t = re.sub(r'{\,}', '{\\cxp, }', t)
    t = re.sub(r'{:}', '{\\cxp: }', t)
    t = re.sub(r'{;}', '{\\cxp; }', t)
    t = re.sub(r'{\^}', '\\cxds ', t)
    t = re.sub(r'{\^([^^}]*)}', '\\cxds \\1', t)
    t = re.sub(r'{([^^}]*)\^}', '\\1\\cxds ', t)
    t = re.sub(r'{\^([^^}]*)\^}', '\\cxds \\1\\cxds ', t)
    t = re.sub(r'{-\|}', '\\cxfc ', t)
    t = re.sub(r'{>}', '\\cxfls ', t)
    t = re.sub(r'{ }', ' ', t)
    t = re.sub(r'{&([^}]+)}', '{\\cxfing \\1}', t)
    t = re.sub(r'{#([^}]+)}', '\\{#\\1\\}', t)
    t = re.sub(r'{PLOVER:([a-zA-Z]+)}', '\\{PLOVER:\\1\\}', t)
    t = re.sub(r'\\"', '"', t)
    
    return t
    

# TODO: test this
def save_dictionary(d, fp):
    fp.write(HEADER)

    for s, t in d.items():
        s = '/'.join(s)
        t = format_translation(t)
        entry = "{\\*\\cxs %s}%s\r\n" % (s, t)
        fp.write(entry)

    fp.write("}\r\n")

########NEW FILE########
__FILENAME__ = test_default_dict
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

import json
import unittest

DICT_PATH='plover/assets/dict.json'

class TestCase(unittest.TestCase):
    
    def test_no_duplicates(self):
        def read_key_pairs(pairs):
            d = {}
            for key, value in pairs:
                holder = []
                if key in d:
                    holder = d[key]
                else:
                    d[key] = holder
                holder.append(value)
            return d
            
        d = json.load(open(DICT_PATH), object_pairs_hook=read_key_pairs)
        
        msg_list = []
        has_duplicate = False
        for key, value_list in d.items():
            if len(value_list) > 1:
                has_duplicate = True
                msg_list.append('key: %s\n' % key)
                for value in value_list:
                    msg_list.append('%s\n' % value)
        msg = ''.join(msg_list)
        self.assertFalse(has_duplicate, msg)

########NEW FILE########
__FILENAME__ = test_json_dict
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

"""Unit tests for json.py."""

import unittest
from json_dict import load_dictionary
from base import DictionaryLoaderException

class JsonDictionaryTestCase(unittest.TestCase):
    
    def test_load_dictionary(self):
        def assertEqual(a, b):
            self.assertEqual(a._dict, b)

        assertEqual(load_dictionary('{"S": "a"}'), {('S',): 'a'})
        assertEqual(load_dictionary('{"S": "\xc3\xb1"}'), {('S',): u'\xf1'})
        assertEqual(load_dictionary('{"S": "\xf1"}'), {('S',): u'\xf1'})
        
        with self.assertRaises(DictionaryLoaderException):
            load_dictionary('foo')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_loading_manager
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

"""Tests for loading_manager.py."""

from collections import defaultdict
import unittest
from mock import patch
import plover.dictionary.loading_manager as loading_manager


class DictionaryLoadingManagerTestCase(unittest.TestCase):

    def test_loading(self):
        class MockLoader(object):
            def __init__(self, files):
                self.files = files
                self.load_counts = defaultdict(int)
                
            def __call__(self, filename):
                self.load_counts[filename] += 1
                return self.files[filename]
                
        files = {c: c * 5 for c in [chr(ord('a') + i) for i in range(10)]}
        loader = MockLoader(files)
        with patch('plover.dictionary.loading_manager.load_dictionary', loader):
            manager = loading_manager.DictionaryLoadingManager()
            manager.start_loading('a')
            manager.start_loading('b')
            results = manager.load(['c', 'b'])
            # Returns the right values in the right order.
            self.assertEqual(results, ['ccccc', 'bbbbb'])
            # Only loaded the files once.
            self.assertTrue(all(x == 1 for x in loader.load_counts.values()))
            # Dropped superfluous files.
            self.assertEqual(['b', 'c'], sorted(manager.dictionaries.keys()))


if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_rtfcre_dict
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

from plover.dictionary.rtfcre_dict import load_dictionary, TranslationConverter, format_translation, save_dictionary
import mock
import re
import unittest
from cStringIO import StringIO

class TestCase(unittest.TestCase):
    
    def test_converter(self):
        styles = {1: 'Normal', 2: 'Continuation'}
        
        convert = TranslationConverter(styles)
        
        cases = (
        
        ('', ''),
        (r'\-', '-'),
        (r'\\', '\\'),
        (r'\{', '{'),
        (r'\}', '}'),
        (r'\~', '{^ ^}'),
        (r'\_', '-'),
        ('\\\r', '{#Return}{#Return}'),
        ('\\\n', '{#Return}{#Return}'),
        (r'\cxds', '{^}'),
        (r'pre\cxds ', '{pre^}'),
        (r'pre\cxds  ', '{pre^} '),
        (r'pre\cxds', '{pre^}'),
        (r'\cxds post', '{^post}'),
        (r'\cxds in\cxds', '{^in^}'),
        (r'\cxds in\cxds ', '{^in^}'),
        (r'\cxfc', '{-|}'),
        (r'\cxfl', '{>}'),
        (r'pre\cxfl', 'pre{>}'),
        (r'{\*\cxsvatdictflags N}', '{-|}'),
        (r'{\*\cxsvatdictflags LN1}', '{-|}'),
        (r'\par', '{#Return}{#Return}'),
        # caseCATalyst declares new styles without a preceding \par so we treat
        # it as an implicit par.
        (r'\s1', '{#Return}{#Return}'),
        # But if the \par is present we don't treat \s as an implicit par.
        (r'\par\s1', '{#Return}{#Return}'),
        # Continuation styles are indented too.
        (r'\par\s2', '{#Return}{#Return}{^    ^}'),
        # caseCATalyst punctuation.
        (r'.', '{.}'),
        (r'. ', '{.} '),
        (r' . ', ' . '),
        (r'{\cxa Q.}.', 'Q..'),
        (r'Mr.', 'Mr.'),  # Don't mess with period that is part of a word.
        (r'.attribute', '.attribute'),
        (r'{\cxstit contents}', 'contents'),
        (r'{\cxfing c}', '{&c}'),
        (r'{\cxp.}', '{.}'),
        (r'{\cxp .}', '{.}'),
        (r'{\cxp . }', '{.}'),
        (r'{\cxp .  }', '{.}'),
        (r'{\cxp !}', '{!}'),
        (r'{\cxp ?}', '{?}'),
        (r'{\cxp ,}', '{,}'),
        (r'{\cxp ;}', '{;}'),
        (r'{\cxp :}', '{:}'),
        ('{\\cxp \'}', '{^\'}'),
        ('{\\cxp -}', '{^-^}'),
        ('{\\cxp /}', '{^/^}'),
        ('{\\cxp...  }', '{^...  ^}'),
        ('{\\cxp ") }', '{^") ^}'),
        ('{\\nonexistant }', ''),
        ('{\\nonexistant contents}', 'contents'),
        ('{\\nonexistant cont\\_ents}', 'cont-ents'),
        ('{\\*\\nonexistant }', ''),
        ('{\\*\\nonexistant contents}', ''),
        ('{eclipse command}', '{eclipse command}'),
        ('test text', 'test text'),
        ('test  text', 'test{^  ^}text'),
        (r'{\cxconf [{\cxc abc}]}', 'abc'),
        (r'{\cxconf [{\cxc abc}|{\cxc def}]}', 'def'),
        (r'{\cxconf [{\cxc abc}|{\cxc def}|{\cxc ghi}]}', 'ghi'),
        (r'{\cxconf [{\cxc abc}|{\cxc {\cxp... }}]}', '{^... ^}'),
        (r'be\cxds{\*\cxsvatdictentrydate\yr2006\mo5\dy10}', '{be^}'),
        
        (r'{\nonexistant {\cxp .}}', '{.}'),
        (r'{\*\nonexistant {\cxp .}}', ''),
        )
        
        failed = []
        for before, after in cases:
            if convert(before) != after:
                failed.append((before, after))
                
        for before, after in failed:
            print 'convert(%s) != %s: %s' % (before, after, convert(before))

        self.assertEqual(len(failed), 0)
    
    def test_load_dict(self):
        """Test the load_dict function.

        This test just tests load_dict so it mocks out the converters and just
        verifies that they are called.

        """
        
        expected_styles = {
            0: 'Normal',
            1: 'Question',
            2: 'Answer',
            3: 'Colloquy',
            4: 'Continuation Q',
            5: 'Continuation A',
            6: 'Continuation Col',
            7: 'Paren',
            8: 'Centered',
        }
        
        header = '\r\n'.join(
            [r'{\rtf1\ansi\cxdict{\*\cxrev100}{\*\cxsystem Fake Software}'] +
            [r'{\s%d %s;}' % (k, v) for k, v in expected_styles.items()] + 
            ['}'])
        footer = '\r\n}'
        
        def make_dict(s):
            return ''.join((header, s, footer))
            
        def assertEqual(a, b):
            self.assertEqual(a._dict, b)

        this = self

        class Converter(object):
            def __init__(self, styles):
                this.assertEqual(styles, expected_styles)

            def __call__(self, s):
                if s == 'return_none':
                    return None
                return 'converted(%s)' % s
                
        convert = Converter(expected_styles)
        normalize = lambda x: 'normalized(%s)' % x
        
        cases = (
        
        # Empty dictionary.
        ('', {}),
        # Only one translation.
        ('{\\*\\cxs SP}translation', {'SP': 'translation'}),
        # Multiple translations no newlines.
        ('{\\*\\cxs SP}translation{\\*\\cxs S}translation2', 
         {'SP': 'translation', 'S': 'translation2'}),
        # Multiple translations on separate lines.
        ('{\\*\\cxs SP}translation\r\n{\\*\\cxs S}translation2', 
         {'SP': 'translation', 'S': 'translation2'}),
        ('{\\*\\cxs SP}translation\n{\\*\\cxs S}translation2', 
         {'SP': 'translation', 'S': 'translation2'}),
        # Escaped \r and \n handled
        ('{\\*\\cxs SP}trans\\\r\\\n', {'SP': 'trans\\\r\\\n'}),
        # Escaped \r\n handled in mid translation
        ('{\\*\\cxs SP}trans\\\r\\\nlation', {'SP': 'trans\\\r\\\nlation'}),
        # Whitespace is preserved in various situations.
        ('{\\*\\cxs S}t  ', {'S': 't  '}),
        ('{\\*\\cxs S}t   {\\*\\cxs T}t    ', {'S': 't   ', 'T': 't    '}),
        ('{\\*\\cxs S}t   \r\n{\\*\\cxs T}t    ', {'S': 't   ', 'T': 't    '}),
        ('{\\*\\cxs S}t  \r\n{\\*\\cxs T} t \r\n', {'S': 't  ', 'T': ' t '}),
        # Translations are ignored if converter returns None
        ('{\\*\\cxs S}return_none', {}),
        ('{\\*\\cxs T}t t t  ', {'T': 't t t  '}),
        # Conflicts result on only the last one kept.
        ('{\\*\\cxs T}t{\\*\\cxs T}g', {'T': 'g'}),
        ('{\\*\\cxs T}t{\\*\\cxs T}return_none', {'T': 't'}),
        
        )
        
        patch_path = 'plover.dictionary.rtfcre_dict'
        with mock.patch.multiple(patch_path, normalize_steno=normalize, 
                                 TranslationConverter=Converter):
            for s, expected in cases:
                expected = dict((normalize(k), convert(v)) 
                                for k, v in expected.iteritems())
                assertEqual(load_dictionary(make_dict(s)), expected)

    def test_format_translation(self):
        cases = (
        ('', ''),
        ('{^in^}', '\cxds in\cxds '),
        ('{pre^}', 'pre\cxds '),
        ('{pre^} ', 'pre\cxds '),
        ('{pre^}  ', 'pre\cxds ')
        )
        
        failed = False
        format_str = "format({}) != {}: {}"
        for before, expected in cases:
            result = format_translation(before)
            if result != expected:
                failed = True
                print format_str.format(before, expected, result)
            
        self.assertFalse(failed)
        
    def test_save_dictionary(self):
        f = StringIO()
        d = {
        'S/T': '{pre^}',
        }
        save_dictionary(d, f)
        expected = '{\\rtf1\\ansi{\\*\\cxrev100}\\cxdict{\\*\\cxsystem Plover}{\\stylesheet{\\s0 Normal;}}\r\n{\\*\\cxs S///T}pre\\cxds \r\n}\r\n' 
        self.assertEqual(f.getvalue(), expected)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = dictionary_editor_store
from plover.steno import normalize_steno

class DictionaryItem():

    def __init__(self, stroke, translation, dictionary, id):

        if translation is None:
            translation = ''
            
        self.stroke = stroke
        self.translation = translation
        self.dictionary = dictionary
        self.id = id


class DictionaryEditorStore():
    
    def __init__(self, engine, config):

        self.config = config
        self.engine = engine
        
        self.all_keys = []
        self.filtered_keys = []
        self.sorted_keys = []
        
        self.modified_items = []
        self.added_items = []
        self.deleted_items = []

        self.sorting_column = -1
        self.sorting_mode = None

        item_id = 0
        self.new_id = -1

        dict_index = len(self.engine.get_dictionary().dicts) - 1
        while dict_index >= 0:
            dict = self.engine.get_dictionary().dicts[dict_index]
            for dk in dict.keys():
                joined = '/'.join(dk)
                translation = self.engine.get_dictionary().lookup(dk)
                item = DictionaryItem(joined, translation, dict.get_path(), item_id)
                self.all_keys.append(item)
                item_id += 1
            dict_index -= 1
        self.filtered_keys = self.all_keys[:]
        self.sorted_keys = self.filtered_keys[:]

    def GetNumberOfRows(self):
        return len(self.sorted_keys)

    def GetValue(self, row, col):
        item = self.sorted_keys[row]
        if col == 0:
            result = item.stroke
        elif col == 1:
            result = item.translation
        else:
            result = item.dictionary
        return result

    def SetValue(self, row, col, value):
        item = self.sorted_keys[row]
        if item.id < 0:
            editing_item = self._getAddedItem(item.id)
        else:
            editing_item = self.all_keys[item.id]
        if col == 0:
            editing_item.stroke = value
        elif col == 1:
            editing_item.translation = value
        if item.id >= 0:
            if item.id not in self.modified_items:
                self.modified_items.append(item.id)

    def GetSortColumn(self):
        return self.sorting_column

    def GetSortMode(self):
        return self.sorting_mode

    def ApplyFilter(self, stroke_filter, translation_filter):
        self.filtered_keys = []
        self.sorted_keys = []
        for di in self.added_items:
            if self._itemMatchesFilter(di, stroke_filter, translation_filter):
                self.filtered_keys.append(di)
        for di in self.all_keys:
            if di not in self.deleted_items:
                if self._itemMatchesFilter(di, stroke_filter, translation_filter):
                    self.filtered_keys.append(di)
        self._applySort()

    def InsertNew(self, row):
        selected_item = self.sorted_keys[row]
        item = DictionaryItem('', '', selected_item.dictionary, self.new_id)
        self.added_items.append(item)
        self.sorted_keys.insert(row, item)
        self.new_id -= 1

    def DeleteSelected(self, row):
        item = self.sorted_keys[row]
        if item.id < 0:
            self.added_items.remove(item)
        else:
            self.deleted_items.append(item)
        self.sorted_keys.remove(item)

    def SaveChanges(self):
        # Creates
        for added_item in self.added_items:
            dict = self.engine.get_dictionary().get_by_path(added_item.dictionary)
            dict.__setitem__(self._splitStrokes(added_item.stroke), added_item.translation)

        # Updates
        for modified_item_id in self.modified_items:
            modified_item = self.all_keys[modified_item_id]
            dict = self.engine.get_dictionary().get_by_path(modified_item.dictionary)
            dict.__setitem__(self._splitStrokes(modified_item.stroke), modified_item.translation)

        # Deletes
        for deleted_item in self.deleted_items:
            dict = self.engine.get_dictionary().get_by_path(deleted_item.dictionary)
            dict.__delitem__(self._splitStrokes(deleted_item.stroke))

        self.engine.get_dictionary().save_all()

    def Sort(self, column):
        if column == 2:
            return
        
        if self.sorting_column == column:
            #Already sorting on this column
            #Next sorting mode
            self.sorting_mode = self._cycleNextSortMode(self.sorting_mode)
        else:
            #Different column than the one currently being sorted
            self.sorting_column = column
            #First sorting mode
            self.sorting_mode = True
        self._applySort()

    def _getAddedItem(self, id):
        for di in self.added_items:
            if di.id == id:
                return di
        return None

    def _itemMatchesFilter(self, di, stroke_filter, translation_filter):
        stroke_add = False
        translation_add = False
        if stroke_filter:
            stroke = di.stroke
            if stroke:
                if stroke.lower().startswith(stroke_filter.lower()):
                    stroke_add = True
        else:
            stroke_add = True
        if translation_filter:
            translation = di.translation
            if translation:
                if translation.lower().startswith(translation_filter.lower()):
                    translation_add = True
        else:
            translation_add = True
        if stroke_add is True:
            if translation_add is True:
                return True
        return False

    def _cycleNextSortMode(self, sort_mode):
        if sort_mode is None:
            return True
        elif sort_mode is True:
            return False
        else:
            return None

    def _applySort(self):
        if self.sorting_mode is not None:
            reverse_sort = not self.sorting_mode
            if self.sorting_column == 0:
                self.sorted_keys = sorted(self.filtered_keys, key=lambda x: x.stroke.lower(), reverse=reverse_sort)
            elif self.sorting_column == 1:
                self.sorted_keys = sorted(self.filtered_keys, key=lambda x: x.translation.lower(), reverse=reverse_sort)
        else:
            self.sorted_keys = self.filtered_keys[:]

    def _splitStrokes(self, strokes_string):
        result = normalize_steno(strokes_string.upper())
        return result

########NEW FILE########
__FILENAME__ = exception
# Copyright (c) 2011 Joshua Harlan Lifton.
# See LICENSE.txt for details.

"""Custom exceptions used by Plover.

The exceptions in this module are typically caught in the main GUI
loop and displayed to the user as an alert dialog.

"""

SERIAL_PORT_EXCEPTION_MESSAGE = ("Either the stenotype machine is not "
                                 "connected to the selected serial port "
                                 "or the serial port is misconfigured. "
                                 "Please check the connection and "
                                 "configuration.")



class InvalidConfigurationError(Exception):
    "Raised when there is something wrong in the configuration."
    pass


class SerialPortException(InvalidConfigurationError):
    """Raised when a serial port is misconfigured."""

    def __init__(self, *args):
        """Override the constructor to include a default message."""
        Exception.__init__(self, SERIAL_PORT_EXCEPTION_MESSAGE, *args)

class DictionaryLoaderException(Exception):
    """Dictionary file could not be loaded."""
    pass

########NEW FILE########
__FILENAME__ = formatting
# Copyright (c) 2010-2011 Joshua Harlan Lifton.
# See LICENSE.txt for details.

"""This module converts translations to printable text.

This module defines and implements plover's custom dictionary language.

"""

from os.path import commonprefix
from collections import namedtuple
import orthography
import re

class Formatter(object):
    """Convert translations into output.

    The main entry point for this class is format, which takes in translations
    to format. Output is sent via an output class passed in through set_output.
    Other than setting the output, the formatter class is stateless. 

    The output class can define the following functions, which will be called if
    available:

    send_backspaces -- Takes a number and deletes back that many characters.

    send_string -- Takes a string and prints it verbatim.

    send_key_combination -- Takes a string the dictionary format for specifying
    key combinations and issues them.

    send_engine_command -- Takes a string which names the special command to
    execute.

    """

    output_type = namedtuple(
        'output', ['send_backspaces', 'send_string', 'send_key_combination', 
                   'send_engine_command'])

    def __init__(self):
        self.set_output(None)

    def set_output(self, output):
        """Set the output class."""
        noop = lambda x: None
        output_type = self.output_type
        fields = output_type._fields
        self._output = output_type(*[getattr(output, f, noop) for f in fields])

    def set_space_placement(self, s):
        """Set whether spaces will be inserted before the output or after the output"""
        if s == 'After Output':
            self.spaces_after = True
        else:
            self.spaces_after = False

    def format(self, undo, do, prev):
        """Format the given translations.

        Arguments:

        undo -- A sequence of translations that should be undone. The formatting
        parameter of the translations will be used to undo the actions that were
        taken, if possible.

        do -- The new actions to format. The formatting attribute will be filled
        in with the result.

        prev -- The last translation before the new actions in do. This
        translation's formatting attribute provides the context for the new
        rendered translations. If there is no context then this may be None.

        """
        for t in do:
            last_action = _get_last_action(prev.formatting if prev else None)
            if t.english:
                t.formatting = _translation_to_actions(t.english, last_action, self.spaces_after)
            else:
                t.formatting = _raw_to_actions(t.rtfcre[0], last_action, self.spaces_after)
            prev = t

        old = [a for t in undo for a in t.formatting]
        new = [a for t in do for a in t.formatting]
        
        min_length = min(len(old), len(new))
        for i in xrange(min_length):
            if old[i] != new[i]:
                break
        else:
            i = min_length

        OutputHelper(self._output).render(old[i:], new[i:])

class OutputHelper(object):
    """A helper class for minimizing the amount of change on output.

    This class figures out the current state, compares it to the new output and
    optimizes away extra backspaces and typing.

    """
    def __init__(self, output):
        self.before = ''
        self.after = ''
        self.output = output
        
    def commit(self):
        offset = len(commonprefix([self.before, self.after]))
        if self.before[offset:]:
            self.output.send_backspaces(len(self.before[offset:]))
        if self.after[offset:]:
            self.output.send_string(self.after[offset:])
        self.before = ''
        self.after = ''

    def render(self, undo, do):
        for a in undo:
            if a.replace:
                if len(a.replace) >= len(self.before):
                    self.before = ''
                else:
                    self.before = self.before[:-len(a.replace)]
            if a.text:
                self.before += a.text

        self.after = self.before
        
        for a in reversed(undo):
            if a.text:
                self.after = self.after[:-len(a.text)]
            if a.replace:
                self.after += a.replace
        
        for a in do:
            if a.replace:
                if len(a.replace) > len(self.after):
                    self.before = a.replace[:len(a.replace)-len(self.after)] + self.before
                    self.after = ''
                else:
                    self.after = self.after[:-len(a.replace)]
            if a.text:
                self.after += a.text
            if a.combo:
                self.commit()
                self.output.send_key_combination(a.combo)
            if a.command:
                self.commit()
                self.output.send_engine_command(a.command)
        self.commit()

def _get_last_action(actions):
    """Return last action in actions if possible or return a blank action."""
    return actions[-1] if actions else _Action()

class _Action(object):
    """A hybrid class that stores instructions and resulting state.

    A single translation may be formatted into one or more actions. The
    instructions are used to render the current action and the state is used as
    context to render future translations.

    """
    def __init__(self, attach=False, glue=False, word='', capitalize=False, 
                 lower=False, orthography=True, text='', replace='', combo='', 
                 command=''):
        """Initialize a new action.

        Arguments:

        attach -- True if there should be no space between this and the next
        action.

        glue -- True if there be no space between this and the next action if
        the next action also has glue set to True.

        word -- The current word. This is context for future actions whose
        behavior depends on the previous word such as suffixes.

        capitalize -- True if the next action should be capitalized.

        lower -- True if the next action should be lower cased.

        othography -- True if orthography rules should be applies when adding
        a suffix to this action.

        text -- The text that should be rendered for this action.

        replace -- Text that should be deleted for this action.

        combo -- The key combo, in plover's key combo language, that should be
        executed for this action.

        command -- The command that should be executed for this actions.

        """
        # State variables
        self.attach = attach
        self.glue = glue
        self.word = word
        self.capitalize = capitalize
        self.lower = lower
        self.orthography = orthography
                
        # Instruction variables
        self.text = text
        self.replace = replace
        self.combo = combo
        self.command = command
        
    def copy_state(self):
        """Clone this action but only clone the state variables."""
        a = _Action()
        a.attach = self.attach
        a.glue = self.glue
        a.word = self.word
        a.capitalize = self.capitalize
        a.lower = self.lower
        a.orthography = self.orthography
        return a
        
    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        return 'Action(%s)' % str(self.__dict__)

    def __repr__(self):
        return str(self)


META_ESCAPE = '\\'
RE_META_ESCAPE = '\\\\'
META_START = '{'
META_END = '}'
META_ESC_START = META_ESCAPE + META_START
META_ESC_END = META_ESCAPE + META_END

META_RE = re.compile(r"""(?:%s%s|%s%s|[^%s%s])+ # One or more of anything
                                                # other than unescaped { or }
                                                #
                                              | # or
                                                #
                     %s(?:%s%s|%s%s|[^%s%s])*%s # Anything of the form {X}
                                                # where X doesn't contain
                                                # unescaped { or }
                      """ % (RE_META_ESCAPE, META_START, RE_META_ESCAPE,
                             META_END, META_START, META_END,
                             META_START,
                             RE_META_ESCAPE, META_START, RE_META_ESCAPE,
                             META_END, META_START, META_END,
                             META_END),
                     re.VERBOSE)

# A more human-readable version of the above RE is:
#
# re.compile(r"""(?:\\{|\\}|[^{}])+ # One or more of anything other than
#                                   # unescaped { or }
#                                   #
#                                 | # or
#                                   #
#              {(?:\\{|\\}|[^{}])*} # Anything of the form {X} where X
#                                   # doesn't contain unescaped { or }
#             """, re.VERBOSE)

def _translation_to_actions(translation, last_action, spaces_after):
    """Create actions for a translation.
    
    Arguments:

    translation -- A string with the translation to render.

    last_action -- The action in whose context this translation is formatted.

    Returns: A list of actions.

    """
    actions = []
    # Reduce the translation to atoms. An atom is an irreducible string that is
    # either entirely a single meta command or entirely text containing no meta
    # commands.
    if translation.isdigit():
        # If a translation is only digits then glue it to neighboring digits.
        atoms = [_apply_glue(translation)]
    else:
        atoms = [x.strip() for x in META_RE.findall(translation) if x.strip()]

    if not atoms:
        return [last_action.copy_state()]

    for atom in atoms:
        action = _atom_to_action(atom, last_action, spaces_after)
        actions.append(action)
        last_action = action

    return actions


SPACE = ' '
NO_SPACE = ''
META_STOPS = ('.', '!', '?')
META_COMMAS = (',', ':', ';')
META_CAPITALIZE = '-|'
META_LOWER = '>'
META_GLUE_FLAG = '&'
META_ATTACH_FLAG = '^'
META_KEY_COMBINATION = '#'
META_COMMAND = 'PLOVER:'

def _raw_to_actions(stroke, last_action, spaces_after):
    """Turn a raw stroke into actions.

    Arguments:

    stroke -- A string representation of the stroke.

    last_action -- The context in which the new actions are created

    Returns: A list of actions.

    """
    # If a raw stroke is composed of digits then remove the dash (if 
    # present) and glue it to any neighboring digits. Otherwise, just 
    # output the raw stroke as is.
    no_dash = stroke.replace('-', '', 1)
    if no_dash.isdigit():
        return _translation_to_actions(no_dash, last_action, spaces_after)
    else:
        if spaces_after:
            return [_Action(text=(stroke + SPACE), word=stroke)]
        else:
            return [_Action(text=(SPACE + stroke), word=stroke)]

def _atom_to_action(atom, last_action, spaces_after):
    """Convert an atom into an action.

    Arguments:

    atom -- A string holding an atom. An atom is an irreducible string that is
    either entirely a single meta command or entirely text containing no meta
    commands.

    last_action -- The context in which the new action takes place.

    Returns: An action for the atom.

    """
    if spaces_after:
        return _atom_to_action_spaces_after(atom, last_action)
    else:
        return _atom_to_action_spaces_before(atom, last_action)
    
def _atom_to_action_spaces_before(atom, last_action):
    """Convert an atom into an action.

    Arguments:

    atom -- A string holding an atom. An atom is an irreducible string that is
    either entirely a single meta command or entirely text containing no meta
    commands.

    last_action -- The context in which the new action takes place.

    Returns: An action for the atom.

    """
    
    action = _Action()
    last_word = last_action.word
    last_glue = last_action.glue
    last_attach = last_action.attach
    last_capitalize = last_action.capitalize
    last_lower = last_action.lower
    last_orthography = last_action.orthography
    meta = _get_meta(atom)
    if meta is not None:
        meta = _unescape_atom(meta)
        if meta in META_COMMAS:
            action.text = meta
        elif meta in META_STOPS:
            action.text = meta
            action.capitalize = True
            action.lower = False
        elif meta == META_CAPITALIZE:
            action = last_action.copy_state()
            action.capitalize = True
            action.lower = False
        elif meta == META_LOWER:
            action = last_action.copy_state()
            action.lower = True
            action.capitalize = False
        elif meta.startswith(META_COMMAND):
            action = last_action.copy_state()
            action.command = meta[len(META_COMMAND):]
        elif meta.startswith(META_GLUE_FLAG):
            action.glue = True
            glue = last_glue or last_attach
            space = NO_SPACE if glue else SPACE
            text = meta[len(META_GLUE_FLAG):]
            if last_capitalize:
                text = _capitalize(text)
            if last_lower:
                text = _lower(text)
            action.text = space + text
            action.word = _rightmost_word(last_word + action.text)
        elif (meta.startswith(META_ATTACH_FLAG) or 
              meta.endswith(META_ATTACH_FLAG)):
            begin = meta.startswith(META_ATTACH_FLAG)
            end = meta.endswith(META_ATTACH_FLAG)
            if begin:
                meta = meta[len(META_ATTACH_FLAG):]
            if end and len(meta) >= len(META_ATTACH_FLAG):
                meta = meta[:-len(META_ATTACH_FLAG)]
            space = NO_SPACE if begin or last_attach else SPACE
            if end:
                action.attach = True
            if begin and end and meta == '':
                # We use an empty connection to indicate a "break" in the 
                # application of orthography rules. This allows the stenographer 
                # to tell plover not to auto-correct a word.
                action.orthography = False
            if (((begin and not end) or (begin and end and ' ' in meta)) and 
                last_orthography):
                new = orthography.add_suffix(last_word.lower(), meta)
                common = commonprefix([last_word.lower(), new])
                action.replace = last_word[len(common):]
                meta = new[len(common):]
            if last_capitalize:
                meta = _capitalize(meta)
            if last_lower:
                meta = _lower(meta)
            action.text = space + meta
            action.word = _rightmost_word(
                last_word[:len(last_word)-len(action.replace)] + action.text)
        elif meta.startswith(META_KEY_COMBINATION):
            action = last_action.copy_state()
            action.combo = meta[len(META_KEY_COMBINATION):]
    else:
        text = _unescape_atom(atom)
        if last_capitalize:
            text = _capitalize(text)
        if last_lower:
            text = _lower(text)
        space = NO_SPACE if last_attach else SPACE
        action.text = space + text
        action.word = _rightmost_word(text)
    return action

def _atom_to_action_spaces_after(atom, last_action):
    """Convert an atom into an action.

    Arguments:

    atom -- A string holding an atom. An atom is an irreducible string that is
    either entirely a single meta command or entirely text containing no meta
    commands.

    last_action -- The context in which the new action takes place.

    Returns: An action for the atom.

    """
    
    action = _Action()
    last_word = last_action.word
    last_glue = last_action.glue
    last_attach = last_action.attach
    last_capitalize = last_action.capitalize
    last_lower = last_action.lower
    last_orthography = last_action.orthography
    last_space = SPACE if last_action.text.endswith(SPACE) else NO_SPACE
    meta = _get_meta(atom)
    if meta is not None:
        meta = _unescape_atom(meta)
        if meta in META_COMMAS:
            action.text = meta + SPACE
            if last_action.text != '':
                action.replace = SPACE
            if last_attach:
                action.replace = NO_SPACE
        elif meta in META_STOPS:
            action.text = meta + SPACE
            action.capitalize = True
            action.lower = False
            if last_action.text != '':
                action.replace = SPACE
            if last_attach:
                action.replace = NO_SPACE
        elif meta == META_CAPITALIZE:
            action = last_action.copy_state()
            action.capitalize = True
            action.lower = False
        elif meta == META_LOWER:
            action = last_action.copy_state()
            action.lower = True
            action.capitalize = False
        elif meta.startswith(META_COMMAND):
            action = last_action.copy_state()
            action.command = meta[len(META_COMMAND):]
        elif meta.startswith(META_GLUE_FLAG):
            action.glue = True
            text = meta[len(META_GLUE_FLAG):]
            if last_capitalize:
                text = _capitalize(text)
            if last_lower:
                text = _lower(text)
            action.text = text + SPACE
            action.word = _rightmost_word(text)
            if last_glue:
                action.replace = SPACE
                action.word = _rightmost_word(last_word + text)
            if last_attach:
                action.replace = NO_SPACE
                action.word = _rightmost_word(last_word + text)
        elif (meta.startswith(META_ATTACH_FLAG) or 
              meta.endswith(META_ATTACH_FLAG)):
            begin = meta.startswith(META_ATTACH_FLAG)
            end = meta.endswith(META_ATTACH_FLAG)
            if begin:
                meta = meta[len(META_ATTACH_FLAG):]
            if end and len(meta) >= len(META_ATTACH_FLAG):
                meta = meta[:-len(META_ATTACH_FLAG)]
                
            space = NO_SPACE if end else SPACE
            replace_space = NO_SPACE if last_attach else SPACE
            
            if end:
                action.attach = True
            if begin and end and meta == '':
                # We use an empty connection to indicate a "break" in the 
                # application of orthography rules. This allows the stenographer 
                # to tell plover not to auto-correct a word.
                action.orthography = False
                if last_action.text != '':
                    action.replace = replace_space
            if (((begin and not end) or (begin and end and ' ' in meta)) and 
                last_orthography):
                new = orthography.add_suffix(last_word.lower(), meta)
                common = commonprefix([last_word.lower(), new])
                if last_action.text == '':
                    replace_space = NO_SPACE
                action.replace = last_word[len(common):] + replace_space
                meta = new[len(common):]
            if begin and end:
                if last_action.text != '':
                    action.replace = replace_space
            if last_capitalize:
                meta = _capitalize(meta)
            if last_lower:
                meta = _lower(meta)
            action.text = meta + space
            action.word = _rightmost_word(
                last_word[:len(last_word + last_space)-len(action.replace)] + meta)
            if end and not begin and last_space == SPACE:
                action.word = _rightmost_word(meta)
        elif meta.startswith(META_KEY_COMBINATION):
            action = last_action.copy_state()
            action.combo = meta[len(META_KEY_COMBINATION):]
    else:
        text = _unescape_atom(atom)
        if last_capitalize:
            text = _capitalize(text)
        if last_lower:
            text = _lower(text)
            
        action.text = text + SPACE
        action.word = _rightmost_word(text)
    return action

def _get_meta(atom):
    """Return the meta command, if any, without surrounding meta markups."""
    if (atom is not None and
        atom.startswith(META_START) and
        atom.endswith(META_END)):
        return atom[len(META_START):-len(META_END)]
    return None

def _apply_glue(s):
    """Mark the given string as a glue stroke."""
    return META_START + META_GLUE_FLAG + s + META_END

def _unescape_atom(atom):
    """Replace escaped meta markups with unescaped meta markups."""
    return atom.replace(META_ESC_START, META_START).replace(META_ESC_END,
                                                            META_END)

def _get_engine_command(atom):
    """Return the steno engine command, if any, represented by the atom."""
    if (atom and
        atom.startswith(META_START + META_COMMAND) and
        atom.endswith(META_END)):
        return atom[len(META_START) + len(META_COMMAND):-len(META_END)]
    return None

def _capitalize(s):
    """Capitalize the first letter of s."""
    return s[0:1].upper() + s[1:]

def _lower(s):
    """Lowercase the first letter of s."""
    return s[0:1].lower() + s[1:]

def _rightmost_word(s):
    """Get the rightmost word in s."""
    return s.rpartition(' ')[2]

########NEW FILE########
__FILENAME__ = add_translation
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

import wx
from wx.lib.utils import AdjustRectToScreen
import sys
from plover.steno import normalize_steno
import plover.gui.util as util

TITLE = 'Plover: Add Translation'

class AddTranslationDialog(wx.Dialog):
    
    BORDER = 3
    STROKES_TEXT = 'Strokes:'
    TRANSLATION_TEXT = 'Translation:'
    
    other_instances = []
    
    def __init__(self, parent, engine, config):
        pos = (config.get_translation_frame_x(), 
               config.get_translation_frame_y())
        wx.Dialog.__init__(self, parent, wx.ID_ANY, TITLE, 
                           pos, wx.DefaultSize, 
                           wx.DEFAULT_DIALOG_STYLE, wx.DialogNameStr)

        self.config = config

        # components
        self.strokes_text = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.translation_text = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        button = wx.Button(self, id=wx.ID_OK, label='Add to dictionary')
        cancel = wx.Button(self, id=wx.ID_CANCEL)
        self.stroke_mapping_text = wx.StaticText(self)
        self.translation_mapping_text = wx.StaticText(self)
        
        # layout
        global_sizer = wx.BoxSizer(wx.VERTICAL)
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, label=self.STROKES_TEXT)
        sizer.Add(label, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, 
                  border=self.BORDER)
        sizer.Add(self.strokes_text, 
                  flag=wx.TOP | wx.RIGHT | wx.BOTTOM | wx.ALIGN_CENTER_VERTICAL, 
                  border=self.BORDER)
        label = wx.StaticText(self, label=self.TRANSLATION_TEXT)
        sizer.Add(label, 
                  flag=wx.TOP | wx.RIGHT | wx.BOTTOM | wx.ALIGN_CENTER_VERTICAL, 
                  border=self.BORDER)
        sizer.Add(self.translation_text          , 
                  flag=wx.TOP | wx.RIGHT | wx.BOTTOM | wx.ALIGN_CENTER_VERTICAL, 
                  border=self.BORDER)
        sizer.Add(button, 
                  flag=wx.TOP | wx.RIGHT | wx.BOTTOM | wx.ALIGN_CENTER_VERTICAL, 
                  border=self.BORDER)
        sizer.Add(cancel, 
                  flag=wx.TOP | wx.RIGHT | wx.BOTTOM | wx.ALIGN_CENTER_VERTICAL, 
                  border=self.BORDER)
        global_sizer.Add(sizer)
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.stroke_mapping_text, 
                  flag= wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                  border=self.BORDER)
        global_sizer.Add(sizer)
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.translation_mapping_text, 
                  flag= wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                  border=self.BORDER)
        global_sizer.Add(sizer)
        
        self.SetAutoLayout(True)
        self.SetSizer(global_sizer)
        global_sizer.Fit(self)
        global_sizer.SetSizeHints(self)
        self.Layout()
        self.SetRect(AdjustRectToScreen(self.GetRect()))
        
        # events
        button.Bind(wx.EVT_BUTTON, self.on_add_translation)
        # The reason for the focus event here is to skip focus on tab traversal
        # of the buttons. But it seems that on windows this prevents the button
        # from being pressed. Leave this commented out until that problem is
        # resolved.
        #button.Bind(wx.EVT_SET_FOCUS, self.on_button_gained_focus)
        cancel.Bind(wx.EVT_BUTTON, self.on_close)
        #cancel.Bind(wx.EVT_SET_FOCUS, self.on_button_gained_focus)
        self.strokes_text.Bind(wx.EVT_TEXT, self.on_strokes_change)
        self.translation_text.Bind(wx.EVT_TEXT, self.on_translation_change)
        self.strokes_text.Bind(wx.EVT_SET_FOCUS, self.on_strokes_gained_focus)
        self.strokes_text.Bind(wx.EVT_KILL_FOCUS, self.on_strokes_lost_focus)
        self.strokes_text.Bind(wx.EVT_TEXT_ENTER, self.on_add_translation)
        self.translation_text.Bind(wx.EVT_SET_FOCUS, self.on_translation_gained_focus)
        self.translation_text.Bind(wx.EVT_KILL_FOCUS, self.on_translation_lost_focus)
        self.translation_text.Bind(wx.EVT_TEXT_ENTER, self.on_add_translation)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_MOVE, self.on_move)
        
        self.engine = engine
        
        # TODO: add functions on engine for state
        self.previous_state = self.engine.translator.get_state()
        # TODO: use state constructor?
        self.engine.translator.clear_state()
        self.strokes_state = self.engine.translator.get_state()
        self.engine.translator.clear_state()
        self.translation_state = self.engine.translator.get_state()
        self.engine.translator.set_state(self.previous_state)
        
        self.last_window = util.GetForegroundWindow()
        
        # Now that we saved the last window we'll close other instances. This 
        # may restore their original window but we've already saved ours so it's 
        # fine.
        for instance in self.other_instances:
            instance.Close()
        del self.other_instances[:]
        self.other_instances.append(self)
    
    def on_add_translation(self, event=None):
        d = self.engine.get_dictionary()
        strokes = self._normalized_strokes()
        translation = self.translation_text.GetValue().strip()
        if strokes and translation:
            d.set(strokes, translation)
            d.save()
        self.Close()

    def on_close(self, event=None):
        self.engine.translator.set_state(self.previous_state)
        try:
            util.SetForegroundWindow(self.last_window)
        except:
            pass
        self.other_instances.remove(self)
        self.Destroy()

    def on_strokes_change(self, event):
        key = self._normalized_strokes()
        if key:
            d = self.engine.get_dictionary()
            translation = d.raw_lookup(key)
            strokes = '/'.join(key)
            if translation:
                label = '%s maps to %s' % (strokes, translation)
            else:
                label = '%s is not in the dictionary' % strokes
        else:
            label = ''
        self.stroke_mapping_text.SetLabel(label)
        self.GetSizer().Layout()

    def on_translation_change(self, event):
        # TODO: normalize dict entries to make reverse lookup more reliable with 
        # whitespace.
        translation = event.GetString().strip()
        if translation:
            d = self.engine.get_dictionary()
            strokes_list = d.reverse_lookup(translation)
            if strokes_list:
                strokes = ', '.join('/'.join(x) for x in strokes_list)
                label = '%s is mapped from %s' % (translation, strokes)
            else:
                label = '%s is not in the dictionary' % translation
        else:
            label = ''
        self.translation_mapping_text.SetLabel(label)
        self.GetSizer().Layout()
        
    def on_strokes_gained_focus(self, event):
        self.engine.get_dictionary().add_filter(self.stroke_dict_filter)
        self.engine.translator.set_state(self.strokes_state)
        
    def on_strokes_lost_focus(self, event):
        self.engine.get_dictionary().remove_filter(self.stroke_dict_filter)
        self.engine.translator.set_state(self.previous_state)

    def on_translation_gained_focus(self, event):
        self.engine.translator.set_state(self.translation_state)
        
    def on_translation_lost_focus(self, event):
        self.engine.translator.set_state(self.previous_state)

    def on_button_gained_focus(self, event):
        self.strokes_text.SetFocus()
        
    def stroke_dict_filter(self, key, value):
        # Only allow translations with special entries. Do this by looking for 
        # braces but take into account escaped braces and slashes.
        escaped = value.replace('\\\\', '').replace('\\{', '')
        special = '{#'  in escaped or '{PLOVER:' in escaped
        return not special

    def on_move(self, event):
        pos = self.GetScreenPositionTuple()
        self.config.set_translation_frame_x(pos[0]) 
        self.config.set_translation_frame_y(pos[1])
        event.Skip()

    def _normalized_strokes(self):
        strokes = self.strokes_text.GetValue().upper().replace('/', ' ').split()
        strokes = normalize_steno('/'.join(strokes))
        return strokes

def Show(parent, engine, config):
    dialog_instance = AddTranslationDialog(parent, engine, config)
    dialog_instance.Show()
    dialog_instance.Raise()
    dialog_instance.strokes_text.SetFocus()
    util.SetTopApp()

########NEW FILE########
__FILENAME__ = config
# Copyright (c) 2010-2011 Joshua Harlan Lifton.
# See LICENSE.txt for details.

"""Configuration dialog graphical user interface."""

import os
import os.path
import wx
from wx.lib.utils import AdjustRectToScreen
from collections import namedtuple
import wx.lib.filebrowsebutton as filebrowse
from wx.lib.scrolledpanel import ScrolledPanel
import plover.config as conf
from plover.gui.serial_config import SerialConfigDialog
import plover.gui.add_translation
import plover.gui.lookup
import plover.gui.dictionary_editor
from plover.app import update_engine
from plover.machine.registry import machine_registry
from plover.exception import InvalidConfigurationError
from plover.dictionary.loading_manager import manager as dict_manager
from plover.gui.paper_tape import StrokeDisplayDialog
from plover.gui.keyboard_config import KeyboardConfigDialog

EDIT_BUTTON_NAME = "Edit"
ADD_TRANSLATION_BUTTON_NAME = "Add Translation"
ADD_DICTIONARY_BUTTON_NAME = "Add Dictionary"
LOOKUP_BUTTON_NAME = "Lookup"
MACHINE_CONFIG_TAB_NAME = "Machine"
DISPLAY_CONFIG_TAB_NAME = "Display"
OUTPUT_CONFIG_TAB_NAME = "Output"
DICTIONARY_CONFIG_TAB_NAME = "Dictionary"
LOGGING_CONFIG_TAB_NAME = "Logging"
SAVE_CONFIG_BUTTON_NAME = "Save"
MACHINE_LABEL = "Stenotype Machine:"
MACHINE_AUTO_START_LABEL = "Automatically Start"
LOG_FILE_LABEL = "Log File:"
LOG_STROKES_LABEL = "Log Strokes"
LOG_TRANSLATIONS_LABEL = "Log Translations"
LOG_FILE_DIALOG_TITLE = "Select a Log File"
CONFIG_BUTTON_NAME = "Configure..."
SPACE_PLACEMENTS_LABEL = "Space Placement:"
SPACE_PLACEMENT_BEFORE = "Before Output"
SPACE_PLACEMENT_AFTER = "After Output"
SPACE_PLACEMENTS = [SPACE_PLACEMENT_BEFORE, SPACE_PLACEMENT_AFTER]
CONFIG_PANEL_SIZE = (-1, -1)
UI_BORDER = 4
COMPONENT_SPACE = 3
UP_IMAGE_FILE = os.path.join(conf.ASSETS_DIR, 'up.png')
DOWN_IMAGE_FILE = os.path.join(conf.ASSETS_DIR, 'down.png')
REMOVE_IMAGE_FILE = os.path.join(conf.ASSETS_DIR, 'remove.png')
TITLE = "Plover Configuration"

class ConfigurationDialog(wx.Dialog):
    """A GUI for viewing and editing Plover configuration files.

    Changes to the configuration file are saved when the GUI is closed. Changes
    will take effect the next time the configuration file is read by the
    application, which is typically after an application restart.

    """
    
    # Keep track of other instances of ConfigurationDialog.
    other_instances = []
    
    def __init__(self, engine, config, parent):
        """Create a configuration GUI based on the given config file.

        Arguments:

        configuration file to view and edit.
        during_plover_init -- If this is set to True, the configuration dialog
        won't tell the user that Plover needs to be restarted.
        """
        pos = (config.get_config_frame_x(), config.get_config_frame_y())
        size = wx.Size(config.get_config_frame_width(), 
                       config.get_config_frame_height())
        wx.Dialog.__init__(self, parent, title=TITLE, pos=pos, size=size, 
                           style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.engine = engine
        self.config = config

        # Close all other instances.
        if self.other_instances:
            for instance in self.other_instances:
                instance.Close()
        del self.other_instances[:]
        self.other_instances.append(self)

        sizer = wx.BoxSizer(wx.VERTICAL)

        # The tab container
        notebook = wx.Notebook(self)

        # Configuring each tab
        self.machine_config = MachineConfig(self.config, notebook)
        self.dictionary_config = DictionaryConfig(self.engine, self.config, 
                                                  notebook)
        self.logging_config = LoggingConfig(self.config, notebook)
        self.display_config = DisplayConfig(self.config, notebook)
        self.output_config = OutputConfig(self.config, notebook)

        # Adding each tab
        notebook.AddPage(self.machine_config, MACHINE_CONFIG_TAB_NAME)
        notebook.AddPage(self.dictionary_config, DICTIONARY_CONFIG_TAB_NAME)
        notebook.AddPage(self.logging_config, LOGGING_CONFIG_TAB_NAME)
        notebook.AddPage(self.display_config, DISPLAY_CONFIG_TAB_NAME)
        notebook.AddPage(self.output_config, OUTPUT_CONFIG_TAB_NAME)

        sizer.Add(notebook, proportion=1, flag=wx.EXPAND)

        # The bottom button container
        button_sizer = wx.StdDialogButtonSizer()

        # Configuring and adding the save button
        save_button = wx.Button(self, wx.ID_SAVE, SAVE_CONFIG_BUTTON_NAME)
        save_button.SetDefault()
        button_sizer.AddButton(save_button)

        # Configuring and adding the cancel button
        cancel_button = wx.Button(self, wx.ID_CANCEL)
        button_sizer.AddButton(cancel_button)
        button_sizer.Realize()

        sizer.Add(button_sizer, flag=wx.ALL | wx.ALIGN_RIGHT, border=UI_BORDER)
        
        self.SetSizer(sizer)
        self.SetAutoLayout(True)
        sizer.Layout()
        #sizer.Fit(self)
        
        self.SetRect(AdjustRectToScreen(self.GetRect()))
        
        # Binding the save button to the self._save callback
        self.Bind(wx.EVT_BUTTON, self._save, save_button)
        
        self.Bind(wx.EVT_MOVE, self.on_move)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        
    def on_move(self, event):
        pos = self.GetScreenPositionTuple()
        self.config.set_config_frame_x(pos[0]) 
        self.config.set_config_frame_y(pos[1])
        event.Skip()

    def on_size(self, event):
        size = self.GetSize()
        self.config.set_config_frame_width(size.GetWidth())
        self.config.set_config_frame_height(size.GetHeight())
        event.Skip()
        
    def on_close(self, event):
        self.other_instances.remove(self)
        event.Skip()

    def _save(self, event):
        old_config = self.config.clone()
        
        self.machine_config.save()
        self.dictionary_config.save()
        self.logging_config.save()
        self.display_config.save()
        self.output_config.save()

        try:
            update_engine(self.engine, old_config, self.config)
        except InvalidConfigurationError as e:
            alert_dialog = wx.MessageDialog(self,
                                            unicode(e),
                                            "Configuration error",
                                            wx.OK | wx.ICON_INFORMATION)
            alert_dialog.ShowModal()
            alert_dialog.Destroy()
            return

        with open(self.config.target_file, 'wb') as f:
            self.config.save(f)

        if self.IsModal():
            self.EndModal(wx.ID_SAVE)
        else:
            self.Close()


class MachineConfig(wx.Panel):
    """Stenotype machine configuration graphical user interface."""

    def __init__(self, config, parent):
        """Create a configuration component based on the given ConfigParser.

        Arguments:

        config -- A Config object.

        parent -- This component's parent component.

        """
        wx.Panel.__init__(self, parent, size=CONFIG_PANEL_SIZE)
        self.config = config
        sizer = wx.BoxSizer(wx.VERTICAL)
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(wx.StaticText(self, label=MACHINE_LABEL),
                border=COMPONENT_SPACE,
                flag=wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT)
        machines = machine_registry.get_all_names()
        value = self.config.get_machine_type()
        self.choice = wx.Choice(self, choices=machines)
        self.choice.SetStringSelection(machine_registry.resolve_alias(value))
        self.Bind(wx.EVT_CHOICE, self._update, self.choice)
        box.Add(self.choice, proportion=1, flag=wx.EXPAND)
        self.config_button = wx.Button(self,
                                       id=wx.ID_PREFERENCES,
                                       label=CONFIG_BUTTON_NAME)
        box.Add(self.config_button)

        self.auto_start_checkbox = wx.CheckBox(self,
                                               label=MACHINE_AUTO_START_LABEL)
        auto_start = config.get_auto_start()
        self.auto_start_checkbox.SetValue(auto_start)

        sizer.Add(box, border=UI_BORDER, flag=wx.ALL | wx.EXPAND)
        sizer.Add(self.auto_start_checkbox,
                  border=UI_BORDER,
                  flag=wx.ALL | wx.EXPAND)
        self.SetSizer(sizer)
        self._update()
        self.Bind(wx.EVT_BUTTON, self._advanced_config, self.config_button)

    def save(self):
        """Write all parameters to the config."""
        machine_type = self.choice.GetStringSelection()
        self.config.set_machine_type(machine_type)
        auto_start = self.auto_start_checkbox.GetValue()
        self.config.set_auto_start(auto_start)
        if self.advanced_options:
            self.config.set_machine_specific_options(machine_type, 
                                                     self.advanced_options)

    def _advanced_config(self, event=None):
        class Struct(object):
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
        config_instance = Struct(**self.advanced_options)
        dialog = None
        if 'port' in self.advanced_options:
            scd = SerialConfigDialog(config_instance, self, self.config)
            scd.ShowModal()  # SerialConfigDialog destroys itself.
        else:
            kbd = KeyboardConfigDialog(config_instance, self, self.config)
            kbd.ShowModal()
            kbd.Destroy()
        self.advanced_options = config_instance.__dict__

    def _update(self, event=None):
        # Refreshes the UI to reflect current data.
        machine_name = self.choice.GetStringSelection()
        options = self.config.get_machine_specific_options(machine_name)
        self.advanced_options = options
        self.config_button.Enable(bool(options))


class DictionaryConfig(ScrolledPanel):
    
    DictionaryControls = namedtuple('DictionaryControls', 
                                    'sizer up down remove label')
    
    """Dictionary configuration graphical user interface."""
    def __init__(self, engine, config, parent):
        """Create a configuration component based on the given ConfigParser.

        Arguments:

        config -- A Config object.

        parent -- This component's parent component.

        """
        ScrolledPanel.__init__(self, parent, size=CONFIG_PANEL_SIZE)
        self.engine = engine
        self.config = config
        dictionaries = config.get_dictionary_file_names()
        
        self.up_bitmap = wx.Bitmap(UP_IMAGE_FILE, wx.BITMAP_TYPE_PNG)
        self.down_bitmap = wx.Bitmap(DOWN_IMAGE_FILE, wx.BITMAP_TYPE_PNG)
        self.remove_bitmap = wx.Bitmap(REMOVE_IMAGE_FILE, wx.BITMAP_TYPE_PNG)
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        button = wx.Button(self, wx.ID_ANY, EDIT_BUTTON_NAME)
        button_sizer.Add(button, border=UI_BORDER, flag=wx.ALL)
        button.Bind(wx.EVT_BUTTON, self.show_edit)
        
        button = wx.Button(self, wx.ID_ANY, ADD_TRANSLATION_BUTTON_NAME)
        button_sizer.Add(button, border=UI_BORDER, flag=wx.ALL)
        button.Bind(wx.EVT_BUTTON, self.show_add_translation)
        
        button = wx.Button(self, wx.ID_ANY, ADD_DICTIONARY_BUTTON_NAME)
        button_sizer.Add(button, border=UI_BORDER, flag=wx.ALL)
        button.Bind(wx.EVT_BUTTON, self.add_dictionary)

        button = wx.Button(self, wx.ID_ANY, LOOKUP_BUTTON_NAME)
        button_sizer.Add(button, border=UI_BORDER, flag=wx.ALL)
        button.Bind(wx.EVT_BUTTON, self.show_lookup)
        
        main_sizer.Add(button_sizer)
        
        self.dictionary_controls = []
        self.dicts_sizer = wx.BoxSizer(wx.VERTICAL)
        for filename in dictionaries:
            self.add_row(filename)

        main_sizer.Add(self.dicts_sizer)
        
        self.mask = 'Json files (*%s)|*%s|RTF/CRE files (*%s)|*%s' % (
            conf.JSON_EXTENSION, conf.JSON_EXTENSION, 
            conf.RTF_EXTENSION, conf.RTF_EXTENSION, 
        )
        
        self.SetSizer(main_sizer)
        self.SetupScrolling()

    def save(self):
        """Write all parameters to the config."""
        filenames = [x.label.GetLabel() for x in self.dictionary_controls]
        self.config.set_dictionary_file_names(filenames)
        
    def show_add_translation(self, event):
        plover.gui.add_translation.Show(self, self.engine, self.config)

    def show_lookup(self, event):
        plover.gui.lookup.Show(self, self.engine, self.config)

    def show_edit(self, event):
        plover.gui.dictionary_editor.Show(self, self.engine, self.config)

    def add_dictionary(self, event):
        dlg = wx.FileDialog(self, "Choose a file", os.getcwd(), "", self.mask, 
                            wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            all_dicts = [x.label.GetLabel() for x in self.dictionary_controls]
            if path not in all_dicts:
                self.add_row(path)
        dlg.Destroy()
        
    def add_row(self, filename):
        dict_manager.start_loading(filename)
        index = len(self.dictionary_controls)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        up = wx.BitmapButton(self, bitmap=self.up_bitmap)
        up.Bind(wx.EVT_BUTTON, lambda e: self.move_row_down(index-1))
        if len(self.dictionary_controls) == 0:
            up.Disable()
        else:
            self.dictionary_controls[-1].down.Enable()
        sizer.Add(up)
        down = wx.BitmapButton(self, bitmap=self.down_bitmap)
        down.Bind(wx.EVT_BUTTON, lambda e: self.move_row_down(index))
        down.Disable()
        sizer.Add(down)
        remove = wx.BitmapButton(self, bitmap=self.remove_bitmap)
        remove.Bind(wx.EVT_BUTTON, 
                    lambda e: wx.CallAfter(self.remove_row, index))
        sizer.Add(remove)
        label = wx.StaticText(self, label=filename)
        sizer.Add(label)
        controls = self.DictionaryControls(sizer, up, down, remove, label)
        self.dictionary_controls.append(controls)
        self.dicts_sizer.Add(sizer)
        if self.GetSizer():
            self.GetSizer().Layout()

    def remove_row(self, index):
        names = [self.dictionary_controls[i].label.GetLabel() 
                 for i in range(index+1, len(self.dictionary_controls))]
        for i, name in enumerate(names, start=index):
            self.dictionary_controls[i].label.SetLabel(name)
        controls = self.dictionary_controls[-1]
        self.dicts_sizer.Detach(controls.sizer)
        for e in controls:
            e.Destroy()
        del self.dictionary_controls[-1]
        if self.dictionary_controls:
            self.dictionary_controls[-1].down.Disable()
        self.GetSizer().Layout()
        
    def move_row_down(self, index):
        top_label = self.dictionary_controls[index].label
        bottom_label = self.dictionary_controls[index+1].label
        tmp = bottom_label.GetLabel()
        bottom_label.SetLabel(top_label.GetLabel())
        top_label.SetLabel(tmp)
        self.GetSizer().Layout()
        
class LoggingConfig(wx.Panel):
    """Logging configuration graphical user interface."""
    def __init__(self, config, parent):
        """Create a configuration component based on the given Config.

        Arguments:

        config -- A Config object.

        parent -- This component's parent component.

        """
        wx.Panel.__init__(self, parent, size=CONFIG_PANEL_SIZE)
        self.config = config
        sizer = wx.BoxSizer(wx.VERTICAL)
        log_file = config.get_log_file_name()
        log_file = os.path.join(conf.CONFIG_DIR, log_file)
        log_dir = os.path.split(log_file)[0]
        self.file_browser = filebrowse.FileBrowseButton(
                                            self,
                                            labelText=LOG_FILE_LABEL,
                                            fileMask='*' + conf.LOG_EXTENSION,
                                            fileMode=wx.SAVE,
                                            dialogTitle=LOG_FILE_DIALOG_TITLE,
                                            initialValue=log_file,
                                            startDirectory=log_dir,
                                            )
        sizer.Add(self.file_browser, border=UI_BORDER, flag=wx.ALL | wx.EXPAND)
        self.log_strokes_checkbox = wx.CheckBox(self, label=LOG_STROKES_LABEL)
        stroke_logging = config.get_enable_stroke_logging()
        self.log_strokes_checkbox.SetValue(stroke_logging)
        sizer.Add(self.log_strokes_checkbox,
                  border=UI_BORDER,
                  flag=wx.ALL | wx.EXPAND)
        self.log_translations_checkbox = wx.CheckBox(self,
                                                 label=LOG_TRANSLATIONS_LABEL)
        translation_logging = config.get_enable_translation_logging()
        self.log_translations_checkbox.SetValue(translation_logging)
        sizer.Add(self.log_translations_checkbox,
                  border=UI_BORDER,
                  flag=wx.ALL | wx.EXPAND)
        self.SetSizer(sizer)

    def save(self):
        """Write all parameters to the config."""
        self.config.set_log_file_name(self.file_browser.GetValue())
        self.config.set_enable_stroke_logging(
            self.log_strokes_checkbox.GetValue())
        self.config.set_enable_translation_logging(
            self.log_translations_checkbox.GetValue())

class DisplayConfig(wx.Panel):
    
    SHOW_STROKES_TEXT = "Open strokes display on startup"
    SHOW_STROKES_BUTTON_TEXT = "Open stroke display"
    
    """Display configuration graphical user interface."""
    def __init__(self, config, parent):
        """Create a configuration component based on the given Config.

        Arguments:

        config -- A Config object.

        parent -- This component's parent component.

        """
        wx.Panel.__init__(self, parent, size=CONFIG_PANEL_SIZE)
        self.config = config
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        show_strokes_button = wx.Button(self, 
                                        label=self.SHOW_STROKES_BUTTON_TEXT)
        show_strokes_button.Bind(wx.EVT_BUTTON, self.on_show_strokes)
        sizer.Add(show_strokes_button, border=UI_BORDER, flag=wx.ALL)
        
        self.show_strokes = wx.CheckBox(self, label=self.SHOW_STROKES_TEXT)
        self.show_strokes.SetValue(config.get_show_stroke_display())
        sizer.Add(self.show_strokes, border=UI_BORDER, 
                  flag=wx.LEFT | wx.RIGHT | wx.BOTTOM)

        self.SetSizer(sizer)

    def save(self):
        """Write all parameters to the config."""
        self.config.set_show_stroke_display(self.show_strokes.GetValue())

    def on_show_strokes(self, event):
        StrokeDisplayDialog.display(self.GetParent(), self.config)

class OutputConfig(wx.Panel):

    """Display configuration graphical user interface."""
    def __init__(self, config, parent):
        """Create a configuration component based on the given Config.

        Arguments:

        config -- A Config object.

        parent -- This component's parent component.

        """
        wx.Panel.__init__(self, parent, size=CONFIG_PANEL_SIZE)
        self.config = config
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(wx.StaticText(self, label=SPACE_PLACEMENTS_LABEL),
                border=COMPONENT_SPACE,
                flag=wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT)
        self.choice = wx.Choice(self, choices=SPACE_PLACEMENTS)
        self.choice.SetStringSelection(self.config.get_space_placement())
        box.Add(self.choice, proportion=1, flag=wx.EXPAND)
        sizer.Add(box, border=UI_BORDER, flag=wx.ALL | wx.EXPAND)        

        self.SetSizer(sizer)

    def save(self):
        """Write all parameters to the config."""
        self.config.set_space_placement(self.choice.GetStringSelection())

########NEW FILE########
__FILENAME__ = dictionary_editor
import threading
import wx
from wx.lib.utils import AdjustRectToScreen
import plover.gui.util as util
from plover.dictionary_editor_store import DictionaryEditorStore
from wx.grid import EVT_GRID_LABEL_LEFT_CLICK
from wx.grid import PyGridTableBase

TITLE = 'Plover: Dictionary Editor'

FILTER_BY_STROKE_TEXT = 'Filter by stroke:'
FILTER_BY_TRANSLATION_TEXT = 'Filter by translation:'
DO_FILTER_BUTTON_NAME = 'Filter'
INSERT_BUTTON_NAME = 'New Entry'
DELETE_BUTTON_NAME = 'Delete Selected'
SAVE_BUTTON_NAME = 'Save and Close'
CANCEL_BUTTON_NAME = 'Cancel'

class DictionaryEditor(wx.Dialog):

    BORDER = 3

    other_instances = []

    def __init__(self, parent, engine, config):
        pos = (config.get_dictionary_editor_frame_x(),
               config.get_dictionary_editor_frame_y())
        wx.Dialog.__init__(self, parent, wx.ID_ANY, TITLE,
                           pos, wx.DefaultSize, 
                           wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER, wx.DialogNameStr)

        self.config = config

        self.show_closing_prompt = True

        # layout
        global_sizer = wx.BoxSizer(wx.VERTICAL)

        filter_sizer = wx.BoxSizer(wx.HORIZONTAL)

        filter_left_sizer = wx.FlexGridSizer(2, 2, 4, 10)

        label = wx.StaticText(self, label=FILTER_BY_STROKE_TEXT)
        filter_left_sizer.Add(label, 
                  flag=wx.ALIGN_CENTER_VERTICAL, 
                  border=self.BORDER)
        
        self.filter_by_stroke = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER, size=wx.Size(200, 20))
        self.Bind(wx.EVT_TEXT_ENTER, self._do_filter, self.filter_by_stroke)
        filter_left_sizer.Add(self.filter_by_stroke)

        label = wx.StaticText(self, label=FILTER_BY_TRANSLATION_TEXT)
        filter_left_sizer.Add(label, 
                  flag=wx.ALIGN_CENTER_VERTICAL, 
                  border=self.BORDER)

        self.filter_by_translation = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER, size=wx.Size(200, 20))
        self.Bind(wx.EVT_TEXT_ENTER, self._do_filter, self.filter_by_translation)
        filter_left_sizer.Add(self.filter_by_translation)

        filter_sizer.Add(filter_left_sizer, flag=wx.ALL, border=self.BORDER)

        do_filter_button = wx.Button(self, label=DO_FILTER_BUTTON_NAME)
        self.Bind(wx.EVT_BUTTON, self._do_filter, do_filter_button)
        
        filter_sizer.Add(do_filter_button, flag=wx.EXPAND | wx.ALL, border=self.BORDER)

        global_sizer.Add(filter_sizer, flag=wx.ALL, border=self.BORDER)

        self.store = DictionaryEditorStore(engine, config)

        # grid
        self.grid = DictionaryEditorGrid(self, size=wx.Size(800, 600))
        self.grid.CreateGrid(self.store, 0, 3)
        self.grid.SetColSize(0, 250)
        self.grid.SetColSize(1, 250)
        self.grid.SetColSize(2, 180)
        global_sizer.Add(self.grid, 1, wx.EXPAND)

        buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)

        insert_button = wx.Button(self, label=INSERT_BUTTON_NAME)
        self.Bind(wx.EVT_BUTTON, self._insert_new, insert_button)

        buttons_sizer.Add(insert_button, flag=wx.ALL, border=self.BORDER)

        delete_button = wx.Button(self, label=DELETE_BUTTON_NAME)
        self.Bind(wx.EVT_BUTTON, self._delete, delete_button)

        buttons_sizer.Add(delete_button, flag=wx.ALL, border=self.BORDER)

        buttons_sizer.Add((0, 0), 1, wx.EXPAND)

        save_button = wx.Button(self, label=SAVE_BUTTON_NAME)
        self.Bind(wx.EVT_BUTTON, self._save_close, save_button)

        buttons_sizer.Add(save_button, flag=wx.ALL, border=self.BORDER)

        cancel_button = wx.Button(self, label=CANCEL_BUTTON_NAME)
        self.Bind(wx.EVT_BUTTON, self._cancel_close, cancel_button)

        buttons_sizer.Add(cancel_button, flag=wx.ALL, border=self.BORDER)

        global_sizer.Add(buttons_sizer, 0, flag=wx.EXPAND | wx.ALL, border=self.BORDER)

        self.Bind(wx.EVT_MOVE, self._on_move)
        self.Bind(wx.EVT_CLOSE, self._on_close)

        self.SetAutoLayout(True)
        self.SetSizer(global_sizer)
        global_sizer.Fit(self)
        global_sizer.SetSizeHints(self)
        self.Layout()
        self.SetRect(AdjustRectToScreen(self.GetRect()))
        
        self.last_window = util.GetForegroundWindow()
        
        # Now that we saved the last window we'll close other instances. This 
        # may restore their original window but we've already saved ours so it's 
        # fine.
        for instance in self.other_instances:
            instance.Close()
        del self.other_instances[:]
        self.other_instances.append(self)

    def _do_filter(self, event=None):
        threading.Thread(target=self._do_filter_thread).start()

    def _do_filter_thread(self):
        self.store.ApplyFilter(self.filter_by_stroke.GetValue(), self.filter_by_translation.GetValue())
        self.grid.RefreshView()

    def _insert_new(self, event=None):
        self.grid.InsertNew()

    def _delete(self, event=None):
        self.grid.DeleteSelected()

    def _save_close(self, event=None):
        self.show_closing_prompt = False
        self.store.SaveChanges()
        self.Close()

    def _cancel_close(self, event=None):
        self.show_closing_prompt = True
        self.Close()

    def _on_move(self, event):
        pos = self.GetScreenPositionTuple()
        self.config.set_dictionary_editor_frame_x(pos[0])
        self.config.set_dictionary_editor_frame_y(pos[1])
        event.Skip()

    def _on_close(self, event=None):
        result = wx.ID_YES
        if self.show_closing_prompt:
            dlg = wx.MessageDialog(self, "You will lose your changes. Are you sure?", "Cancel", wx.YES_NO | wx.ICON_QUESTION)
            result = dlg.ShowModal()
            dlg.Destroy()
        if result == wx.ID_YES:
            try:
                util.SetForegroundWindow(self.last_window)
            except:
                pass
            self.other_instances.remove(self)
            self.Destroy()

class DictionaryEditorGrid(wx.grid.Grid):
    """ Dictionary Manager's grid """
    GRID_LABEL_STROKE = "Stroke"
    GRID_LABEL_TRANSLATION = "Translation"
    GRID_LABEL_DICTIONARY = "Dictionary"
    GRID_LABELS = [GRID_LABEL_STROKE, GRID_LABEL_TRANSLATION, GRID_LABEL_DICTIONARY]

    def __init__(self, *args, **kwargs):
        wx.grid.Grid.__init__(self, *args, **kwargs)

        self.parent = args[0]

        self._changedRow = None

    def CreateGrid(self, store, rows, cols):
        """ Create the grid """

        wx.grid.Grid.CreateGrid(self, rows, cols)
        wx.grid.Grid.DisableDragRowSize(self)

        self.store = store

        # Set GridTable
        self._table = DictionaryEditorGridTable(self.store)
        self.SetTable(self._table)

        self._sortingColumn = 0
        self._sortingAsc = None

        self.Bind(EVT_GRID_LABEL_LEFT_CLICK, self._onLabelClick)

    def RefreshView(self):
        self._table.ResetView(self)

    def InsertNew(self):
        selected_row = self.GetGridCursorRow()
        self.store.InsertNew(selected_row)
        self._table.ResetView(self)

    def DeleteSelected(self):
        selected_row = self.GetGridCursorRow()
        self.store.DeleteSelected(selected_row)
        self._table.ResetView(self)

    def _onLabelClick(self, evt):
        """ Handle Grid label click"""

        if evt.Row == -1:
            if evt.Col >= 0:
                self.store.Sort(evt.Col)
                sort_column = self.store.GetSortColumn()
                sort_mode = self.store.GetSortMode()
                self._updateGridLabel(sort_column, sort_mode)
                self._table.ResetView(self)

        if evt.Col == -1:
            if evt.Row >= 0:
                self.SelectRow(evt.Row)
                self.SetGridCursor(evt.Row, 0)

    def _updateGridLabel(self, column, mode):
        """ Change grid's column labels """

        directionLabel = ""
        if mode is not None:
            directionLabel = " (asc)" if mode else " (desc)"
        for i in range(3):
            self._table.SetColLabelValue(i, self.GRID_LABELS[i] + (directionLabel if column == i else ""))

class DictionaryEditorGridTable(PyGridTableBase):
    """
    A custom wx.Grid Table using user supplied data
    """
    def __init__(self, store):
        """ Init GridTableBase with a Store. """

        # The base class must be initialized *first*
        PyGridTableBase.__init__(self)
        self.store = store
        self.col_names = ["Stroke", "Translation", "Dictionary"]

        self._rows = self.GetNumberRows()
        self._cols = self.GetNumberCols()

    def GetNumberCols(self):
        return len(self.col_names)

    def GetNumberRows(self):
        return self.store.GetNumberOfRows()

    def GetColLabelValue(self, col):
        return self.col_names[col]

    def SetColLabelValue(self, col, name):
        self.col_names[col] = name

    def GetRowLabelValue(self, row):
        return str(row + 1)

    def GetValue(self, row, col):
        return self.store.GetValue(row, col)

    def SetValue(self, row, col, value):
        self.store.SetValue(row, col, value)

    def ResetView(self, grid):

        grid.BeginBatch()

        for current, new, delmsg, addmsg in [
            (self._rows, self.GetNumberRows(), wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED),
            (self._cols, self.GetNumberCols(), wx.grid.GRIDTABLE_NOTIFY_COLS_DELETED, wx.grid.GRIDTABLE_NOTIFY_COLS_APPENDED)
        ]:
            if new < current:
                msg = wx.grid.GridTableMessage(self,delmsg,new,current-new)
                grid.ProcessTableMessage(msg)
            elif new > current:
                msg = wx.grid.GridTableMessage(self,addmsg,new-current)
                grid.ProcessTableMessage(msg)
                self.UpdateValues(grid)

        grid.EndBatch()

        self._rows = self.GetNumberRows()
        self._cols = self.GetNumberCols()

        grid.AdjustScrollbars()
        grid.ForceRefresh()

    def UpdateValues(self, grid):
        """Update all displayed values"""
        # This sends an event to the grid table to update all of the values
        msg = wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        grid.ProcessTableMessage(msg)

def Show(parent, engine, config):
    dialog_instance = DictionaryEditor(parent, engine, config)
    dialog_instance.Show()
    dialog_instance.Raise()
    util.SetTopApp()

########NEW FILE########
__FILENAME__ = keyboard_config
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

import wx
from wx.lib.utils import AdjustRectToScreen

DIALOG_TITLE = 'Keyboard Configuration'
ARPEGGIATE_LABEL = "Arpeggiate"
ARPEGGIATE_INSTRUCTIONS = """Arpeggiate allows using non-NKRO keyboards.
Each key can be pressed separately and the space bar
is pressed to send the stroke."""
UI_BORDER = 4

class KeyboardConfigDialog(wx.Dialog):
    """Keyboard configuration dialog."""

    def __init__(self, options, parent, config):
        self.config = config
        self.options = options
        
        pos = (config.get_keyboard_config_frame_x(), 
               config.get_keyboard_config_frame_y())
        wx.Dialog.__init__(self, parent, title=DIALOG_TITLE, pos=pos)

        sizer = wx.BoxSizer(wx.VERTICAL)
        
        instructions = wx.StaticText(self, label=ARPEGGIATE_INSTRUCTIONS)
        sizer.Add(instructions, border=UI_BORDER, flag=wx.ALL)
        self.arpeggiate_option = wx.CheckBox(self, label=ARPEGGIATE_LABEL)
        self.arpeggiate_option.SetValue(options.arpeggiate)
        sizer.Add(self.arpeggiate_option, border=UI_BORDER, 
                  flag=wx.LEFT | wx.RIGHT | wx.BOTTOM)
        
        ok_button = wx.Button(self, id=wx.ID_OK)
        ok_button.SetDefault()
        cancel_button = wx.Button(self, id=wx.ID_CANCEL)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(ok_button, border=UI_BORDER, flag=wx.ALL)
        button_sizer.Add(cancel_button, border=UI_BORDER, flag=wx.ALL)
        sizer.Add(button_sizer, flag=wx.ALL | wx.ALIGN_RIGHT, border=UI_BORDER)
                  
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.SetRect(AdjustRectToScreen(self.GetRect()))
        
        self.Bind(wx.EVT_MOVE, self.on_move)
        ok_button.Bind(wx.EVT_BUTTON, self.on_ok)
        cancel_button.Bind(wx.EVT_BUTTON, self.on_cancel)

    def on_move(self, event):
        pos = self.GetScreenPositionTuple()
        self.config.set_keyboard_config_frame_x(pos[0]) 
        self.config.set_keyboard_config_frame_y(pos[1])
        event.Skip()

    def on_ok(self, event):
        self.options.arpeggiate = self.arpeggiate_option.GetValue()
        self.EndModal(wx.ID_OK)
    
    def on_cancel(self, event):
        self.EndModal(wx.ID_CANCEL)
        
        
        
########NEW FILE########
__FILENAME__ = lookup
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

import wx
from wx.lib.utils import AdjustRectToScreen
import sys
from plover.steno import normalize_steno
import plover.gui.util as util

TITLE = 'Plover: Lookup'

class LookupDialog(wx.Dialog):

    BORDER = 3
    TRANSLATION_TEXT = 'Text:'
    
    other_instances = []
    
    def __init__(self, parent, engine, config):
        pos = (config.get_lookup_frame_x(), 
               config.get_lookup_frame_y())
        wx.Dialog.__init__(self, parent, wx.ID_ANY, TITLE, 
                           pos, wx.DefaultSize, 
                           wx.DEFAULT_DIALOG_STYLE, wx.DialogNameStr)

        self.config = config

        # components
        self.translation_text = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        cancel = wx.Button(self, id=wx.ID_CANCEL)
        self.listbox = wx.ListBox(self, size=wx.Size(210, 200))
        
        # layout
        global_sizer = wx.BoxSizer(wx.VERTICAL)
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, label=self.TRANSLATION_TEXT)
        sizer.Add(label, 
                  flag=wx.TOP | wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.ALIGN_CENTER_VERTICAL, 
                  border=self.BORDER)
        sizer.Add(self.translation_text, 
                  flag=wx.TOP | wx.RIGHT | wx.BOTTOM | wx.ALIGN_CENTER_VERTICAL, 
                  border=self.BORDER)
        sizer.Add(cancel, 
                  flag=wx.TOP | wx.RIGHT | wx.BOTTOM | wx.ALIGN_CENTER_VERTICAL, 
                  border=self.BORDER)
        global_sizer.Add(sizer)
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.listbox,
                  flag=wx.ALL | wx.FIXED_MINSIZE,
                  border=self.BORDER)

        global_sizer.Add(sizer)
        
        self.SetAutoLayout(True)
        self.SetSizer(global_sizer)
        global_sizer.Fit(self)
        global_sizer.SetSizeHints(self)
        self.Layout()
        self.SetRect(AdjustRectToScreen(self.GetRect()))
        
        # events

        # The reason for the focus event here is to skip focus on tab traversal
        # of the buttons. But it seems that on windows this prevents the button
        # from being pressed. Leave this commented out until that problem is
        # resolved.
        #button.Bind(wx.EVT_SET_FOCUS, self.on_button_gained_focus)
        cancel.Bind(wx.EVT_BUTTON, self.on_close)
        #cancel.Bind(wx.EVT_SET_FOCUS, self.on_button_gained_focus)
        self.translation_text.Bind(wx.EVT_TEXT, self.on_translation_change)
        self.translation_text.Bind(wx.EVT_SET_FOCUS, self.on_translation_gained_focus)
        self.translation_text.Bind(wx.EVT_KILL_FOCUS, self.on_translation_lost_focus)
        self.translation_text.Bind(wx.EVT_TEXT_ENTER, self.on_close)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_MOVE, self.on_move)
        
        self.engine = engine
        
        # TODO: add functions on engine for state
        self.previous_state = self.engine.translator.get_state()
        # TODO: use state constructor?
        self.engine.translator.clear_state()
        self.translation_state = self.engine.translator.get_state()
        self.engine.translator.set_state(self.previous_state)
        
        self.last_window = util.GetForegroundWindow()
        
        # Now that we saved the last window we'll close other instances. This 
        # may restore their original window but we've already saved ours so it's 
        # fine.
        for instance in self.other_instances:
            instance.Close()
        del self.other_instances[:]
        self.other_instances.append(self)

    def on_close(self, event=None):
        self.engine.translator.set_state(self.previous_state)
        try:
            util.SetForegroundWindow(self.last_window)
        except:
            pass
        self.other_instances.remove(self)
        self.Destroy()

    def on_translation_change(self, event):
        # TODO: normalize dict entries to make reverse lookup more reliable with 
        # whitespace.
        translation = event.GetString().strip()
        self.listbox.Clear()
        if translation:
            d = self.engine.get_dictionary()
            strokes_list = d.reverse_lookup(translation)
            if strokes_list:
                entries = ('/'.join(x) for x in strokes_list)
                for str in entries:
                    self.listbox.Append(str)
            else:
                self.listbox.Append('No entries')
                
        self.GetSizer().Layout()

    def on_translation_gained_focus(self, event):
        self.engine.translator.set_state(self.translation_state)
        
    def on_translation_lost_focus(self, event):
        self.engine.translator.set_state(self.previous_state)

    def on_button_gained_focus(self, event):
        self.strokes_text.SetFocus()

    def on_move(self, event):
        pos = self.GetScreenPositionTuple()
        self.config.set_lookup_frame_x(pos[0]) 
        self.config.set_lookup_frame_y(pos[1])
        event.Skip()

    def _normalized_strokes(self):
        strokes = self.strokes_text.GetValue().upper().replace('/', ' ').split()
        strokes = normalize_steno('/'.join(strokes))
        return strokes

def Show(parent, engine, config):
    dialog_instance = LookupDialog(parent, engine, config)
    dialog_instance.Show()
    dialog_instance.Raise()
    dialog_instance.translation_text.SetFocus()
    util.SetTopApp()

########NEW FILE########
__FILENAME__ = main
# Copyright (c) 2010-2011 Joshua Harlan Lifton.
# See LICENSE.txt for details.

"""The main graphical user interface.

Plover's graphical user interface is a simple task bar icon that pauses and
resumes stenotype translation and allows for application configuration.

"""

import os
import wx
import wx.animate
from wx.lib.utils import AdjustRectToScreen
import plover.app as app
from plover.config import ASSETS_DIR, SPINNER_FILE
from plover.gui.config import ConfigurationDialog
import plover.gui.add_translation
import plover.gui.lookup
from plover.oslayer.keyboardcontrol import KeyboardEmulation
from plover.machine.base import STATE_ERROR, STATE_INITIALIZING, STATE_RUNNING
from plover.machine.registry import machine_registry
from plover.exception import InvalidConfigurationError
from plover.gui.paper_tape import StrokeDisplayDialog

from plover import __name__ as __software_name__
from plover import __version__
from plover import __copyright__
from plover import __long_description__
from plover import __url__
from plover import __credits__
from plover import __license__


class PloverGUI(wx.App):
    """The main entry point for the Plover application."""

    def __init__(self, config):
        self.config = config
        wx.App.__init__(self, redirect=False)

    def OnInit(self):
        """Called just before the application starts."""
        frame = MainFrame(self.config)
        self.SetTopWindow(frame)
        frame.Show()
        return True

def gui_thread_hook(fn, *args):
    wx.CallAfter(fn, *args)

class MainFrame(wx.Frame):
    """The top-level GUI element of the Plover application."""

    # Class constants.
    TITLE = "Plover"
    ALERT_DIALOG_TITLE = TITLE
    ON_IMAGE_FILE = os.path.join(ASSETS_DIR, 'plover_on.png')
    OFF_IMAGE_FILE = os.path.join(ASSETS_DIR, 'plover_off.png')
    CONNECTED_IMAGE_FILE = os.path.join(ASSETS_DIR, 'connected.png')
    DISCONNECTED_IMAGE_FILE = os.path.join(ASSETS_DIR, 'disconnected.png')
    REFRESH_IMAGE_FILE = os.path.join(ASSETS_DIR, 'refresh.png')
    BORDER = 5
    RUNNING_MESSAGE = "running"
    STOPPED_MESSAGE = "stopped"
    ERROR_MESSAGE = "error"
    CONFIGURE_BUTTON_LABEL = "Configure..."
    ABOUT_BUTTON_LABEL = "About..."
    RECONNECT_BUTTON_LABEL = "Reconnect..."
    COMMAND_SUSPEND = 'SUSPEND'
    COMMAND_ADD_TRANSLATION = 'ADD_TRANSLATION'
    COMMAND_LOOKUP = 'LOOKUP'
    COMMAND_RESUME = 'RESUME'
    COMMAND_TOGGLE = 'TOGGLE'
    COMMAND_CONFIGURE = 'CONFIGURE'
    COMMAND_FOCUS = 'FOCUS'
    COMMAND_QUIT = 'QUIT'

    def __init__(self, config):
        self.config = config
        
        pos = wx.DefaultPosition
        size = wx.DefaultSize
        wx.Frame.__init__(self, None, title=self.TITLE, pos=pos, size=size,
                          style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER |
                                                           wx.RESIZE_BOX |
                                                           wx.MAXIMIZE_BOX))

        # Status button.
        self.on_bitmap = wx.Bitmap(self.ON_IMAGE_FILE, wx.BITMAP_TYPE_PNG)
        self.off_bitmap = wx.Bitmap(self.OFF_IMAGE_FILE, wx.BITMAP_TYPE_PNG)
        self.status_button = wx.BitmapButton(self, bitmap=self.on_bitmap)
        self.status_button.Bind(wx.EVT_BUTTON, self._toggle_steno_engine)

        # Configure button.
        self.configure_button = wx.Button(self,
                                          label=self.CONFIGURE_BUTTON_LABEL)
        self.configure_button.Bind(wx.EVT_BUTTON, self._show_config_dialog)

        # About button.
        self.about_button = wx.Button(self, label=self.ABOUT_BUTTON_LABEL)
        self.about_button.Bind(wx.EVT_BUTTON, self._show_about_dialog)

        # Machine status.
        # TODO: Figure out why spinner has darker gray background.
        self.spinner = wx.animate.GIFAnimationCtrl(self, -1, SPINNER_FILE)
        self.spinner.GetPlayer().UseBackgroundColour(True)
        self.spinner.Hide()

        self.connected_bitmap = wx.Bitmap(self.CONNECTED_IMAGE_FILE, 
                                          wx.BITMAP_TYPE_PNG)
        self.disconnected_bitmap = wx.Bitmap(self.DISCONNECTED_IMAGE_FILE, 
                                             wx.BITMAP_TYPE_PNG)
        self.connection_ctrl = wx.StaticBitmap(self, 
                                               bitmap=self.disconnected_bitmap)

        # Layout.
        global_sizer = wx.BoxSizer(wx.VERTICAL)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.status_button,
                  flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                  border=self.BORDER)
        sizer.Add(self.configure_button,
                  flag=wx.TOP | wx.BOTTOM | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
                  border=self.BORDER)
        sizer.Add(self.about_button,
                  flag=wx.TOP | wx.BOTTOM | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
                  border=self.BORDER)
        global_sizer.Add(sizer)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.spinner,
                  flag=(wx.LEFT | wx.BOTTOM | wx.RIGHT | 
                        wx.ALIGN_CENTER_VERTICAL), 
                  border=self.BORDER)
        sizer.Add(self.connection_ctrl, 
                  flag=(wx.LEFT | wx.BOTTOM | wx.RIGHT | 
                        wx.ALIGN_CENTER_VERTICAL), 
                  border=self.BORDER)
        longest_machine = max(machine_registry.get_all_names(), key=len)
        longest_state = max((STATE_ERROR, STATE_INITIALIZING, STATE_RUNNING), 
                            key=len)
        longest_status = '%s: %s' % (longest_machine, longest_state)
        self.machine_status_text = wx.StaticText(self, label=longest_status)
        sizer.Add(self.machine_status_text, 
                  flag=wx.BOTTOM | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
                  border=self.BORDER)
        refresh_bitmap = wx.Bitmap(self.REFRESH_IMAGE_FILE, wx.BITMAP_TYPE_PNG)          
        self.reconnect_button = wx.BitmapButton(self, bitmap=refresh_bitmap)
        sizer.Add(self.reconnect_button, 
                  flag=wx.BOTTOM | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 
                  border=self.BORDER)
        self.machine_status_sizer = sizer
        global_sizer.Add(sizer)
        self.SetSizer(global_sizer)
        global_sizer.Fit(self)
        
        self.SetRect(AdjustRectToScreen(self.GetRect()))

        self.Bind(wx.EVT_CLOSE, self._quit)
        self.Bind(wx.EVT_MOVE, self.on_move)
        self.reconnect_button.Bind(wx.EVT_BUTTON, 
            lambda e: app.reset_machine(self.steno_engine, self.config))

        try:
            with open(config.target_file, 'rb') as f:
                self.config.load(f)
        except InvalidConfigurationError as e:
            self._show_alert(unicode(e))
            self.config.clear()

        self.steno_engine = app.StenoEngine(gui_thread_hook)
        self.steno_engine.add_callback(
            lambda s: wx.CallAfter(self._update_status, s))
        self.steno_engine.set_output(
            Output(self.consume_command, self.steno_engine))

        while True:
            try:
                app.init_engine(self.steno_engine, self.config)
                break
            except InvalidConfigurationError as e:
                self._show_alert(unicode(e))
                dlg = ConfigurationDialog(self.steno_engine,
                                          self.config,
                                          parent=self)
                ret = dlg.ShowModal()
                if ret == wx.ID_CANCEL:
                    self._quit()
                    return
                    
        self.steno_engine.add_stroke_listener(
            StrokeDisplayDialog.stroke_handler)
        if self.config.get_show_stroke_display():
            StrokeDisplayDialog.display(self, self.config)
            
        pos = (config.get_main_frame_x(), config.get_main_frame_y())
        self.SetPosition(pos)

    def consume_command(self, command):
        # The first commands can be used whether plover is active or not.
        if command == self.COMMAND_RESUME:
            wx.CallAfter(self.steno_engine.set_is_running, True)
            return True
        elif command == self.COMMAND_TOGGLE:
            wx.CallAfter(self.steno_engine.set_is_running,
                         not self.steno_engine.is_running)
            return True
        elif command == self.COMMAND_QUIT:
            wx.CallAfter(self._quit)
            return True

        if not self.steno_engine.is_running:
            return False

        # These commands can only be run when plover is active.
        if command == self.COMMAND_SUSPEND:
            wx.CallAfter(self.steno_engine.set_is_running, False)
            return True
        elif command == self.COMMAND_CONFIGURE:
            wx.CallAfter(self._show_config_dialog)
            return True
        elif command == self.COMMAND_FOCUS:
            def f():
                self.Raise()
                self.Iconize(False)
            wx.CallAfter(f)
            return True
        elif command == self.COMMAND_ADD_TRANSLATION:
            wx.CallAfter(plover.gui.add_translation.Show, 
                         self, self.steno_engine, self.config)
            return True
        elif command == self.COMMAND_LOOKUP:
            wx.CallAfter(plover.gui.lookup.Show, 
                         self, self.steno_engine, self.config)
            return True
            
        return False

    def _update_status(self, state):
        if state:
            machine_name = machine_registry.resolve_alias(
                self.config.get_machine_type())
            self.machine_status_text.SetLabel('%s: %s' % (machine_name, state))
            self.reconnect_button.Show(state == STATE_ERROR)
            self.spinner.Show(state == STATE_INITIALIZING)
            self.connection_ctrl.Show(state != STATE_INITIALIZING)
            if state == STATE_INITIALIZING:
                self.spinner.Play()
            else:
                self.spinner.Stop()
            if state == STATE_RUNNING:
                self.connection_ctrl.SetBitmap(self.connected_bitmap)
            elif state == STATE_ERROR:
                self.connection_ctrl.SetBitmap(self.disconnected_bitmap)
            self.machine_status_sizer.Layout()
        if self.steno_engine.machine:
            self.status_button.Enable()
            if self.steno_engine.is_running:
                self.status_button.SetBitmapLabel(self.on_bitmap)
                self.SetTitle("%s: %s" % (self.TITLE, self.RUNNING_MESSAGE))
            else:
                self.status_button.SetBitmapLabel(self.off_bitmap)
                self.SetTitle("%s: %s" % (self.TITLE, self.STOPPED_MESSAGE))
        else:
            self.status_button.Disable()
            self.status_button.SetBitmapLabel(self.off_bitmap)
            self.SetTitle("%s: %s" % (self.TITLE, self.ERROR_MESSAGE))

    def _quit(self, event=None):
        if self.steno_engine:
            self.steno_engine.destroy()
        self.Destroy()

    def _toggle_steno_engine(self, event=None):
        """Called when the status button is clicked."""
        self.steno_engine.set_is_running(not self.steno_engine.is_running)

    def _show_config_dialog(self, event=None):
        dlg = ConfigurationDialog(self.steno_engine,
                                  self.config,
                                  parent=self)
        dlg.Show()

    def _show_about_dialog(self, event=None):
        """Called when the About... button is clicked."""
        info = wx.AboutDialogInfo()
        info.Name = __software_name__
        info.Version = __version__
        info.Copyright = __copyright__
        info.Description = __long_description__
        info.WebSite = __url__
        info.Developers = __credits__
        info.License = __license__
        wx.AboutBox(info)

    def _show_alert(self, message):
        alert_dialog = wx.MessageDialog(self,
                                        message,
                                        self.ALERT_DIALOG_TITLE,
                                        wx.OK | wx.ICON_INFORMATION)
        alert_dialog.ShowModal()
        alert_dialog.Destroy()

    def on_move(self, event):
        pos = self.GetScreenPositionTuple()
        self.config.set_main_frame_x(pos[0]) 
        self.config.set_main_frame_y(pos[1])
        event.Skip()
        

class Output(object):
    def __init__(self, engine_command_callback, engine):
        self.engine_command_callback = engine_command_callback
        self.keyboard_control = KeyboardEmulation()
        self.engine = engine

    def send_backspaces(self, b):
        wx.CallAfter(self.keyboard_control.send_backspaces, b)

    def send_string(self, t):
        wx.CallAfter(self.keyboard_control.send_string, t)

    def send_key_combination(self, c):
        wx.CallAfter(self.keyboard_control.send_key_combination, c)

    # TODO: test all the commands now
    def send_engine_command(self, c):
        result = self.engine_command_callback(c)
        if result and not self.engine.is_running:
            self.engine.machine.suppress = self.send_backspaces

########NEW FILE########
__FILENAME__ = paper_tape
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

"""A gui display of recent strokes."""

import wx
from wx.lib.utils import AdjustRectToScreen
from collections import deque
from plover.steno import STENO_KEY_ORDER, STENO_KEY_NUMBERS

TITLE = 'Plover: Stroke Display'
ON_TOP_TEXT = "Always on top"
UI_BORDER = 4
ALL_KEYS = ''.join(x[0].strip('-') for x in 
                   sorted(STENO_KEY_ORDER.items(), key=lambda x: x[1]))
REVERSE_NUMBERS = {v: k for k, v in STENO_KEY_NUMBERS.items()}
STROKE_LINES = 30
STYLE_TEXT = 'Style:'
STYLE_PAPER = 'Paper'
STYLE_RAW = 'Raw'
STYLES = [STYLE_PAPER, STYLE_RAW]

class StrokeDisplayDialog(wx.Dialog):
    
    other_instances = []
    strokes = deque(maxlen=STROKE_LINES)

    def __init__(self, parent, config):
        self.config = config        
        on_top = config.get_stroke_display_on_top()
        style = wx.DEFAULT_DIALOG_STYLE
        if on_top:
            style |= wx.STAY_ON_TOP
        pos = (config.get_stroke_display_x(), config.get_stroke_display_y())
        wx.Dialog.__init__(self, parent, title=TITLE, style=style, pos=pos)
                
        self.SetBackgroundColour(wx.WHITE)
                
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.on_top = wx.CheckBox(self, label=ON_TOP_TEXT)
        self.on_top.SetValue(config.get_stroke_display_on_top())
        self.on_top.Bind(wx.EVT_CHECKBOX, self.handle_on_top)
        sizer.Add(self.on_top, flag=wx.ALL, border=UI_BORDER)
        
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(wx.StaticText(self, label=STYLE_TEXT),
                border=UI_BORDER,
                flag=wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT)
        self.choice = wx.Choice(self, choices=STYLES)
        self.choice.SetStringSelection(self.config.get_stroke_display_style())
        self.choice.Bind(wx.EVT_CHOICE, self.on_style)
        box.Add(self.choice, proportion=1)
        sizer.Add(box, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 
                  border=UI_BORDER)
        
        self.header = MyStaticText(self, label=ALL_KEYS)
        font = self.header.GetFont()
        font.SetFaceName("Courier")
        self.header.SetFont(font)
        sizer.Add(self.header, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, 
                  border=UI_BORDER)
        sizer.Add(wx.StaticLine(self), flag=wx.EXPAND)

        self.labels = []
        for i in range(STROKE_LINES):
            label = MyStaticText(self, label=' ')
            self.labels.append(label)
            font = label.GetFont()
            font.SetFaceName("Courier")
            font.SetWeight(wx.FONTWEIGHT_NORMAL)
            label.SetFont(font)
            sizer.Add(label, border=UI_BORDER, 
                      flag=wx.LEFT | wx.RIGHT | wx.BOTTOM)
        
        self.SetSizer(sizer)
        self.SetAutoLayout(True)
        sizer.Layout()
        sizer.Fit(self)
        
        self.on_style()
            
        self.Show()
        self.close_all()
        self.other_instances.append(self)
        
        self.SetRect(AdjustRectToScreen(self.GetRect()))
        
        self.Bind(wx.EVT_MOVE, self.on_move)
        
    def on_move(self, event):
        pos = self.GetScreenPositionTuple()
        self.config.set_stroke_display_x(pos[0]) 
        self.config.set_stroke_display_y(pos[1])
        event.Skip()
        
    def on_close(self, event):
        self.other_instances.remove(self)
        event.Skip()
        
    def show_text(self, text):
        for i in range(len(self.labels) - 1):
            self.labels[i].SetLabel(self.labels[i + 1].GetLabel())
        self.labels[-1].SetLabel(text)
        
    def show_stroke(self, stroke):
        self.show_text(self.formatter(stroke))

    def handle_on_top(self, event):
        self.config.set_stroke_display_on_top(event.IsChecked())
        self.display(self.GetParent(), self.config)

    def on_style(self, event=None):
        format = self.choice.GetStringSelection()
        self.formatter = getattr(self, format.lower() + '_format')
        for stroke in self.strokes:
            self.show_stroke(stroke)
        self.header.SetLabel(ALL_KEYS if format == STYLE_PAPER else ' ')
        self.config.set_stroke_display_style(format)

    def paper_format(self, stroke):
        text = [' '] * len(ALL_KEYS)
        keys = stroke.steno_keys[:]
        if any(key in REVERSE_NUMBERS for key in keys):
            keys.append('#')
        for key in keys:
            if key in REVERSE_NUMBERS:
                key = REVERSE_NUMBERS[key]
            index = STENO_KEY_ORDER[key]
            text[index] = ALL_KEYS[index]
        text = ''.join(text)
        return text        

    def raw_format(self, stroke):
        return stroke.rtfcre

    @staticmethod
    def close_all():
        for instance in StrokeDisplayDialog.other_instances:
            instance.Close()
        del StrokeDisplayDialog.other_instances[:]

    @staticmethod
    def stroke_handler(stroke):
        StrokeDisplayDialog.strokes.append(stroke)
        for instance in StrokeDisplayDialog.other_instances:
            wx.CallAfter(instance.show_stroke, stroke)

    @staticmethod
    def display(parent, config):
        # StrokeDisplayDialog shows itself.
        StrokeDisplayDialog(parent, config)


# This class exists solely so that the text doesn't get grayed out when the
# window is not in focus.
# This class exists solely so that the text doesn't get grayed out when the
# window is not in focus.
class MyStaticText(wx.PyControl):
    def __init__(self, parent, id=wx.ID_ANY, label="", 
                 pos=wx.DefaultPosition, size=wx.DefaultSize, 
                 style=0, validator=wx.DefaultValidator, 
                 name="MyStaticText"):
        wx.PyControl.__init__(self, parent, id, pos, size, style|wx.NO_BORDER,
                              validator, name)
        wx.PyControl.SetLabel(self, label)
        self.InheritAttributes()
        self.SetInitialSize(size)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        
    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self)
        self.Draw(dc)

    def Draw(self, dc):
        width, height = self.GetClientSize()

        if not width or not height:
            return

        backBrush = wx.Brush(wx.WHITE, wx.SOLID)
        dc.SetBackground(backBrush)
        dc.Clear()
            
        dc.SetTextForeground(wx.BLACK)
        dc.SetFont(self.GetFont())
        label = self.GetLabel()
        dc.DrawText(label, 0, 0)

    def OnEraseBackground(self, event):
        pass

    def SetLabel(self, label):
        wx.PyControl.SetLabel(self, label)
        self.InvalidateBestSize()
        self.SetSize(self.GetBestSize())
        self.Refresh()
        
    def SetFont(self, font):
        wx.PyControl.SetFont(self, font)
        self.InvalidateBestSize()
        self.SetSize(self.GetBestSize())
        self.Refresh()
        
    def DoGetBestSize(self):
        label = self.GetLabel()
        font = self.GetFont()

        if not font:
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)

        dc = wx.ClientDC(self)
        dc.SetFont(font)

        textWidth, textHeight = dc.GetTextExtent(label)
        best = wx.Size(textWidth, textHeight)
        self.CacheBestSize(best)
        return best
    
    def AcceptsFocus(self):
        return False

    def SetForegroundColour(self, colour):
        wx.PyControl.SetForegroundColour(self, colour)
        self.Refresh()

    def SetBackgroundColour(self, colour):
        wx.PyControl.SetBackgroundColour(self, colour)
        self.Refresh()

    def GetDefaultAttributes(self):
        return wx.StaticText.GetClassDefaultAttributes()
    
    def ShouldInheritColours(self):
        return True

class fake_config(object):
    def __init__(self):
        self.on_top = True
        self.target_file = 'testfile'
        self.x = -1
        self.y = -1
        self.style = 'Raw'
        
    def get_stroke_display_on_top(self):
        return self.on_top
    
    def set_stroke_display_on_top(self, b):
        self.on_top = b
        
    def get_stroke_display_x(self):
        return self.x

    def set_stroke_display_x(self, x):
        self.x = x

    def get_stroke_display_y(self):
        return self.y

    def set_stroke_display_y(self, y):
        self.y = y

    def set_stroke_display_style(self, style):
        self.style = style
        
    def get_stroke_display_style(self):
        return self.style

    def save(self, fp):
        pass

class TestApp(wx.App):
    def OnInit(self):
        StrokeDisplayDialog.display(None, fake_config())
        #self.SetTopWindow(dlg)
        import random
        from plover.steno import Stroke
        keys = STENO_KEY_ORDER.keys()
        for i in range(100):
            num = random.randint(1, len(keys))
            StrokeDisplayDialog.stroke_handler(Stroke(random.sample(keys, num)))
        return True

if __name__ == "__main__":
    app = TestApp(0)
    app.MainLoop()

########NEW FILE########
__FILENAME__ = serial_config
# Copyright (c) 2010 Joshua Harlan Lifton.
# See LICENSE.txt for details.


"""A graphical user interface for configuring a serial port."""

from serial import Serial
from plover.oslayer.comscan import comports
import string
import wx
import wx.animate
from wx.lib.utils import AdjustRectToScreen
from threading import Thread
import os.path

from plover.config import SPINNER_FILE

DIALOG_TITLE = 'Serial Port Configuration'
USE_TIMEOUT_STR = 'Use Timeout'
RTS_CTS_STR = 'RTS/CTS'
XON_XOFF_STR = 'Xon/Xoff'
OK_STR = 'OK'
SCAN_STR = "Scan"
LOADING_STR = "Scanning ports..."
CANCEL_STR = 'Cancel'
CONNECTION_STR = 'Connection'
PORT_STR = 'Port'
BAUDRATE_STR = 'Baudrate'
DATA_FORMAT_STR = 'Data Format'
DATA_BITS_STR = 'Data Bits'
STOP_BITS_STR = 'Stop Bits'
PARITY_STR = 'Parity'
TIMEOUT_STR = 'Timeout'
SECONDS_STR = 'seconds'
FLOW_CONTROL_STR = 'Flow Control'
LABEL_BORDER = 4
GLOBAL_BORDER = 4


def enumerate_ports():
    """Enumerates available ports"""
    return sorted(x[0] for x in comports())

class SerialConfigDialog(wx.Dialog):
    """Serial port configuration dialog."""

    def __init__(self, serial, parent, config):
        """Create a configuration GUI for the given serial port.

        Arguments:

        serial -- An object containing all the current serial options. This 
        object will be modified when pressing the OK button. The object will not 
        be changed if the cancel button is pressed.

        parent -- See wx.Dialog.
        
        config -- The config object that holds plover's settings.

        """
        self.config = config
        pos = (config.get_serial_config_frame_x(), 
               config.get_serial_config_frame_y())
        wx.Dialog.__init__(self, parent, title=DIALOG_TITLE, pos=pos)

        self.serial = serial

        # Create and layout components. Components must be created after the 
        # static box that contains them or they will be unresponsive on OSX.

        global_sizer = wx.BoxSizer(wx.VERTICAL)

        static_box = wx.StaticBox(self, label=CONNECTION_STR)
        outline_sizer = wx.StaticBoxSizer(static_box, wx.VERTICAL)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(wx.StaticText(self, label=PORT_STR),
                    proportion=1,
                    flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                    border=LABEL_BORDER)
        self.port_combo_box = wx.ComboBox(self,
                                          choices=[],
                                          style=wx.CB_DROPDOWN)
        sizer.Add(self.port_combo_box, flag=wx.ALIGN_CENTER_VERTICAL)
        self.scan_button = wx.Button(self, label=SCAN_STR)
        sizer.Add(self.scan_button, flag=wx.ALIGN_CENTER_VERTICAL)
        self.loading_text = wx.StaticText(self, label=LOADING_STR)
        sizer.Add(self.loading_text,
                  flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                  border=LABEL_BORDER)
        self.loading_text.Hide()
        self.gif = wx.animate.GIFAnimationCtrl(self, -1, SPINNER_FILE)
        self.gif.GetPlayer().UseBackgroundColour(True)
        self.gif.Hide()
        sizer.Add(self.gif, flag=wx.ALIGN_CENTER_VERTICAL)
        outline_sizer.Add(sizer, flag=wx.EXPAND)
        self.port_sizer = sizer

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(wx.StaticText(self, label=BAUDRATE_STR),
                  flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                  border=LABEL_BORDER)
        self.baudrate_choice = wx.Choice(self,
                                         choices=map(str, Serial.BAUDRATES))
        sizer.Add(self.baudrate_choice, flag=wx.ALIGN_RIGHT)
        outline_sizer.Add(sizer, flag=wx.EXPAND)
        global_sizer.Add(outline_sizer,
                         flag=wx.EXPAND | wx.ALL, border=GLOBAL_BORDER)

        static_box = wx.StaticBox(self, label=DATA_FORMAT_STR)
        outline_sizer = wx.StaticBoxSizer(static_box, wx.VERTICAL)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(wx.StaticText(self, label=DATA_BITS_STR),
                  proportion=5,
                  flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                  border=LABEL_BORDER)
        self.databits_choice = wx.Choice(self,
                                         choices=map(str, Serial.BYTESIZES))
        sizer.Add(self.databits_choice, proportion=3, flag=wx.ALIGN_RIGHT)
        outline_sizer.Add(sizer, flag=wx.EXPAND)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(wx.StaticText(self, label=STOP_BITS_STR),
                  proportion=5,
                  flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                  border=LABEL_BORDER)
        self.stopbits_choice = wx.Choice(self,
                                         choices=map(str, Serial.STOPBITS))
        sizer.Add(self.stopbits_choice, proportion=3, flag=wx.ALIGN_RIGHT)
        outline_sizer.Add(sizer, flag=wx.EXPAND)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(wx.StaticText(self, label=PARITY_STR),
                  proportion=5,
                  flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                  border=LABEL_BORDER)
        self.parity_choice = wx.Choice(self,
                                       choices=map(str, Serial.PARITIES))
        sizer.Add(self.parity_choice, proportion=3, flag=wx.ALIGN_RIGHT)
        outline_sizer.Add(sizer, flag=wx.EXPAND)
        global_sizer.Add(outline_sizer,
                         flag=wx.EXPAND | wx.ALL, border=GLOBAL_BORDER)

        static_box = wx.StaticBox(self, label=TIMEOUT_STR)
        outline_sizer = wx.StaticBoxSizer(static_box, wx.HORIZONTAL)
        self.timeout_checkbox = wx.CheckBox(self, label=USE_TIMEOUT_STR)
        outline_sizer.Add(self.timeout_checkbox,
                          flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                          border=LABEL_BORDER)
        self.timeout_text_ctrl = wx.TextCtrl(self,
                                             value='',
                                             validator=FloatValidator())
        outline_sizer.Add(self.timeout_text_ctrl)
        outline_sizer.Add(wx.StaticText(self, label=SECONDS_STR),
                          flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                          border=LABEL_BORDER)
        global_sizer.Add(outline_sizer, flag=wx.ALL, border=GLOBAL_BORDER)

        static_box = wx.StaticBox(self, label=FLOW_CONTROL_STR)
        outline_sizer = wx.StaticBoxSizer(static_box, wx.HORIZONTAL)
        self.rtscts_checkbox = wx.CheckBox(self, label=RTS_CTS_STR)
        outline_sizer.Add(self.rtscts_checkbox,
                          flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                          border=LABEL_BORDER)
        self.xonxoff_checkbox = wx.CheckBox(self, label=XON_XOFF_STR)
        outline_sizer.Add(self.xonxoff_checkbox,
                          flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                          border=LABEL_BORDER)
        outline_sizer.Add((10, 10), proportion=1, flag=wx.EXPAND)
        global_sizer.Add(outline_sizer,
                         flag=wx.EXPAND | wx.ALL,
                         border=GLOBAL_BORDER)

        self.ok_button = wx.Button(self, label=OK_STR)
        cancel_button = wx.Button(self, label=CANCEL_STR)
        self.ok_button.SetDefault()
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.ok_button)
        sizer.Add(cancel_button)
        global_sizer.Add(sizer,
                         flag=wx.ALL | wx.ALIGN_RIGHT,
                         border=GLOBAL_BORDER)

        # Bind events.
        self.Bind(wx.EVT_BUTTON, self._on_ok, self.ok_button)
        self.Bind(wx.EVT_BUTTON, self._on_cancel, cancel_button)
        self.Bind(wx.EVT_CHECKBOX,
                  self._on_timeout_select,
                  self.timeout_checkbox)
        self.Bind(wx.EVT_BUTTON, self._on_scan, self.scan_button)

        self.SetAutoLayout(True)
        self.SetSizer(global_sizer)
        global_sizer.Fit(self)
        global_sizer.SetSizeHints(self)
        self.Layout()
        self.SetRect(AdjustRectToScreen(self.GetRect()))
        
        self.Bind(wx.EVT_MOVE, self.on_move)
        self.Bind(wx.EVT_CLOSE, self._on_cancel)
        
        self._update()
        self.scan_pending = False
        self.closed = False
        
        if serial.port and serial.port != 'None':
            self.port_combo_box.SetValue(serial.port)
        else:
            self._on_scan()

    def _update(self):
        # Updates the GUI to reflect the current data model.
        if self.serial.port is not None:
            self.port_combo_box.SetValue(str(self.serial.port))
        elif self.port_combo_box.GetCount() > 0:
            self.port_combo_box.SetSelection(0)
        self.baudrate_choice.SetStringSelection(str(self.serial.baudrate))
        self.databits_choice.SetStringSelection(str(self.serial.bytesize))
        self.stopbits_choice.SetStringSelection(str(self.serial.stopbits))
        self.parity_choice.SetStringSelection(str(self.serial.parity))
        if self.serial.timeout is None:
            self.timeout_text_ctrl.SetValue('')
            self.timeout_checkbox.SetValue(False)
            self.timeout_text_ctrl.Enable(False)
        else:
            self.timeout_text_ctrl.SetValue(str(self.serial.timeout))
            self.timeout_checkbox.SetValue(True)
            self.timeout_text_ctrl.Enable(True)
        self.rtscts_checkbox.SetValue(self.serial.rtscts)
        self.xonxoff_checkbox.SetValue(self.serial.xonxoff)

    def _on_ok(self, event):
        # Transfer the configuration values to the serial config object.
        sb = lambda s: int(float(s)) if float(s).is_integer() else float(s)
        self.serial.port = self.port_combo_box.GetValue()
        self.serial.baudrate = int(self.baudrate_choice.GetStringSelection())
        self.serial.bytesize = int(self.databits_choice.GetStringSelection())
        self.serial.stopbits = sb(self.stopbits_choice.GetStringSelection())
        self.serial.parity = self.parity_choice.GetStringSelection()
        self.serial.rtscts = self.rtscts_checkbox.GetValue()
        self.serial.xonxoff = self.xonxoff_checkbox.GetValue()
        if self.timeout_checkbox.GetValue():
            value = self.timeout_text_ctrl.GetValue()
            try:
                self.serial.timeout = float(value)
            except ValueError:
                self.serial.timeout = None
        else:
            self.serial.timeout = None
        self.EndModal(wx.ID_OK)
        self._destroy()
        
    def _on_cancel(self, event):
        # Dismiss the dialog without making any changes.
        self.EndModal(wx.ID_CANCEL)
        self._destroy()

    def _on_timeout_select(self, event):
        # Dis/allow user input to timeout text control.
        if self.timeout_checkbox.GetValue():
            self.timeout_text_ctrl.Enable(True)
        else:
            self.timeout_text_ctrl.Enable(False)
            
    def _on_scan(self, event=None):
        self.scan_button.Hide()
        self.port_combo_box.Hide()
        self.gif.Show()
        self.gif.Play()
        self.loading_text.Show()
        self.ok_button.Disable()
        self.port_sizer.Layout()
        t = Thread(target=self._do_scan)
        t.daemon = True
        self.scan_pending = True
        t.start()

    def _do_scan(self):
        ports = enumerate_ports()
        wx.CallAfter(self._scan_done, ports)

    def _scan_done(self, ports):
        if self.closed:
            self.Destroy()
            return
        self.scan_pending = False
        self.gif.Hide()
        self.gif.Stop()
        self.loading_text.Hide()
        self.scan_button.Show()
        self.port_combo_box.Show()
        self.port_combo_box.Clear()
        self.port_combo_box.AppendItems(ports)
        if self.port_combo_box.GetCount() > 0:
            self.port_combo_box.Select(0)
        self.ok_button.Enable()
        self.port_sizer.Layout()

    def _destroy(self):
        if self.scan_pending:
            self.closed = True
        else:
            self.Destroy()
            
    def on_move(self, event):
        pos = self.GetScreenPositionTuple()
        self.config.set_serial_config_frame_x(pos[0]) 
        self.config.set_serial_config_frame_y(pos[1])
        event.Skip()

class FloatValidator(wx.PyValidator):
    """Validates that a string can be converted to a float."""

    def __init__(self):
        """Create the validator."""
        wx.PyValidator.__init__(self)
        self.Bind(wx.EVT_CHAR, self._on_char)

    def Clone(self):
        """Return a copy of this validator."""
        return FloatValidator()

    def Validate(self, window):
        """Return True if the window's value is a float, False otherwise.

        Argument:

        window -- The parent of the control being validated.

        """
        value = self.GetWindow().GetValue()
        try:
            float(value)
            return True
        except:
            return False

    def TransferToWindow(self):
        """Trivial implementation."""
        return True

    def TransferFromWindow(self):
        """Trivial implementation."""
        return True

    def _on_char(self, event):
        # Filter text input to ensure value is always a valid float.
        key = event.GetKeyCode()
        char = chr(key)
        current_value = self.GetWindow().GetValue()
        if key < wx.WXK_SPACE or key == wx.WXK_DELETE or key > 255:
            event.Skip()
            return
        if ((char in string.digits) or
            (char == '.' and char not in current_value)):
            event.Skip()
            return
        if not wx.Validator_IsSilent():
            wx.Bell()
        return


class TestApp(wx.App):
    """A test application that brings up a SerialConfigDialog.

    Serial port information is printed both before and after the
    dialog is dismissed.
    """
    def OnInit(self):
        class SerialConfig(object):
            def __init__(self):
                self.__dict__.update({
                    'port': None,
                    'baudrate': 9600,
                    'bytesize': 8,
                    'parity': 'N',
                    'stopbits': 1,
                    'timeout': 2.0,
                    'xonxoff': False,
                    'rtscts': False,
                })
        ser = SerialConfig()
        print 'Before:', ser.__dict__
        serial_config_dialog = SerialConfigDialog(ser, None)
        self.SetTopWindow(serial_config_dialog)
        result = serial_config_dialog.ShowModal()
        print 'After:', ser.__dict__
        print 'Result:', result
        return True

if __name__ == "__main__":
    app = TestApp(0)
    app.MainLoop()

########NEW FILE########
__FILENAME__ = util
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

import sys

if sys.platform.startswith('win32'):
    import win32gui
    GetForegroundWindow = win32gui.GetForegroundWindow
    SetForegroundWindow = win32gui.SetForegroundWindow

    def SetTopApp():
        # Nothing else is necessary for windows.
        pass

elif sys.platform.startswith('darwin'):
    from Foundation import NSAppleScript
    from AppKit import NSApp, NSApplication

    def GetForegroundWindow():
        return NSAppleScript.alloc().initWithSource_("""
tell application "System Events"
    return unix id of first process whose frontmost = true
end tell""").executeAndReturnError_(None)[0].int32Value()

    def SetForegroundWindow(pid):
        NSAppleScript.alloc().initWithSource_("""
tell application "System Events"
    set the frontmost of first process whose unix id is %d to true
end tell""" % pid).executeAndReturnError_(None)

    def SetTopApp():
        NSApplication.sharedApplication()
        NSApp().activateIgnoringOtherApps_(True)

elif sys.platform.startswith('linux'):
    from subprocess import call, check_output, CalledProcessError

    def GetForegroundWindow():
        try:
            output = check_output(['xprop', '-root', '_NET_ACTIVE_WINDOW'])
            return output.split()[-1]
        except CalledProcessError:
            return None

    def SetForegroundWindow(w):
        try:
            call(['wmctrl', '-i', '-a', w])
        except CalledProcessError:
            pass

    def SetTopApp():
        try:
            call(['wmctrl', '-a', TITLE])
        except CalledProcessError:
            pass

else:
    # These functions are optional so provide a non-functional default 
    # implementation.
    def GetForegroundWindow():
        return None

    def SetForegroundWindow(w):
        pass

    def SetTopApp():
        pass

########NEW FILE########
__FILENAME__ = logger
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

"""A module to handle logging."""

import logging
from logging.handlers import RotatingFileHandler

LOGGER_NAME = 'plover_logger'
LOG_FORMAT = '%(asctime)s %(message)s'
LOG_MAX_BYTES = 10000000
LOG_COUNT = 9

class Logger(object):
    def __init__(self):
        self._logger = logging.getLogger(LOGGER_NAME)
        self._logger.setLevel(logging.DEBUG)
        self._handler = None
        self._log_strokes = False
        self._log_translations = False

    def set_filename(self, filename):
        if self._handler:
            self._logger.removeHandler(self._handler)
        handler = None
        if filename:
            handler = RotatingFileHandler(filename, maxBytes=LOG_MAX_BYTES,
                                          backupCount=LOG_COUNT,)
            handler.setFormatter(logging.Formatter(LOG_FORMAT))
            self._logger.addHandler(handler)
        self._handler = handler

    def enable_stroke_logging(self, b):
        self._log_strokes = b

    def enable_translation_logging(self, b):
        self._log_translations = b

    def log_stroke(self, steno_keys):
        if self._log_strokes and self._handler:
            self._logger.info('Stroke(%s)' % ' '.join(steno_keys))

    def log_translation(self, undo, do, prev):
        if self._log_translations and self._handler:
            # TODO: Figure out what to actually log here.
            for u in undo:
                self._logger.info('*%s', u)
            for d in do:
                self._logger.info(d)

########NEW FILE########
__FILENAME__ = base
# Copyright (c) 2010-2011 Joshua Harlan Lifton.
# See LICENSE.txt for details.

# TODO: add tests for all machines
# TODO: add tests for new status callbacks

"""Base classes for machine types. Do not use directly."""

import serial
import threading
from plover.exception import SerialPortException
import collections

STATE_STOPPED = 'closed'
STATE_INITIALIZING = 'initializing'
STATE_RUNNING = 'connected'
STATE_ERROR = 'disconnected'

class StenotypeBase(object):
    """The base class for all Stenotype classes."""

    def __init__(self):
        self.stroke_subscribers = []
        self.state_subscribers = []
        self.state = STATE_STOPPED
        self.suppress = None

    def start_capture(self):
        """Begin listening for output from the stenotype machine."""
        pass

    def stop_capture(self):
        """Stop listening for output from the stenotype machine."""
        pass

    def add_stroke_callback(self, callback):
        """Subscribe to output from the stenotype machine.

        Argument:

        callback -- The function to call whenever there is output from
        the stenotype machine and output is being captured.

        """
        self.stroke_subscribers.append(callback)

    def remove_stroke_callback(self, callback):
        """Unsubscribe from output from the stenotype machine.

        Argument:

        callback -- A function that was previously subscribed.

        """
        self.stroke_subscribers.remove(callback)

    def add_state_callback(self, callback):
        self.state_subscribers.append(callback)
        
    def remove_state_callback(self, callback):
        self.state_subscribers.remove(callback)

    def _notify(self, steno_keys):
        """Invoke the callback of each subscriber with the given argument."""
        # If the stroke matches a command while the keyboard is not suppressed 
        # then the stroke needs to be suppressed after the fact. One of the 
        # handlers will set the suppress function. This function is passed in to 
        # prevent threading issues with the gui.
        self.suppress = None
        for callback in self.stroke_subscribers:
            callback(steno_keys)
        if self.suppress:
            self._post_suppress(self.suppress, steno_keys)
            
    def _post_suppress(self, suppress, steno_keys):
        """This is a complicated way for the application to tell the machine to 
        suppress this stroke after the fact. This only currently has meaning for 
        the keyboard machine so it can backspace over the last stroke when used 
        to issue a command when plover is 'off'.
        """
        pass

    def _set_state(self, state):
        self.state = state
        for callback in self.state_subscribers:
            callback(state)

    def _stopped(self):
        self._set_state(STATE_STOPPED)

    def _initializing(self):
        self._set_state(STATE_INITIALIZING)

    def _ready(self):
        self._set_state(STATE_RUNNING)
            
    def _error(self):
        self._set_state(STATE_ERROR)

    @staticmethod
    def get_option_info():
        """Get the default options for this machine."""
        return {}

class ThreadedStenotypeBase(StenotypeBase, threading.Thread):
    """Base class for thread based machines.
    
    Subclasses should override run.
    """
    def __init__(self):
        threading.Thread.__init__(self)
        StenotypeBase.__init__(self)
        self.finished = threading.Event()

    def run(self):
        """This method should be overridden by a subclass."""
        pass

    def start_capture(self):
        """Begin listening for output from the stenotype machine."""
        self.finished.clear()
        self._initializing()
        self.start()

    def stop_capture(self):
        """Stop listening for output from the stenotype machine."""
        self.finished.set()
        try:
            self.join()
        except RuntimeError:
            pass
        self._stopped()

class SerialStenotypeBase(ThreadedStenotypeBase):
    """For use with stenotype machines that connect via serial port.

    This class implements the three methods necessary for a standard
    stenotype interface: start_capture, stop_capture, and
    add_callback.

    """

    def __init__(self, serial_params):
        """Monitor the stenotype over a serial port.

        Keyword arguments are the same as the keyword arguments for a
        serial.Serial object.

        """
        ThreadedStenotypeBase.__init__(self)
        self.serial_port = None
        self.serial_params = serial_params

    def start_capture(self):
        if self.serial_port:
            self.serial_port.close()

        try:
            self.serial_port = serial.Serial(**self.serial_params)
        except (serial.SerialException, OSError) as e:
            print e
            self._error()
            return
        if self.serial_port is None or not self.serial_port.isOpen():
            self._error()
            return
        return ThreadedStenotypeBase.start_capture(self)

    def stop_capture(self):
        """Stop listening for output from the stenotype machine."""
        ThreadedStenotypeBase.stop_capture(self)
        if self.serial_port:
            self.serial_port.close()

    @staticmethod
    def get_option_info():
        """Get the default options for this machine."""
        bool_converter = lambda s: s == 'True'
        sb = lambda s: int(float(s)) if float(s).is_integer() else float(s)
        return {
            'port': (None, str), # TODO: make first port default
            'baudrate': (9600, int),
            'bytesize': (8, int),
            'parity': ('N', str),
            'stopbits': (1, sb),
            'timeout': (2.0, float),
            'xonxoff': (False, bool_converter),
            'rtscts': (False, bool_converter)
        }

########NEW FILE########
__FILENAME__ = geminipr
# Copyright (c) 2010-2011 Joshua Harlan Lifton.
# See LICENSE.txt for details.

"""Thread-based monitoring of a Gemini PR stenotype machine."""

import plover.machine.base

# In the Gemini PR protocol, each packet consists of exactly six bytes
# and the most significant bit (MSB) of every byte is used exclusively
# to indicate whether that byte is the first byte of the packet
# (MSB=1) or one of the remaining five bytes of the packet (MSB=0). As
# such, there are really only seven bits of steno data in each packet
# byte. This is why the STENO_KEY_CHART below is visually presented as
# six rows of seven elements instead of six rows of eight elements.
STENO_KEY_CHART = ("Fn", "#", "#", "#", "#", "#", "#",
                   "S-", "S-", "T-", "K-", "P-", "W-", "H-",
                   "R-", "A-", "O-", "*", "*", "res", "res",
                   "pwr", "*", "*", "-E", "-U", "-F", "-R",
                   "-P", "-B", "-L", "-G", "-T", "-S", "-D",
                   "#", "#", "#", "#", "#", "#", "-Z")

BYTES_PER_STROKE = 6


class Stenotype(plover.machine.base.SerialStenotypeBase):
    """Standard stenotype interface for a Gemini PR machine.

    This class implements the three methods necessary for a standard
    stenotype interface: start_capture, stop_capture, and
    add_callback.

    """

    def run(self):
        """Overrides base class run method. Do not call directly."""
        self._ready()
        while not self.finished.isSet():

            # Grab data from the serial port.
            raw = self.serial_port.read(BYTES_PER_STROKE)
            if not raw:
                continue

            # XXX : work around for python 3.1 and python 2.6 differences
            if isinstance(raw, str):
                raw = [ord(x) for x in raw]

            # Make sure this is a valid steno stroke.
            if not ((len(raw) == BYTES_PER_STROKE) and
                    (raw[0] & 0x80) and
                    (len([b for b in raw if b & 0x80]) == 1)):
                serial_port.flushInput()
                continue

            # Convert the raw to a list of steno keys.
            steno_keys = []
            for i, b in enumerate(raw):
                for j in range(1, 8):
                    if (b & (0x80 >> j)):
                        steno_keys.append(STENO_KEY_CHART[i * 7 + j - 1])

            # Notify all subscribers.
            self._notify(steno_keys)


########NEW FILE########
__FILENAME__ = passport
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

"Thread-based monitoring of a stenotype machine using the passport protocol."

from plover.machine.base import SerialStenotypeBase
from itertools import izip_longest

# Passport protocol is documented here:
# http://www.eclipsecat.com/?q=system/files/Passport%20protocol_0.pdf

STENO_KEY_CHART = {
    '!': None,
    '#': '#',
    '^': None,
    '+': None,
    'S': 'S-',
    'C': 'S-',
    'T': 'T-',
    'K': 'K-',
    'P': 'P-',
    'W': 'W-',
    'H': 'H-',
    'R': 'R-',
    '~': '*',
    '*': '*',
    'A': 'A-',
    'O': 'O-',
    'E': '-E',
    'U': '-U',
    'F': '-F',
    'Q': '-R',
    'N': '-P',
    'B': '-B',
    'L': '-L',
    'G': '-G',
    'Y': '-T',
    'X': '-S',
    'D': '-D',
    'Z': '-Z',
}


class Stenotype(SerialStenotypeBase):
    """Passport interface."""

    def __init__(self, params):
        SerialStenotypeBase.__init__(self, params)
        self.packet = []

    def _read(self, b):
        b = chr(b)
        self.packet.append(b)
        if b == '>':
            self._handle_packet(''.join(self.packet))
            del self.packet[:]

    def _handle_packet(self, packet):
        encoded = packet.split('/')[1]
        keys = []
        for key, shadow in grouper(encoded, 2, 0):
            shadow = int(shadow, base=16)
            if shadow >= 8:
                key = STENO_KEY_CHART[key]
                if key:
                    keys.append(key)
        if keys:
            self._notify(keys)

    def run(self):
        """Overrides base class run method. Do not call directly."""
        self._ready()

        while not self.finished.isSet():
            # Grab data from the serial port.
            raw = self.serial_port.read(self.serial_port.inWaiting())

            # XXX : work around for python 3.1 and python 2.6 differences
            if isinstance(raw, str):
                raw = [ord(x) for x in raw]

            for b in raw:
                self._read(b)

    @staticmethod
    def get_option_info():
        """Get the default options for this machine."""
        bool_converter = lambda s: s == 'True'
        sb = lambda s: int(float(s)) if float(s).is_integer() else float(s)
        return {
            'port': (None, str), # TODO: make first port default
            'baudrate': (38400, int),
            'bytesize': (8, int),
            'parity': ('N', str),
            'stopbits': (1, sb),
            'timeout': (2.0, float),
            'xonxoff': (False, bool_converter),
            'rtscts': (False, bool_converter)
        }


def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    return izip_longest(fillvalue=fillvalue, *args)


########NEW FILE########
__FILENAME__ = registry
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

"Manager for stenotype machines types."

from plover.machine.geminipr import Stenotype as geminipr
from plover.machine.txbolt import Stenotype as txbolt
from plover.machine.sidewinder import Stenotype as sidewinder
from plover.machine.stentura import Stenotype as stentura
from plover.machine.passport import Stenotype as passport

try:
    from plover.machine.treal import Stenotype as treal
except:
    treal = None

class NoSuchMachineException(Exception):
    def __init__(self, id):
        self._id = id

    def __str__(self):
        return 'Unrecognized machine type: {}'.format(self._id)

class Registry(object):
    def __init__(self):
        self._machines = {}
        self._aliases = {}

    def register(self, name, machine):
        self._machines[name] = machine

    def add_alias(self, alias, name):
        self._aliases[alias] = name

    def get(self, name):
        try:
            return self._machines[self.resolve_alias(name)]
        except KeyError:
            raise NoSuchMachineException(name)

    def get_all_names(self):
        return self._machines.keys()
        
    def resolve_alias(self, name):
        try:
            return self._aliases[name]
        except KeyError:
            return name

machine_registry = Registry()
machine_registry.register('NKRO Keyboard', sidewinder)
machine_registry.register('Gemini PR', geminipr)
machine_registry.register('TX Bolt', txbolt)
machine_registry.register('Stentura', stentura)
machine_registry.register('Passport', passport)
if treal:
    machine_registry.register('Treal', treal)

machine_registry.add_alias('Microsoft Sidewinder X4', 'NKRO Keyboard')

########NEW FILE########
__FILENAME__ = sidewinder
# Copyright (c) 2010 Joshua Harlan Lifton.
# See LICENSE.txt for details.

# TODO: add options to remap keys
# TODO: look into programmatically pasting into other applications

"For use with a Microsoft Sidewinder X4 keyboard used as stenotype machine."

# TODO: Change name to NKRO Keyboard.

from plover.machine.base import StenotypeBase
from plover.oslayer import keyboardcontrol

KEYSTRING_TO_STENO_KEY = {"a": "S-",
                          "q": "S-",
                          "w": "T-",
                          "s": "K-",
                          "e": "P-",
                          "d": "W-",
                          "r": "H-",
                          "f": "R-",
                          "c": "A-",
                          "v": "O-",
                          "t": "*",
                          "g": "*",
                          "y": "*",
                          "h": "*",
                          "n": "-E",
                          "m": "-U",
                          "u": "-F",
                          "j": "-R",
                          "i": "-P",
                          "k": "-B",
                          "o": "-L",
                          "l": "-G",
                          "p": "-T",
                          ";": "-S",
                          "[": "-D",
                          "'": "-Z",
                          "1": "#",
                          "2": "#",
                          "3": "#",
                          "4": "#",
                          "5": "#",
                          "6": "#",
                          "7": "#",
                          "8": "#",
                          "9": "#",
                          "0": "#",
                          "-": "#",
                          "=": "#",
                         }


class Stenotype(StenotypeBase):
    """Standard stenotype interface for a Microsoft Sidewinder X4 keyboard.

    This class implements the three methods necessary for a standard
    stenotype interface: start_capture, stop_capture, and
    add_callback.

    """

    def __init__(self, params):
        """Monitor a Microsoft Sidewinder X4 keyboard via X events."""
        StenotypeBase.__init__(self)
        self._keyboard_emulation = keyboardcontrol.KeyboardEmulation()
        self._keyboard_capture = keyboardcontrol.KeyboardCapture()
        self._keyboard_capture.key_down = self._key_down
        self._keyboard_capture.key_up = self._key_up
        self.suppress_keyboard(True)
        self._down_keys = set()
        self._released_keys = set()
        self.arpeggiate = params['arpeggiate']

    def start_capture(self):
        """Begin listening for output from the stenotype machine."""
        self._keyboard_capture.start()
        self._ready()

    def stop_capture(self):
        """Stop listening for output from the stenotype machine."""
        self._keyboard_capture.cancel()
        self._stopped()

    def suppress_keyboard(self, suppress):
        self._is_keyboard_suppressed = suppress
        self._keyboard_capture.suppress_keyboard(suppress)

    def _key_down(self, event):
        """Called when a key is pressed."""
        if (self._is_keyboard_suppressed
            and event.keystring is not None
            and not self._keyboard_capture.is_keyboard_suppressed()):
            self._keyboard_emulation.send_backspaces(1)
        if event.keystring in KEYSTRING_TO_STENO_KEY:
            self._down_keys.add(event.keystring)

    def _post_suppress(self, suppress, steno_keys):
        """Backspace the last stroke since it matched a command.
        
        The suppress function is passed in to prevent threading issues with the 
        gui.
        """
        n = len(steno_keys)
        if self.arpeggiate:
            n += 1
        suppress(n)

    def _key_up(self, event):
        """Called when a key is released."""
        if event.keystring in KEYSTRING_TO_STENO_KEY:            
            # Process the newly released key.
            self._released_keys.add(event.keystring)
            # Remove invalid released keys.
            self._released_keys = self._released_keys.intersection(self._down_keys)

        # A stroke is complete if all pressed keys have been released.
        # If we are in arpeggiate mode then only send stroke when spacebar is pressed.
        send_strokes = bool(self._down_keys and 
                            self._down_keys == self._released_keys)
        if self.arpeggiate:
            send_strokes &= event.keystring == ' '
        if send_strokes:
            steno_keys = [KEYSTRING_TO_STENO_KEY[k] for k in self._down_keys
                          if k in KEYSTRING_TO_STENO_KEY]
            if steno_keys:
                self._down_keys.clear()
                self._released_keys.clear()
                self._notify(steno_keys)

    @staticmethod
    def get_option_info():
        bool_converter = lambda s: s == 'True'
        return {
            'arpeggiate': (False, bool_converter),
        }

########NEW FILE########
__FILENAME__ = stentura
# Copyright (c) 2011 Hesky Fisher
# See LICENSE.txt for details.
# Many thanks to a steno geek for help with the protocol.

# TODO: Come up with a mechanism to communicate back to the engine when there
# is a connection error.
# TODO: Address any generic exceptions still left.

"""Thread-based monitoring of a stenotype machine using the stentura protocol.
"""

"""
The stentura protocol uses packets to communicate with the machine. A
request packet is sent to the machine and a response packet is received. If
no response is received after a one second timeout then the same packet
should be sent again. The machine may hold off on responding to a READC
packet for up to 500ms if there are no new strokes.

Each request packet should have a sequence number that is one higher than
the previously sent packet modulo 256. The response packet will have the
same sequence number. Each packet consists of a header followed by an
optional data section. All multibyte fields are little endian.

The request packet header is structured as follows:
- SOH: 1 byte. Always set to ASCII SOH (0x1).
- seq: 1 byte. The sequence number of this packet.
- length: 2 bytes. The total length of the packet, including the data
  section, in bytes.
- action: 2 bytes. The action requested. See actions below.
- p1: 2 bytes. Parameter 1. The values for the parameters depend on the
  action.
- p2: 2 bytes. Parameter 2.
- p3: 2 bytes. Parameter 3.
- p4: 2 bytes. Parameter 4.
- p5: 2 bytes. Parameter 5.
- checksum: 2 bytes. The CRC is computed over the packet from seq through
  p5. The specific CRC algorithm used is described above in the Crc class.

The request header can be followed by a data section. The meaning of the
data section depends on the action:
- data: variable length.
- crc: 2 bytes. A CRC over just the data section.

The response packet header is structured as follows:
- SOH: 1 byte. Always set to ASCII SOH (0x1).
- seq: 1 byte. The sequence number of the request packet.
- length: 2 bytes. The total length of the packet, including the data
  section, in bytes.
- action: 2 bytes. The action of the request packet.
- error: 2 bytes. The error code. Zero if no error.
- p1: 2 bytes. Parameter 1. The values of the parameters depend on the
  action.
- p2: 2 bytes. Parameter 2.
- checksum: 2 bytes. The CRC is computed over the packet from seq through
  p2.

The response header can be follows by a data section, whose meaning is
dependent on the action. The structure is the same as in request packets.

The stentura machine has a concept of drives and files. The first (and
possibly only) drive is called A. Each file consists of a set of one or
more blocks. Each block is 512 bytes long.

In addition to regular files, there is a realtime file whose name is
'REALTIME.000'. All strokes typed are appended to this file. Subsequent
reads from the realtime file ignore positional arguments and only return
all the strokes since the last read action. However, opening the file again
and reading from the beginning will result in all the same strokes being
read again. The only reliable way to jump to the end is to do a full,
sequential, read to the end before processing any strokes. I'm told that on
some machines sending a READC without an OPEN will just read from the
realtime file.

The contents of the files are a sequence of strokes. Each stroke consists
of four bytes. Each byte has the two most significant bytes set to one. The
rest of the byte is a bitmask indicating which keys were pressed during the
stroke. The format is as follows: 11^#STKP 11WHRAO* 11EUFRPB 11LGTSDZ ^ is
something called a stenomark. I'm not sure what that is. # is the number
bar.

Note: Only OPEN and READC are needed to get strokes as they are typed from
the realtime file.

Actions and their packets:

All unmentioned parameters should be zero and unless explicitly mentioned
the packet should have no data section.

RESET (0x14):
Unknown.

DISKSTATUS (0x7):
Unknown.
p1 is set to the ASCII value corresponding to the drive letter, e.g. 'A'.

GETDOS (0x18):
Returns the DOS filenames for the files in the requested drive.
p1 is set to the ASCII value corresponding to the drive letter, e.g. 'A'.
p2 is set to one to return the name of the realtime file (which is always
'REALTIME.000').
p3 controls which page to return, with 20 filenames per page.
The return packet contains a data section that is 512 bytes long. The first
bytes seems to be one. The filename for the first file starts at offset 32.
My guess would be that the other filenames would exist at a fixed offset of
24 bytes apart. So first filename is at 32, second is at 56, third at 80,
etc. There seems to be some meta data stored after the filename but I don't
know what it means.

DELETE (0x3):
Deletes the specified files. NOP on realtime file.
p1 is set to the ASCII value corresponding to the drive letter, e.g. 'A'.
The filename is specified in the data section.

OPEN (0xA):
Opens a file for reading. This action is sticky and causes this file to be
the current file for all following READC packets.
p1 is set to the ASCII value corresponding to the drive letter, e.g. 'A'.
The filename is specified in the data section.
I'm told that if there is an error opening the realtime file then no
strokes have been written yet.
TODO: Check that and implement workaround.

READC (0xB):
Reads characters from the currently opened file.
p1 is set to 1, I'm not sure why.
p3 is set to the maximum number of bytes to read but should probably be
512.
p4 is set to the block number.
p5 is set to the starting byte offset within the block.
It's possible that the machine will ignore the positional arguments to
READC when reading from the realtime file and just return successive values
for each call.
The response will have the number of bytes read in p1 (but the same is
deducible from the length). The data section will have the contents read
from the file.

CLOSE (0x2):
Closes the current file.
p1 is set to one, I don't know why.

TERM (0x15):
Unknown.

DIAG (0x19):
Unknown.

"""

import array
import itertools
import struct
import time

import plover.machine.base


class _ProtocolViolationException(Exception):
    """Something has happened that is doesn't follow the protocol."""
    pass


class _StopException(Exception):
    """The thread was asked to stop."""
    pass


class _TimeoutException(Exception):
    """An operation has timed out."""
    pass


class _ConnectionLostException(Exception):
    """Cannot communicate with the machine."""
    pass


_CRC_TABLE = [
    0x0000, 0xc0c1, 0xc181, 0x0140, 0xc301, 0x03c0, 0x0280, 0xc241,
    0xc601, 0x06c0, 0x0780, 0xc741, 0x0500, 0xc5c1, 0xc481, 0x0440,
    0xcc01, 0x0cc0, 0x0d80, 0xcd41, 0x0f00, 0xcfc1, 0xce81, 0x0e40,
    0x0a00, 0xcac1, 0xcb81, 0x0b40, 0xc901, 0x09c0, 0x0880, 0xc841,
    0xd801, 0x18c0, 0x1980, 0xd941, 0x1b00, 0xdbc1, 0xda81, 0x1a40,
    0x1e00, 0xdec1, 0xdf81, 0x1f40, 0xdd01, 0x1dc0, 0x1c80, 0xdc41,
    0x1400, 0xd4c1, 0xd581, 0x1540, 0xd701, 0x17c0, 0x1680, 0xd641,
    0xd201, 0x12c0, 0x1380, 0xd341, 0x1100, 0xd1c1, 0xd081, 0x1040,
    0xf001, 0x30c0, 0x3180, 0xf141, 0x3300, 0xf3c1, 0xf281, 0x3240,
    0x3600, 0xf6c1, 0xf781, 0x3740, 0xf501, 0x35c0, 0x3480, 0xf441,
    0x3c00, 0xfcc1, 0xfd81, 0x3d40, 0xff01, 0x3fc0, 0x3e80, 0xfe41,
    0xfa01, 0x3ac0, 0x3b80, 0xfb41, 0x3900, 0xf9c1, 0xf881, 0x3840,
    0x2800, 0xe8c1, 0xe981, 0x2940, 0xeb01, 0x2bc0, 0x2a80, 0xea41,
    0xee01, 0x2ec0, 0x2f80, 0xef41, 0x2d00, 0xedc1, 0xec81, 0x2c40,
    0xe401, 0x24c0, 0x2580, 0xe541, 0x2700, 0xe7c1, 0xe681, 0x2640,
    0x2200, 0xe2c1, 0xe381, 0x2340, 0xe101, 0x21c0, 0x2080, 0xe041,
    0xa001, 0x60c0, 0x6180, 0xa141, 0x6300, 0xa3c1, 0xa281, 0x6240,
    0x6600, 0xa6c1, 0xa781, 0x6740, 0xa501, 0x65c0, 0x6480, 0xa441,
    0x6c00, 0xacc1, 0xad81, 0x6d40, 0xaf01, 0x6fc0, 0x6e80, 0xae41,
    0xaa01, 0x6ac0, 0x6b80, 0xab41, 0x6900, 0xa9c1, 0xa881, 0x6840,
    0x7800, 0xb8c1, 0xb981, 0x7940, 0xbb01, 0x7bc0, 0x7a80, 0xba41,
    0xbe01, 0x7ec0, 0x7f80, 0xbf41, 0x7d00, 0xbdc1, 0xbc81, 0x7c40,
    0xb401, 0x74c0, 0x7580, 0xb541, 0x7700, 0xb7c1, 0xb681, 0x7640,
    0x7200, 0xb2c1, 0xb381, 0x7340, 0xb101, 0x71c0, 0x7080, 0xb041,
    0x5000, 0x90c1, 0x9181, 0x5140, 0x9301, 0x53c0, 0x5280, 0x9241,
    0x9601, 0x56c0, 0x5780, 0x9741, 0x5500, 0x95c1, 0x9481, 0x5440,
    0x9c01, 0x5cc0, 0x5d80, 0x9d41, 0x5f00, 0x9fc1, 0x9e81, 0x5e40,
    0x5a00, 0x9ac1, 0x9b81, 0x5b40, 0x9901, 0x59c0, 0x5880, 0x9841,
    0x8801, 0x48c0, 0x4980, 0x8941, 0x4b00, 0x8bc1, 0x8a81, 0x4a40,
    0x4e00, 0x8ec1, 0x8f81, 0x4f40, 0x8d01, 0x4dc0, 0x4c80, 0x8c41,
    0x4400, 0x84c1, 0x8581, 0x4540, 0x8701, 0x47c0, 0x4680, 0x8641,
    0x8201, 0x42c0, 0x4380, 0x8341, 0x4100, 0x81c1, 0x8081, 0x4040
]


def _crc(data):
    """Compute the Crc algorithm used by the stentura protocol.

    This algorithm is described by the Rocksoft^TM Model CRC Algorithm as
    follows:

    Name   : "CRC-16"
    Width  : 16
    Poly   : 8005
    Init   : 0000
    RefIn  : True
    RefOut : True
    XorOut : 0000
    Check  : BB3D

    Args:
    - data: The data to checksum. The data should be an iterable that returns
            bytes

    Returns: The computed crc for the data.

    """
    checksum = 0
    for b in data:
        if isinstance(b, str):
            b = ord(b)
        checksum = (_CRC_TABLE[(checksum ^ b) & 0xff] ^
                    ((checksum >> 8) & 0xff))
    return checksum


def _write_to_buffer(buf, offset, data):
    """Write data to buf at offset.

    Extends the size of buf as needed.

    Args:
    - buf: The buffer. Should be of type array('B')
    - offset. The offset at which to start writing.
    - data: An iterable containing the data to write.
    """
    if len(buf) < offset + len(data):
        buf.extend([0] * (offset + len(data) - len(buf)))
    for i, v in enumerate(data, offset):
        if isinstance(v, str):
            v = ord(v)
        buf[i] = v

# Helper table for parsing strokes of the form:
# 11^#STKP 11WHRAO* 11EUFRPB 11LGTSDZ
_STENO_KEY_CHART = ('^', '#', 'S-', 'T-', 'K-', 'P-',    # Byte #1
                    'W-', 'H-', 'R-', 'A-', 'O-', '*',   # Byte #2
                    '-E', '-U', '-F', '-R', '-P', '-B',  # Byte #3
                    '-L', '-G', '-T', '-S', '-D', '-Z')  # Byte #4


def _parse_stroke(a, b, c, d):
    """Parse a stroke and return a list of keys pressed.

    Args:
    - a: The first byte.
    - b: The second byte.
    - c: The third byte.
    - d: The fourth byte.

    Returns: A sequence with all the keys pressed in the stroke.
             e.g. ['S-', 'A-', '-T']

    """
    fullstroke = (((a & 0x3f) << 18) | ((b & 0x3f) << 12) |
                  ((c & 0x3f) << 6) | d & 0x3f)
    return [_STENO_KEY_CHART[i] for i in xrange(24)
            if (fullstroke & (1 << (23 - i)))]


def _parse_strokes(data):
    """Parse strokes from a buffer and return a sequence of strokes.

    Args:
    - data: A byte buffer.

    Returns: A sequence of strokes. Each stroke is a sequence of pressed keys.

    Throws:
    - _ProtocolViolationException if the data doesn't follow the protocol.

    """
    strokes = []
    if (len(data) % 4 != 0):
        raise _ProtocolViolationException(
            "Data size is not divisible by 4: %d" % (len(data)))
    for b in data:
        if (ord(b) & 0b11000000) != 0b11000000:
            raise _ProtocolViolationException("Data is not stroke: 0x%X" % (b))
    for a, b, c, d in itertools.izip(*([iter(data)] * 4)):
        strokes.append(_parse_stroke(ord(a), ord(b), ord(c), ord(d)))
    return strokes

# Actions
_CLOSE = 0x2
_DELETE = 0x3
_DIAG = 0x19
_DISKSTATUS = 0x7
_GETDOS = 0x18
_OPEN = 0xA
_READC = 0xB
_RESET = 0x14
_TERM = 0x15

# Compiled struct for writing request headers.
_REQUEST_STRUCT = struct.Struct('<2B7H')
_SHORT_STRUCT = struct.Struct('<H')


def _make_request(buf, action, seq, p1=0, p2=0, p3=0, p4=0, p5=0, data=None):
    """Create a request packet.

    Args:
    - buf: The buffer used for the packet. Should be array.array('B') and will
    be extended as needed.
    - action: The action for the packet.
    - seq: The sequence numbe for the packet.
    - p1 - p5: Paremeter N for the packet (default: 0).
    - data: The data to add to the packet as a sequence of bytes, if any
    (default: None).

    Returns: A buffer as a slice of the passed in buf that holds the packet.

    """
    length = 18
    if data:
        length += len(data) + 2  # +2 for the data CRC.
    if len(buf) < length:
        buf.extend([0] * (length - len(buf)))
    _REQUEST_STRUCT.pack_into(buf, 0, 1, seq, length, action,
                              p1, p2, p3, p4, p5)
    crc = _crc(buffer(buf, 1, 15))
    _SHORT_STRUCT.pack_into(buf, 16, crc)
    if data:
        _write_to_buffer(buf, 18, data)
        crc = _crc(data)
        _SHORT_STRUCT.pack_into(buf, length - 2, crc)
    return buffer(buf, 0, length)


def _make_open(buf, seq, drive, filename):
    """Make a packet with the OPEN command.

    Args:
    - buf: The buffer to use of type array.array('B'). Will be extended if
    needed.
    - seq: The sequence number of the packet.
    - drive: The letter of the drive (probably 'A').
    - filename: The name of the file (probably 'REALTIME.000').

    Returns: A buffer as a slice of the passed in buf that holds the packet.

    """
    return _make_request(buf, _OPEN, seq, p1=ord(drive), data=filename)


def _make_read(buf, seq, block, byte, length=512):
    """Make a packet with the READC command.

    Args:
    - buf: The buffer to use of type array.array('B'). Will be extended if
    needed.
    - seq: The sequence number of the packet.
    - block: The index of the file block to read.
    - byte: The byte offset within the block at which to start reading.
    - length: The number of bytes to read, max 512 (default: 512).

    Returns: A buffer as a slice of the passed in buf that holds the packet.

    """
    return _make_request(buf, _READC, seq, p1=1, p3=length, p4=block, p5=byte)


def _make_reset(buf, seq):
    """Make a packet with the RESET command.

    Args:
    - buf: The buffer to use of type array.array('B'). Will be extended if
    needed.
    - seq: The sequence number of the packet.

    Returns: A buffer as a slice of the passed in buf that holds the packet.

    """
    return _make_request(buf, _RESET, seq)


def _validate_response(packet):
    """Validate a response packet.

    Args:
    - packet: The packet to validate.

    Returns: True if the packet is valid, False otherwise.

    """
    if len(packet) < 14:
        return False
    length = _SHORT_STRUCT.unpack(buffer(packet, 2, 2))[0]
    if length != len(packet):
        return False
    if _crc(buffer(packet, 1, 13)) != 0:
        return False
    if length > 14:
        if length < 17:
            return False
        if _crc(buffer(packet, 14)) != 0:
            return False
    return True


# Timeout is in seconds, can be a float.
def _read_data(port, stop, buf, offset, timeout):
    """Read data off the serial port and into port at offset.

    Args:
    - port: The serial port to read.
    - stop: An event which, when set, causes this function to stop.
    - buf: The buffer to write.
    - offset: The offset into the buffer to write.
    - timeout: The amount of time to wait for data.

    Returns: The number of bytes read.

    Raises:
    _StopException: If stop is set.
    _TimeoutException: If the timeout is reached with no data read.

    """
    start_time = time.clock()
    end_time = start_time + timeout
    while not stop.is_set() and time.clock() < end_time:
        num_bytes = port.inWaiting()
        if num_bytes > 0:
            bytes = port.read(num_bytes)
            _write_to_buffer(buf, offset, bytes)
            return num_bytes
    if stop.is_set():
        raise _StopException()
    else:
        raise _TimeoutException()


def _read_packet(port, stop, buf, timeout):
    """Read a full packet from the port.

    Reads from the port until a full packet is received or the stop or timeout
    conditions are met.

    Args:
    - port: The port to read.
    - stop: Event object used to request stopping.
    - buf: The buffer to write.
    - timeout: The amount of time to keep trying.

    Returns: A buffer as a slice of buf holding the packet.

    Raises:
    _ProtocolViolationException: If the packet doesn't conform to the protocol.
    _TimeoutException: If the packet is not read within the timeout.
    _StopException: If a stop was requested.

    """
    start_time = time.clock()
    end_time = start_time + timeout
    bytes_read = 0
    while bytes_read < 4:
        bytes_read += _read_data(port, stop, buf, bytes_read,
                                 end_time - time.clock())
    packet_length = _SHORT_STRUCT.unpack_from(buf, 2)[0]
    while bytes_read < packet_length:
        bytes_read += _read_data(port, stop, buf, bytes_read,
                                 end_time - time.clock())
    packet = buffer(buf, 0, bytes_read)
    if not _validate_response(packet):
        raise _ProtocolViolationException()
    return buffer(buf, 0, bytes_read)


def _write_to_port(port, data):
    """Write data to a port.

    Args:
    - port: The port to write.
    - data: The data to write

    """
    while data:
        data = buffer(data, port.write(data))


def _send_receive(port, stop, packet, buf, max_tries=3, timeout=1):
    """Send a packet and return the response.

    Send a packet and make sure there is a response and it is for the correct
    request and return it, otherwise retry max_retries times.

    Args:
    - port: The port to read.
    - stop: Event used to signal tp stop.
    - packet: The packet to send. May be used after buf is written so should be
    distinct.
    - buf: Buffer used to store response.
    - max_tries: The maximum number of times to retry sending the packet and
    reading the response before giving up (default: 3).
    - timeout: The timeout to give on each retry. Should be one second when
    dealing with a real machine. (default: 1)

    Returns: A buffer as a slice of buf holding the response packet.

    Raises:
    _ConnectionLostException: If we can't seem to talk to the machine.
    _StopException: If a stop was requested.
    _ProtocolViolationException: If the responses packet violates the protocol.

    """
    request_action = _SHORT_STRUCT.unpack(buffer(packet, 4, 2))[0]
    for attempt in xrange(max_tries):
        _write_to_port(port, packet)
        try:
            response = _read_packet(port, stop, buf, timeout)
            if response[1] != packet[1]:
                continue  # Wrong sequence number.
            response_action = _SHORT_STRUCT.unpack(buffer(response, 4, 2))[0]
            if request_action != response_action:
                raise _ProtocolViolationException()
            return response
        except _TimeoutException:
            continue
    raise _ConnectionLostException()


class _SequenceCounter(object):
    """A mod 256 counter."""
    def __init__(self, seq=0):
        """Init a new counter starting at seq."""
        self.seq = seq

    def __call__(self):
        """Return the next value."""
        cur, self.seq = self.seq, (self.seq + 1) % 256
        return cur


def _read(port, stop, seq, request_buf, response_buf, stroke_buf, block, byte, timeout=1):
    """Read the full contents of the current file from beginning to end.

    The file should be opened first.

    Args:
    - port: The port to use.
    - stop: The event used to request stopping.
    - seq: A _SequenceCounter instance to use to track packets.
    - request_buf: Buffer to use for request packet.
    - response_buf: Buffer to use for response packet.
    - stroke_buf: Buffer to use for strokes read from the file.
    - timeout: Timeout to use when waiting for a response in seconds. Should be
    1 when talking to a real machine. (default: 1)

    Raises:
    _ProtocolViolationException: If the protocol is violated.
    _StopException: If a stop is requested.
    _ConnectionLostException: If we can't seem to talk to the machine.

    """
    bytes_read = 0
    while True:
        packet = _make_read(request_buf, seq(), block, byte, length=512)
        response = _send_receive(port, stop, packet, response_buf,
                   timeout=timeout)
        p1 = _SHORT_STRUCT.unpack(buffer(response, 8, 2))[0]
        if not ((p1 == 0 and len(response) == 14) or  # No data.
                (p1 == len(response) - 16)):          # Data.
            raise _ProtocolViolationException()
        if p1 == 0:
            return block, byte, buffer(stroke_buf, 0, bytes_read)
        data = buffer(response, 14, p1)
        _write_to_buffer(stroke_buf, bytes_read, data)
        bytes_read += len(data)
        byte += p1
        if byte >= 512:
            block += 1
            byte -= 512

def _loop(port, stop, callback, ready_callback, timeout=1):
    """Enter into a loop talking to the machine and returning strokes.

    Args:
    - port: The port to use.
    - stop: The event used to signal that it's time to stop.
    - callback: A function that takes a list of pressed keys, called for each
    stroke.
    - ready_callback: A function that is called when the machine is ready.
    - timeout: Timeout to use when waiting for a response in seconds. Should be
    1 when talking to a real machine. (default: 1)

    Raises:
    _ProtocolViolationException: If the protocol is violated.
    _StopException: If a stop is requested.
    _ConnectionLostException: If we can't seem to talk to the machine.

    """
    # We want to give the machine a standard timeout to finish whatever it's
    # doing but we also want to stop if asked to so this is the safe way to
    # wait.
    if stop.wait(timeout):
        raise _StopException()
    port.flushInput()
    port.flushOutput()
    request_buf, response_buf = array.array('B'), array.array('B')
    stroke_buf = array.array('B')
    seq = _SequenceCounter()
    request = _make_open(request_buf, seq(), 'A', 'REALTIME.000')
    # Any checking needed on the response packet?
    _send_receive(port, stop, request, response_buf)
    # Do a full read to get to the current position in the realtime file.
    block, byte = 0, 0
    block, byte, _ = _read(port, stop, seq, request_buf, response_buf, stroke_buf, block, byte)
    ready_callback()
    while True:
        block, byte, data = _read(port, stop, seq, request_buf, response_buf, stroke_buf, block, byte)
        strokes = _parse_strokes(data)
        for stroke in strokes:
            callback(stroke)


class Stenotype(plover.machine.base.SerialStenotypeBase):
    """Stentura interface.

    This class implements the three methods necessary for a standard
    stenotype interface: start_capture, stop_capture, and
    add_callback.
    """

    def __init__(self, params):
        plover.machine.base.SerialStenotypeBase.__init__(self, params)

    def run(self):
        """Overrides base class run method. Do not call directly."""
        try:
            _loop(self.serial_port, self.finished, self._notify, self._ready)
        except _StopException:
            pass
        except _ConnectionLostException, _ProtocolViolationException:
            self._error()

########NEW FILE########
__FILENAME__ = test_passport
# Copyright (c) 2011 Hesky Fisher
# See LICENSE.txt for details.

"""Unit tests for passport.py."""

from operator import eq
from itertools import starmap
import unittest
from mock import patch
from plover.machine.passport import Stenotype
import time

class MockSerial(object):
    
    inputs = []
    index = 0
    
    def __init__(self, **params):
      MockSerial.index = 0

    def isOpen(self):
        return True

    def _get(self):
        if len(MockSerial.inputs) > MockSerial.index:
            return MockSerial.inputs[MockSerial.index]
        return ''

    def inWaiting(self):
        return len(self._get())

    def read(self, size=1):
        assert size == self.inWaiting()
        result = [ord(x) for x in self._get()]
        MockSerial.index += 1
        return result
        
    def close(self):
        pass


def cmp_keys(a, b):
    return all(starmap(eq, zip(a, b)))

class TestCase(unittest.TestCase):
    def test_pasport(self):
        
        def p(s):
            return '<123/%s/something>' % s
        
        cases = (
            # Test all keys
            (('!f#f+f*fAfCfBfEfDfGfFfHfKfLfOfNfQfPfSfRfUfTfWfYfXfZf^f~f',),
            (('#', '*', 'A-', 'S-', '-B', '-E', '-D', '-G', '-F', 'H-', 'K-', 
              '-L', 'O-', '-P', '-R', 'P-', 'S-', 'R-', '-U', 'T-', 'W-', '-T', 
              '-S', '-Z', '*'),)),
            # Anything below 8 is not registered
            (('S9T8A7',), (('S-', 'T-'),)),
            # Sequence of strokes
            (('SfTf', 'Zf', 'QfLf'), (('S-', 'T-'), ('-Z',), ('-R', '-L'))),
        )

        params = {k: v[0] for k, v in Stenotype.get_option_info().items()}
        results = []
        with patch('plover.machine.base.serial.Serial', MockSerial) as mock:
            for inputs, expected in cases:
                mock.inputs = map(p, inputs)
                actual = []
                m = Stenotype(params)
                m.add_stroke_callback(lambda s: actual.append(s))
                m.start_capture()
                while mock.index < len(mock.inputs):
                    time.sleep(0.00001)
                m.stop_capture()
                result = (len(expected) == len(actual) and 
                          all(starmap(cmp_keys, zip(actual, expected))))
                if not result:
                    print actual, '!=', expected
                results.append(result)
                
        self.assertTrue(all(results))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_registry
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

"""Unit tests for registry.py."""

import unittest
from registry import Registry, machine_registry, NoSuchMachineException

class RegistryClassTestCase(unittest.TestCase):
    def test_lookup(self):
        registry = Registry()
        registry.register('a', 1)
        self.assertEqual(1, registry.get('a'))
    
    def test_unknown_entry(self):
        registry = Registry()
        with self.assertRaises(NoSuchMachineException):
            registry.get('b')
            
    def test_alias(self):
        registry = Registry()
        registry.register('a', 1)
        registry.add_alias('b', 'a')
        self.assertEqual(registry.resolve_alias('b'), 'a')
        self.assertEqual(1, registry.get('b'))
            
    def test_all_names(self):
        registry = Registry()
        registry.register('a', 1)
        registry.register('b', 5)
        registry.add_alias('c', 'b')
        self.assertEqual(['a', 'b'], sorted(registry.get_all_names()))

class MachineRegistryTestCase(object):
    def test_sidewinder(self):
        self.assertEqual(machine_registery.get("NKRO Keyboard"), 
                         machine_registry.get('Microsoft Sidewinder X4'))

    def test_unknown_machine(self):
        with self.assertRaises(NoSuchMachineException):
            machine_registry.get('No such machine')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_stentura
# Copyright (c) 2011 Hesky Fisher
# See LICENSE.txt for details.

"""Unit tests for stentura.py."""

import array
import struct
import threading
import unittest

import stentura


def make_response(seq, action, error=0, p1=0, p2=0, data=None,
                  length=None):
    if not length:
        length = 14
        if data:
            length += 2 + len(data)
    response = struct.pack('<2B5H', 1, seq, length, action, error, p1, p2)
    crc = stentura._crc(buffer(response, 1, 11))
    response += struct.pack('<H', crc)
    if data:
        crc = stentura._crc(data)
        if not isinstance(data, str) and not isinstance(data, buffer):
            data = ''.join([chr(b) for b in data])
        response += data + struct.pack('<H', crc)
    return response


def make_read_response(seq, data=[]):
    return make_response(seq, stentura._READC, p1=len(data), data=data)


def make_readc_packets(data):
    requests, responses = [], []
    seq = stentura._SequenceCounter()
    buf = array.array('B')
    block, byte = 0, 0
    while data:
        s = seq()
        chunk = buffer(data, 0, 512)
        data = buffer(data, 512)
        q = stentura._make_read(buf, s, block, byte)
        requests.append(str(q))
        r = make_read_response(s, chunk)
        responses.append(str(r))
        byte += len(chunk)
        if byte >= 512:
            block += 1
            byte -= 512
    s = seq()
    q = stentura._make_read(buf, s, block, byte)
    requests.append(str(q))
    r = make_read_response(s)
    responses.append(str(r))
    return requests, responses


def parse_request(request):
    header = struct.unpack_from('<2B8H', request)
    if header[2] > 18:
        header = list(header) + [request[18:-2], struct.unpack('<H',
                                                               request[-2:])]
    else:
        header = list(header) + [None] * 2
    return dict(zip(['SOH', 'seq', 'length', 'action', 'p1', 'p2',
                     'p3', 'p4', 'p5', 'crc', 'data', 'data_crc'], header))


class MockPacketPort(object):
    def __init__(self, responses, requests=None):
        self._responses = responses
        self.writes = 0
        self._requests = requests

    def inWaiting(self):
        return len(self._responses[self.writes - 1])

    def write(self, data):
        self.writes += 1
        if self._requests and self._requests[self.writes - 1] != str(data):
            raise Exception("Wrong packet.")
        return len(data)

    def read(self, count):
        response = self._responses[self.writes - 1]
        return response


class TestCase(unittest.TestCase):
    def test_crc(self):
        data = [ord(x) for x in '123456789']
        self.assertEqual(stentura._crc(data), 0xBB3D)

    def test_write_buffer(self):
        buf = array.array('B')
        data = [1, 2, 3]
        stentura._write_to_buffer(buf, 0, data)
        self.assertSequenceEqual(buf, data)
        stentura._write_to_buffer(buf, 0, [5, 6])
        self.assertSequenceEqual(buf, [5, 6, 3])

    def test_parse_stroke(self):
        # SAT
        a = 0b11001000
        b = 0b11000100
        c = 0b11000000
        d = 0b11001000
        self.assertItemsEqual(stentura._parse_stroke(a, b, c, d),
                              ['S-', 'A-', '-T'])

# 11^#STKP 11WHRAO* 11EUFRPB 11LGTSDZ
# PRAOERBGS
    def test_parse_strokes(self):
        data = []
        # SAT
        a = 0b11001000
        b = 0b11000100
        c = 0b11000000
        d = 0b11001000
        data.extend([a, b, c, d])
        # PRAOERBGS
        a = 0b11000001
        b = 0b11001110
        c = 0b11100101
        d = 0b11010100
        data.extend([a, b, c, d])
        strokes = stentura._parse_strokes(''.join([chr(b) for b in data]))
        expected = [['S-', 'A-', '-T'],
                    ['P-', 'R-', 'A-', 'O-', '-E', '-R', '-B', '-G', '-S']]
        for i, stroke in enumerate(strokes):
            self.assertItemsEqual(stroke, expected[i])

    def test_make_request(self):
        buf = array.array('B')
        seq = 2
        action = stentura._OPEN
        p1, p2, p3, p4, p5 = 1, 2, 3, 4, 5
        p = stentura._make_request(buf, action, seq, p1, p2, p3, p4, p5)
        for_crc = [seq, 18, 0, action, 0, p1, 0, p2, 0, p3, 0, p4, 0, p5, 0]
        crc = stentura._crc(for_crc)
        expected = [1] + for_crc + [crc & 0xFF, crc >> 8]
        self.assertSequenceEqual(p, [chr(b) for b in expected])

        # Now with data.
        data = 'Testing Testing 123'
        p = stentura._make_request(buf, action, seq, p1, p2, p3, p4, p5, data)
        length = 18 + len(data) + 2
        for_crc = [seq, length & 0xFF, length >> 8, action, 0,
                   p1, 0, p2, 0, p3, 0, p4, 0, p5, 0]
        crc = stentura._crc(for_crc)
        data_crc = stentura._crc(data)
        expected = ([1] + for_crc + [crc & 0xFF, crc >> 8] +
                    [ord(b) for b in data] + [data_crc & 0xFF, data_crc >> 8])
        self.assertSequenceEqual(p, [chr(b) for b in expected])

    def test_make_open(self):
        buf = array.array('B', [3] * 18)  # Start with junk in the buffer.
        seq = 79
        drive = 'A'
        filename = 'REALTIME.000'
        p = stentura._make_open(buf, seq, drive, filename)
        for_crc = [seq, 20 + len(filename), 0, stentura._OPEN, 0, ord(drive),
                   0, 0, 0, 0, 0, 0, 0, 0, 0]
        crc = stentura._crc(for_crc)
        data_crc = stentura._crc(filename)
        expected = ([1] + for_crc + [crc & 0xFF, crc >> 8] +
                    [ord(b) for b in filename] +
                    [data_crc & 0xFF, data_crc >> 8])
        self.assertSequenceEqual(p, [chr(b) for b in expected])

    def test_make_read(self):
        buf = array.array('B', [3] * 20)  # Start with junk in the buffer.
        seq = 32
        block = 1
        byte = 8
        length = 20
        p = stentura._make_read(buf, seq, block, byte, length)
        for_crc = [seq, 18, 0, stentura._READC, 0, 1, 0, 0, 0, length, 0,
                   block, 0, byte, 0]
        crc = stentura._crc(for_crc)
        expected = [1] + for_crc + [crc & 0xFF, crc >> 8]
        self.assertSequenceEqual(p, [chr(b) for b in expected])

    def test_make_reset(self):
        buf = array.array('B', [3] * 20)  # Start with junk in the buffer.
        seq = 67
        p = stentura._make_reset(buf, seq)
        for_crc = [seq, 18, 0, stentura._RESET, 0] + ([0] * 10)
        crc = stentura._crc(for_crc)
        expected = [1] + for_crc + [crc & 0xFF, crc >> 8]
        self.assertSequenceEqual(p, [chr(b) for b in expected])

    def test_validate_response(self):
        tests = [
            (make_response(5, 9, 1, 2, 3), True, "valid no data"),
            (make_response(5, 9, 1, 2, 3, data="hello"), True, "valid, data"),
            (make_response(5, 9, 1, 2, 3)[:12], False, "short"),
            (make_response(5, 9, 1, 2, 3, length=15), False, "Length long"),
            (make_response(5, 9, 1, 2, 3, data='foo', length=15), False,
             "Length short"),
            (make_response(5, 9, 1, 2, 3) + '1', False, "Bad data"),
            (make_response(5, 9, 1, 2, 3)[:-1] + '1', False, "bad crc"),
            (make_response(5, 9, 1, 2, 3, data='foo')[:-1] + '1', False,
             "bad data crc")
        ]
        for test in tests:
            self.assertEqual(stentura._validate_response(
                test[0]), test[1], test[2])

    def test_read_data_simple(self):
        class MockPort(object):
            def inWaiting(self):
                return 5

            def read(self, count):
                if count != 5:
                    raise Exception("Incorrect number read.")
                return "12345"

        port = MockPort()
        buf = array.array('B')
        count = stentura._read_data(port, threading.Event(), buf, 0, 1)
        self.assertEqual(count, 5)
        self.assertSequenceEqual([chr(b) for b in buf], "12345")

        # Test the offset parameter.
        count = stentura._read_data(port, threading.Event(), buf, 4, 1)
        self.assertSequenceEqual([chr(b) for b in buf], "123412345")

    def test_read_data_waiting(self):
        class MockPort(object):
            def __init__(self):
                self._times = 0

            def inWaiting(self):
                self._times += 1
                if self._times == 5:
                    return 4

            def read(self, count):
                if self._times != 5:
                    raise Exception("Called read too early.")
                if count != 4:
                    raise Exception("Wrong count.")

                return "1234"

        buf = array.array('B')
        count = stentura._read_data(MockPort(), threading.Event(), buf, 0, 1)
        self.assertEqual(count, 4)
        self.assertSequenceEqual([chr(b) for b in buf], "1234")

    def test_read_data_stop_immediately(self):
        class MockPort(object):
            def inWaiting(self):
                return 0

        buf = array.array('B')
        event = threading.Event()
        event.set()
        with self.assertRaises(stentura._StopException):
            stentura._read_data(MockPort(), event, buf, 0, 1)

    def test_read_data_stop_waiting(self):
        class MockPort(object):
            def __init__(self):
                self.event = threading.Event()
                self._times = 0

            def inWaiting(self):
                self._times += 1
                if self._times < 5:
                    return 0
                if self._times == 5:
                    self.event.set()
                    return 0

        port = MockPort()
        buf = array.array('B')
        with self.assertRaises(stentura._StopException):
            stentura._read_data(port, port.event, buf, 0, 1)

    def test_read_data_timeout(self):
        class MockPort(object):
            def inWaiting(self):
                return 0

        port = MockPort()
        buf = array.array('B')
        with self.assertRaises(stentura._TimeoutException):
            stentura._read_data(port, threading.Event(), buf, 0, 0.001)

    def test_read_packet_simple(self):
        class MockPort(object):
            def __init__(self, packet):
                self._packet = packet

            def inWaiting(self):
                return len(self._packet)

            def read(self, count):
                return packet

        buf = array.array('B')
        for packet in [make_response(1, 2, 3, 4, 5),
                       make_response(1, 2, 3, 4, 5, "hello")]:
            port = MockPort(packet)
            response = stentura._read_packet(port, threading.Event(), buf, 1)
            self.assertSequenceEqual(response, packet)

    def test_read_packet_parts(self):
        class MockPort(object):
            def __init__(self, packet):
                self._times = 0
                self._results = {3: packet[0:2],
                                 5: packet[2:4],
                                 7: packet[4:8],
                                 9: packet[8:]}

            def inWaiting(self):
                self._times += 1
                if self._times in self._results:
                    return len(self._results[self._times])

            def read(self, count):
                result = self._results[self._times]
                if len(result) != count:
                    raise Exception("Wrong count.")
                return result

        packet = make_response(1, 2, 3, 4, 5)
        buf = array.array('B')
        port = MockPort(packet)
        event = threading.Event()
        response = stentura._read_packet(port, event, buf, 1)
        self.assertSequenceEqual(packet, response)

    def test_read_packet_fail(self):
        class MockPort(object):
            def __init__(self, length1, length2=0, length=None, set1=False,
                         set2=False, wrong=False):
                self._length1 = length1
                self._length2 = length2
                self._set1 = set1
                self._set2 = set2
                self._read1 = False
                self._read2 = False
                self.event = threading.Event()
                self._wrong = wrong
                if not length:
                    length = length1 + length2
                self._data = [1, 0, length, 0] + ([0] * (length - 4))
                if wrong:
                    self._data.append(0)
                self._data = ''.join([chr(b) for b in self._data])

            def inWaiting(self):
                length = 0
                if not self._read1:
                    length = self._length1
                elif not self._read2:
                    length = self._length2
                if self._wrong:
                    length += 1
                return length

            def read(self, count):
                if not self._read1:
                    self._read1 = True
                    if self._set1:
                        self.event.set()
                    return buffer(self._data, 0, count)
                elif not self._read2:
                    self._read2 = True
                    if self._set2:
                        self.event.set()
                    return buffer(self._data, self._length1, count)
                raise Exception("Alread read data.")

        buf = array.array('B')

        with self.assertRaises(stentura._StopException):
            port = MockPort(3, set1=True)
            stentura._read_packet(port, port.event, buf, 1)

        with self.assertRaises(stentura._StopException):
            port = MockPort(6, 20, length=30, set2=True)
            stentura._read_packet(port, port.event, buf, 1)

        with self.assertRaises(stentura._TimeoutException):
            port = MockPort(3)
            stentura._read_packet(port, port.event, buf, 0.001)

        with self.assertRaises(stentura._TimeoutException):
            port = MockPort(6, 20, length=30)
            stentura._read_packet(port, port.event, buf, 0.001)

        with self.assertRaises(stentura._ProtocolViolationException):
            port = MockPort(18, wrong=True)
            stentura._read_packet(port, port.event, buf, 1)

    def test_write_to_port(self):
        class MockPort(object):
            def __init__(self, chunk):
                self._chunk = chunk
                self.data = ''

            def write(self, data):
                data = data[:self._chunk]
                self.data += data
                return len(data)

        data = ''.join([chr(b) for b in xrange(20)])

        # All in one shot.
        port = MockPort(20)
        stentura._write_to_port(port, data)
        self.assertSequenceEqual(data, port.data)

        # In parts.
        port = MockPort(5)
        stentura._write_to_port(port, data)
        self.assertSequenceEqual(data, port.data)

    def test_send_receive(self):
        event = threading.Event()
        buf, seq, action = array.array('B'), 5, stentura._OPEN
        request = stentura._make_request(array.array('B'), stentura._OPEN, seq)
        correct_response = make_response(seq, action)
        wrong_seq = make_response(seq - 1, action)
        wrong_action = make_response(seq, action + 1)
        bad_response = make_response(seq, action, data="foo", length=15)

        # Correct response first time.
        responses = [correct_response]
        port = MockPacketPort(responses)
        response = stentura._send_receive(port, event, request, buf)
        self.assertSequenceEqual(response, correct_response)

        # Timeout once then correct response.
        responses = ['', correct_response]
        port = MockPacketPort(responses)
        response = stentura._send_receive(port, event, request, buf,
                                          timeout=0.001)
        self.assertSequenceEqual(response, correct_response)

        # Wrong sequence number then correct response.
        responses = [wrong_seq, correct_response]
        port = MockPacketPort(responses)
        response = stentura._send_receive(port, event, request, buf)
        self.assertSequenceEqual(response, correct_response)

        # No correct responses. Also make sure max_retries is honored.
        max_tries = 6
        responses = [''] * max_tries
        port = MockPacketPort(responses)
        with self.assertRaises(stentura._ConnectionLostException):
            stentura._send_receive(port, event, request, buf, max_tries,
            timeout=0.0001)
        self.assertEqual(max_tries, port.writes)

        # Wrong action.
        responses = [wrong_action]
        port = MockPacketPort(responses)
        with self.assertRaises(stentura._ProtocolViolationException):
            stentura._send_receive(port, event, request, buf)

        # Bad packet.
        responses = [bad_response]
        port = MockPacketPort(responses)
        with self.assertRaises(stentura._ProtocolViolationException):
            stentura._send_receive(port, event, request, buf)

        # Stopped.
        responses = []
        event.set()
        port = MockPacketPort(responses)
        with self.assertRaises(stentura._StopException):
            stentura._send_receive(port, event, request, buf)

    def test_sequence_counter(self):
        seq = stentura._SequenceCounter()
        actual = [seq() for x in xrange(512)]
        expected = range(256) * 2
        self.assertEqual(actual, expected)

        seq = stentura._SequenceCounter(67)
        actual = [seq() for x in xrange(512)]
        expected = range(67, 256) + range(256) + range(67)
        self.assertEqual(actual, expected)

    def test_read(self):
        request_buf = array.array('B')
        response_buf = array.array('B')
        stroke_buf = array.array('B')
        event = threading.Event()

        tests = ([0b11000001] * (3 * 512 + 28), [0b11010101] * 4,
                 [0b11000010] * 8)

        for data in tests:
            data = str(buffer(array.array('B', data)))
            requests, responses = make_readc_packets(data)
            port = MockPacketPort(responses, requests)
            seq = stentura._SequenceCounter()
            block, byte = 0, 0
            block, byte, response = stentura._read(port, event, seq, request_buf,
                                      response_buf, stroke_buf, block, byte)
            self.assertEqual(data, str(response))
            self.assertEqual(block, len(data) / 512)
            self.assertEqual(byte, len(data) % 512)

    def test_loop(self):
        class Event(object):
            def __init__(self, count, data, stop=False):
                self.count = count
                self.data = data
                self.stop = stop
                
            def __repr__(self):
                return '<{}, {}, {}>'.format(self.count, self.data, self.stop)

        class MockPort(object):
            def __init__(self, events=[]):
                self._file = ''
                self._out = ''
                self._is_open = False
                self.event = threading.Event()
                self.count = 0
                self.events = [Event(*x) for x in
                               sorted(events, key=lambda x: x[0])]

            def inWaiting(self):
                return len(self._out)

            def write(self, request):
                # Process the packet and put together a response.
                p = parse_request(request)
                if p['action'] == stentura._OPEN:
                    self._out = make_response(p['seq'], p['action'])
                    self._is_open = True
                elif p['action'] == stentura._READC:
                    if not self._is_open:
                        raise Exception("no open")
                    length, block, byte = p['p3'], p['p4'], p['p5']
                    seq = p['seq']
                    action = stentura._READC
                    start = block * 512 + byte
                    end = start + length
                    data = self._file[start:end]
                    self._out = make_response(seq, action, p1=len(data),
                                              data=data)
                while self.events and self.events[0].count <= self.count:
                    event = self.events.pop(0)
                    self.append(event.data)
                    if event.stop:
                        self.event.set()
                self.count += 1
                return len(request)

            def read(self, count):
                if count != len(self._out):
                    raise Exception("Wrong count.")
                return self._out

            def append(self, data):
                self._file += data
                return self

            def flushInput(self):
                pass

            def flushOutput(self):
                pass

        data1 = ''.join([chr(b) for b in [0b11001010] * 4 * 9])
        data1_trans = [['S-', 'K-', 'R-', 'O-', '-F', '-P', '-T', '-D']] * 9
        data2 = ''.join([chr(b) for b in [0b11001011] * 4 * 30])

        tests = [
            # No inputs but nothing crashes either.
            (MockPort([(30, '', True)]), []),
            # A few strokes.
            (MockPort([(23, data1), (43, '', True)]), data1_trans),
            # Ignore data that's there before we started.
            (MockPort([(46, '', True)]).append(data2), []),
            # Ignore data that was there and also parse some strokes.
            (MockPort([(25, data1), (36, '', True)]).append(data2), data1_trans)
        ]

        for test in tests:
            read_data = []

            def callback(data):
                read_data.append(data)

            port = test[0]
            expected = test[1]
            
            ready_called = [False]
            def ready():
                ready_called[0] = True
            
            try:
                ready_called[0] = False
                stentura._loop(port, port.event, callback, ready, 0.001)
            except stentura._StopException:
                pass
            self.assertEqual(read_data, expected)
            self.assertTrue(ready_called[0])

# TODO: add a test on the machine itself with mocks

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = treal
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

# TODO: add tests

"Thread-based monitoring of a stenotype machine using the Treal machine."

import sys

STENO_KEY_CHART = (('K-', 'W-', 'R-', '*', '-R', '-B', '-G', '-S'),
                   ('*', '-F', '-P', '-L', '-T', '-D', '', 'S-'),
                   ('#', '#', '#', '', 'S-', 'T-', 'P-', 'H-'),
                   ('#', '#', '#', '#', '#', '#', '#', '#'),
                   ('', '', '-Z', 'A-', 'O-', '', '-E', '-U'))

def packet_to_stroke(p):
   keys = []
   for i, b in enumerate(p):
       map = STENO_KEY_CHART[i]
       for i in xrange(8):
           if (b >> i) & 1:
               key = map[-i + 7]
               if key:
                   keys.append(key)
   return keys

VENDOR_ID = 3526

EMPTY = [0] * 5

class DataHandler(object):
    def __init__(self, callback):
        self._callback = callback
        self._pressed = EMPTY
        
    def update(self, p):
        if p == EMPTY and self._pressed != EMPTY:
            stroke = packet_to_stroke(self._pressed)
            if stroke:
                self._callback(stroke)
            self._pressed = EMPTY
        else:
            self._pressed = [x[0] | x[1] for x in zip(self._pressed, p)]
        

if sys.platform.startswith('win32'):
    from plover.machine.base import StenotypeBase
    from pywinusb import hid
    
    class Stenotype(StenotypeBase):
        def __init__(self, params):
            StenotypeBase.__init__(self)
            self._machine = None

        def start_capture(self):
            """Begin listening for output from the stenotype machine."""
            devices = hid.HidDeviceFilter(vendor_id = VENDOR_ID).get_devices()
            if len(devices) == 0:
                self._error()
                return
            self._machine = devices[0]
            self._machine.open()
            handler = DataHandler(self._notify)
            
            def callback(p):
                if len(p) != 6: return
                handler.update(p[1:])
            
            self._machine.set_raw_data_handler(callback)
            self._ready()

        def stop_capture(self):
            """Stop listening for output from the stenotype machine."""
            if self._machine:
                self._machine.close()
            self._stopped()

else:
    from plover.machine.base import ThreadedStenotypeBase
    import hid

    class Stenotype(ThreadedStenotypeBase):
        
        def __init__(self, params):
            ThreadedStenotypeBase.__init__(self)
            self._machine = None

        def start_capture(self):
            """Begin listening for output from the stenotype machine."""
            try:
                self._machine = hid.device(VENDOR_ID, 1)
                self._machine.set_nonblocking(1)
            except IOError as e:
                self._error()
                return
            return ThreadedStenotypeBase.start_capture(self)

        def stop_capture(self):
            """Stop listening for output from the stenotype machine."""
            ThreadedStenotypeBase.stop_capture(self)
            if self._machine:
                self._machine.close()
            self._stopped()

        def run(self):
            handler = DataHandler(self._notify)
            self._ready()
            while not self.finished.isSet():
                packet = self._machine.read(5)
                if len(packet) != 5: continue
                handler.update(packet)

if __name__ == '__main__':
    from plover.steno import Stroke
    import time
    def callback(s):
        print Stroke(s).rtfcre
    machine = Stenotype()
    machine.add_callback(callback)
    machine.start_capture()
    time.sleep(30)
    machine.stop_capture()

########NEW FILE########
__FILENAME__ = txbolt
# Copyright (c) 2011 Hesky Fisher
# See LICENSE.txt for details.

"Thread-based monitoring of a stenotype machine using the TX Bolt protocol."

import plover.machine.base

# In the TX Bolt protocol, there are four sets of keys grouped in
# order from left to right. Each byte represents all the keys that
# were pressed in that set. The first two bits indicate which set this
# byte represents. The next bits are set if the corresponding key was
# pressed for the stroke.

# 00XXXXXX 01XXXXXX 10XXXXXX 110XXXXX
#   HWPKTS   UE*OAR   GLBPRF    #ZDST

# The protocol uses variable length packets of one, two, three or four
# bytes. Only those bytes for which keys were pressed will be
# transmitted. The bytes arrive in order of the sets so it is clear
# when a new stroke starts. Also, if a key is pressed in an earlier
# set in one stroke and then a key is pressed only in a later set then
# there will be a zero byte to indicate that this is a new stroke. So,
# it is reliable to assume that a stroke ended when a lower set is
# seen. Additionally, if there is no activity then the machine will
# send a zero byte every few seconds.

STENO_KEY_CHART = ("S-", "T-", "K-", "P-", "W-", "H-",  # 00
                   "R-", "A-", "O-", "*", "-E", "-U",   # 01
                   "-F", "-R", "-P", "-B", "-L", "-G",  # 10
                   "-T", "-S", "-D", "-Z", "#")         # 11


class Stenotype(plover.machine.base.SerialStenotypeBase):
    """TX Bolt interface.

    This class implements the three methods necessary for a standard
    stenotype interface: start_capture, stop_capture, and
    add_callback.

    """

    def __init__(self, params):
        plover.machine.base.SerialStenotypeBase.__init__(self, params)
        self._reset_stroke_state()

    def _reset_stroke_state(self):
        self._pressed_keys = []
        self._last_key_set = 0

    def _finish_stroke(self):
        self._notify(self._pressed_keys)
        self._reset_stroke_state()

    def run(self):
        """Overrides base class run method. Do not call directly."""
        settings = self.serial_port.getSettingsDict()
        settings['timeout'] = 0.1 # seconds
        self.serial_port.applySettingsDict(settings)
        self._ready()
        while not self.finished.isSet():
            # Grab data from the serial port, or wait for timeout if none available.
            raw = self.serial_port.read(max(1, self.serial_port.inWaiting()))
            
            # XXX : work around for python 3.1 and python 2.6 differences
            if isinstance(raw, str):
                raw = [ord(x) for x in raw]

            if not raw and len(self._pressed_keys) > 0:
                self._finish_stroke()
                continue

            for byte in raw:
                key_set = byte >> 6
                if (key_set <= self._last_key_set
                    and len(self._pressed_keys) > 0):
                    self._finish_stroke()
                self._last_key_set = key_set
                for i in xrange(6):
                    if (byte >> i) & 1:
                        self._pressed_keys.append(
                            STENO_KEY_CHART[(key_set * 6) + i])

########NEW FILE########
__FILENAME__ = main
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

"Launch the plover application."

import os
import shutil
import sys
import traceback

WXVER = '2.8'
if not hasattr(sys, 'frozen'):
    import wxversion
    wxversion.ensureMinimal(WXVER)

import wx
import json
import glob

from collections import OrderedDict

import plover.gui.main
import plover.oslayer.processlock
from plover.oslayer.config import CONFIG_DIR, ASSETS_DIR
from plover.config import CONFIG_FILE, DEFAULT_DICTIONARY_FILE, Config

def show_error(title, message):
    """Report error to the user.

    This shows a graphical error and prints the same to the terminal.
    """
    print message
    app = wx.PySimpleApp()
    alert_dialog = wx.MessageDialog(None,
                                    message,
                                    title,
                                    wx.OK | wx.ICON_INFORMATION)
    alert_dialog.ShowModal()
    alert_dialog.Destroy()

def init_config_dir():
    """Creates plover's config dir.

    This usually only does anything the first time plover is launched.
    """
    # Create the configuration directory if needed.
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

    # Copy the default dictionary to the configuration directory.
    if not os.path.exists(DEFAULT_DICTIONARY_FILE):
        unified_dict = {}
        dict_filenames = glob.glob(os.path.join(ASSETS_DIR, '*.json'))
        for dict_filename in dict_filenames:
            unified_dict.update(json.load(open(dict_filename, 'rb')))
        ordered = OrderedDict(sorted(unified_dict.iteritems(), key=lambda x: x[1]))
        outfile = open(DEFAULT_DICTIONARY_FILE, 'wb')
        json.dump(ordered, outfile, indent=0, separators=(',', ': '))

    # Create a default configuration file if one doesn't already
    # exist.
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'wb') as f:
            f.close()


def main():
    """Launch plover."""
    try:
        # Ensure only one instance of Plover is running at a time.
        with plover.oslayer.processlock.PloverLock():
            init_config_dir()
            config = Config()
            config.target_file = CONFIG_FILE
            gui = plover.gui.main.PloverGUI(config)
            gui.MainLoop()
            with open(config.target_file, 'wb') as f:
                config.save(f)
    except plover.oslayer.processlock.LockNotAcquiredException:
        show_error('Error', 'Another instance of Plover is already running.')
    except:
        show_error('Unexpected error', traceback.format_exc())
    os._exit(1)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = orthography
# Copyright (c) 2010-2011 Joshua Harlan Lifton.
# See LICENSE.txt for details.

"""Functions that implement some English orthographic rules."""

import os.path
import re
from plover.config import ASSETS_DIR

word_list_file_name = os.path.join(ASSETS_DIR, 'american_english_words.txt')
WORDS = dict()
try:
    with open(word_list_file_name) as f:
        pairs = [word.strip().rsplit(' ', 1) for word in f]
        pairs.sort(reverse=True, key=lambda x: int(x[1]))
        WORDS = {p[0].lower(): int(p[1]) for p in pairs}
except IOError as e:
    print e

RULES = [
    # == +ly ==
    # artistic + ly = artistically
    (re.compile(r'^(.*[aeiou]c) \^ ly$', re.I),
        r'\1ally'),

    # == +s ==
    # establish + s = establishes (sibilant pluralization)
    (re.compile(r'^(.*(?:s|sh|x|z|zh)) \^ s$', re.I),
        r'\1es'),
    # speech + s = speeches (soft ch pluralization)
    (re.compile(r'^(.*(?:oa|ea|i|ee|oo|au|ou|l|n|(?<![gin]a)r|t)ch) \^ s$', re.I),
        r'\1es'),
    # cherry + s = cherries (consonant + y pluralization)
    (re.compile(r'^(.+[bcdfghjklmnpqrstvwxz])y \^ s$', re.I),
        r'\1ies'),

    # == y ==
    # die+ing = dying
    (re.compile(r'^(.+)ie \^ ing$', re.I),
        r'\1ying'),
    # metallurgy + ist = metallurgist
    (re.compile(r'^(.+[cdfghlmnpr])y \^ ist$', re.I),
        r'\1ist'),
    # beauty + ful = beautiful (y -> i)
    (re.compile(r'^(.+[bcdfghjklmnpqrstvwxz])y \^ ([a-hj-xz].*)$', re.I),
        r'\1i\2'),

    # == e ==
    # write + en = written
    (re.compile(r'^(.+)([t])e \^ en$', re.I), r'\1\2\2en'),


    # narrate + ing = narrating (silent e)
    (re.compile(r'^(.+[bcdfghjklmnpqrstuvwxz])e \^ ([aeiouy].*)$', re.I),
        r'\1\2'),

    # == misc ==
    # defer + ed = deferred (consonant doubling)   XXX monitor(stress not on last syllable)
    (re.compile(r'^(.*(?:[bcdfghjklmnprstvwxyz]|qu)[aeiou])([bcdfgklmnprtvz]) \^ ([aeiouy].*)$', re.I),
        r'\1\2\2\3'),
]


def make_candidates_from_rules(word, suffix, check=lambda x: True):
    candidates = []
    for r in RULES:
        m = r[0].match(word + " ^ " + suffix)
        if m:   
            expanded = m.expand(r[1])
            if check(expanded):
                candidates.append(expanded)
    return candidates

def _add_suffix(word, suffix):
    in_dict_f = lambda x: x in WORDS

    candidates = []
    
    # Try 'ible' and see if it's in the dictionary.
    if suffix == 'able':
        candidates.extend(make_candidates_from_rules(word, 'ible', in_dict_f))
    
    # Try a simple join if it is in the dictionary.
    simple = word + suffix
    if in_dict_f(simple):
        candidates.append(simple)
    
    # Try rules with dict lookup.
    candidates.extend(make_candidates_from_rules(word, suffix, in_dict_f))

    # For all candidates sort by prominence in dictionary and, since sort is
    # stable, also by the order added to candidates list.
    if candidates:
        candidates.sort(key=lambda x: WORDS[x])
        return candidates[0]
    
    # Try rules without dict lookup.
    candidates = make_candidates_from_rules(word, suffix)
    if candidates:
        return candidates[0]
    
    # If all else fails then just do a simple join.
    return simple

def add_suffix(word, suffix):
    """Add a suffix to a word by applying the rules above
    
    Arguments:
        
    word -- A word
    suffix -- The suffix to add
    
    """
    suffix, sep, rest = suffix.partition(' ')
    expanded = _add_suffix(word, suffix)
    return expanded + sep + rest

########NEW FILE########
__FILENAME__ = comscan
from serial.tools.list_ports import comports as serial_comports

try:
    from plover.oslayer.list_ports_posix import comports as alternative_comports
except ImportError:
    alternative_comports = lambda: []
    
def comports():
    try:
        return serial_comports()
    except NameError:
        # For some reason, the official release of pyserial 2.6 has a simple NameError in it :(
        return alternative_comports()

########NEW FILE########
__FILENAME__ = config
# Copyright (c) 2012 Hesky Fisher
# See LICENSE.txt for details.

"""Platform dependent configuration."""

import appdirs
import os
from os.path import realpath, join, dirname, abspath, isfile, pardir
import sys


# If plover is run from a pyinstaller binary.
if hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS'):
    ASSETS_DIR = sys._MEIPASS
    PROGRAM_DIR = dirname(sys.executable)
# If plover is run from an app bundle on Mac.
elif (sys.platform.startswith('darwin') and '.app' in realpath(__file__)):
    ASSETS_DIR = os.getcwd()
    PROGRAM_DIR = abspath(join(dirname(sys.executable), *[pardir] * 3))
else:
    ASSETS_DIR = join(dirname(dirname(realpath(__file__))), 'assets')
    PROGRAM_DIR = os.getcwd()

# If the program's directory has a plover.cfg file then run in "portable mode",
# i.e. store all data in the same directory. This allows keeping all Plover
# files in a portable drive.
if isfile(join(PROGRAM_DIR, 'plover.cfg')):
    CONFIG_DIR = PROGRAM_DIR
else:
    CONFIG_DIR = appdirs.user_data_dir('plover', 'plover')

########NEW FILE########
__FILENAME__ = keyboardcontrol
#!/usr/bin/env python
# Copyright (c) 2010 Joshua Harlan Lifton.
# See LICENSE.txt for details.
#
# keyboardcontrol.py - Abstracted keyboard control.
#
# Uses OS appropriate module.

"""Keyboard capture and control.

This module provides an interface for basic keyboard event capture and
emulation. Set the key_up and key_down functions of the
KeyboardCapture class to capture keyboard input. Call the send_string
and send_backspaces functions of the KeyboardEmulation class to
emulate keyboard input.

"""

import sys

KEYBOARDCONTROL_NOT_FOUND_FOR_OS = \
        "No keyboard control module was found for os %s" % sys.platform

if sys.platform.startswith('linux'):
    import xkeyboardcontrol as keyboardcontrol
elif sys.platform.startswith('win32'):
    import winkeyboardcontrol as keyboardcontrol
elif sys.platform.startswith('darwin'):
    import osxkeyboardcontrol as keyboardcontrol
else:
    raise Exception(KEYBOARDCONTROL_NOT_FOUND_FOR_OS)


class KeyboardCapture(keyboardcontrol.KeyboardCapture):
    """Listen to keyboard events."""
    pass


class KeyboardEmulation(keyboardcontrol.KeyboardEmulation):
    """Emulate printable key presses and backspaces."""
    pass


if __name__ == '__main__':
    kc = KeyboardCapture()
    ke = KeyboardEmulation()

    def test(event):
        print event
        ke.send_backspaces(3)
        ke.send_string('foo')

    # For the windows version
    kc._create_own_pump = True

    kc.key_down = test
    kc.key_up = test
    kc.start()
    print 'Press CTRL-c to quit.'
    try:
        while True:
            pass
    except KeyboardInterrupt:
        kc.cancel()

########NEW FILE########
__FILENAME__ = list_ports_posix
""" This file is taken from the pyserial source trunk and is licensed as follows:

Copyright (C) 2001-2011 Chris Liechti <cliechti(at)gmx.net>; All Rights Reserved.

This is the Python license. In short, you can use this product in commercial and non-commercial applications, modify it, redistribute it. A notification to the author when you use and/or modify it is welcome.

TERMS AND CONDITIONS FOR ACCESSING OR OTHERWISE USING THIS SOFTWARE

LICENSE AGREEMENT

This LICENSE AGREEMENT is between the copyright holder of this product, and the Individual or Organization ("Licensee") accessing and otherwise using this product 
in source or binary form and its associated documentation.
Subject to the terms and conditions of this License Agreement, the copyright holder hereby grants Licensee a nonexclusive, royalty-free, world-wide license to 
reproduce, analyze, test, perform and/or display publicly, prepare derivative works, distribute, and otherwise use this product alone or in any derivative version, 
provided, however, that copyright holders License Agreement and copyright holders notice of copyright are retained in this product alone or in any derivative version 
prepared by Licensee.
In the event Licensee prepares a derivative work that is based on or incorporates this product or any part thereof, and wants to make the derivative work available 
to others as provided herein, then Licensee hereby agrees to include in any such work a brief summary of the changes made to this product.
The copyright holder is making this product available to Licensee on an "AS IS" basis. THE COPYRIGHT HOLDER MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR 
IMPLIED. BY WAY OF EXAMPLE, BUT NOT LIMITATION, THE COPYRIGHT HOLDER MAKES NO AND DISCLAIMS ANY REPRESENTATION OR WARRANTY OF MERCHANTABILITY OR FITNESS FOR ANY 
PARTICULAR PURPOSE OR THAT THE USE OF THIS PRODUCT WILL NOT INFRINGE ANY THIRD PARTY RIGHTS.
THE COPYRIGHT HOLDER SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF THIS PRODUCT FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS A RESULT OF 
MODIFYING, DISTRIBUTING, OR OTHERWISE USING THIS PRODUCT, OR ANY DERIVATIVE THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.
This License Agreement will automatically terminate upon a material breach of its terms and conditions.
Nothing in this License Agreement shall be deemed to create any relationship of agency, partnership, or joint venture between the copyright holder and Licensee. 
This License Agreement does not grant permission to use trademarks or trade names from the copyright holder in a trademark sense to endorse or promote products or 
services of Licensee, or any third party.
By copying, installing or otherwise using this product, Licensee agrees to be bound by the terms and conditions of this License Agreement.

"""

import glob
import sys
import os
import re

try:
    import subprocess
except ImportError:
    def popen(argv):
        try:
            si, so =  os.popen4(' '.join(argv))
            return so.read().strip()
        except:
            raise IOError('lsusb failed')
else:
    def popen(argv):
        try:
            return subprocess.check_output(argv, stderr=subprocess.STDOUT).strip()
        except:
            raise IOError('lsusb failed')


# The comports function is expected to return an iterable that yields tuples of
# 3 strings: port name, human readable description and a hardware ID.
#
# as currently no method is known to get the second two strings easily, they
# are currently just identical to the port name.

# try to detect the OS so that a device can be selected...
plat = sys.platform.lower()

def read_line(filename):
    """help function to read a single line from a file. returns none"""
    try:
        f = open(filename)
        line = f.readline().strip()
        f.close()
        return line
    except IOError:
        return None

def re_group(regexp, text):
    """search for regexp in text, return 1st group on match"""
    if sys.version < '3':
        m = re.search(regexp, text)
    else:
        # text is bytes-like
        m = re.search(regexp, text.decode('ascii', 'replace'))
    if m: return m.group(1)


if   plat[:5] == 'linux':    # Linux (confirmed)
    # try to extract descriptions from sysfs. this was done by experimenting,
    # no guarantee that it works for all devices or in the future...

    def usb_sysfs_hw_string(sysfs_path):
        """given a path to a usb device in sysfs, return a string describing it"""
        bus, dev = os.path.basename(os.path.realpath(sysfs_path)).split('-')
        snr = read_line(sysfs_path+'/serial')
        if snr:
            snr_txt = ' SNR=%s' % (snr,)
        else:
            snr_txt = ''
        return 'USB VID:PID=%s:%s%s' % (
                read_line(sysfs_path+'/idVendor'),
                read_line(sysfs_path+'/idProduct'),
                snr_txt
                )

    def usb_lsusb_string(sysfs_path):
        base = os.path.basename(os.path.realpath(sysfs_path))

        bus, dev = base.split('-')

        try:
            desc = popen(['lsusb', '-v', '-s', '%s:%s' % (bus, dev)])
            # descriptions from device
            iManufacturer = re_group('iManufacturer\s+\w+ (.+)', desc)
            iProduct = re_group('iProduct\s+\w+ (.+)', desc)
            iSerial = re_group('iSerial\s+\w+ (.+)', desc) or ''
            # descriptions from kernel
            idVendor = re_group('idVendor\s+0x\w+ (.+)', desc)
            idProduct = re_group('idProduct\s+0x\w+ (.+)', desc)
            # create descriptions. prefer text from device, fall back to the others
            return '%s %s %s' % (iManufacturer or idVendor, iProduct or idProduct, iSerial)
        except IOError:
            return base

    def describe(device):
        """\
        Get a human readable description.
        For USB-Serial devices try to run lsusb to get a human readable description.
        For USB-CDC devices read the description from sysfs.
        """
        base = os.path.basename(device)
        # USB-Serial devices
        sys_dev_path = '/sys/class/tty/%s/device/driver/%s' % (base, base)
        if os.path.exists(sys_dev_path):
            sys_usb = os.path.dirname(os.path.dirname(os.path.realpath(sys_dev_path)))
            return usb_lsusb_string(sys_usb)
        # USB-CDC devices
        sys_dev_path = '/sys/class/tty/%s/device/interface' % (base,)
        if os.path.exists(sys_dev_path):
            return read_line(sys_dev_path)
        return base

    def hwinfo(device):
        """Try to get a HW identification using sysfs"""
        base = os.path.basename(device)
        if os.path.exists('/sys/class/tty/%s/device' % (base,)):
            # PCI based devices
            sys_id_path = '/sys/class/tty/%s/device/id' % (base,)
            if os.path.exists(sys_id_path):
                return read_line(sys_id_path)
            # USB-Serial devices
            sys_dev_path = '/sys/class/tty/%s/device/driver/%s' % (base, base)
            if os.path.exists(sys_dev_path):
                sys_usb = os.path.dirname(os.path.dirname(os.path.realpath(sys_dev_path)))
                return usb_sysfs_hw_string(sys_usb)
            # USB-CDC devices
            if base.startswith('ttyACM'):
                sys_dev_path = '/sys/class/tty/%s/device' % (base,)
                if os.path.exists(sys_dev_path):
                    return usb_sysfs_hw_string(sys_dev_path + '/..')
        return 'n/a'    # XXX directly remove these from the list?

    def comports():
        devices = glob.glob('/dev/ttyS*') + glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
        return [(d, describe(d), hwinfo(d)) for d in devices]

elif plat == 'cygwin':       # cygwin/win32
    def comports():
        devices = glob.glob('/dev/com*')
        return [(d, d, d) for d in devices]

elif plat[:7] == 'openbsd':    # OpenBSD
    def comports():
        devices = glob.glob('/dev/cua*')
        return [(d, d, d) for d in devices]

elif plat[:3] == 'bsd' or  \
        plat[:7] == 'freebsd':

    def comports():
        devices = glob.glob('/dev/cuad*')
        return [(d, d, d) for d in devices]

elif plat[:6] == 'darwin':   # OS X (confirmed)
    def comports():
        """scan for available ports. return a list of device names."""
        devices = glob.glob('/dev/tty.*')
        return [(d, d, d) for d in devices]

elif plat[:6] == 'netbsd':   # NetBSD
    def comports():
        """scan for available ports. return a list of device names."""
        devices = glob.glob('/dev/dty*')
        return [(d, d, d) for d in devices]

elif plat[:4] == 'irix':     # IRIX
    def comports():
        """scan for available ports. return a list of device names."""
        devices = glob.glob('/dev/ttyf*')
        return [(d, d, d) for d in devices]

elif plat[:2] == 'hp':       # HP-UX (not tested)
    def comports():
        """scan for available ports. return a list of device names."""
        devices = glob.glob('/dev/tty*p0')
        return [(d, d, d) for d in devices]

elif plat[:5] == 'sunos':    # Solaris/SunOS
    def comports():
        """scan for available ports. return a list of device names."""
        devices = glob.glob('/dev/tty*c')
        return [(d, d, d) for d in devices]

elif plat[:3] == 'aix':      # AIX
    def comports():
        """scan for available ports. return a list of device names."""
        devices = glob.glob('/dev/tty*')
        return [(d, d, d) for d in devices]

else:
    raise ImportError("Sorry: no implementation for your platform ('%s') available" % (os.name,))

# test
if __name__ == '__main__':
    for port, desc, hwid in sorted(comports()):
        print "%s: %s [%s]" % (port, desc, hwid)

########NEW FILE########
__FILENAME__ = osxkeyboardcontrol
from Quartz import (
    CFMachPortCreateRunLoopSource,
    CFRunLoopAddSource,
    CFRunLoopGetCurrent,
    CFRunLoopRun,
    CFRunLoopStop,
    CGEventCreateKeyboardEvent,
    CGEventGetFlags,
    CGEventGetIntegerValueField,
    CGEventMaskBit,
    CGEventPost,
    CGEventSetFlags,
    CGEventSourceCreate,
    CGEventSourceGetSourceStateID,
    CGEventTapCreate,
    CGEventTapEnable,
    kCFRunLoopCommonModes,
    kCGEventFlagMaskAlternate,
    kCGEventFlagMaskCommand,
    kCGEventFlagMaskControl,
    kCGEventFlagMaskNonCoalesced,
    kCGEventFlagMaskShift,
    kCGEventKeyDown,
    kCGEventKeyUp,
    kCGEventSourceStateID,
    kCGEventTapOptionDefault,
    kCGHeadInsertEventTap,
    kCGKeyboardEventKeycode,
    kCGSessionEventTap,
)
import threading
import collections
import ctypes
import ctypes.util
import objc
import sys


# This mapping only works on keyboards using the ANSI standard layout. Each
# entry represents a sequence of keystrokes that are needed to achieve the
# given symbol. First, all keydown events are sent, in order, and then all
# keyup events are send in reverse order.
KEYNAME_TO_KEYCODE = collections.defaultdict(list, {
    # The order follows that of the plover guide.
    # Keycodes from http://forums.macrumors.com/showthread.php?t=780577
    '0': [29], '1': [18], '2': [19], '3': [20], '4': [21], '5': [23],
    '6': [22], '7': [26], '8': [28], '9': [25],

    'a': [0], 'b': [11], 'c': [8], 'd': [2], 'e': [14], 'f': [3], 'g': [5],
    'h': [4], 'i': [34], 'j': [38], 'k': [40], 'l': [37], 'm': [46], 'n': [45],
    'o': [31], 'p': [35], 'q': [12], 'r': [15], 's': [1], 't': [17], 'u': [32],
    'v': [9], 'w': [13], 'x': [7], 'y': [16], 'z': [6],

    'A': [56, 0], 'B': [56, 11], 'C': [56, 8], 'D': [56, 2], 'E': [56, 14],
    'F': [56, 3], 'G': [56, 5], 'H': [56, 4], 'I': [56, 34], 'J': [56, 38],
    'K': [56, 40], 'L': [56, 37], 'M': [56, 46], 'N': [56, 45], 'O': [56, 31],
    'P': [56, 35], 'Q': [56, 12], 'R': [56, 15], 'S': [56, 1], 'T': [56, 17],
    'U': [56, 32], 'V': [56, 9], 'W': [56, 13], 'X': [56, 7], 'Y': [56, 16],
    'Z': [56, 6],

    'Alt_L': [58], 'Alt_R': [61], 'Control_L': [59], 'Control_R': [62],
    'Hyper_L': [], 'Hyper_R': [], 'Meta_L': [], 'Meta_R': [],
    'Shift_L': [56], 'Shift_R': [60], 'Super_L': [55], 'Super_R': [55],

    'Caps_Lock': [57], 'Num_Lock': [], 'Scroll_Lock': [], 'Shift_Lock': [],

    'Return': [36], 'Tab': [48], 'BackSpace': [51], 'Delete': [117],
    'Escape': [53], 'Break': [], 'Insert': [], 'Pause': [], 'Print': [],
    'Sys_Req': [],

    'Up': [126], 'Down': [125], 'Left': [123], 'Right': [124],
    'Page_Up': [116],
    'Page_Down': [121], 'Home': [115], 'End': [119],

    'F1': [122], 'F2': [120], 'F3': [99], 'F4': [118], 'F5': [96], 'F6': [97],
    'F7': [98], 'F8': [100], 'F9': [101], 'F10': [109], 'F11': [103],
    'F12': [111], 'F13': [105], 'F14': [107], 'F15': [113], 'F16': [106],
    'F17': [64], 'F18': [79], 'F19': [80], 'F20': [90], 'F21': [], 'F22': [],
    'F23': [], 'F24': [], 'F25': [], 'F26': [], 'F27': [], 'F28': [],
    'F29': [], 'F30': [], 'F31': [], 'F32': [], 'F33': [], 'F34': [],
    'F35': [],

    'L1': [], 'L2': [], 'L3': [], 'L4': [], 'L5': [], 'L6': [],
    'L7': [], 'L8': [], 'L9': [], 'L10': [],

    'R1': [], 'R2': [], 'R3': [], 'R4': [], 'R5': [], 'R6': [],
    'R7': [], 'R8': [], 'R9': [], 'R10': [], 'R11': [], 'R12': [],
    'R13': [], 'R14': [], 'R15': [],

    'KP_0': [82], 'KP_1': [83], 'KP_2': [84], 'KP_3': [85], 'KP_4': [86],
    'KP_5': [87], 'KP_6': [88], 'KP_7': [89], 'KP_8': [91], 'KP_9': [92],
    'KP_Add': [69], 'KP_Begin': [], 'KP_Decimal': [65], 'KP_Delete': [71],
    'KP_Divide': [75], 'KP_Down': [], 'KP_End': [], 'KP_Enter': [76],
    'KP_Equal': [81], 'KP_F1': [], 'KP_F2': [], 'KP_F3': [], 'KP_F4': [],
    'KP_Home': [], 'KP_Insert': [], 'KP_Left': [], 'KP_Multiply': [67],
    'KP_Next': [], 'KP_Page_Down': [], 'KP_Page_Up': [], 'KP_Prior': [],
    'KP_Right': [], 'KP_Separator': [], 'KP_Space': [], 'KP_Subtract': [78],
    'KP_Tab': [], 'KP_Up': [],

    'ampersand': [56, 26], 'apostrophe': [39], 'asciitilde': [56, 50],
    'asterisk': [56, 28], 'at': [56, 19], 'backslash': [42],
    'braceleft': [56, 33], 'braceright': [56, 30], 'bracketleft': [33],
    'bracketright': [30], 'colon': [56, 41], 'comma': [43], 'division': [],
    'dollar': [56, 21], 'equal': [24], 'exclam': [56, 18], 'greater': [56, 47],
    'hyphen': [], 'less': [56, 43], 'minus': [27], 'multiply': [],
    'numbersign': [56, 20], 'parenleft': [56, 25], 'parenright': [56, 29],
    'percent': [56, 23], 'period': [47], 'plus': [56, 24],
    'question': [56, 44], 'quotedbl': [56, 39], 'quoteleft': [],
    'quoteright': [], 'semicolon': [41], 'slash': [44], 'space': [49],
    'underscore': [56, 27],

    # Many of these are possible but I haven't filled them in because it's a
    # pain to do so. Others are only possible with multiple keypresses and
    # releases making it impossible to do as a keycombo.

    'AE': [], 'Aacute': [], 'Acircumflex': [], 'Adiaeresis': [],
    'Agrave': [], 'Aring': [], 'Atilde': [], 'Ccedilla': [], 'Eacute': [],
    'Ecircumflex': [], 'Ediaeresis': [], 'Egrave': [], 'Eth': [],
    'ETH': [], 'Iacute': [], 'Icircumflex': [], 'Idiaeresis': [],
    'Igrave': [], 'Ntilde': [], 'Oacute': [], 'Ocircumflex': [],
    'Odiaeresis': [], 'Ograve': [], 'Ooblique': [], 'Otilde': [],
    'THORN': [], 'Thorn': [], 'Uacute': [], 'Ucircumflex': [],
    'Udiaeresis': [], 'Ugrave': [], 'Yacute': [],

    'ae': [], 'aacute': [], 'acircumflex': [], 'acute': [],
    'adiaeresis': [], 'agrave': [], 'aring': [], 'atilde': [],
    'ccedilla': [], 'eacute': [], 'ecircumflex': [], 'ediaeresis': [],
    'egrave': [], 'eth': [], 'iacute': [], 'icircumflex': [],
    'idiaeresis': [], 'igrave': [], 'ntilde': [], 'oacute': [],
    'ocircumflex': [], 'odiaeresis': [], 'ograve': [], 'oslash': [],
    'otilde': [], 'thorn': [], 'uacute': [], 'ucircumflex': [],
    'udiaeresis': [], 'ugrave': [], 'yacute': [], 'ydiaeresis': [],

    'cedilla': [], 'diaeresis': [], 'grave': [50], 'asciicircum': [56, 22],
    'bar': [56, 42], 'brokenbar': [], 'cent': [], 'copyright': [],
    'currency': [], 'degree': [], 'exclamdown': [], 'guillemotleft': [],
    'guillemotright': [], 'macron': [], 'masculine': [], 'mu': [],
    'nobreakspace': [], 'notsign': [], 'onehalf': [], 'onequarter': [],
    'onesuperior': [], 'ordfeminine': [], 'paragraph': [],
    'periodcentered': [], 'plusminus': [], 'questiondown': [],
    'registered': [], 'script_switch': [], 'section': [], 'ssharp': [],
    'sterling': [], 'threequarters': [], 'threesuperior': [],
    'twosuperior': [], 'yen': [],

    'Begin': [], 'Cancel': [], 'Clear': [], 'Execute': [], 'Find': [],
    'Help': [114], 'Linefeed': [], 'Menu': [], 'Mode_switch': [58],
    'Multi_key': [], 'MultipleCandidate': [], 'Next': [],
    'PreviousCandidate': [], 'Prior': [], 'Redo': [], 'Select': [],
    'SingleCandidate': [], 'Undo': [],

    'Eisu_Shift': [], 'Eisu_toggle': [], 'Hankaku': [], 'Henkan': [],
    'Henkan_Mode': [], 'Hiragana': [], 'Hiragana_Katakana': [],
    'Kana_Lock': [], 'Kana_Shift': [], 'Kanji': [], 'Katakana': [],
    'Mae_Koho': [], 'Massyo': [], 'Muhenkan': [], 'Romaji': [],
    'Touroku': [], 'Zen_Koho': [], 'Zenkaku': [], 'Zenkaku_Hankaku': [],
})


def down(seq):
    return [(x, True) for x in seq]


def up(seq):
    return [(x, False) for x in reversed(seq)]


def down_up(seq):
    return down(seq) + up(seq)

# Maps from literal characters to their key names.
LITERALS = collections.defaultdict(str, {
    '0': '0', '1': '1', '2': '2', '3': '3', '4': '4', '5': '5', '6': '6',
    '7': '7', '8': '8', '9': '9',

    'a': 'a', 'b': 'b', 'c': 'c', 'd': 'd', 'e': 'e', 'f': 'f', 'g': 'g',
    'h': 'h', 'i': 'i', 'j': 'j', 'k': 'k', 'l': 'l', 'm': 'm', 'n': 'n',
    'o': 'o', 'p': 'p', 'q': 'q', 'r': 'r', 's': 's', 't': 't', 'u': 'u',
    'v': 'v', 'w': 'w', 'x': 'x', 'y': 'y', 'z': 'z',

    'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D', 'E': 'E', 'F': 'F', 'G': 'G',
    'H': 'H', 'I': 'I', 'J': 'J', 'K': 'K', 'L': 'L', 'M': 'M', 'N': 'N',
    'O': 'O', 'P': 'P', 'Q': 'Q', 'R': 'R', 'S': 'S', 'T': 'T', 'U': 'U',
    'V': 'V', 'W': 'W', 'X': 'X', 'Y': 'Y', 'Z': 'Z',

    '`': 'grave', '~': 'asciitilde', '!': 'exclam', '@': 'at',
    '#': 'numbersign', '$': 'dollar', '%': 'percent', '^': 'asciicircum',
    '&': 'ampersand', '*': 'asterisk', '(': 'parenleft', ')': 'parenright',
    '-': 'minus', '_': 'underscore', '=': 'equal', '+': 'plus',
    '[': 'bracketleft', ']': 'bracketright', '{': 'braceleft',
    '}': 'braceright', '\\': 'backslash', '|': 'bar', ';': 'semicolon',
    ':': 'colon', '\'': 'apostrophe', '"': 'quotedbl', ',': 'comma',
    '<': 'less', '.': 'period', '>': 'greater', '/': 'slash',
    '?': 'question', '\t': 'Tab', ' ': 'space'
})

# Maps from keycodes to corresponding event masks.
MODIFIER_KEYS_TO_MASKS = {
    58: kCGEventFlagMaskAlternate,
    61: kCGEventFlagMaskAlternate,
    59: kCGEventFlagMaskControl,
    62: kCGEventFlagMaskControl,
    56: kCGEventFlagMaskShift,
    60: kCGEventFlagMaskShift,
    55: kCGEventFlagMaskCommand
}

# kCGEventSourceStatePrivate is -1 but when -1 is passed in here it is
# unmarshalled incorrectly as 10379842816535691263.
MY_EVENT_SOURCE = CGEventSourceCreate(0xFFFFFFFF)  # 32 bit -1
MY_EVENT_SOURCE_ID = CGEventSourceGetSourceStateID(MY_EVENT_SOURCE)

# For the purposes of this class, we're only watching these keys.
KEYCODE_TO_CHAR = {
    50: '`', 29: '0', 18: '1', 19: '2', 20: '3', 21: '4', 23: '5', 22: '6', 26: '7', 28: '8', 25: '9', 27: '-', 24: '=',
    12: 'q', 13: 'w', 14: 'e', 15: 'r', 17: 't', 16: 'y', 32: 'u', 34: 'i', 31: 'o',  35: 'p', 33: '[', 30: ']', 42: '\\',
    0: 'a', 1: 's', 2: 'd', 3: 'f', 5: 'g', 4: 'h', 38: 'j', 40: 'k', 37: 'l', 41: ';', 39: '\'',
    6: 'z', 7: 'x', 8: 'c', 9: 'v', 11: 'b', 45: 'n', 46: 'm', 43: ',', 47: '.', 44: '/',
    49: ' ',
}

class KeyboardCapture(threading.Thread):
    """Implementation of KeyboardCapture for OSX."""

    _KEYBOARD_EVENTS = set([kCGEventKeyDown, kCGEventKeyUp])

    def __init__(self):
        threading.Thread.__init__(self)
        self._running_thread = None
        self.suppress_keyboard(True)

        # Returning the event means that it is passed on for further processing by others. 
        # Returning None means that the event is intercepted.
        def callback(proxy, event_type, event, reference):
            # Don't pass on meta events meant for this event tap.
            if event_type not in self._KEYBOARD_EVENTS:
                return None
            # Don't intercept events from this module.
            if (CGEventGetIntegerValueField(event, kCGEventSourceStateID) ==
                MY_EVENT_SOURCE_ID):
                return event
            # Don't intercept the event if it has modifiers.
            if CGEventGetFlags(event) & ~kCGEventFlagMaskNonCoalesced:
                return event
            keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            if keycode not in KEYCODE_TO_CHAR:
                return event
            char = KEYCODE_TO_CHAR[keycode]
            handler_name = 'key_up' if event_type == kCGEventKeyUp else 'key_down'
            handler = getattr(self, handler_name, lambda event: None)
            handler(KeyboardEvent(char))
            return None if self.is_keyboard_suppressed() else event

        self._tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionDefault,
            CGEventMaskBit(kCGEventKeyDown) | CGEventMaskBit(kCGEventKeyUp),
            callback, None)
        if self._tap is None:
            # Todo(hesky): See if there is a nice way to show the user what's
            # needed (or do it for them).
            raise Exception("Enable access for assistive devices.")
        self._source = CFMachPortCreateRunLoopSource(None, self._tap, 0)
        CGEventTapEnable(self._tap, False)

    def run(self):
        self._running_thread = CFRunLoopGetCurrent()
        CFRunLoopAddSource(self._running_thread, self._source,
            kCFRunLoopCommonModes)
        CGEventTapEnable(self._tap, True)
        CFRunLoopRun()

    def cancel(self):
        CGEventTapEnable(self._tap, False)
        CFRunLoopStop(self._running_thread)

    def can_suppress_keyboard(self):
        return True

    def suppress_keyboard(self, suppress):
        self._suppress_keyboard = suppress

    def is_keyboard_suppressed(self):
        return self._suppress_keyboard


# "Narrow python" unicode objects store chracters in UTF-16 so we 
# can't iterate over characters in the standard way. This workaround 
# let's us iterate over full characters in the string.
def characters(s):
    encoded = s.encode('utf-32-be')
    characters = []
    for i in xrange(len(encoded)/4):
        start = i * 4
        end = start + 4
        character = encoded[start:end].decode('utf-32-be')
        yield character

CGEventKeyboardSetUnicodeString = ctypes.cdll.LoadLibrary(ctypes.util.find_library('ApplicationServices')).CGEventKeyboardSetUnicodeString
CGEventKeyboardSetUnicodeString.restype = None
native_utf16 = 'utf-16-le' if sys.byteorder == 'little' else 'utf-16-be'

def set_string(event, s):
    buf = s.encode(native_utf16)
    CGEventKeyboardSetUnicodeString(objc.pyobjc_id(event), len(buf) / 2, buf)

class KeyboardEmulation(object):

    def __init__(self):
        pass

    def send_backspaces(self, number_of_backspaces):
        for _ in xrange(number_of_backspaces):
            CGEventPost(kCGSessionEventTap,
                CGEventCreateKeyboardEvent(MY_EVENT_SOURCE, 51, True))
            CGEventPost(kCGSessionEventTap,
                CGEventCreateKeyboardEvent(MY_EVENT_SOURCE, 51, False))

    def send_string(self, s):
        for c in characters(s):
            event = CGEventCreateKeyboardEvent(MY_EVENT_SOURCE, 0, True)
            set_string(event, c)
            CGEventPost(kCGSessionEventTap, event)
            event = CGEventCreateKeyboardEvent(MY_EVENT_SOURCE, 0, False)
            set_string(event, c)
            CGEventPost(kCGSessionEventTap, event)

    def send_key_combination(self, combo_string):
        """Emulate a sequence of key combinations.

        Argument:

        combo_string -- A string representing a sequence of key
        combinations. Keys are represented by their names in the
        Xlib.XK module, without the 'XK_' prefix. For example, the
        left Alt key is represented by 'Alt_L'. Keys are either
        separated by a space or a left or right parenthesis.
        Parentheses must be properly formed in pairs and may be
        nested. A key immediately followed by a parenthetical
        indicates that the key is pressed down while all keys enclosed
        in the parenthetical are pressed and released in turn. For
        example, Alt_L(Tab) means to hold the left Alt key down, press
        and release the Tab key, and then release the left Alt key.

        """

        # Convert the argument into a sequence of keycode, event type pairs
        # that, if executed in order, would emulate the key combination
        # represented by the argument.
        keycode_events = []
        key_down_stack = []
        current_command = []
        for c in combo_string:
            if c in (' ', '(', ')'):
                keystring = ''.join(current_command)
                current_command = []
                seq = KEYNAME_TO_KEYCODE[keystring]
                if c == ' ':
                    # Record press and release for command's keys.
                    keycode_events.extend(down_up(seq))
                elif c == '(':
                    # Record press for command's key.
                    keycode_events.extend(down(seq))
                    key_down_stack.append(seq)
                elif c == ')':
                    # Record press and release for command's key and
                    # release previously held keys.
                    keycode_events.extend(down_up(seq))
                    if key_down_stack:
                        keycode_events.extend(up(key_down_stack.pop()))
            else:
                current_command.append(c)
        # Record final command key.
        keystring = ''.join(current_command)
        seq = KEYNAME_TO_KEYCODE[keystring]
        keycode_events.extend(down_up(seq))
        # Release all keys.
        # Should this be legal in the dict (lack of closing parens)?
        for seq in key_down_stack:
            keycode_events.extend(up(seq))

        # Emulate the key combination by sending key events.
        self._send_sequence(keycode_events)

    def _send_sequence(self, sequence):
        # There is a bug in the event system that seems to cause inconsistent
        # modifiers on key events:
        # http://stackoverflow.com/questions/2008126/cgeventpost-possible-bug-when-simulating-keyboard-events
        # My solution is to manage the state myself.
        # I'm not sure how to deal with caps lock.
        # If event_mask is not zero at the end then bad things might happen.
        event_mask = 0
        for keycode, key_down in sequence:
            if not key_down and keycode in MODIFIER_KEYS_TO_MASKS:
                event_mask &= ~MODIFIER_KEYS_TO_MASKS[keycode]
            event = CGEventCreateKeyboardEvent(
                MY_EVENT_SOURCE, keycode, key_down)
            CGEventSetFlags(event, event_mask)
            CGEventPost(kCGSessionEventTap, event)
            if key_down and keycode in MODIFIER_KEYS_TO_MASKS:
                event_mask |= MODIFIER_KEYS_TO_MASKS[keycode]


class KeyboardEvent(object):
    """A keyboard event."""

    def __init__(self, char):
        self.keystring = char

########NEW FILE########
__FILENAME__ = processlock
#!/usr/bin/env python
# Copyright (c) 2012 Hesky Fisher
# See LICENSE.txt for details.
#
# processlock.py - Cross platform global lock to ensure plover only runs once.

"""Global lock to ensure plover only runs once."""

import sys


class LockNotAcquiredException(Exception):

    pass

if sys.platform.startswith('win32'):
    import win32event
    import win32api
    import winerror


    class PloverLock(object):
        # A GUID from http://createguid.com/
        guid = 'plover_{F8C06652-2C51-410B-8D15-C94DF96FC1F9}'

        def __init__(self):
            pass

        def acquire(self):
            self.mutex = win32event.CreateMutex(None, False, self.guid)
            if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
                raise LockNotAcquiredException()

        def release(self):
            if hasattr(self, 'mutex'):
                win32api.CloseHandle(self.mutex)
                del self.mutex

        def __del__(self):
            self.release()

        def __enter__(self):
            self.acquire()

        def __exit__(self, type, value, traceback):
            self.release()

else:
    import fcntl
    import os
    import tempfile


    class PloverLock(object):
        def __init__(self):
            # Check the environment for items to make the lockfile unique
            # fallback if not found
            if 'USER' in os.environ:
                user = os.environ['USER']
            else:
                user = "UNKNOWN"

            if 'DISPLAY' in os.environ:
                display = os.environ['DISPLAY'][-1:]
            else:
                display = "0"

            if hasattr(os, "uname"):
                hostname = os.uname()[1]
            else:
                import socket
                hostname = socket.gethostname()

            lock_file_name = os.path.expanduser(
                '~/.plover-lock-%s-%s' % (hostname, display))
            self.fd = open(lock_file_name, 'w')

        def acquire(self):
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError as e:
                raise LockNotAcquiredException(str(e))

        def release(self):
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
            except:
                pass

        def __del__(self):
            self.release()
            try:
                self.fd.close()
            except:
                pass

        def __enter__(self):
            self.acquire()

        def __exit__(self, type, value, traceback):
            self.release()

########NEW FILE########
__FILENAME__ = winkeyboardcontrol
#!/usr/bin/env python
# Copyright (c) 2011 Hesky Fisher.
# See LICENSE.txt for details.
#
# winkeyboardcontrol.py - capturing and injecting keyboard events in windows.

"""Keyboard capture and control in windows.

This module provides an interface for basic keyboard event capture and
emulation. Set the key_up and key_down functions of the
KeyboardCapture class to capture keyboard input. Call the send_string
and send_backspaces functions of the KeyboardEmulation class to
emulate keyboard input.

"""

import re
import functools

import pyHook
import pythoncom
import threading
import win32api
import win32con
from pywinauto.SendKeysCtypes import SendKeys as _SendKeys

def SendKeys(s):
    _SendKeys(s, with_spaces=True, pause=0)

# For the purposes of this class, we'll only report key presses that
# result in these outputs in order to exclude special key combos.
KEY_TO_ASCII = {
    41: '`', 2: '1', 3: '2', 4: '3', 5: '4', 6: '5', 7: '6', 8: '7', 
    9: '8', 10: '9', 11: '0', 12: '-', 13: '=', 16: 'q', 
    17: 'w', 18: 'e', 19: 'r', 20: 't', 21: 'y', 22: 'u', 23: 'i',
    24: 'o', 25: 'p', 26: '[', 27: ']', 43: '\\',
    30: 'a', 31: 's', 32: 'd', 33: 'f', 34: 'g', 35: 'h', 36: 'j',
    37: 'k', 38: 'l', 39: ';', 40: '\'', 44: 'z', 45: 'x',
    46: 'c', 47: 'v', 48: 'b', 49: 'n', 50: 'm', 51: ',', 
    52: '.', 53: '/', 57: ' ',
}


class KeyboardCapture(threading.Thread):
    """Listen to all keyboard events."""

    CONTROL_KEYS = set(('Lcontrol', 'Rcontrol'))
    SHIFT_KEYS = set(('Lshift', 'Rshift'))
    ALT_KEYS = set(('Lmenu', 'Rmenu'))
    
    def __init__(self):
        threading.Thread.__init__(self)

        self.suppress_keyboard(True)
        
        self.shift = False
        self.ctrl = False
        self.alt = False

        # NOTE(hesky): Does this need to be more efficient and less
        # general if it will be called for every keystroke?
        def on_key_event(func_name, event):
            ascii = KEY_TO_ASCII.get(event.ScanCode, None)
            if not event.Injected:
                if event.Key in self.CONTROL_KEYS:
                    self.ctrl = func_name == 'key_down'
                if event.Key in self.SHIFT_KEYS:
                    self.shift = func_name == 'key_down'
                if event.Key in self.ALT_KEYS:
                    self.alt = func_name == 'key_down'
                if ascii and not self.ctrl and not self.alt and not self.shift:
                    getattr(self, func_name, lambda x: True)(KeyboardEvent(ascii))
                    return not self.is_keyboard_suppressed()
            
            return True

        self.hm = pyHook.HookManager()
        self.hm.KeyDown = functools.partial(on_key_event, 'key_down')
        self.hm.KeyUp = functools.partial(on_key_event, 'key_up')

    def run(self):
        self.hm.HookKeyboard()
        pythoncom.PumpMessages()

    def cancel(self):
        if self.is_alive():
            self.hm.UnhookKeyboard()
            win32api.PostThreadMessage(self.ident, win32con.WM_QUIT)

    def can_suppress_keyboard(self):
        return True

    def suppress_keyboard(self, suppress):
        self._suppress_keyboard = suppress

    def is_keyboard_suppressed(self):
        return self._suppress_keyboard


class KeyboardEmulation:
    "Mapping found here: http://msdn.microsoft.com/en-us/library/8c6yea83"
    ''' Need to test: I can't generate any of these sequences via querty '''
    keymap_multi = {
        "Alt_L": "%",
        "Alt_R": "%",
        "Control_L": "^",
        "Control_R": "^",
        "Shift_L": "+",
        "Shift_R": "+",
        }

    keymap_single = {
        # This library doesn't do anything with just keypresses for alt, ctrl
        # and shift.
        "Alt_L": "",
        "Alt_R": "",
        "Control_L": "",
        "Control_R": "",
        "Shift_L": "",
        "Shift_R": "",

        "Caps_Lock": "{CAPSLOCK}",
        "Num_Lock": "{NUMLOCK}",
        "Scroll_Lock": "{SCROLLLOCK}",
        "Shift_Lock": "{CAPSLOCK}",  # This is the closest we have.

        "Return": "{ENTER}",
        "Tab": "{TAB}",
        "BackSpace": "{BS}",
        "Delete": "{DEL}",
        "Escape": "{ESC}",
        "Break": "{BREAK}",
        "Insert": "{INS}",

        "Down": "{DOWN}",
        "Up": "{UP}",
        "Left": "{LEFT}",
        "Right": "{RIGHT}",
        "Page_Up": "{PGUP}",
        "Page_Down": "{PGDN}",
        "Home": "{HOME}",
        "End": "{END}",

        "Print": "{PRTSC}",
        "Help": "{HELP}",

        "F1": "{F1}",
        "F2": "{F2}",
        "F3": "{F3}",
        "F4": "{F4}",
        "F5": "{F5}",
        "F6": "{F6}",
        "F7": "{F7}",
        "F8": "{F8}",
        "F9": "{F9}",
        "F10": "{F10}",
        "F11": "{F11}",
        "F12": "{F12}",
        "F13": "{F13}",
        "F14": "{F14}",
        "F15": "{F15}",
        "F16": "{F16}",
    }

    SPECIAL_CHARS_PATTERN = re.compile(r'([]{}()+^%~[])')
    
    def send_backspaces(self, number_of_backspaces):
        for _ in xrange(number_of_backspaces):
            SendKeys(self.keymap_single['BackSpace'])

    def send_string(self, s):
        SendKeys(re.sub(self.SPECIAL_CHARS_PATTERN, r'{\1}', s))

    def send_key_combination(self, s):
        combo = []
        tokens = re.split(r'[() ]', s)
        for token in tokens:
            if token in self.keymap_multi:
                combo.append(self.keymap_multi[token])
            elif token in self.keymap_single:
                combo.append(self.keymap_single[token])
            elif token == ' ':
                pass
            else:
                combo.append(token)
        SendKeys(''.join(combo))


class KeyboardEvent(object):
    """A keyboard event."""

    def __init__(self, char):
        self.keystring = char

if __name__ == '__main__':
    kc = KeyboardCapture()
    ke = KeyboardEmulation()

    def test(event):
        print event.keystring
        ke.send_backspaces(1)
        ke.send_string(' you pressed: "' + event.keystring + '" ')

    kc.key_up = test
    kc.start()
    print 'Press CTRL-c to quit.'
    try:
        while True:
            pass
    except KeyboardInterrupt:
        kc.cancel()

########NEW FILE########
__FILENAME__ = xkeyboardcontrol
#!/usr/bin/env python
# Copyright (c) 2010 Joshua Harlan Lifton.
# See LICENSE.txt for details.
#
# keyboardcontrol.py - capturing and injecting X keyboard events
#
# This code requires the X Window System with the 'record' extension
# and python-xlib 1.4 or greater.
#
# This code is based on the AutoKey and pyxhook programs, both of
# which use python-xlib.

"""Keyboard capture and control using Xlib.

This module provides an interface for basic keyboard event capture and
emulation. Set the key_up and key_down functions of the
KeyboardCapture class to capture keyboard input. Call the send_string
and send_backspaces functions of the KeyboardEmulation class to
emulate keyboard input.

For an explanation of keycodes, keysyms, and modifiers, see:
http://tronche.com/gui/x/xlib/input/keyboard-encoding.html

"""

import sys
import threading

from Xlib import X, XK, display
from Xlib.ext import record, xtest
from Xlib.protocol import rq, event

RECORD_EXTENSION_NOT_FOUND = "Xlib's RECORD extension is required, \
but could not be found."

keyboard_capture_instances = []

KEYCODE_TO_PSEUDOKEY = {38: ord("a"),
                        24: ord("q"),
                        25: ord("w"),
                        39: ord("s"),
                        26: ord("e"),
                        40: ord("d"),
                        27: ord("r"),
                        41: ord("f"),
                        54: ord("c"),
                        55: ord("v"),
                        28: ord("t"),
                        42: ord("g"),
                        29: ord("y"),
                        43: ord("h"),
                        57: ord("n"),
                        58: ord("m"),
                        30: ord("u"),
                        44: ord("j"),
                        31: ord("i"),
                        45: ord("k"),
                        32: ord("o"),
                        46: ord("l"),
                        33: ord("p"),
                        47: ord(";"),
                        34: ord("["),
                        48: ord("'"),
                        10: ord("1"),
                        11: ord("2"),
                        12: ord("3"),
                        13: ord("4"),
                        14: ord("5"),
                        15: ord("6"),
                        16: ord("7"),
                        17: ord("8"),
                        18: ord("9"),
                        19: ord("0"),
                        20: ord("-"),
                        21: ord("=")}

class KeyboardCapture(threading.Thread):
    """Listen to keyboard press and release events."""

    def __init__(self):
        """Prepare to listen for keyboard events."""
        threading.Thread.__init__(self)
        self.context = None
        self.key_events_to_ignore = []

        # Assign default callback functions.
        self.key_down = lambda x: True
        self.key_up = lambda x: True

        # Get references to the display.
        self.local_display = display.Display()
        self.record_display = display.Display()

    def run(self):
        # Check if the extension is present
        if not self.record_display.has_extension("RECORD"):
            raise Exception(RECORD_EXTENSION_NOT_FOUND)
            sys.exit(1)
        # Create a recording context for key events.
        self.context = self.record_display.record_create_context(
                                 0,
                                 [record.AllClients],
                                 [{'core_requests': (0, 0),
                                   'core_replies': (0, 0),
                                   'ext_requests': (0, 0, 0, 0),
                                   'ext_replies': (0, 0, 0, 0),
                                   'delivered_events': (0, 0),
                                   'device_events': (X.KeyPress, X.KeyRelease),
                                   'errors': (0, 0),
                                   'client_started': False,
                                   'client_died': False,
                                   }])

        # This method returns only after record_disable_context is
        # called. Until then, the callback function will be called
        # whenever an event occurs.
        self.record_display.record_enable_context(self.context,
                                                  self.process_events)
        # Clean up.
        self.record_display.record_free_context(self.context)

    def start(self):
        """Starts the thread after registering with a global list."""
        keyboard_capture_instances.append(self)
        threading.Thread.start(self)

    def cancel(self):
        """Stop listening for keyboard events."""
        if self.context is not None:
            self.local_display.record_disable_context(self.context)
        self.local_display.flush()
        if self in keyboard_capture_instances:
            keyboard_capture_instances.remove(self)

    def can_suppress_keyboard(self):
        return False

    def suppress_keyboard(self, suppress):
        pass

    def is_keyboard_suppressed(self):
        return False

    def process_events(self, reply):
        """Handle keyboard events.

        This usually means passing them off to other callback methods. 
        """
        if reply.category != record.FromServer:
            return
        if reply.client_swapped:
            # Ignoring swapped protocol data.
            return
        if not len(reply.data) or ord(reply.data[0]) < 2:
            # Not an event.
            return
        data = reply.data
        while len(data):
            event, data = rq.EventField(None).parse_binary_value(data,
                                       self.record_display.display, None, None)
            keycode = event.detail
            modifiers = event.state & ~0b10000 & 0xFF
            keysym = self.local_display.keycode_to_keysym(keycode, modifiers)
            if modifiers == 0:
                keysym = KEYCODE_TO_PSEUDOKEY.get(keycode, keysym)
            key_event = XKeyEvent(keycode, modifiers, keysym)
            # Either ignore the event...
            if self.key_events_to_ignore:
                ignore_keycode, ignore_event_type = self.key_events_to_ignore[0]
                if (keycode == ignore_keycode and
                    event.type == ignore_event_type):
                    self.key_events_to_ignore.pop(0)
                    continue
            # ...or pass it on to a callback method.
            if event.type == X.KeyPress:
                self.key_down(key_event)
            elif event.type == X.KeyRelease:
                self.key_up(key_event)

    def ignore_key_events(self, key_events):
        """A sequence of keycode, event type tuples to ignore.

        The sequence of keycode, event type pairs is added to a
        queue. The first keycode event that matches the head of the
        queue is ignored and the head of the queue is removed. This
        method can be used in combination with
        KeyboardEmulation.send_key_combination to prevent loops.

        Argument:

        key_events -- The sequence of keycode, event type tuples to
        ignore. Each element of the sequence is a two-tuple, the first
        element of which is a keycode (integer in [8-255], inclusive)
        and the second element of which is either Xlib.X.KeyPress or
        Xlib.X.KeyRelease.

        """
        self.key_events_to_ignore += key_events


class KeyboardEmulation(object):
    """Emulate keyboard events."""

    def __init__(self):
        """Prepare to emulate keyboard events."""
        self.display = display.Display()
        self.modifier_mapping = self.display.get_modifier_mapping()
        # Determine the backspace keycode.
        backspace_keysym = XK.string_to_keysym('BackSpace')
        self.backspace_keycode, mods = self._keysym_to_keycode_and_modifiers(
                                                backspace_keysym)
        self.time = 0

    def send_backspaces(self, number_of_backspaces):
        """Emulate the given number of backspaces.

        The emulated backspaces are not detected by KeyboardCapture.

        Argument:

        number_of_backspace -- The number of backspaces to emulate.

        """
        for x in xrange(number_of_backspaces):
            self._send_keycode(self.backspace_keycode)

    def send_string(self, s):
        """Emulate the given string.

        The emulated string is not detected by KeyboardCapture.

        Argument:

        s -- The string to emulate.

        """
        for char in s:
            keysym = ord(char)
            keycode, modifiers = self._keysym_to_keycode_and_modifiers(keysym)
            if keycode is not None:
                self._send_keycode(keycode, modifiers)
                self.display.sync()

    def send_key_combination(self, combo_string):
        """Emulate a sequence of key combinations.

        KeyboardCapture instance would normally detect the emulated
        key events. In order to prevent this, all KeyboardCapture
        instances are told to ignore the emulated key events.

        Argument:

        combo_string -- A string representing a sequence of key
        combinations. Keys are represented by their names in the
        Xlib.XK module, without the 'XK_' prefix. For example, the
        left Alt key is represented by 'Alt_L'. Keys are either
        separated by a space or a left or right parenthesis.
        Parentheses must be properly formed in pairs and may be
        nested. A key immediately followed by a parenthetical
        indicates that the key is pressed down while all keys enclosed
        in the parenthetical are pressed and released in turn. For
        example, Alt_L(Tab) means to hold the left Alt key down, press
        and release the Tab key, and then release the left Alt key.

        """
        # Convert the argument into a sequence of keycode, event type pairs
        # that, if executed in order, would emulate the key
        # combination represented by the argument.
        keycode_events = []
        key_down_stack = []
        current_command = []
        for c in combo_string:
            if c in (' ', '(', ')'):
                keystring = ''.join(current_command)
                keysym = XK.string_to_keysym(keystring)
                keycode, mods = self._keysym_to_keycode_and_modifiers(keysym)
                current_command = []
                if keycode is None:
                    continue
                if c == ' ':
                    # Record press and release for command's key.
                    keycode_events.append((keycode, X.KeyPress))
                    keycode_events.append((keycode, X.KeyRelease))
                elif c == '(':
                    # Record press for command's key.
                    key_down_stack.append(keycode)
                    keycode_events.append((keycode, X.KeyPress))
                elif c == ')':
                    # Record press and release for command's key and
                    # release previously held key.
                    keycode_events.append((keycode, X.KeyPress))
                    keycode_events.append((keycode, X.KeyRelease))
                    if len(key_down_stack):
                        keycode = key_down_stack.pop()
                        keycode_events.append((keycode, X.KeyRelease))
            else:
                current_command.append(c)
        # Record final command key.
        keystring = ''.join(current_command)
        keysym = XK.string_to_keysym(keystring)
        keycode, mods = self._keysym_to_keycode_and_modifiers(keysym)
        if keycode is not None:
            keycode_events.append((keycode, X.KeyPress))
            keycode_events.append((keycode, X.KeyRelease))
        # Release all keys.
        for keycode in key_down_stack:
            keycode_events.append((keycode, X.KeyRelease))

        # Tell all KeyboardCapture instances to ignore the key
        # events that are about to be sent.
        for capture in keyboard_capture_instances:
            capture.ignore_key_events(keycode_events)

        # Emulate the key combination by sending key events.
        for keycode, event_type in keycode_events:
            xtest.fake_input(self.display, event_type, keycode)
            self.display.sync()

    def _send_keycode(self, keycode, modifiers=0):
        """Emulate a key press and release.

        Arguments:

        keycode -- An integer in the inclusive range [8-255].

        modifiers -- An 8-bit bit mask indicating if the key pressed
        is modified by other keys, such as Shift, Capslock, Control,
        and Alt.

        """
        self._send_key_event(keycode, modifiers, event.KeyPress)
        self._send_key_event(keycode, modifiers, event.KeyRelease)

    def _send_key_event(self, keycode, modifiers, event_class):
        """Simulate a key press or release.

        These events are not detected by KeyboardCapture.

        Arguments:

        keycode -- An integer in the inclusive range [8-255].

        modifiers -- An 8-bit bit mask indicating if the key pressed
        is modified by other keys, such as Shift, Capslock, Control,
        and Alt.

        event_class -- One of Xlib.protocol.event.KeyPress or
        Xlib.protocol.event.KeyRelease.

        """
        target_window = self.display.get_input_focus().focus
        # Make sure every event time is different than the previous one, to
        # avoid an application thinking its an auto-repeat.
        self.time = (self.time + 1) % 4294967295
        key_event = event_class(detail=keycode,
                                 time=self.time,
                                 root=self.display.screen().root,
                                 window=target_window,
                                 child=X.NONE,
                                 root_x=1,
                                 root_y=1,
                                 event_x=1,
                                 event_y=1,
                                 state=modifiers,
                                 same_screen=1
                                 )
        target_window.send_event(key_event)

    def _keysym_to_keycode_and_modifiers(self, keysym):
        """Return a keycode and modifier mask pair that result in the keysym.

        There is a one-to-many mapping from keysyms to keycode and
        modifiers pairs; this function returns one of the possibly
        many valid mappings, or the tuple (None, None) if no mapping
        exists.

        Arguments:

        keysym -- A key symbol.

        """
        keycodes = self.display.keysym_to_keycodes(keysym)
        if len(keycodes) > 0:
            keycode, offset = keycodes[0]
            modifiers = 0
            if offset == 1 or offset == 3:
                # The keycode needs the Shift modifier.
                modifiers |= X.ShiftMask
            if offset == 2 or offset == 3:
                # The keysym is in group Group 2 instead of Group 1.
                for i, mod_keycodes in enumerate(self.modifier_mapping):
                    if keycode in mod_keycodes:
                        modifiers |= (1 << i)
            return (keycode, modifiers)
        return (None, None)



class XKeyEvent(object):
    """A class to hold all the information about a key event."""

    def __init__(self, keycode, modifiers, keysym):
        """Create an event instance.

        Arguments:

        keycode -- The keycode that identifies a physical key.

        modifiers -- An 8-bit mask. A set bit means the corresponding
        modifier is active. See Xlib.X.ShiftMask, Xlib.X.LockMask,
        Xlib.X.ControlMask, and Xlib.X.Mod1Mask through
        Xlib.X.Mod5Mask.

        keysym -- The symbol obtained when the key corresponding to
        keycode without any modifiers. The KeyboardEmulation class
        does not track modifiers such as Shift and Control.

        """
        self.keycode = keycode
        self.modifiers = modifiers
        self.keysym = keysym
        # Only want printable characters.
        if keysym < 255 or keysym in (XK.XK_Return, XK.XK_Tab):
            self.keystring = XK.keysym_to_string(keysym)
            if self.keystring == '\x00':
                self.keystring = None
        else:
            self.keystring = None

    def __str__(self):
        return ' '.join([('%s: %s' % (k, str(v)))
                                      for k, v in self.__dict__.items()])

if __name__ == '__main__':
    kc = KeyboardCapture()
    ke = KeyboardEmulation()

    import time

    def test(event):
        if not event.keycode:
            return
        print event
        time.sleep(0.1)
        keycode_events = ke.send_key_combination('Alt_L(Tab)')
        #ke.send_backspaces(5)
        #ke.send_string('Foo:~')

    #kc.key_down = test
    kc.key_up = test
    kc.start()
    print 'Press CTRL-c to quit.'
    try:
        while True:
            pass
    except KeyboardInterrupt:
        kc.cancel()

########NEW FILE########
__FILENAME__ = steno
# Copyright (c) 2010-2011 Joshua Harlan Lifton.
# See LICENSE.txt for details.

# TODO: unit test this file

"""Generic stenography data models.

This module contains the following class:

Stroke -- A data model class that encapsulates a sequence of steno keys.

"""

import re

STROKE_DELIMITER = '/'
IMPLICIT_HYPHENS = set('AOEU*50')

def normalize_steno(strokes_string):
    """Convert steno strings to one common form."""
    strokes = strokes_string.split(STROKE_DELIMITER)
    normalized_strokes = []
    for stroke in strokes:
        if '#' in stroke:
            stroke = stroke.replace('#', '')
            if not re.search('[0-9]', stroke):
                stroke = '#' + stroke
        has_implicit_dash = bool(set(stroke) & IMPLICIT_HYPHENS)
        if has_implicit_dash:
            stroke = stroke.replace('-', '')
        if stroke.endswith('-'):
            stroke = stroke[:-1]
        normalized_strokes.append(stroke)
    return tuple(normalized_strokes)

STENO_KEY_NUMBERS = {'S-': '1-',
                     'T-': '2-',
                     'P-': '3-',
                     'H-': '4-',
                     'A-': '5-',
                     'O-': '0-',
                     '-F': '-6',
                     '-P': '-7',
                     '-L': '-8',
                     '-T': '-9'}

STENO_KEY_ORDER = {"#": 0,
                   "S-": 1,
                   "T-": 2,
                   "K-": 3,
                   "P-": 4,
                   "W-": 5,
                   "H-": 6,
                   "R-": 7,
                   "A-": 8,
                   "O-": 9,
                   "*": 10,
                   "-E": 11,
                   "-U": 12,
                   "-F": 13,
                   "-R": 14,
                   "-P": 15,
                   "-B": 16,
                   "-L": 17,
                   "-G": 18,
                   "-T": 19,
                   "-S": 20,
                   "-D": 21,
                   "-Z": 22}


class Stroke:
    """A standardized data model for stenotype machine strokes.

    This class standardizes the representation of a stenotype chord. A stenotype
    chord can be any sequence of stenotype keys that can be simultaneously
    pressed. Nearly all stenotype machines offer the same set of keys that can
    be combined into a chord, though some variation exists due to duplicate
    keys. This class accounts for such duplication, imposes the standard
    stenographic ordering on the keys, and combines the keys into a single
    string (called RTFCRE for historical reasons).

    """

    IMPLICIT_HYPHEN = set(('A-', 'O-', '5-', '0-', '-E', '-U', '*'))

    def __init__(self, steno_keys) :
        """Create a steno stroke by formatting steno keys.

        Arguments:

        steno_keys -- A sequence of pressed keys.

        """
        # Remove duplicate keys and save local versions of the input 
        # parameters.
        steno_keys_set = set(steno_keys)
        steno_keys = list(steno_keys_set)

        # Order the steno keys so comparisons can be made.
        steno_keys.sort(key=lambda x: STENO_KEY_ORDER.get(x, -1))
         
        # Convert strokes involving the number bar to numbers.
        if '#' in steno_keys:
            numeral = False
            for i, e in enumerate(steno_keys):
                if e in STENO_KEY_NUMBERS:
                    steno_keys[i] = STENO_KEY_NUMBERS[e]
                    numeral = True
            if numeral:
                steno_keys.remove('#')
        
        if steno_keys_set & self.IMPLICIT_HYPHEN:
            self.rtfcre = ''.join(key.strip('-') for key in steno_keys)
        else:
            pre = ''.join(k.strip('-') for k in steno_keys if k[-1] == '-' or 
                          k == '#')
            post = ''.join(k.strip('-') for k in steno_keys if k[0] == '-')
            self.rtfcre = '-'.join([pre, post]) if post else pre

        self.steno_keys = steno_keys

        # Determine if this stroke is a correction stroke.
        self.is_correction = (self.rtfcre == '*')

    def __str__(self):
        if self.is_correction:
            prefix = '*'
        else:
            prefix = ''
        return '%sStroke(%s : %s)' % (prefix, self.rtfcre, self.steno_keys)

    def __eq__(self, other):
        return (isinstance(other, Stroke)
                and self.steno_keys == other.steno_keys)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return str(self)


########NEW FILE########
__FILENAME__ = steno_dictionary
# Copyright (c) 2013 Hesky Fisher.
# See LICENSE.txt for details.

"""StenoDictionary class and related functions.

A steno dictionary maps sequences of steno strokes to translations.

"""

import collections
import itertools
from steno import normalize_steno

class StenoDictionary(collections.MutableMapping):
    """A steno dictionary.

    This dictionary maps immutable sequences to translations and tracks the
    length of the longest key.

    Attributes:
    longest_key -- A read only property holding the length of the longest key.
    save -- If set, is a function that will save this dictionary.

    """
    def __init__(self, *args, **kw):
        self._dict = {}
        self._longest_key_length = 0
        self._longest_listener_callbacks = set()
        self.reverse = collections.defaultdict(list)
        self.filters = []
        self.update(*args, **kw)
        self.save = None
        self._path = ''

    @property
    def longest_key(self):
        """The length of the longest key in the dict."""
        return self._longest_key

    def __len__(self):
        return self._dict.__len__()
        
    def __iter__(self):
        return self._dict.__iter__()

    def __getitem__(self, key):
        value = self._dict.__getitem__(key)
        for f in self.filters:
            if f(key, value):
                raise KeyError('(%s, %s) is filtered' % (str(key), str(value)))
        return value

    def __setitem__(self, key, value):
        self._longest_key = max(self._longest_key, len(key))
        self._dict.__setitem__(key, value)
        self.reverse[value].append(key)

    def __delitem__(self, key):
        value = self._dict[key]
        self.reverse[value].remove(key)
        self._dict.__delitem__(key)
        if len(key) == self.longest_key:
            if self._dict:
                self._longest_key = max(len(x) for x in self._dict.iterkeys())
            else:
                self._longest_key = 0

    def __contains__(self, key):
        contained = self._dict.__contains__(key)
        if not contained:
            return False
        value = self._dict[key]
        for f in self.filters:
            if f(key, value):
                return False
        return True

    def set_path(self, path):
        self._path = path    

    def get_path(self):
        return self._path    

    def iterkeys(self):
        return self._dict.iterkeys()

    def itervalues(self):
        return self._dict.itervalues()
        
    def iteritems(self):
        return self._dict.iteritems()

    @property
    def _longest_key(self):
        return self._longest_key_length

    @_longest_key.setter
    def _longest_key(self, longest_key):
        if longest_key == self._longest_key_length:
            return
        self._longest_key_length = longest_key
        for callback in self._longest_listener_callbacks:
            callback(longest_key)

    def add_longest_key_listener(self, callback):
        self._longest_listener_callbacks.add(callback)

    def remove_longest_key_listener(self, callback):
        self._longest_listener_callbacks.remove(callback)

    def add_filter(self, f):
        self.filters.append(f)
        
    def remove_filter(self, f):
        self.filters.remove(f)
    
    def raw_get(self, key, default):
        """Bypass filters."""
        return self._dict.get(key, default)


class StenoDictionaryCollection(object):
    def __init__(self):
        self.dicts = []
        self.filters = []
        self.longest_key = 0
        self.longest_key_callbacks = set()

    def set_dicts(self, dicts):
        for d in self.dicts:
            d.remove_longest_key_listener(self._longest_key_listener)
        self.dicts = dicts[:]
        self.dicts.reverse()
        for d in dicts:
            d.add_longest_key_listener(self._longest_key_listener)
        self._longest_key_listener()

    def lookup(self, key):
        for d in self.dicts:
            value = d.get(key, None)
            if value:
                for f in self.filters:
                    if f(key, value):
                        return None
                return value

    def raw_lookup(self, key):
        for d in self.dicts:
            value = d.get(key, None)
            if value:
                return value

    def reverse_lookup(self, value):
        for d in self.dicts:
            key = d.reverse.get(value, None)
            if key:
                return key

    def set(self, key, value):
        if self.dicts:
            self.dicts[0][key] = value

    def save(self):
        if self.dicts:
            self.dicts[0].save()

    def save_all(self):
        for dict in self.dicts:
            dict.save()

    def get_by_path(self, path):
        for d in self.dicts:
            if d.get_path() == path:
                return d

    def add_filter(self, f):
        self.filters.append(f)

    def remove_filter(self, f):
        self.filters.remove(f)

    def add_longest_key_listener(self, callback):
        self.longest_key_callbacks.add(callback)

    def remove_longest_key_listener(self, callback):
        self.longest_key_callbacks.remove(callback)
    
    def _longest_key_listener(self, ignored=None):
        new_longest_key = max(d.longest_key for d in self.dicts)
        if new_longest_key != self.longest_key:
            self.longest_key = new_longest_key
            for c in self.longest_key_callbacks:
                c(new_longest_key)

########NEW FILE########
__FILENAME__ = test_config
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

"""Unit tests for config.py."""

import unittest
from mock import patch
from collections import namedtuple
import plover.config as config
from cStringIO import StringIO
from plover.machine.registry import Registry

class ConfigTestCase(unittest.TestCase):

    def test_simple_fields(self):
        Case = namedtuple('Case', ['field', 'section', 'option', 'default', 
                                   'value1', 'value2', 'value3'])

        cases = (
        ('machine_type', config.MACHINE_CONFIG_SECTION, 
         config.MACHINE_TYPE_OPTION, config.DEFAULT_MACHINE_TYPE, 'foo', 'bar', 
         'blee'),
        ('log_file_name', config.LOGGING_CONFIG_SECTION, config.LOG_FILE_OPTION, 
         config.DEFAULT_LOG_FILE, 'l1', 'log', 'sawzall'),
        ('enable_stroke_logging', config.LOGGING_CONFIG_SECTION, 
         config.ENABLE_STROKE_LOGGING_OPTION, 
         config.DEFAULT_ENABLE_STROKE_LOGGING, False, True, False),
        ('enable_translation_logging', config.LOGGING_CONFIG_SECTION, 
         config.ENABLE_TRANSLATION_LOGGING_OPTION, 
         config.DEFAULT_ENABLE_TRANSLATION_LOGGING, False, True, False),
        ('auto_start', config.MACHINE_CONFIG_SECTION, 
         config.MACHINE_AUTO_START_OPTION, config.DEFAULT_MACHINE_AUTO_START, 
         True, False, True),
        ('show_stroke_display', config.STROKE_DISPLAY_SECTION, 
         config.STROKE_DISPLAY_SHOW_OPTION, config.DEFAULT_STROKE_DISPLAY_SHOW, 
         True, False, True),
        ('space_placement', config.OUTPUT_CONFIG_SECTION, 
         config.OUTPUT_CONFIG_SPACE_PLACEMENT_OPTION, config.DEFAULT_OUTPUT_CONFIG_SPACE_PLACEMENT, 
         'Before Output', 'After Output', 'None'),
        ('stroke_display_on_top', config.STROKE_DISPLAY_SECTION, 
         config.STROKE_DISPLAY_ON_TOP_OPTION, 
         config.DEFAULT_STROKE_DISPLAY_ON_TOP, False, True, False),
        ('stroke_display_style', config.STROKE_DISPLAY_SECTION, 
         config.STROKE_DISPLAY_STYLE_OPTION, 
         config.DEFAULT_STROKE_DISPLAY_STYLE, 'Raw', 'Paper', 'Pseudo'),
        ('stroke_display_x', config.STROKE_DISPLAY_SECTION, 
         config.STROKE_DISPLAY_X_OPTION, config.DEFAULT_STROKE_DISPLAY_X, 1, 2, 
         3),
        ('stroke_display_y', config.STROKE_DISPLAY_SECTION, 
         config.STROKE_DISPLAY_Y_OPTION, config.DEFAULT_STROKE_DISPLAY_Y, 1, 2, 
         3),
        ('config_frame_x', config.CONFIG_FRAME_SECTION, 
         config.CONFIG_FRAME_X_OPTION, config.DEFAULT_CONFIG_FRAME_X, 1, 2, 3),
        ('config_frame_y', config.CONFIG_FRAME_SECTION, 
         config.CONFIG_FRAME_Y_OPTION, config.DEFAULT_CONFIG_FRAME_Y, 1, 2, 3),
        ('config_frame_width', config.CONFIG_FRAME_SECTION, 
         config.CONFIG_FRAME_WIDTH_OPTION, config.DEFAULT_CONFIG_FRAME_WIDTH, 1, 
         2, 3),
        ('config_frame_height', config.CONFIG_FRAME_SECTION, 
         config.CONFIG_FRAME_HEIGHT_OPTION, config.DEFAULT_CONFIG_FRAME_HEIGHT, 
         1, 2, 3),
        ('main_frame_x', config.MAIN_FRAME_SECTION, 
         config.MAIN_FRAME_X_OPTION, config.DEFAULT_MAIN_FRAME_X, 1, 2, 3),
        ('main_frame_y', config.MAIN_FRAME_SECTION, 
         config.MAIN_FRAME_Y_OPTION, config.DEFAULT_MAIN_FRAME_Y, 1, 2, 3),
        ('translation_frame_x', config.TRANSLATION_FRAME_SECTION, 
         config.TRANSLATION_FRAME_X_OPTION, config.DEFAULT_TRANSLATION_FRAME_X, 
         1, 2, 3),
        ('translation_frame_y', config.TRANSLATION_FRAME_SECTION, 
         config.TRANSLATION_FRAME_Y_OPTION, config.DEFAULT_TRANSLATION_FRAME_Y, 
         1, 2, 3),
        ('lookup_frame_x', config.LOOKUP_FRAME_SECTION, 
         config.LOOKUP_FRAME_X_OPTION, config.DEFAULT_LOOKUP_FRAME_X, 
         1, 2, 3),
        ('lookup_frame_y', config.LOOKUP_FRAME_SECTION, 
         config.LOOKUP_FRAME_Y_OPTION, config.DEFAULT_LOOKUP_FRAME_Y, 
         1, 2, 3),
        ('dictionary_editor_frame_x', config.DICTIONARY_EDITOR_FRAME_SECTION,
         config.DICTIONARY_EDITOR_FRAME_X_OPTION, config.DEFAULT_DICTIONARY_EDITOR_FRAME_X,
         1, 2, 3),
        ('dictionary_editor_frame_y', config.DICTIONARY_EDITOR_FRAME_SECTION,
         config.DICTIONARY_EDITOR_FRAME_Y_OPTION, config.DEFAULT_DICTIONARY_EDITOR_FRAME_Y,
         1, 2, 3),
        ('serial_config_frame_x', config.SERIAL_CONFIG_FRAME_SECTION, 
         config.SERIAL_CONFIG_FRAME_X_OPTION, 
         config.DEFAULT_SERIAL_CONFIG_FRAME_X, 1, 2, 3),
        ('serial_config_frame_y', config.SERIAL_CONFIG_FRAME_SECTION, 
         config.SERIAL_CONFIG_FRAME_Y_OPTION, 
         config.DEFAULT_SERIAL_CONFIG_FRAME_Y, 1, 2, 3),
        )

        for case in cases:
            case = Case(*case)
            c = config.Config()
            getter = getattr(c, 'get_' + case.field)
            setter = getattr(c, 'set_' + case.field)
            # Check the default value.
            self.assertEqual(getter(), case.default)
            # Set a value...
            setter(case.value1)
            # ...and make sure it is really set.
            self.assertEqual(getter(), case.value1)
            # Load from a file...
            f = StringIO('[%s]\n%s: %s' % (case.section, case.option,
                                           case.value2))
            c.load(f)
            # ..and make sure the right value is set.
            self.assertEqual(getter(), case.value2)
            # Set a value...
            setter(case.value3)
            f = StringIO()
            # ...save it...
            c.save(f)
            # ...and make sure it's right.
            self.assertEqual(f.getvalue(), 
                             '[%s]\n%s = %s\n\n' % (case.section, case.option,
                                                    case.value3))

    def test_clone(self):
        s = '[%s]%s = %s\n\n' % (config.MACHINE_CONFIG_SECTION, 
                                 config.MACHINE_TYPE_OPTION, 'foo')
        c = config.Config()
        c.load(StringIO(s))
        f1 = StringIO()
        c.save(f1)
        c2 = c.clone()
        f2 = StringIO()
        c2.save(f2)
        self.assertEqual(f1.getvalue(), f2.getvalue())

    def test_machine_specific_options(self):
        class FakeMachine(object):
            @staticmethod
            def get_option_info():
                bool_converter = lambda s: s == 'True'
                return {
                    'stroption1': (None, str),
                    'intoption1': (3, int),
                    'stroption2': ('abc', str),
                    'floatoption1': (1, float),
                    'booloption1': (True, bool_converter),
                    'booloption2': (False, bool_converter)
                }
        defaults = {k: v[0] for k, v in FakeMachine.get_option_info().items()}

        machine_name = 'machine foo'
        registry = Registry()
        registry.register(machine_name, FakeMachine)
        with patch('plover.config.machine_registry', registry):
            c = config.Config()
            
            # Check default value.
            actual = c.get_machine_specific_options(machine_name)
            self.assertEqual(actual, defaults)

            # Make sure setting a value is reflecting in the getter.
            options = {
                'stroption1': 'something',
                'intoption1': 5,
                'floatoption1': 5.9,
                'booloption1': False,
            }
            c.set_machine_specific_options(machine_name, options)
            actual = c.get_machine_specific_options(machine_name)
            expected = dict(defaults.items() + options.items())
            self.assertEqual(actual, expected)
            
            # Test loading a file. Unknown option is ignored.
            s = '\n'.join(('[machine foo]', 'stroption1 = foo', 
                           'intoption1 = 3', 'booloption1 = True', 
                           'booloption2 = False', 'unknown = True'))
            f = StringIO(s)
            c.load(f)
            expected = {
                'stroption1': 'foo',
                'intoption1': 3,
                'booloption1': True,
                'booloption2': False,
            }
            expected = dict(defaults.items() + expected.items())
            actual = c.get_machine_specific_options(machine_name)
            self.assertEqual(actual, expected)
            
            # Test saving a file.
            f = StringIO()
            c.save(f)
            self.assertEqual(f.getvalue(), s + '\n\n')
            
            # Test reading invalid values.
            s = '\n'.join(['[machine foo]', 'floatoption1 = None', 
                           'booloption2 = True'])
            f = StringIO(s)
            c.load(f)
            expected = {
                'floatoption1': 1,
                'booloption2': True,
            }
            expected = dict(defaults.items() + expected.items())
            actual = c.get_machine_specific_options(machine_name)
            self.assertEqual(actual, expected)

    def test_dictionary_option(self):
        c = config.Config()
        section = config.DICTIONARY_CONFIG_SECTION
        option = config.DICTIONARY_FILE_OPTION
        # Check the default value.
        self.assertEqual(c.get_dictionary_file_names(), 
                         [config.DEFAULT_DICTIONARY_FILE])
        # Set a value...
        names = ['b', 'a', 'd', 'c']
        c.set_dictionary_file_names(names)
        # ...and make sure it is really set.
        self.assertEqual(c.get_dictionary_file_names(), names)
        # Load from a file encoded the old way...
        f = StringIO('[%s]\n%s: %s' % (section, option, 'some_file'))
        c.load(f)
        # ..and make sure the right value is set.
        self.assertEqual(c.get_dictionary_file_names(), ['some_file'])
        # Load from a file encoded the new way...
        filenames = '\n'.join('%s%d: %s' % (option, d, v) 
                              for d, v in enumerate(names, start=1))
        f = StringIO('[%s]\n%s' % (section, filenames))
        c.load(f)
        # ...and make sure the right value is set.
        self.assertEqual(c.get_dictionary_file_names(), names)
        
        names.reverse()
        
        # Set a value...
        c.set_dictionary_file_names(names)
        f = StringIO()
        # ...save it...
        c.save(f)
        # ...and make sure it's right.
        filenames = '\n'.join('%s%d = %s' % (option, d, v) 
                              for d, v in enumerate(names, start=1))
        self.assertEqual(f.getvalue(), 
                         '[%s]\n%s\n\n' % (section, filenames))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_formatting
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

"""Unit tests for formatting.py."""

import formatting
import unittest

# Add tests with partial output specified.

def action(**kwargs):
    return formatting._Action(**kwargs)

class CaptureOutput(object):
    def __init__(self):
        self.instructions = []
    
    def send_backspaces(self, n):
        self.instructions.append(('b', n))
        
    def send_string(self, s):
        self.instructions.append(('s', s))
        
    def send_key_combination(self, c):
        self.instructions.append(('c', c))
        
    def send_engine_command(self, c):
        self.instructions.append(('e', c))

class MockTranslation(object):
    def __init__(self, rtfcre=tuple(), english=None, formatting=None):
        self.rtfcre = rtfcre
        self.english = english
        self.formatting = formatting
        
    def __str__(self):
        return str(self.__dict__)
        
def translation(**kwargs):
    return MockTranslation(**kwargs)

class FormatterTestCase(unittest.TestCase):

    def check(self, f, cases):
        for input, output in cases:
            self.assertEqual(f(input), output)
            
    def check_arglist(self, f, cases):
        for inputs, expected in cases:
            actual = f(*inputs)
            if actual != expected:
                print actual, '!=', expected, 'for', inputs
            self.assertEqual(actual, expected)

    def test_formatter(self):
        cases = (

        (
         ([translation(formatting=[action(text='hello')])], [], None),
         (),
         [('b', 5)]
        ),
        
        (
         ([], 
          [translation(rtfcre=('S'), english='hello')], 
          translation(rtfcre=('T'), english='a', formatting=[action(text='f')])
         ),
         ([action(text=' hello', word='hello')],),
         [('s', ' hello')]
        ),
        
        (
         ([], [translation(rtfcre=('S'), english='hello')], None),
         ([action(text=' hello', word='hello')],),
         [('s', ' hello')]
        ),
        
        (
         ([], [translation(rtfcre=('ST-T',))], None),
         ([action(text=' ST-T', word='ST-T')],),
         [('s', ' ST-T')]
        ),
        
        (
         ([], 
          [translation(rtfcre=('ST-T',))], 
          translation(formatting=[action(text='hi')])),
         ([action(text=' ST-T', word='ST-T')],),
         [('s', ' ST-T')]
        ),
        
        (
         ([translation(formatting=[action(text=' test')])],
          [translation(english='rest')],
          translation(formatting=[action(capitalize=True)])),
         ([action(text=' Rest', word='Rest')],),
         [('b', 4), ('s', 'Rest')]
        ),
        
        (
         ([translation(formatting=[action(text='dare'), 
                                   action(text='ing', replace='e')])],
         [translation(english='rest')],
         translation(formatting=[action(capitalize=True)])),
         ([action(text=' Rest', word='Rest')],),
         [('b', 6), ('s', ' Rest')]
        ),
        
        (
         ([translation(formatting=[action(text=' drive')])],
         [translation(english='driving')],
         None),
         ([action(text=' driving', word='driving')],),
         [('b', 1), ('s', 'ing')]
        ),
        
        (
         ([translation(formatting=[action(text=' drive')])],
         [translation(english='{#c}driving')],
         None),
         ([action(combo='c'), action(text=' driving', word='driving')],),
         [('b', 6), ('c', 'c'), ('s', ' driving')]
        ),
        
        (
         ([translation(formatting=[action(text=' drive')])],
         [translation(english='{PLOVER:c}driving')],
         None),
         ([action(command='c'), action(text=' driving', word='driving')],),
         [('b', 6), ('e', 'c'), ('s', ' driving')]
        ),
        
        (
         ([],
          [translation(rtfcre=('1',))],
          None),
         ([action(text=' 1', word='1', glue=True)],),
         [('s', ' 1')]
        ),
        
        (
         ([],
          [translation(rtfcre=('1',))],
          translation(formatting=[action(text='hi', word='hi')])),
         ([action(text=' 1', word='1', glue=True)],),
         [('s', ' 1')]
        ),

        (
         ([],
          [translation(rtfcre=('1',))],
          translation(formatting=[action(text='hi', word='hi', glue=True)])),
         ([action(text='1', word='hi1', glue=True)],),
         [('s', '1')]
        ),

        (
         ([],
          [translation(rtfcre=('1-9',))],
          translation(formatting=[action(text='hi', word='hi', glue=True)])),
         ([action(text='19', word='hi19', glue=True)],),
         [('s', '19')]
        ),

        (
         ([],
          [translation(rtfcre=('ST-PL',))],
          translation(formatting=[action(text='hi', word='hi')])),
         ([action(text=' ST-PL', word='ST-PL')],),
         [('s', ' ST-PL')]
        ),

        (
         ([],
          [translation(rtfcre=('ST-PL',))],
          None),
         ([action(text=' ST-PL', word='ST-PL')],),
         [('s', ' ST-PL')]
        ),

        )

        for args, formats, outputs in cases:
            output = CaptureOutput()
            formatter = formatting.Formatter()
            formatter.set_output(output)
            formatter.set_space_placement('Before Output')
            undo, do, prev = args
            formatter.format(undo, do, prev)
            for i in xrange(len(do)):
                self.assertEqual(do[i].formatting, formats[i])
            self.assertEqual(output.instructions, outputs)

    def test_get_last_action(self):
        self.assertEqual(formatting._get_last_action(None), action())
        self.assertEqual(formatting._get_last_action([]), action())
        actions = [action(text='hello'), action(text='world')]
        self.assertEqual(formatting._get_last_action(actions), actions[-1])

    def test_action(self):
        self.assertNotEqual(action(word='test'), 
                            action(word='test', attach=True))
        self.assertEqual(action(text='test'), action(text='test'))
        self.assertEqual(action(text='test', word='test').copy_state(),
                         action(word='test'))

    def test_translation_to_actions(self):
        cases = [
        (('test', action(), False), 
         [action(text=' test', word='test')]),
        
        (('{^^}', action(), False), [action(attach=True, orthography=False)]),
         
        (('1-9', action(), False), 
         [action(word='1-9', text=' 1-9')]),
         
        (('32', action(), False), 
         [action(word='32', text=' 32', glue=True)]),
         
        (('', action(text=' test', word='test', attach=True), False),
         [action(word='test', attach=True)]),
         
        (('  ', action(text=' test', word='test', attach=True), False),
         [action(word='test', attach=True)]),
         
        (('{^} {.} hello {.} {#ALT_L(Grave)}{^ ^}', action(), False),
         [action(attach=True, orthography=False), 
          action(text='.', capitalize=True), 
          action(text=' Hello', word='Hello'), 
          action(text='.', capitalize=True), 
          action(combo='ALT_L(Grave)', capitalize=True),
          action(text=' ', attach=True)
         ]),
         
         (('{-|} equip {^s}', action(), False),
          [action(capitalize=True),
           action(text=' Equip', word='Equip'),
           action(text='s', word='Equips'),
          ]),

        (('{-|} equip {^ed}', action(), False),
         [action(capitalize=True),
          action(text=' Equip', word='Equip'),
          action(text='ped', word='Equipped'),
         ]),

        (('{>} Equip', action(), False),
         [action(lower=True),
          action(text=' equip', word='equip')
         ]),

        (('{>} equip', action(), False),
         [action(lower=True),
          action(text=' equip', word='equip')
         ]),
         
        (('equip {^} {^ed}', action(), False),
         [action(text=' equip', word='equip'),
          action(word='equip', attach=True, orthography=False),
          action(text='ed', word='equiped'),
         ]),
         
         (('{prefix^} test {^ing}', action(), False),
         [action(text=' prefix', word='prefix', attach=True),
          action(text='test', word='test'),
          action(text='ing', word='testing'),
         ]),

        (('{two prefix^} test {^ing}', action(), False),
         [action(text=' two prefix', word='prefix', attach=True),
          action(text='test', word='test'),
          action(text='ing', word='testing'),
         ]),


        (('test', action(), True), 
         [action(text='test ', word='test')]),
        
        (('{^^}', action(), True), [action(attach=True, orthography=False)]),
         
        (('1-9', action(), True), 
         [action(word='1-9', text='1-9 ')]),
         
        (('32', action(), True), 
         [action(word='32', text='32 ', glue=True)]),
         
        (('', action(text='test ', word='test', attach=True), True),
         [action(word='test', attach=True)]),
         
        (('  ', action(text='test ', word='test', attach=True), True),
         [action(word='test', attach=True)]),
         
        (('{^} {.} hello {.} {#ALT_L(Grave)}{^ ^}', action(), True),
         [action(attach=True, orthography=False), 
          action(text='. ', capitalize=True), 
          action(text='Hello ', word='Hello'), 
          action(text='. ', capitalize=True, replace=' '), 
          action(combo='ALT_L(Grave)', capitalize=True),
          action(text=' ', attach=True)
         ]),
         
         (('{-|} equip {^s}', action(), True),
          [action(capitalize=True),
           action(text='Equip ', word='Equip'),
           action(text='s ', word='Equips', replace=' '),
          ]),

        (('{-|} equip {^ed}', action(), True),
         [action(capitalize=True),
          action(text='Equip ', word='Equip'),
          action(text='ped ', word='Equipped', replace=' '),
         ]),

        (('{>} Equip', action(), True),
         [action(lower=True),
          action(text='equip ', word='equip')
         ]),

        (('{>} equip', action(), True),
         [action(lower=True),
          action(text='equip ', word='equip')
         ]),
         
        (('equip {^} {^ed}', action(), True),
         [action(text='equip ', word='equip'),
          action(word='equip', attach=True, orthography=False, replace=' '),
          action(text='ed ', word='equiped'),
         ]),
         
         (('{prefix^} test {^ing}', action(), True),
         [action(text='prefix', word='prefix', attach=True),
          action(text='test ', word='test'),
          action(text='ing ', word='testing', replace=' '),
         ]),

        (('{two prefix^} test {^ing}', action(), True),
         [action(text='two prefix', word='prefix', attach=True),
          action(text='test ', word='test'),
          action(text='ing ', word='testing', replace=' '),
         ]),
        ]
        self.check_arglist(formatting._translation_to_actions, cases)

    def test_raw_to_actions(self):
        cases = (

        (
         ('2-6', action(), False),
         [action(glue=True, text=' 26', word='26')]
        ),

        (
         ('2', action(), False),
         [action(glue=True, text=' 2', word='2')]
        ),

        (
         ('-8', action(), False),
         [action(glue=True, text=' 8', word='8')]
        ),


        (
         ('-68', action(), False),
         [action(glue=True, text=' 68', word='68')]
        ),

        (
         ('S-T', action(), False),
         [action(text=' S-T', word='S-T')]
        ),


        )
        self.check_arglist(formatting._raw_to_actions, cases)

    def test_atom_to_action_spaces_before(self):
        cases = [
        (('{^ed}', action(word='test')), 
         action(text='ed', replace='', word='tested')),
         
        (('{^ed}', action(word='carry')), 
         action(text='ied', replace='y', word='carried')),
          
        (('{^er}', action(word='test')), 
         action(text='er', replace='', word='tester')),
         
        (('{^er}', action(word='carry')), 
         action(text='ier', replace='y', word='carrier')),
                 
        (('{^ing}', action(word='test')), 
         action(text='ing', replace='', word='testing')),

        (('{^ing}', action(word='begin')), 
         action(text='ning', replace='', word='beginning')),
        
        (('{^ing}', action(word='parade')), 
         action(text='ing', replace='e', word='parading')),
                 
        (('{^s}', action(word='test')), 
         action(text='s', replace='', word='tests')),
                 
        (('{,}', action(word='test')), action(text=',')),
         
        (('{:}', action(word='test')), action(text=':')),
         
        (('{;}', action(word='test')), action(text=';')),
         
        (('{.}', action(word='test')), 
         action(text='.', capitalize=True)),
         
        (('{?}', action(word='test')),
         action(text='?', capitalize=True)),

        (('{!}', action(word='test')),
         action(text='!', capitalize=True)),

        (('{-|}', action(word='test')),
         action(capitalize=True, word='test')),

        (('{>}', action(word='test')),
         action(lower=True, word='test')),
          
        (('{PLOVER:test_command}', action(word='test')),
         action(word='test', command='test_command')),
          
        (('{&glue_text}', action(word='test')),
         action(text=' glue_text', word='glue_text', glue=True)),

        (('{&glue_text}', action(word='test', glue=True)),
         action(text='glue_text', word='testglue_text', glue=True)),
           
        (('{&glue_text}', action(word='test', attach=True)),
         action(text='glue_text', word='testglue_text', glue=True)),
           
        (('{^attach_text}', action(word='test')),
         action(text='attach_text', word='testattach_text')),
          
        (('{^attach_text^}', action(word='test')),
         action(text='attach_text', word='testattach_text', attach=True)),
          
        (('{attach_text^}', action(word='test')),
         action(text=' attach_text', word='attach_text', attach=True)),
                
        (('{#ALT_L(A)}', action(word='test')), 
         action(combo='ALT_L(A)', word='test')),
         
        (('text', action(word='test')), 
         action(text=' text', word='text')),

        (('text', action(word='test', glue=True)), 
         action(text=' text', word='text')),
         
        (('text', action(word='test', attach=True)), 
         action(text='text', word='text')),
         
        (('text', action(word='test', capitalize=True)), 
         action(text=' Text', word='Text')),

        (('some text', action(word='test')), 
         action(text=' some text', word='text')),

        ]
        self.check_arglist(formatting._atom_to_action_spaces_before, cases)

    def test_atom_to_action_spaces_after(self):
        cases = [
        (('{^ed}', action(word='test', text='test ')), 
         action(text='ed ', replace=' ', word='tested')),

        (('{^ed}', action(word='carry', text='carry ')), 
         action(text='ied ', replace='y ', word='carried')),

        (('{^er}', action(word='test', text='test ')), 
         action(text='er ', replace=' ', word='tester')),

        (('{^er}', action(word='carry', text='carry ')), 
         action(text='ier ', replace='y ', word='carrier')),

        (('{^ing}', action(word='test', text='test ')), 
         action(text='ing ', replace=' ', word='testing')),

        (('{^ing}', action(word='begin', text='begin ')), 
         action(text='ning ', replace=' ', word='beginning')),

        (('{^ing}', action(word='parade', text='parade ')), 
         action(text='ing ', replace='e ', word='parading')),

        (('{^s}', action(word='test', text='test ')), 
         action(text='s ', replace=' ', word='tests')),

        (('{,}', action(word='test', text='test ')), action(text=', ', replace=' ')),

        (('{:}', action(word='test', text='test ')), action(text=': ', replace=' ')),
         
        (('{;}', action(word='test', text='test ')), action(text='; ', replace=' ')),

        (('{.}', action(word='test', text='test ')), 
         action(text='. ', replace=' ', capitalize=True)),

        (('{?}', action(word='test', text='test ')),
         action(text='? ', replace=' ', capitalize=True)),

        (('{!}', action(word='test', text='test ')),
         action(text='! ', replace=' ', capitalize=True)),

        (('{-|}', action(word='test', text='test ')),
         action(capitalize=True, word='test')),

        (('{>}', action(word='test', text='test ')),
         action(lower=True, word='test')),

        (('{PLOVER:test_command}', action(word='test', text='test ')),
         action(word='test', command='test_command')),
        
        (('{&glue_text}', action(word='test', text='test ')),
         action(text='glue_text ', word='glue_text', glue=True)),
        
        (('{&glue_text}', action(word='test', text='test ', glue=True)),
         action(text='glue_text ', word='testglue_text', replace=' ', glue=True)),
        
        (('{&glue_text}', action(word='test', text='test', attach=True)),
         action(text='glue_text ', word='testglue_text', glue=True)),

        (('{^attach_text}', action(word='test', text='test ')),
         action(text='attach_text ', word='testattach_text', replace=' ')),

        (('{^attach_text^}', action(word='test', text='test ')),
         action(text='attach_text', word='testattach_text', replace=' ', attach=True)),

        (('{attach_text^}', action(word='test', text='test ')),
         action(text='attach_text', word='attach_text', attach=True)),

        (('{#ALT_L(A)}', action(word='test', text='test ')), 
         action(combo='ALT_L(A)', word='test')),

        (('text', action(word='test', text='test ')), 
         action(text='text ', word='text')),

        (('text', action(word='test', text='test ', glue=True)), 
         action(text='text ', word='text')),

        (('text2', action(word='test2', text='test2', attach=True)), 
         action(text='text2 ', word='text2', replace='')),

        (('text', action(word='test', text='test ', capitalize=True)), 
         action(text='Text ', word='Text')),

        (('some text', action(word='test', text='test ')), 
         action(text='some text ', word='text')),
        ]
        self.check_arglist(formatting._atom_to_action_spaces_after, cases)        
    
    def test_get_meta(self):
        cases = [('', None), ('{abc}', 'abc'), ('abc', None)]
        self.check(formatting._get_meta, cases)
    
    def test_apply_glue(self):
        cases = [('abc', '{&abc}'), ('1', '{&1}')]
        self.check(formatting._apply_glue, cases)
    
    def test_unescape_atom(self):
        cases = [('', ''), ('abc', 'abc'), (r'\{', '{'), (r'\}', '}'), 
                 (r'\{abc\}}{', '{abc}}{')]
        self.check(formatting._unescape_atom, cases)
    
    def test_get_engine_command(self):
        cases = [('', None), ('{PLOVER:command}', 'command')]
        self.check(formatting._get_engine_command, cases)
    
    def test_capitalize(self):
        cases = [('', ''), ('abc', 'Abc'), ('ABC', 'ABC')]
        self.check(formatting._capitalize, cases)
    
    def test_rightmost_word(self):
        cases = [('', ''), ('abc', 'abc'), ('a word', 'word'), 
                 ('word.', 'word.')]
        self.check(formatting._rightmost_word, cases)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_logger
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

import unittest
from mock import patch
from logging import Handler
from collections import defaultdict
from plover.logger import Logger

class FakeHandler(Handler):
    
    outputs = defaultdict(list)
    
    def __init__(self, filename, maxBytes=0, backupCount=0):
        Handler.__init__(self)
        self.filename = filename
        
    def emit(self, record):
        FakeHandler.outputs[self.filename].append(record.getMessage())
        
    @staticmethod
    def get_output():
        d = dict(FakeHandler.outputs)
        FakeHandler.outputs.clear()
        return d

class LoggerTestCase(unittest.TestCase):

    def setUp(self):
        self.patcher = patch('plover.logger.RotatingFileHandler', FakeHandler)
        self.patcher.start()
        self.logger = Logger()
            
    def tearDown(self):
        self.logger.set_filename(None)
        self.patcher.stop()

    def test_set_filename(self):
        self.logger.set_filename('fn1')
        self.logger.enable_stroke_logging(True)
        self.logger.log_stroke(('S',))
        self.logger.set_filename('fn2')
        self.logger.log_stroke(('T',))
        self.logger.set_filename(None)
        self.logger.log_stroke(('P',))
        self.assertEqual(FakeHandler.get_output(), {'fn1': ['Stroke(S)'], 
                                                    'fn2': ['Stroke(T)']})

    def test_log_stroke(self):
        self.logger.set_filename('fn')
        self.logger.enable_stroke_logging(True)
        self.logger.log_stroke(('ST', 'T'))
        self.assertEqual(FakeHandler.get_output(), {'fn': ['Stroke(ST T)']})

    def test_log_translation(self):
        self.logger.set_filename('fn')
        self.logger.enable_translation_logging(True)
        self.logger.log_translation(['a', 'b'], ['c', 'd'], None)
        self.assertEqual(FakeHandler.get_output(), 
                        {'fn': ['*a', '*b', 'c', 'd']})

    def test_enable_stroke_logging(self):
        self.logger.set_filename('fn')
        self.logger.log_stroke(('a',))
        self.logger.enable_stroke_logging(True)
        self.logger.log_stroke(('b',))
        self.logger.enable_stroke_logging(False)
        self.logger.log_stroke(('c',))
        self.assertEqual(FakeHandler.get_output(), {'fn': ['Stroke(b)']})

    def test_enable_translation_logging(self):
        self.logger.set_filename('fn')
        self.logger.log_translation(['a'], ['b'], None)
        self.logger.enable_translation_logging(True)
        self.logger.log_translation(['c'], ['d'], None)
        self.logger.enable_translation_logging(False)
        self.logger.log_translation(['e'], ['f'], None)
        self.assertEqual(FakeHandler.get_output(), {'fn': ['*c', 'd']})

if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_orthography
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

from orthography import add_suffix
import unittest

class OrthographyTestCase(unittest.TestCase):

    def test_add_suffix(self):
        cases = (
        
            ('artistic', 'ly', 'artistically'),
            ('cosmetic', 'ly', 'cosmetically'),
            ('establish', 's', 'establishes'),
            ('speech', 's', 'speeches'),
            ('approach', 's', 'approaches'),
            ('beach', 's', 'beaches'),
            ('arch', 's', 'arches'),
            ('larch', 's', 'larches'),
            ('march', 's', 'marches'),
            ('search', 's', 'searches'),
            ('starch', 's', 'starches'),
            ('stomach', 's', 'stomachs'),
            ('monarch', 's', 'monarchs'),
            ('patriarch', 's', 'patriarchs'),
            ('oligarch', 's', 'oligarchs'),
            ('cherry', 's', 'cherries'),
            ('day', 's', 'days'),
            ('penny', 's', 'pennies'),
            ('pharmacy', 'ist', 'pharmacist'),
            ('melody', 'ist', 'melodist'),
            ('pacify', 'ist', 'pacifist'),
            ('geology', 'ist', 'geologist'),
            ('metallurgy', 'ist', 'metallurgist'),
            ('anarchy', 'ist', 'anarchist'),
            ('monopoly', 'ist', 'monopolist'),
            ('alchemy', 'ist', 'alchemist'),
            ('botany', 'ist', 'botanist'),
            ('therapy', 'ist', 'therapist'),
            ('theory', 'ist', 'theorist'),
            ('psychiatry', 'ist', 'psychiatrist'),
            ('lobby', 'ist', 'lobbyist'),
            ('hobby', 'ist', 'hobbyist'),
            ('copy', 'ist', 'copyist'),
            ('beauty', 'ful', 'beautiful'),
            ('weary', 'ness', 'weariness'),
            ('weary', 'some', 'wearisome'),
            ('lonely', 'ness', 'loneliness'),
            ('narrate', 'ing', 'narrating'),
            ('narrate', 'or', 'narrator'),
            ('generalize', 'ability', 'generalizability'),
            ('reproduce', 'able', 'reproducible'),
            ('grade', 'ations', 'gradations'),
            ('urine', 'ary', 'urinary'),
            ('achieve', 'able', 'achievable'),
            ('polarize', 'ation', 'polarization'),
            ('done', 'or', 'donor'),
            ('analyze', 'ed', 'analyzed'),
            ('narrate', 'ing', 'narrating'),
            ('believe', 'able', 'believable'),
            ('animate', 'ors', 'animators'),
            ('discontinue', 'ation', 'discontinuation'),
            ('innovate', 'ive', 'innovative'),
            ('future', 'ists', 'futurists'),
            ('illustrate', 'or', 'illustrator'),
            ('emerge', 'ent', 'emergent'),
            ('equip', 'ed', 'equipped'),
            ('defer', 'ed', 'deferred'),
            ('defer', 'er', 'deferrer'),
            ('defer', 'ing', 'deferring'),
            ('pigment', 'ed', 'pigmented'),
            ('refer', 'ed', 'referred'),
            ('fix', 'ed', 'fixed'),
            ('alter', 'ed', 'altered'),
            ('interpret', 'ing', 'interpreting'),
            ('wonder', 'ing', 'wondering'),
            ('target', 'ing', 'targeting'),
            ('limit', 'er', 'limiter'),
            ('maneuver', 'ing', 'maneuvering'),
            ('monitor', 'ing', 'monitoring'),
            ('color', 'ing', 'coloring'),
            ('inhibit', 'ing', 'inhibiting'),
            ('master', 'ed', 'mastered'),
            ('target', 'ing', 'targeting'),
            ('fix', 'ed', 'fixed'),
            ('scrap', 'y', 'scrappy'),
            ('trip', 's', 'trips'),
            ('equip', 's', 'equips'),
            ('bat', 'en', 'batten'),
            ('smite', 'en', 'smitten'),
            ('got', 'en', 'gotten'),
            ('bite', 'en', 'bitten'),
            ('write', 'en', 'written'),
            ('flax', 'en', 'flaxen'),
            ('wax', 'en', 'waxen'),
            ('fast', 'est', 'fastest'),
            ('white', 'er', 'whiter'),
            ('crap', 'y', 'crappy'),
            ('lad', 'er', 'ladder'),
        
        )
        
        failed = []
        for word, suffix, expected in cases:
            if add_suffix(word, suffix) != expected:
                failed.append((word, suffix, expected))
                
        for word, suffix, expected in failed:
            print 'add_suffix(%s, %s) is %s not %s' % (word, suffix, add_suffix(word, suffix),expected)
            
        self.assertEqual(len(failed), 0)
        
if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_steno
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

"""Unit tests for steno.py."""

import unittest
from steno import normalize_steno, Stroke

class StenoTestCase(unittest.TestCase):
    def test_normalize_steno(self):
        cases = (
        
        # TODO: More cases
        ('S', 'S'),
        ('S-', 'S'),
        ('-S', '-S'),
        ('ES', 'ES'),
        ('-ES', 'ES'),
        ('TW-EPBL', 'TWEPBL'),
        ('TWEPBL', 'TWEPBL'),
        )
        
        for arg, expected in cases:
            self.assertEqual('/'.join(normalize_steno(arg)), expected)
            
    def test_steno(self):
        self.assertEqual(Stroke(['S-']).rtfcre, 'S')
        self.assertEqual(Stroke(['S-', 'T-']).rtfcre, 'ST')
        self.assertEqual(Stroke(['T-', 'S-']).rtfcre, 'ST')
        self.assertEqual(Stroke(['-P', '-P']).rtfcre, '-P')
        self.assertEqual(Stroke(['-P', 'X-']).rtfcre, 'X-P')

if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_steno_dictionary
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

"""Unit tests for steno_dictionary.py."""

import unittest
from steno_dictionary import StenoDictionary, StenoDictionaryCollection

class StenoDictionaryTestCase(unittest.TestCase):

    def test_dictionary(self):
        notifications = []
        def listener(longest_key):
            notifications.append(longest_key)
        
        d = StenoDictionary()
        self.assertEqual(d.longest_key, 0)
        
        d.add_longest_key_listener(listener)
        d[('S',)] = 'a'
        self.assertEqual(d.longest_key, 1)
        self.assertEqual(notifications, [1])
        d[('S', 'S', 'S', 'S')] = 'b'
        self.assertEqual(d.longest_key, 4)
        self.assertEqual(notifications, [1, 4])
        d[('S', 'S')] = 'c'
        self.assertEqual(d.longest_key, 4)
        self.assertEqual(d[('S', 'S')], 'c')
        self.assertEqual(notifications, [1, 4])
        del d[('S', 'S', 'S', 'S')]
        self.assertEqual(d.longest_key, 2)
        self.assertEqual(notifications, [1, 4, 2])
        del d[('S',)]
        self.assertEqual(d.longest_key, 2)
        self.assertEqual(notifications, [1, 4, 2])
        d.clear()
        self.assertEqual(d.longest_key, 0)
        self.assertEqual(notifications, [1, 4, 2, 0])
        
        d.remove_longest_key_listener(listener)
        d[('S', 'S')] = 'c'
        self.assertEqual(d.longest_key, 2)
        self.assertEqual(notifications, [1, 4, 2, 0])
        
        self.assertEqual(StenoDictionary([('a', 'b')]).items(), [('a', 'b')])
        self.assertEqual(StenoDictionary(a='b').items(), [('a', 'b')])
        
    def test_dictionary_collection(self):
        dc = StenoDictionaryCollection()
        d1 = StenoDictionary()
        d1[('S',)] = 'a'
        d1[('T',)] = 'b'
        d2 = StenoDictionary()
        d2[('S',)] = 'c'
        d2[('W',)] = 'd'
        dc.set_dicts([d1, d2])
        self.assertEqual(dc.lookup(('S',)), 'c')
        self.assertEqual(dc.lookup(('W',)), 'd')
        self.assertEqual(dc.lookup(('T',)), 'b')
        f = lambda k, v: v == 'c'
        dc.add_filter(f)
        self.assertIsNone(dc.lookup(('S',)))
        self.assertEqual(dc.raw_lookup(('S',)), 'c')
        self.assertEqual(dc.lookup(('W',)), 'd')
        self.assertEqual(dc.lookup(('T',)), 'b')
        self.assertEqual(dc.reverse_lookup('c'), [('S',)])
        
        dc.remove_filter(f)
        self.assertEqual(dc.lookup(('S',)), 'c')
        self.assertEqual(dc.lookup(('W',)), 'd')
        self.assertEqual(dc.lookup(('T',)), 'b')
        
        self.assertEqual(dc.reverse_lookup('c'), [('S',)])
        
        dc.set(('S',), 'e')
        self.assertEqual(dc.lookup(('S',)), 'e')
        self.assertEqual(d2[('S',)], 'e')
        
if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_translation
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

"""Unit tests for translation.py."""

from collections import namedtuple
import copy
from mock import patch
from steno_dictionary import StenoDictionary, StenoDictionaryCollection
from translation import Translation, Translator, _State, _translate_stroke, _lookup
import unittest
from plover.steno import Stroke, normalize_steno

def stroke(s):
    keys = []
    on_left = True
    for k in s:
        if k in 'EU*-':
            on_left = False
        if k == '-': 
            continue
        elif k == '*': 
            keys.append(k)
        elif on_left: 
            keys.append(k + '-')
        else:
            keys.append('-' + k)
    return Stroke(keys)

class TranslationTestCase(unittest.TestCase):
    def test_no_translation(self):
        t = Translation([stroke('S'), stroke('T')], None)
        self.assertEqual(t.strokes, [stroke('S'), stroke('T')])
        self.assertEqual(t.rtfcre, ('S', 'T'))
        self.assertIsNone(t.english)
        
    def test_translation(self):
        t = Translation([stroke('S'), stroke('T')], 'translation')
        self.assertEqual(t.strokes, [stroke('S'), stroke('T')])
        self.assertEqual(t.rtfcre, ('S', 'T'))
        self.assertEqual(t.english, 'translation')

class TranslatorStateSizeTestCase(unittest.TestCase):
    class FakeState(_State):
        def __init__(self):
            _State.__init__(self)
            self.restrict_calls = []
        def restrict_size(self, n):
            self.restrict_calls.append(n)

    def assert_size_call(self, size):
        self.assertEqual(self.s.restrict_calls[-1], size)

    def assert_no_size_call(self):
        self.assertEqual(self.s.restrict_calls, [])

    def clear(self):
        self.s.restrict_calls = []

    def setUp(self):
        self.t = Translator()
        self.s = type(self).FakeState()
        self.t._state = self.s
        self.d = StenoDictionary()
        self.dc = StenoDictionaryCollection()
        self.dc.set_dicts([self.d])
        self.t.set_dictionary(self.dc)

    def test_dictionary_update_grows_size1(self):
        self.d[('S',)] = '1'
        self.assert_size_call(1)

    def test_dictionary_update_grows_size4(self):
        self.d[('S', 'PT', '-Z', 'TOP')] = 'hi'
        self.assert_size_call(4)

    def test_dictionary_update_no_grow(self):
        self.t.set_min_undo_length(4)
        self.assert_size_call(4)
        self.clear()
        self.d[('S', 'T')] = 'nothing'
        self.assert_size_call(4)

    def test_dictionary_update_shrink(self):
        self.d[('S', 'T', 'P', '-Z', '-D')] = '1'
        self.assert_size_call(5)
        self.clear()
        self.d[('A', 'P')] = '2'
        self.assert_no_size_call()
        del self.d[('S', 'T', 'P', '-Z', '-D')]
        self.assert_size_call(2)

    def test_dictionary_update_no_shrink(self):
        self.t.set_min_undo_length(7)
        self.d[('S', 'T', 'P', '-Z', '-D')] = '1'
        del self.d[('S', 'T', 'P', '-Z', '-D')]
        self.assert_size_call(7)

    def test_translation_calls_restrict(self):
        self.t.translate(stroke('S'))
        self.assert_size_call(0)

class TranslatorTestCase(unittest.TestCase):

    def test_translate_calls_translate_stroke(self):
        t = Translator()
        s = stroke('S')
        def check(stroke, state, dictionary, output):
            self.assertEqual(stroke, s)
            self.assertEqual(state, t._state)
            self.assertEqual(dictionary, t._dictionary)
            self.assertEqual(output, t._output)

        with patch('plover.translation._translate_stroke', check) as _translate_stroke:
            t.translate(s)

    def test_listeners(self):
        output1 = []
        def listener1(undo, do, prev):
            output1.append((undo, do, prev))
        
        output2 = []
        def listener2(undo, do, prev):
            output2.append((undo, do, prev))
        
        t = Translator()
        s = stroke('S')
        tr = Translation([s], None)
        expected_output = [([], [tr], tr)]
        
        t.translate(s)
        
        t.add_listener(listener1)
        t.translate(s)
        self.assertEqual(output1, expected_output)
        
        del output1[:]
        t.add_listener(listener2)
        t.translate(s)
        self.assertEqual(output1, expected_output)
        self.assertEqual(output2, expected_output)

        del output1[:]
        del output2[:]
        t.add_listener(listener2)
        t.translate(s)
        self.assertEqual(output1, expected_output)
        self.assertEqual(output2, expected_output)

        del output1[:]
        del output2[:]
        t.remove_listener(listener1)
        t.translate(s)
        self.assertEqual(output1, [])
        self.assertEqual(output2, expected_output)

        del output1[:]
        del output2[:]
        t.remove_listener(listener2)
        t.translate(s)
        self.assertEqual(output1, [])
        self.assertEqual(output2, [])
        
    def test_changing_state(self):
        output = []
        def listener(undo, do, prev):
            output.append((undo, do, prev))

        d = StenoDictionary()
        d[('S', 'P')] = 'hi'
        dc = StenoDictionaryCollection()
        dc.set_dicts([d])
        t = Translator()
        t.set_dictionary(dc)
        t.translate(stroke('T'))
        t.translate(stroke('S'))
        s = copy.deepcopy(t.get_state())
        
        t.add_listener(listener)
        
        expected = [([Translation([stroke('S')], None)], 
                     [Translation([stroke('S'), stroke('P')], 'hi')], 
                     Translation([stroke('T')], None))]
        t.translate(stroke('P'))
        self.assertEqual(output, expected)
        
        del output[:]
        t.set_state(s)
        t.translate(stroke('P'))
        self.assertEqual(output, expected)
        
        del output[:]
        t.clear_state()
        t.translate(stroke('P'))
        self.assertEqual(output, [([], [Translation([stroke('P')], None)], None)])
        
        del output[:]
        t.set_state(s)
        t.translate(stroke('P'))
        self.assertEqual(output, 
                         [([], 
                           [Translation([stroke('P')], None)], 
                           Translation([stroke('S'), stroke('P')], 'hi'))])

    def test_translator(self):

        # It's not clear that this test is needed anymore. There are separate 
        # tests for _translate_stroke and test_translate_calls_translate_stroke 
        # makes sure that translate calls it properly. But since I already wrote
        # this test I'm going to keep it.

        class Output(object):
            def __init__(self):
                self._output = []
                
            def write(self, undo, do, prev):
                for t in undo:
                    self._output.pop()
                for t in do:
                    if t.english:
                        self._output.append(t.english)
                    else:
                        self._output.append('/'.join(t.rtfcre))
                        
            def get(self):
                return ' '.join(self._output)
                
            def clear(self):
                del self._output[:]
                
        d = StenoDictionary()        
        out = Output()        
        t = Translator()
        dc = StenoDictionaryCollection()
        dc.set_dicts([d])
        t.set_dictionary(dc)
        t.add_listener(out.write)
        
        t.translate(stroke('S'))
        self.assertEqual(out.get(), 'S')
        t.translate(stroke('T'))
        self.assertEqual(out.get(), 'S T')
        t.translate(stroke('*'))
        self.assertEqual(out.get(), 'S')
        t.translate(stroke('*'))
        self.assertEqual(out.get(), 'S')  # Undo buffer ran out.
        
        t.set_min_undo_length(3)
        out.clear()
        t.translate(stroke('S'))
        self.assertEqual(out.get(), 'S')
        t.translate(stroke('T'))
        self.assertEqual(out.get(), 'S T')
        t.translate(stroke('*'))
        self.assertEqual(out.get(), 'S')
        t.translate(stroke('*'))
        self.assertEqual(out.get(), '')
        t.translate(stroke('*'))
        self.assertEqual(out.get(), '')  # Undo buffer ran out.
        
        out.clear()
        d[('S',)] = 't1'
        d[('T',)] = 't2'
        d[('S', 'T')] = 't3'
        
        t.translate(stroke('S'))
        self.assertEqual(out.get(), 't1')
        t.translate(stroke('T'))
        self.assertEqual(out.get(), 't3')
        t.translate(stroke('T'))
        self.assertEqual(out.get(), 't3 t2')
        t.translate(stroke('S'))
        self.assertEqual(out.get(), 't3 t2 t1')
        t.translate(stroke('*'))
        self.assertEqual(out.get(), 't3 t2')
        t.translate(stroke('*'))
        self.assertEqual(out.get(), 't3')
        t.translate(stroke('*'))
        self.assertEqual(out.get(), 't1')
        t.translate(stroke('*'))
        self.assertEqual(out.get(), '')
        
        t.translate(stroke('S'))
        self.assertEqual(out.get(), 't1')
        t.translate(stroke('T'))
        self.assertEqual(out.get(), 't3')
        t.translate(stroke('T'))
        self.assertEqual(out.get(), 't3 t2')

        d[('S', 'T', 'T')] = 't4'
        d[('S', 'T', 'T', 'S')] = 't5'
        
        t.translate(stroke('S'))
        self.assertEqual(out.get(), 't5')
        t.translate(stroke('*'))
        self.assertEqual(out.get(), 't3 t2')
        t.translate(stroke('*'))
        self.assertEqual(out.get(), 't3')
        t.translate(stroke('T'))
        self.assertEqual(out.get(), 't4')
        t.translate(stroke('S'))
        self.assertEqual(out.get(), 't5')
        t.translate(stroke('S'))
        self.assertEqual(out.get(), 't5 t1')
        t.translate(stroke('*'))
        self.assertEqual(out.get(), 't5')
        t.translate(stroke('*'))
        self.assertEqual(out.get(), 't4')
        t.translate(stroke('*'))
        self.assertEqual(out.get(), 't3')
        t.translate(stroke('*'))
        self.assertEqual(out.get(), 't1')
        t.translate(stroke('*'))
        self.assertEqual(out.get(), '')
        
        d.clear()

        s = stroke('S')
        t.translate(s)
        t.translate(s)
        t.translate(s)
        t.translate(s)
        s = stroke('*')
        t.translate(s)
        t.translate(s)
        t.translate(s)
        t.translate(s)
        self.assertEqual(out.get(), 'S')  # Not enough undo to clear output.
        
        out.clear()
        t.remove_listener(out.write)
        t.translate(stroke('S'))
        self.assertEqual(out.get(), '')

class StateTestCase(unittest.TestCase):
    
    def setUp(self):
        self.a = Translation([stroke('S')], None)
        self.b = Translation([stroke('T'), stroke('-D')], None)
        self.c = Translation([stroke('-Z'), stroke('P'), stroke('T*')], None)
    
    def test_last_list0(self):
        s = _State()
        self.assertIsNone(s.last())    
    
    def test_last_list1(self):
        s = _State()
        s.translations = [self.a]
        self.assertEqual(s.last(), self.a)

    def test_last_list2(self):
        s = _State()
        s.translations = [self.a, self.b]
        self.assertEqual(s.last(), self.b)        

    def test_last_tail1(self):
        s = _State()
        s.translations = [self.a]
        s.tail = self.b
        self.assertEqual(s.last(), self.a)

    def test_last_tail0(self):
        s = _State()
        s.tail = self.b
        self.assertEqual(s.last(), self.b)
        
    def test_restrict_size_zero_on_empty(self):
        s = _State()
        s.restrict_size(0)
        self.assertEquals(s.translations, [])
        self.assertIsNone(s.tail)

    def test_restrict_size_zero_on_one_stroke(self):
        s = _State()
        s.translations = [self.a]
        s.restrict_size(0)
        self.assertEquals(s.translations, [self.a])
        self.assertIsNone(s.tail)

    def test_restrict_size_to_exactly_one_stroke(self):
        s = _State()
        s.translations = [self.a]
        s.restrict_size(1)
        self.assertEquals(s.translations, [self.a])
        self.assertIsNone(s.tail)
        
    def test_restrict_size_to_one_on_two_strokes(self):
        s = _State()
        s.translations = [self.b]
        s.restrict_size(1)
        self.assertEquals(s.translations, [self.b])
        self.assertIsNone(s.tail)

    def test_restrict_size_to_one_on_two_translations(self):
        s = _State()
        s.translations = [self.b, self.a]
        s.restrict_size(1)
        self.assertEquals(s.translations, [self.a])
        self.assertEqual(s.tail, self.b)

    def test_restrict_size_to_one_on_two_translations_too_big(self):
        s = _State()
        s.translations = [self.a, self.b]
        s.restrict_size(1)
        self.assertEquals(s.translations, [self.b])
        self.assertEqual(s.tail, self.a)

    def test_restrict_size_lose_translations(self):
        s = _State()
        s.translations = [self.a, self.b, self.c]
        s.restrict_size(2)
        self.assertEquals(s.translations, [self.c])
        self.assertEqual(s.tail, self.b)

    def test_restrict_size_multiple_translations(self):
        s = _State()
        s.translations = [self.a, self.b, self.c]
        s.restrict_size(5)
        self.assertEquals(s.translations, [self.b, self.c])
        self.assertEqual(s.tail, self.a)

class TranslateStrokeTestCase(unittest.TestCase):

    class CaptureOutput(object):
        output = namedtuple('output', 'undo do prev')
        
        def __init__(self):
            self.output = []

        def __call__(self, undo, new, prev):
            self.output = type(self).output(undo, new, prev)

    def t(self, strokes):
        """A quick way to make a translation."""
        strokes = [stroke(x) for x in strokes.split('/')]
        return Translation(strokes, _lookup(strokes, self.dc, []))

    def lt(self, translations):
        """A quick way to make a list of translations."""
        return [self.t(x) for x in translations.split()]

    def define(self, key, value):
        key = normalize_steno(key)
        self.d[key] = value

    def translate(self, stroke):
        _translate_stroke(stroke, self.s, self.dc, self.o)

    def assertTranslations(self, expected):
        self.assertEqual(self.s.translations, expected)

    def assertOutput(self, undo, do, prev):
        self.assertEqual(self.o.output, (undo, do, prev))

    def setUp(self):
        self.d = StenoDictionary()
        self.dc = StenoDictionaryCollection()
        self.dc.set_dicts([self.d])
        self.s = _State()
        self.o = type(self).CaptureOutput()

    def test_first_stroke(self):
        self.translate(stroke('-B'))
        self.assertTranslations(self.lt('-B'))
        self.assertOutput([], self.lt('-B'), None)

    def test_second_stroke(self):
        self.define('S/P', 'spiders')
        self.s.translations = self.lt('S')
        self.translate(stroke('-T'))
        self.assertTranslations(self.lt('S -T'))
        self.assertOutput([], self.lt('-T'), self.t('S'))

    def test_second_stroke_tail(self):
        self.s.tail = self.t('T/A/I/L')
        self.translate(stroke('-E'))
        self.assertTranslations(self.lt('E'))
        self.assertOutput([], self.lt('E'), self.t('T/A/I/L'))

    def test_with_translation(self):
        self.define('S', 'is')
        self.define('-T', 'that')
        self.s.translations = self.lt('S')
        self.translate(stroke('-T'))
        self.assertTranslations(self.lt('S -T'))
        self.assertOutput([], self.lt('-T'), self.t('S'))
        self.assertEqual(self.o.output.do[0].english, 'that')

    def test_finish_two_translation(self):
        self.define('S/T', 'hello')
        self.s.translations = self.lt('S')
        self.translate(stroke('T'))
        self.assertTranslations(self.lt('S/T'))
        self.assertOutput(self.lt('S'), self.lt('S/T'), None)
        self.assertEqual(self.o.output.do[0].english, 'hello')
        self.assertEqual(self.o.output.do[0].replaced, self.lt('S'))

    def test_finish_three_translation(self):
        self.define('S/T/-B', 'bye')
        self.s.translations = self.lt('S T')
        self.translate(stroke('-B'))
        self.assertTranslations(self.lt('S/T/-B'))
        self.assertOutput(self.lt('S T'), self.lt('S/T/-B'), None)
        self.assertEqual(self.o.output.do[0].english, 'bye')
        self.assertEqual(self.o.output.do[0].replaced, self.lt('S T'))

    def test_replace_translation(self):
        self.define('S/T/-B', 'longer')
        self.s.translations = self.lt('S/T')
        self.translate(stroke('-B'))
        self.assertTranslations(self.lt('S/T/-B'))
        self.assertOutput(self.lt('S/T'), self.lt('S/T/-B'), None)
        self.assertEqual(self.o.output.do[0].english, 'longer')
        self.assertEqual(self.o.output.do[0].replaced, self.lt('S/T'))

    def test_undo(self):
        self.s.translations = self.lt('POP')
        self.translate(stroke('*'))
        self.assertTranslations([])
        self.assertOutput(self.lt('POP'), [], None)

    def test_empty_undo(self):
        self.translate(stroke('*'))
        self.assertTranslations([])
        self.assertOutput([], [], None)

    def test_undo_translation(self):
        self.define('P/P', 'pop')
        self.translate(stroke('P'))
        self.translate(stroke('P'))
        self.translate(stroke('*'))
        self.assertTranslations(self.lt('P'))
        self.assertOutput(self.lt('P/P'), self.lt('P'), None)

    def test_undo_longer_translation(self):
        self.define('P/P/-D', 'popped')
        self.translate(stroke('P'))
        self.translate(stroke('P'))
        self.translate(stroke('-D'))
        self.translate(stroke('*'))
        self.assertTranslations(self.lt('P P'))
        self.assertOutput(self.lt('P/P/-D'), self.lt('P P'), None)

    def test_undo_tail(self):
        self.s.tail = self.t('T/A/I/L')
        self.translate(stroke('*'))
        self.assertTranslations([])
        self.assertOutput([], [], self.t('T/A/I/L'))
        
    def test_suffix_folding(self):
        self.define('K-L', 'look')
        self.define('-G', '{^ing}')
        lt = self.lt('K-LG')
        lt[0].english = 'look {^ing}'
        self.translate(stroke('K-LG'))
        self.assertTranslations(lt)

    def test_suffix_folding_multi_stroke(self):
        self.define('E/HR', 'he will')
        self.define('-S', '{^s}')
        self.translate(stroke('E'))
        self.translate(stroke('HR-S'))
        output = ' '.join(t.english for t in self.s.translations)
        self.assertEqual(output, 'he will {^s}')

    def test_suffix_folding_doesnt_interfere(self):
        self.define('E/HR', 'he will')
        self.define('-S', '{^s}')
        self.define('E', 'he')
        self.define('HR-S', 'also')
        self.translate(stroke('E'))
        self.translate(stroke('HR-S'))
        output = ' '.join(t.english for t in self.s.translations)
        self.assertEqual(output, 'he also')

    def test_suffix_folding_no_suffix(self):
        self.define('K-L', 'look')
        lt = self.lt('K-LG')
        self.assertEqual(lt[0].english, None)
        self.translate(stroke('K-LG'))
        self.assertTranslations(lt)
        
    def test_suffix_folding_no_main(self):
        self.define('-G', '{^ing}')
        lt = self.lt('K-LG')
        self.assertEqual(lt[0].english, None)
        self.translate(stroke('K-LG'))
        self.assertTranslations(lt)
    

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = translation
# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

"""Stenography translation.

This module handles translating streams of strokes in translations. Two classes
compose this module:

Translation -- A data model class that encapsulates a sequence of Stroke objects
in the context of a particular dictionary. The dictionary in question maps
stroke sequences to strings, which are typically words or phrases, but could
also be meta commands.

Translator -- A state machine that takes in a single Stroke object at a time and
emits one or more Translation objects based on a greedy conversion algorithm.

"""

from plover.steno import Stroke
from plover.steno_dictionary import StenoDictionaryCollection
import itertools

class Translation(object):
    """A data model for the mapping between a sequence of Strokes and a string.

    This class represents the mapping between a sequence of Stroke objects and
    a text string, typically a word or phrase. This class is used as the output
    from translation and the input to formatting. The class contains the 
    following attributes:

    strokes -- A sequence of Stroke objects from which the translation is
    derived.

    rtfcre -- A tuple of RTFCRE strings representing the stroke list. This is
    used as the key in the translation mapping.

    english -- The value of the dictionary mapping given the rtfcre
    key, or None if no mapping exists.

    replaced -- A list of translations that were replaced by this one. If this
    translation is undone then it is replaced by these.

    formatting -- Information stored on the translation by the formatter for
    sticky state (e.g. capitalize next stroke) and to hold undo info.

    """

    def __init__(self, outline, translation):
        """Create a translation by looking up strokes in a dictionary.

        Arguments:

        outline -- A list of Stroke objects.

        translation -- A translation for the outline or None.

        """
        self.strokes = outline
        self.rtfcre = tuple(s.rtfcre for s in outline)
        self.english = translation
        self.replaced = []
        self.formatting = None

    def __eq__(self, other):
        return self.rtfcre == other.rtfcre and self.english == other.english

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return 'Translation(%s : %s)' % (self.rtfcre, self.english)

    def __repr__(self):
        return str(self)

    def __len__(self):
        if self.strokes is not None:
            return len(self.strokes)
        return 0

class Translator(object):
    """Converts a stenotype key stream to a translation stream.

    An instance of this class serves as a state machine for processing key
    presses as they come off a stenotype machine. Key presses arrive in batches,
    each batch representing a single stenotype chord. The Translator class
    receives each chord as a Stroke and adds the Stroke to an internal,
    length-limited FIFO, which is then translated into a sequence of Translation
    objects. The resulting sequence of Translations is compared to those
    previously emitted by the state machine and a sequence of new Translations
    (some corrections and some new) is emitted.

    The internal Stroke FIFO is translated in a greedy fashion; the Translator
    finds a translation for the longest sequence of Strokes that starts with the
    oldest Stroke in the FIFO before moving on to newer Strokes that haven't yet
    been translated. In practical terms, this means that corrections are needed
    for cases in which a Translation comprises two or more Strokes, at least the
    first of which is a valid Translation in and of itself.

    For example, consider the case in which the first Stroke can be translated
    as 'cat'. In this case, a Translation object representing 'cat' will be
    emitted as soon as the Stroke is processed by the Translator. If the next
    Stroke is such that combined with the first they form 'catalogue', then the
    Translator will first issue a correction for the initial 'cat' Translation
    and then issue a new Translation for 'catalogue'.

    A Translator takes input via the translate method and provides translation
    output to every function that has registered via the add_callback method.

    """
    def __init__(self):
        self._undo_length = 0
        self._dictionary = None
        self.set_dictionary(StenoDictionaryCollection())
        self._listeners = set()
        self._state = _State()

    def translate(self, stroke):
        """Process a single stroke."""
        _translate_stroke(stroke, self._state, self._dictionary, self._output)
        self._resize_translations()

    def set_dictionary(self, d):
        """Set the dictionary."""
        callback = self._dict_callback
        if self._dictionary:
            self._dictionary.remove_longest_key_listener(callback)
        self._dictionary = d
        d.add_longest_key_listener(callback)
        
    def get_dictionary(self):
        return self._dictionary

    def add_listener(self, callback):
        """Add a listener for translation outputs.
        
        Arguments:

        callback -- A function that takes: a list of translations to undo, a
        list of new translations to render, and a translation that is the
        context for the new translations.

        """
        self._listeners.add(callback)

    def remove_listener(self, callback):
        """Remove a listener added by add_listener."""
        self._listeners.remove(callback)

    def set_min_undo_length(self, n):
        """Set the minimum number of strokes that can be undone.

        The actual number may be larger depending on the translations in the
        dictionary.

        """
        self._undo_length = n
        self._resize_translations()

    def _output(self, undo, do, prev):
        for callback in self._listeners:
            callback(undo, do, prev)

    def _resize_translations(self):
        self._state.restrict_size(max(self._dictionary.longest_key,
                                      self._undo_length))

    def _dict_callback(self, value):
        self._resize_translations()
        
    def get_state(self):
        """Get the state of the translator."""
        return self._state
        
    def set_state(self, state):
        """Set the state of the translator."""
        self._state = state
        
    def clear_state(self):
        """Reset the sate of the translator."""
        self._state = _State()

class _State(object):
    """An object representing the current state of the translator state machine.
    
    Attributes:

    translations -- A list of all previous translations that are still undoable.

    tail -- The oldest translation still saved but is no longer undoable.

    """
    def __init__(self):
        self.translations = []
        self.tail = None

    def last(self):
        """Get the most recent translation."""
        if self.translations:
            return self.translations[-1]
        return self.tail

    def restrict_size(self, n):
        """Reduce the history of translations to n."""
        stroke_count = 0
        translation_count = 0
        for t in reversed(self.translations):
            stroke_count += len(t)
            translation_count += 1
            if stroke_count >= n:
                break
        translation_index = len(self.translations) - translation_count
        if translation_index:
            self.tail = self.translations[translation_index - 1]
        del self.translations[:translation_index]

def has_undo(t):
    # If there is no formatting then we're not dealing with a formatter so all 
    # translations can be undone.
    # TODO: combos are not undoable but in some contexts they appear as text. 
    # Should we provide a way to undo those? or is backspace enough?
    if not t.formatting:
        return True
    for a in t.formatting:
        if a.text or a.replace:
            return True
    return False

def _translate_stroke(stroke, state, dictionary, callback):
    """Process a stroke.

    See the class documentation for details of how Stroke objects
    are converted to Translation objects.

    Arguments:

    stroke -- The Stroke object to process.

    state -- The state object hold stroke and translation history.

    dictionary -- The steno dictionary.

    callback -- A function that takes the following arguments: A list of
    translations to undo, a list of new translations, and the translation that
    is the context for the new translations.

    """
    
    undo = []
    do = []
    
    # TODO: Test the behavior of undoing until a translation is undoable.
    if stroke.is_correction:
        for t in reversed(state.translations):
            undo.append(t)
            if has_undo(t):
                break
        undo.reverse()
        for t in undo:
            do.extend(t.replaced)
    else:
        # Figure out how much of the translation buffer can be involved in this
        # stroke and build the stroke list for translation.
        num_strokes = 1
        translation_count = 0
        for t in reversed(state.translations):
            num_strokes += len(t)
            if num_strokes > dictionary.longest_key:
                break
            translation_count += 1
        translation_index = len(state.translations) - translation_count
        translations = state.translations[translation_index:]
        t = _find_translation(translations, dictionary, stroke)
        do.append(t)
        undo.extend(t.replaced)
    
    del state.translations[len(state.translations) - len(undo):]
    callback(undo, do, state.last())
    state.translations.extend(do)

SUFFIX_KEYS = ['-S', '-G', '-Z', '-D']

def _find_translation(translations, dictionary, stroke):
    t = _find_translation_helper(translations, dictionary, stroke, [])
    if t:
        return t
    mapping = _lookup([stroke], dictionary, [])
    if mapping is not None:  # Could be the empty string.
        return Translation([stroke], mapping)
    t = _find_translation_helper(translations, dictionary, stroke, SUFFIX_KEYS)
    if t:
        return t
    return Translation([stroke], _lookup([stroke], dictionary, SUFFIX_KEYS))

def _find_translation_helper(translations, dictionary, stroke, suffixes):
    # The new stroke can either create a new translation or replace
    # existing translations by matching a longer entry in the
    # dictionary.
    for i in xrange(len(translations)):
        replaced = translations[i:]
        strokes = list(itertools.chain(*[t.strokes for t in replaced]))
        strokes.append(stroke)
        mapping = _lookup(strokes, dictionary, suffixes)
        if mapping != None:
            t = Translation(strokes, mapping)
            t.replaced = replaced
            return t

def _lookup(strokes, dictionary, suffixes):
    dict_key = tuple(s.rtfcre for s in strokes)
    result = dictionary.lookup(dict_key)
    if result != None:
        return result

    for key in suffixes:
        if key in strokes[-1].steno_keys:
            dict_key = (Stroke([key]).rtfcre,)
            suffix_mapping = dictionary.lookup(dict_key)
            if suffix_mapping == None: continue
            keys = strokes[-1].steno_keys[:]
            keys.remove(key)
            copy = strokes[:]
            copy[-1] = Stroke(keys)
            dict_key = tuple(s.rtfcre for s in copy)
            main_mapping = dictionary.lookup(dict_key)
            if main_mapping == None: continue
            return main_mapping + ' ' + suffix_mapping

    return None

########NEW FILE########
__FILENAME__ = run_tests
# Copyright (c) 2012 Hesky Fisher
# See LICENSE.txt for details.

import os.path
import unittest

if __name__ == '__main__':
    suite = unittest.defaultTestLoader.discover(os.path.dirname(__file__))
    unittest.TextTestRunner().run(suite)

########NEW FILE########
