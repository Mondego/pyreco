__FILENAME__ = configuration
""" Configuration helper for STProjectMaker """

import json, os
import sublime
__ST3 = int(sublime.version()) >= 3000
if __ST3:
    from STProjectMaker.filetask import RemoteFileFetchTask 
else:
    from filetask import RemoteFileFetchTask

class ConfigurationReader:
    """ Reads JSON file configuration and executes associated tasks. """

    def __init__(self):
        self.file_task = RemoteFileFetchTask()
        # Add tasks associated with key in JSON.
        self.tasks = dict({
            "files": self.file_task
        })

    def load_config(self, filepath):
        f = open(filepath)
        configuration = json.loads(f.read())
        f.close()
        return configuration

    def read(self, filepath, destination_path):
        configuration = self.load_config(filepath)
        # Iterate through task list and run associated task.
        for key, value in self.tasks.items():
            if key.lower() == 'files':
                exceptions = self.file_task.execute(configuration['files'], destination_path)
                if exceptions is not None and len(exceptions) > 0:
                    build_filename = 'STProjectMaker_build.log'
                    message = 'The following problems occured from FileTask:\n'
                    exception_iter = iter(exceptions)
                    f = open(os.path.join(destination_path, build_filename), "w")
                    try:
                        message += str(next(exception_iter)) + '\n'
                    except StopIteration as e:
                        pass
                    f.write(message)
                    f.close()

        return configuration

########NEW FILE########
__FILENAME__ = filetask
""" File task helper for configurations in STProjectMaker """

import os, errno
import sublime
__ST3 = int(sublime.version()) >= 3000
if __ST3:
    from urllib.error import URLError
    from urllib.request import urlopen
else:
    from urllib2 import URLError
    from urllib2 import urlopen

class DownloadError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class RemoteFileFetchTask:
    """ Reads in file objects in the following format and downloads them to disk: {'name':'str', 'url':'str', 'locations':['str']} """

    def read_file(self, url):
        try:
            response = urlopen(url)
            return response.read()
        except URLError as e:
            raise DownloadError(e.reason)
        
    def write_file(self, contents, to_file_path):
        with open(to_file_path, 'w') as f:
            f.write(contents)
            f.close()
            return os.path.exists(to_file_path)

    def execute(self, filelist, root_path):
        exceptions = []
        for file_obj in filelist:
            file_url = file_obj['url']
            file_ext = os.path.splitext(file_url)[1]
            file_name = file_obj['name']
            locations = file_obj['locations']

            try:
                contents = self.read_file(file_url)
            except DownloadError as e:
                exceptions.append('Could not load ' + file_url + '. [Reason]: ' + e.value)
                sublime.error_message("Unable to download:\n " + file_url + "\nReason:\n " + e.value + "\nNote: Sublime Text 2 on Linux cannot deal with https urls.")
                continue

            for location in locations:
                directory = os.path.join(root_path, location)
                # try to create directory listing if not present.
                try:
                    os.makedirs(directory)
                except OSError as e:
                    # if it is just reporting that it exists, fail silently.
                    if e.errno != errno.EEXIST:
                        raise e
                # write to location.
                filepath = os.path.join(directory, file_name + file_ext)
                self.write_file(contents, filepath)

        return exceptions

########NEW FILE########
__FILENAME__ = projectmaker
import sublime, sublime_plugin, os, shutil, re, codecs
__ST3 = int(sublime.version()) >= 3000
if __ST3:
    from STProjectMaker.configuration import ConfigurationReader
else:
    from configuration import ConfigurationReader

class ProjectMakerCommand(sublime_plugin.WindowCommand):
    def run(self):
        settings = sublime.load_settings("STProjectMaker.sublime-settings")
        templates_path_setting = settings.get('template_path')
        default_project_path_setting = settings.get('default_project_path')

        if not default_project_path_setting:
            if sublime.platform() == "windows":
                self.default_project_path = os.path.expanduser("~\\project_name").replace("\\", "/")
            else:
                self.default_project_path = os.path.expanduser("~/project_name")
        else:
            self.default_project_path = default_project_path_setting

        self.project_files_folder = settings.get('project_files_folder')
        self.non_parsed_ext = settings.get("non_parsed_ext")
        self.non_parsed_files = settings.get("non_parsed_files")
        self.plugin_path = os.path.join(sublime.packages_path(), "STProjectMaker")
        if not templates_path_setting:
            self.templates_path = os.path.expanduser("~/STProjectMakerTemplates")
        else:
            self.templates_path = os.path.abspath(templates_path_setting)
        self.template_names = []
        self.choose_template()

    def choose_template(self):
        files = self.get_templates()
        for file_name in files:
            if os.path.isdir(os.path.join(self.templates_path, file_name)):
                self.template_names.append(file_name)
        self.window.show_quick_panel(self.template_names, self.on_template_chosen)

    def get_templates(self):
        files = os.listdir(self.templates_path)
        files = [(f.lower(), f) for f in files]
        return [f[1] for f in sorted(files)]

    def on_template_chosen(self, index):
        if index > -1:
            self.chosen_template_name = self.template_names[index]
            self.chosen_template_path = os.path.join(self.templates_path, self.chosen_template_name)
            self.get_project_path()

    def get_project_path(self):
        self.window.show_input_panel("Project Location:", self.default_project_path, self.on_project_path, None, None)

    def on_project_path(self, path):
        self.project_path = path
        self.project_path_escaped = path.replace("/", "\\\\\\\\")
        self.project_name = os.path.basename(self.project_path)

        if os.path.exists(self.project_path):
            sublime.error_message("Something already exists at " + self.project_path)
        else:
            if not self.project_files_folder:
                self.create_project()
            else:
                self.get_project_name()

    def get_project_name(self):
        self.window.show_input_panel("Project Name:", self.project_name, self.on_project_name, None, None)

    def on_project_name(self, name):
        self.project_name = name
        self.create_project()

    def create_project(self):
        self.copy_project()
        self.get_tokens(self.project_path);
        self.get_token_values()

    def copy_project(self):
        shutil.copytree(self.chosen_template_path, self.project_path)

    def get_tokens(self, path):
        self.tokens = []
        self.tokenized_files = []
        self.tokenized_titles = []
        self.get_tokens_from_path(path)

    def get_tokens_from_path(self, path):
        files = os.listdir(path)
        for file_name in files:
            if file_name in self.non_parsed_files:
                continue
            ext = os.path.splitext(file_name)[1];
            if ext in self.non_parsed_ext:
                continue
            file_path = os.path.join(path, file_name)
            self.get_token_from_file_name(path, file_name)
            if os.path.isdir(file_path):
                self.get_tokens_from_path(file_path)
            else:
                self.get_tokens_from_file(file_path)

    def get_token_from_file_name(self, path, file_name):
        dot_index = file_name.find(".")
        if file_name[0:1] == "_" and file_name[dot_index-1:dot_index] == "_":
            file_path = os.path.join(path, file_name)
            self.tokenized_titles.append(file_path)
            token = file_name[1:dot_index-1]
            if not token in self.tokens:
                self.tokens.append(token)

    def open_file(self, file_path, mode = "r", return_content = True):
        has_exception = False
        try:
            file_ref = codecs.open(file_path, mode, "utf-8")
            content = file_ref.read()
            if return_content == True:
                file_ref.close()
                return content
            else:
                return file_ref
        except UnicodeDecodeError as e:
            has_exception = True
        
        try:
            file_ref = codecs.open(file_path, mode, "latin-1")
            content = file_ref.read()
            if return_content == True:
                file_ref.close()
                return content
            else:
                return file_ref
        except UnicodeDecodeError as e:
            has_exception = True

        sublime.error_message("Could not open " + file_path)

    def get_tokens_from_file(self, file_path):
        content = self.open_file(file_path)
        if content is None:
            return;

        r = re.compile(r"\${[^}]*}")
        matches = r.findall(content)
        if len(matches) > 0:
            self.tokenized_files.append(file_path)
        for match in matches:
            token = match[2:-1]
            if not token in self.tokens:
                self.tokens.append(token)

    def get_token_values(self):
        self.token_values = []
        self.token_index = 0
        self.get_next_token_value()

    def get_next_token_value(self):
        # are there any tokens left?
        if self.token_index < len(self.tokens):
            token = self.tokens[self.token_index]
            # built-in values (may need to extract these):
            if token == "project_path":
                self.token_values.append((token, self.project_path))
                self.token_index += 1
                self.get_next_token_value()
            elif token == "project_path_escaped":
                self.token_values.append((token, self.project_path_escaped))
                self.token_index += 1
                self.get_next_token_value()
            elif token == "project_name":
                self.token_values.append((token, self.project_name))
                self.token_index += 1
                self.get_next_token_value()
            # custom token. get value from user:
            else:
                self.window.show_input_panel("Value for token \"" + token + "\"", "", self.on_token_value, None, None)
        else:
            # all done. do replacements
            self.customize_project()

    def on_token_value(self, token_value):
        self.token_values.append((self.tokens[self.token_index], token_value));
        self.token_index += 1
        self.get_next_token_value()

    def customize_project(self):
        self.replace_tokens()
        self.rename_files()
        self.find_project_file()
        self.read_configuration()
        self.window.run_command("open_dir", {"dir":self.project_path});

    def replace_tokens(self):
        for file_path in self.tokenized_files:
            self.replace_tokens_in_file(file_path)

    def replace_tokens_in_file(self, file_path):        
        template = self.open_file(file_path)
        if template is None:
            return;
            
        for token, value in self.token_values:
            r = re.compile(r"\${" + token + "}")
            template = r.sub(value, template)

        file_ref = self.open_file(file_path, "w+", False)
        file_ref.write(template)
        file_ref.close()

    def rename_files(self):
        for file_path in self.tokenized_titles:
            for token, value in self.token_values:
                # we do NOT want to use a full path for a single file name!
                if token != "project_path":
                    r = re.compile(r"_" + token + "_")
                    if r.search(file_path):
                        os.rename(file_path, r.sub(value, file_path))
                        break

    def find_project_file(self):
        files = os.listdir(self.project_path)
        r = re.compile(r".*\.sublime-project")
        self.project_file = None
        for file_name in files:
            if r.search(file_name):
                self.project_file = os.path.join(self.project_path, file_name)
        if self.project_file == None:
            self.create_project_file()

    def create_project_file(self):
        file_name = self.project_name + ".sublime-project"

        if not self.project_files_folder:
            self.project_file = os.path.join(self.project_path, file_name)
        else:
            self.project_file = os.path.join(self.project_files_folder, file_name)

        file_ref = open(self.project_file, "w")
        file_ref.write(("{\n"
                        "    \"folders\":\n"
                        "    [\n"
                        "        {\n"
                        "            \"path\": \""+self.project_path+"\"\n"
                        "        }\n"
                        "    ]\n"
                        "}\n"));
        file_ref.close()

    def read_configuration(self):
        config_file = os.path.join(self.chosen_template_path, 'config.json')
        if os.path.exists(config_file):
            ConfigurationReader().read(config_file, self.project_path)


########NEW FILE########
__FILENAME__ = main


class MainClass:

	def __init__(self):
		self.say_hello()

	def say_hello(self):
		print("Hello, World!")


if(__name__ == "__main__"):
	MainClass()
########NEW FILE########
__FILENAME__ = filetasktest
""" Unit tests for configuration.py and filetask.py from STProjectMaker project. """
""" [NOTE] filetask module imports sublime for error handling within the Sublime Text 2 IDE. Comment references to sublime to run tests properly. """

import sys, os, json, shutil, unittest
sys.path.append('../')
from configuration import ConfigurationReader
from filetask import RemoteFileFetchTask

class TestConfigurationLoad(unittest.TestCase):
	"""Testing load and parse of config.json"""
	
	configuration = None
	
	def setUp(self):
		""" Python <2.7 psuedo setUpBeforeClass """
		if self.__class__.configuration is None:
			config = ConfigurationReader()
			self.__class__.configuration = config.load_config('config_test.json')

	def test_load_config_not_none(self):
		self.assertTrue(self.__class__.configuration is not None)

	def test_config_has_file_array(self):
		self.assertTrue(type(self.__class__.configuration['files']) == list)

	def test_file_array_length(self):
		files = self.__class__.configuration['files']
		self.assertEqual(len(files), 2 )

	def test_file_read(self):
		files = self.__class__.configuration['files']
		file_obj = files[0]
		name = file_obj['name']
		url = file_obj['url']
		locations = file_obj['locations']
		self.assertTrue(url is not None)
		self.assertTrue(name is not None)
		self.assertEqual(len(locations), 1)

class TestFileTask(unittest.TestCase):
	"""Testing FileTask on configuration"""

	configuration = None
	task = None

	def setUp(self):
		""" Python <2.7 psuedo setUpBeforeClass """
		if self.__class__.configuration is None:
			f = open('config_test.json')
			self.__class__.configuration = json.loads(f.read())
			f.close()
		if self.__class__.task is None:
			self.__class__.task = RemoteFileFetchTask()

	def test_file_read(self):
		files = self.__class__.configuration['files']
		url = files[0]['url']
		contents = self.__class__.task.read_file(url)
		self.assertTrue(contents is not None)

	def test_file_write(self):
		files = self.__class__.configuration['files']
		url = files[0]['url']
		contents = self.__class__.task.read_file(url)
		filepath = os.path.join(os.curdir,files[0]['name'])
		self.assertTrue(self.__class__.task.write_file(contents, filepath))
		if os.path.exists(filepath):
			try:
				os.remove(filepath)
			except Exception, e:
				raise e

	def test_execute_from_list(self):
		files = self.__class__.configuration['files']
		self.__class__.task.execute(files, os.curdir)
		to_dir = os.path.join(os.curdir,'libs')
		self.assertTrue(os.path.exists(to_dir))
		if os.path.exists(to_dir):
			try:
				shutil.rmtree(to_dir)
			except Exception, e:
				raise e

	def test_exceptions_from_execute(self):
		files = [{'url':'httpf://code.jquery.com/jquery-latest.js', 'name':'badurltest', 'locations':[]}]
		exceptions = self.__class__.task.execute(files, os.curdir)
		self.assertEqual(len(exceptions), 1)

suite = unittest.TestSuite()
suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestConfigurationLoad))
suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestFileTask))
unittest.TextTestRunner(verbosity=2).run(suite)
########NEW FILE########