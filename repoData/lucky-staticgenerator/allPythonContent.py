__FILENAME__ = filesystem
#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os
import tempfile

class FileSystem(object):
    def exists(self, path):
        return os.path.exists(path)

    def makedirs(self, path):
        os.makedirs(path)

    def tempfile(self, directory):
        return tempfile.mkstemp(dir=directory)

    def write(self, f, content):
        return os.write(f, content)

    def close(self, f):
        os.close(f)

    def chmod(self, filename, flags):
        os.chmod(filename, flags)

    def rename(self, from_file, to_file):
        os.rename(from_file, to_file)

    def remove(self, path):
        os.remove(path)

    def rmdir(self, directory):
        os.rmdir(directory)
        
    def join(self, *paths):
        if not paths:
            return ""
        return os.path.join(paths[0], *[path.lstrip("/") for path in paths[1:]])
        
    def dirname(self, path):
        return os.path.dirname(path)


########NEW FILE########
__FILENAME__ = handlers
#!/usr/bin/env python
#-*- coding:utf-8 -*-

from django.core.handlers.base import BaseHandler

class DummyHandler(BaseHandler):
    """Required to process request and response middleware"""

    def __call__(self, request):
        self.load_middleware()
        response = self.get_response(request)
        for middleware_method in self._response_middleware:
            response = middleware_method(request, response)

        return response

########NEW FILE########
__FILENAME__ = middleware
import re
from django.conf import settings
from staticgenerator import StaticGenerator

class StaticGeneratorMiddleware(object):
    """
    This requires settings.STATIC_GENERATOR_URLS tuple to match on URLs
    
    Example::
        
        STATIC_GENERATOR_URLS = (
            r'^/$',
            r'^/blog',
        )
        
    """
    urls = tuple([re.compile(url) for url in settings.STATIC_GENERATOR_URLS])
    gen = StaticGenerator()
    
    def process_response(self, request, response):
        if response.status_code == 200:
            for url in self.urls:
                if url.match(request.path_info):
                    self.gen.publish_from_path(request.path_info, response.content)
                    break
        return response

########NEW FILE########
__FILENAME__ = test_filesystem
#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os
from os.path import abspath, join, dirname, exists
import tempfile

from staticgenerator.staticgenerator import FileSystem

ROOT_DIR = join(abspath(os.curdir), "test_data")

def test_can_create_filesystem():
    fs = FileSystem()

    assert fs
    assert isinstance(fs, FileSystem)

def test_current_directory_exists():
    fs = FileSystem()
    assert fs.exists(ROOT_DIR)

def test_directory_not_exists():
    fs = FileSystem()
    assert not fs.exists('/fake/dir')

def test_can_create_directory():
    fs = FileSystem()

    path = join(ROOT_DIR, "test")

    fs.makedirs(path)

    assert exists(path)

    os.rmdir(path)

def test_can_create_tempfile():
    fs = FileSystem()

    temp_file = fs.tempfile(ROOT_DIR)

    assert len(temp_file) == 2

    os.remove(temp_file[1])

def test_can_write_content_in_tempfile():
    fs = FileSystem()

    temp_file = tempfile.mkstemp()
    bytes = fs.write(temp_file[0], "foo")

    assert bytes == 3

def test_can_close_tempfile():
    fs = FileSystem()

    temp_file = tempfile.mkstemp()
    fs.close(temp_file[0])

    try:
        fs.close(temp_file[0])
        assert False
    except OSError:
        pass

def test_can_rename_file():
    fs = FileSystem()

    file_path = join(ROOT_DIR, "some_file")
    f = open(file_path, "w")
    f.write("content")
    f.close()

    new_file_path = join(ROOT_DIR, "new_file")
    fs.rename(file_path, new_file_path)

    f = open(new_file_path, "r")
    assert f.read() == "content"

    f.close()

def test_can_remove_file():
    fs = FileSystem()

    file_path = join(ROOT_DIR, "some_file")
    f = open(file_path, "w")
    f.write("content")
    f.close()

    fs.remove(file_path)

    assert not exists(file_path)

def test_can_remove_dir():
    fs = FileSystem()

    dir_path = join(ROOT_DIR, "some_dir")
    os.mkdir(dir_path)

    fs.rmdir(dir_path)

    assert not exists(dir_path)

def test_join_many_paths():
    fs = FileSystem()
    assert fs.join("/fake", "/dir", "/other") == "/fake/dir/other"

def test_join_single_path():
    fs = FileSystem()
    assert fs.join("/fake") == "/fake"

def test_join_two_paths():
    fs = FileSystem()
    assert fs.join("/fake", "/dir") == "/fake/dir"

def test_join_two_paths_when_second_is_not_rooted():
    fs = FileSystem()
    assert fs.join("/fake", "dir") == "/fake/dir"

def test_join_two_paths_when_second_is_virtual():
    fs = FileSystem()
    assert fs.join("/fake", "../dir") == "/fake/../dir"

def test_join_returns_empty_string_when_empty():
    fs = FileSystem()
    assert fs.join('') == ''

def test_join_returns_empty_string_when_null():
    fs = FileSystem()
    assert fs.join() == ''

def test_join_returns_rooted_path_when_second_path_is_empty():
    fs = FileSystem()
    assert fs.join("/root","") == '/root/'

def test_dirname_returns_last_dir():
    fs = FileSystem()
    assert fs.dirname("/root/test/index.html") == '/root/test'


########NEW FILE########
__FILENAME__ = test_staticgenerator
#!/usr/bin/env python
#-*- coding:utf-8 -*-

import stat

from mox import Mox

from staticgenerator.staticgenerator import StaticGenerator, StaticGeneratorException, DummyHandler
import staticgenerator.staticgenerator

class CustomSettings(object):
    def __init__(self, **kw):
        for k,v in kw.iteritems():
            setattr(self, k, v)

def get_mocks(mox):
    http_request_mock = mox.CreateMockAnything()
    model_base_mock = mox.CreateMockAnything()
    manager_mock = mox.CreateMockAnything()
    model_mock = mox.CreateMockAnything()
    queryset_mock = mox.CreateMockAnything()

    return http_request_mock, model_base_mock, manager_mock, model_mock, queryset_mock

def test_can_create_staticgenerator():
    mox = Mox()
    http_request, model_base, manager, model, queryset = get_mocks(mox)
    settings = CustomSettings(WEB_ROOT="test_web_root")

    mox.ReplayAll()

    instance = StaticGenerator(http_request=http_request,
                               model_base=model_base,
                               manager=manager,
                               model=model,
                               queryset=queryset,
                               settings=settings)

    assert instance
    assert isinstance(instance, StaticGenerator)
    mox.VerifyAll()

def test_not_having_web_root_raises():
    mox = Mox()
    http_request, model_base, manager, model, queryset = get_mocks(mox)

    settings = CustomSettings()

    mox.ReplayAll()

    try:
        StaticGenerator(http_request=http_request,
                                   model_base=model_base,
                                   manager=manager,
                                   model=model,
                                   queryset=queryset,
                                   settings=settings)

    except StaticGeneratorException, e:
        assert str(e) == 'You must specify WEB_ROOT in settings.py'
        mox.VerifyAll()
        return

    assert False, "Shouldn't have gotten this far."

def test_staticgenerator_keeps_track_of_web_root():
    mox = Mox()
    http_request, model_base, manager, model, queryset = get_mocks(mox)

    settings = CustomSettings(WEB_ROOT="test_web_root_1294128189")
    
    mox.ReplayAll()

    instance = StaticGenerator(http_request=http_request,
                               model_base=model_base,
                               manager=manager,
                               model=model,
                               queryset=queryset,
                               settings=settings)

    assert instance.web_root == "test_web_root_1294128189"
    mox.VerifyAll()

def test_get_server_name_gets_name_from_settings():
    mox = Mox()
    http_request, model_base, manager, model, queryset = get_mocks(mox)
    
    settings = CustomSettings(WEB_ROOT="test_web_root_1294128189",
                              SERVER_NAME="some_random_server")

    mox.ReplayAll()

    instance = StaticGenerator(http_request=http_request,
                               model_base=model_base,
                               manager=manager,
                               model=model,
                               queryset=queryset,
                               settings=settings)

    assert instance.server_name == "some_random_server"
    mox.VerifyAll()

def test_get_server_name_gets_name_from_site():
    mox = Mox()
    http_request, model_base, manager, model, queryset = get_mocks(mox)
    
    current_site = mox.CreateMockAnything()
    site_mock = mox.CreateMockAnything()
    site_mock.objects = mox.CreateMockAnything()
    site_mock.objects.get_current().AndReturn(current_site)
    current_site.domain = "custom_domain"

    settings = CustomSettings(WEB_ROOT="some_web_root")

    mox.ReplayAll()

    instance = StaticGenerator(http_request=http_request,
                               model_base=model_base,
                               manager=manager,
                               model=model,
                               queryset=queryset,
                               settings=settings,
                               site=site_mock)

    assert instance.server_name == "custom_domain"
    mox.VerifyAll()

def test_get_server_name_as_localhost_by_default():
    mox = Mox()
    http_request, model_base, manager, model, queryset = get_mocks(mox)

    settings = CustomSettings(WEB_ROOT="some_web_root")

    mox.ReplayAll()

    instance = StaticGenerator(http_request=http_request,
                               model_base=model_base,
                               manager=manager,
                               model=model,
                               queryset=queryset,
                               settings=settings)

    assert instance.server_name == "localhost"
    mox.VerifyAll()
    
def test_extract_resources_when_resource_is_a_str():
    mox = Mox()
    http_request, model_base, manager, model, queryset = get_mocks(mox)
    
    resources_mock = "some_str"

    settings = CustomSettings(WEB_ROOT="some_web_root")

    mox.ReplayAll()

    instance = StaticGenerator(resources_mock,
                               http_request=http_request,
                               model_base=model_base,
                               manager=manager,
                               model=model,
                               queryset=queryset,
                               settings=settings)

    assert len(instance.resources) == 1 
    assert instance.resources[0] == "some_str"
    mox.VerifyAll()
    
def test_extract_resources_when_resource_is_a_model():
    mox = Mox()
    http_request, model_base, manager, model, queryset = get_mocks(mox)
    
    class Model(object):
        def get_absolute_url(self):
            return 'some_model_url'
        
    resources_mock = Model()
    model = Model
    
    settings = CustomSettings(WEB_ROOT="some_web_root")

    mox.ReplayAll()

    instance = StaticGenerator(resources_mock,
                               http_request=http_request,
                               model_base=model_base,
                               manager=manager,
                               model=model,
                               queryset=queryset,
                               settings=settings)

    assert len(instance.resources) == 1 
    assert instance.resources[0] == 'some_model_url'
    mox.VerifyAll()
    
def test_extract_resources_when_resource_is_a_model_base():
    mox = Mox()
    http_request, model_base, manager, model, queryset = get_mocks(mox)
    
    class ModelBase(object):
        def __init__(self, manager):
            self._default_manager = manager
            
    instance_mock = mox.CreateMockAnything()
    instance_mock.get_absolute_url().AndReturn('some_url1')

    instance_mock2 = mox.CreateMockAnything()
    instance_mock2.get_absolute_url().AndReturn('some_url2')

    instance_mocks = [instance_mock, instance_mock2]

    mock_manager = mox.CreateMockAnything()
    mock_manager.all().AndReturn(instance_mocks)

    resources_mock = ModelBase(mock_manager)
    model_base = ModelBase
    
    model.__instancecheck__(resources_mock).AndReturn(False)
    manager.__instancecheck__(mock_manager).AndReturn(True)
    queryset.__instancecheck__(instance_mocks).AndReturn(True)
    
    settings = CustomSettings(WEB_ROOT="some_web_root")

    mox.ReplayAll()

    instance = StaticGenerator(resources_mock,
                               http_request=http_request,
                               model_base=model_base,
                               manager=manager,
                               model=model,
                               queryset=queryset,
                               settings=settings)

    assert len(instance.resources) == 2
    assert instance.resources[0] == 'some_url1'
    assert instance.resources[1] == 'some_url2'
    mox.VerifyAll()
    
def test_get_content_from_path():
    mox = Mox()
    http_request, model_base, manager, model, queryset = get_mocks(mox)
    settings = CustomSettings(WEB_ROOT="test_web_root")
    
    path_mock = 'some_path'
    
    request_mock = mox.CreateMockAnything()
    request_mock.META = mox.CreateMockAnything()
    request_mock.META.setdefault('SERVER_PORT', 80)
    request_mock.META.setdefault('SERVER_NAME', 'localhost')
    
    response_mock = mox.CreateMockAnything()
    response_mock.content = 'foo'
    response_mock.status_code = 200

    http_request.__call__().AndReturn(request_mock)
    
    handler_mock = mox.CreateMockAnything()
    handler_mock.__call__().AndReturn(handler_mock)
    handler_mock.__call__(request_mock).AndReturn(response_mock)

    mox.ReplayAll()
    
    try:
        dummy_handler = staticgenerator.staticgenerator.DummyHandler
        staticgenerator.staticgenerator.DummyHandler = handler_mock

        instance = StaticGenerator(http_request=http_request,
                                   model_base=model_base,
                                   manager=manager,
                                   model=model,
                                   queryset=queryset,
                                   settings=settings)
    
        result = instance.get_content_from_path(path_mock)
    finally:
        staticgenerator.staticgenerator.DummyHandler = dummy_handler
    
    assert result == 'foo'
    mox.VerifyAll()
    
def test_get_filename_from_path():
    mox = Mox()
    http_request, model_base, manager, model, queryset = get_mocks(mox)
    settings = CustomSettings(WEB_ROOT="test_web_root")
    
    path_mock = '/foo/bar'
    
    fs_mock = mox.CreateMockAnything()
    fs_mock.join("test_web_root", "foo/bar").AndReturn("test_web_root/foo/bar")
    fs_mock.dirname("test_web_root/foo/bar").AndReturn("test_web_root/foo")

    mox.ReplayAll()
    
    instance = StaticGenerator(http_request=http_request,
                               model_base=model_base,
                               manager=manager,
                               model=model,
                               queryset=queryset,
                               settings=settings,
                               fs=fs_mock)

    result = instance.get_filename_from_path(path_mock)
    
    assert result ==  ('test_web_root/foo/bar', 'test_web_root/foo')
    mox.VerifyAll()
    
def test_get_filename_from_path_when_path_ends_with_slash():
    mox = Mox()
    http_request, model_base, manager, model, queryset = get_mocks(mox)
    settings = CustomSettings(WEB_ROOT="test_web_root")
    
    fs_mock = mox.CreateMockAnything()
    fs_mock.join("test_web_root", "foo/bar/index.html").AndReturn("test_web_root/foo/bar/index.html")
    fs_mock.dirname("test_web_root/foo/bar/index.html").AndReturn("test_web_root/foo/bar")
    
    path_mock = '/foo/bar/'

    mox.ReplayAll()
    
    instance = StaticGenerator(http_request=http_request,
                               model_base=model_base,
                               manager=manager,
                               model=model,
                               queryset=queryset,
                               settings=settings,
                               fs=fs_mock)

    result = instance.get_filename_from_path(path_mock)
    
    assert result ==  ('test_web_root/foo/bar/index.html', 'test_web_root/foo/bar')
    mox.VerifyAll()

def test_publish_raises_when_unable_to_create_folder():
    mox = Mox()
    http_request, model_base, manager, model, queryset = get_mocks(mox)

    fs_mock = mox.CreateMockAnything()
    fs_mock.join("test_web_root", "some_path").AndReturn("test_web_root/some_path")
    fs_mock.dirname("test_web_root/some_path").AndReturn("test_web_root")
    fs_mock.exists("test_web_root").AndReturn(False)

    fs_mock.makedirs("test_web_root").AndRaise(ValueError())

    settings = CustomSettings(WEB_ROOT="test_web_root")

    mox.ReplayAll()
    
    instance = StaticGenerator(http_request=http_request,
                               model_base=model_base,
                               manager=manager,
                               model=model,
                               queryset=queryset,
                               settings=settings,
                               fs=fs_mock)

    try:
        instance.publish_from_path("some_path", content="some_content")
    except StaticGeneratorException, e:
        assert str(e) == 'Could not create the directory: test_web_root'
        mox.VerifyAll()
        return

    assert False, "Shouldn't have gotten this far."

def test_publish_raises_when_unable_to_create_temp_file():
    mox = Mox()
    http_request, model_base, manager, model, queryset = get_mocks(mox)

    fs_mock = mox.CreateMockAnything()
    fs_mock.join("test_web_root", "some_path").AndReturn("test_web_root/some_path")
    fs_mock.dirname("test_web_root/some_path").AndReturn("test_web_root")
    fs_mock.exists("test_web_root").AndReturn(True)

    fs_mock.tempfile(directory="test_web_root").AndRaise(ValueError())

    settings = CustomSettings(WEB_ROOT="test_web_root")

    mox.ReplayAll()
    
    instance = StaticGenerator(http_request=http_request,
                               model_base=model_base,
                               manager=manager,
                               model=model,
                               queryset=queryset,
                               settings=settings,
                               fs=fs_mock)

    try:
        instance.publish_from_path("some_path", content="some_content")
    except StaticGeneratorException, e:
        assert str(e) == 'Could not create the file: test_web_root/some_path'
        mox.VerifyAll()
        return

    assert False, "Shouldn't have gotten this far."

def test_publish_from_path():
    mox = Mox()
    http_request, model_base, manager, model, queryset = get_mocks(mox)

    fs_mock = mox.CreateMockAnything()
    fs_mock.join("test_web_root", "some_path").AndReturn("test_web_root/some_path")
    fs_mock.dirname("test_web_root/some_path").AndReturn("test_web_root")
    fs_mock.exists("test_web_root").AndReturn(True)

    f = mox.CreateMockAnything()
    filename = "some_temp_file"
    fs_mock.tempfile(directory="test_web_root").AndReturn([f, filename])
    fs_mock.write(f, "some_content")
    fs_mock.close(f)
    fs_mock.chmod(filename, stat.S_IREAD | stat.S_IWRITE | stat.S_IWUSR | stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    fs_mock.rename('some_temp_file', 'test_web_root/some_path')

    settings = CustomSettings(WEB_ROOT="test_web_root")

    mox.ReplayAll()

    instance = StaticGenerator(http_request=http_request,
                               model_base=model_base,
                               manager=manager,
                               model=model,
                               queryset=queryset,
                               settings=settings,
                               fs=fs_mock)

    instance.publish_from_path("some_path", content="some_content")

    mox.VerifyAll()

def test_delete_raises_when_unable_to_delete_file():
    mox = Mox()
    http_request, model_base, manager, model, queryset = get_mocks(mox)

    fs_mock = mox.CreateMockAnything()

    fs_mock.join("test_web_root", "some_path").AndReturn("test_web_root/some_path")
    fs_mock.dirname("test_web_root/some_path").AndReturn("test_web_root")
    fs_mock.exists("test_web_root/some_path").AndReturn(True)
    fs_mock.remove("test_web_root/some_path").AndRaise(ValueError())

    settings = CustomSettings(WEB_ROOT="test_web_root")

    mox.ReplayAll()
    
    instance = StaticGenerator(http_request=http_request,
                               model_base=model_base,
                               manager=manager,
                               model=model,
                               queryset=queryset,
                               settings=settings,
                               fs=fs_mock)

    try:
        instance.delete_from_path("some_path")
    except StaticGeneratorException, e:
        assert str(e) == 'Could not delete file: test_web_root/some_path'
        mox.VerifyAll()
        return

    assert False, "Shouldn't have gotten this far."

def test_delete_ignores_folder_delete_when_unable_to_delete_folder():
    mox = Mox()
    http_request, model_base, manager, model, queryset = get_mocks(mox)

    fs_mock = mox.CreateMockAnything()

    fs_mock.join("test_web_root", "some_path").AndReturn("test_web_root/some_path")
    fs_mock.dirname("test_web_root/some_path").AndReturn("test_web_root")
    fs_mock.exists("test_web_root/some_path").AndReturn(True)
    fs_mock.remove("test_web_root/some_path")

    fs_mock.rmdir("test_web_root").AndRaise(OSError())

    settings = CustomSettings(WEB_ROOT="test_web_root")

    mox.ReplayAll()
    
    instance = StaticGenerator(http_request=http_request,
                               model_base=model_base,
                               manager=manager,
                               model=model,
                               queryset=queryset,
                               settings=settings,
                               fs=fs_mock)

    instance.delete_from_path("some_path")

    assert True, "Should work even when raising OSError"

def test_delete_from_path():
    mox = Mox()
    http_request, model_base, manager, model, queryset = get_mocks(mox)

    fs_mock = mox.CreateMockAnything()
    fs_mock.join("test_web_root", "some_path").AndReturn("test_web_root/some_path")
    fs_mock.dirname("test_web_root/some_path").AndReturn("test_web_root")
    fs_mock.exists("test_web_root/some_path").AndReturn(True)
    fs_mock.remove("test_web_root/some_path")

    fs_mock.rmdir("test_web_root")

    settings = CustomSettings(WEB_ROOT="test_web_root")

    mox.ReplayAll()

    instance = StaticGenerator(http_request=http_request,
                               model_base=model_base,
                               manager=manager,
                               model=model,
                               queryset=queryset,
                               settings=settings,
                               fs=fs_mock)

    instance.delete_from_path("some_path")

    mox.VerifyAll()

def test_publish_loops_through_all_resources():
    mox = Mox()
    http_request, model_base, manager, model, queryset = get_mocks(mox)

    fs_mock = mox.CreateMockAnything()
    f = mox.CreateMockAnything()
    fs_mock.join('test_web_root', 'some_path_1').AndReturn('test_web_root/some_path_1')
    fs_mock.dirname('test_web_root/some_path_1').AndReturn('test_web_root')
    fs_mock.exists("test_web_root").AndReturn(True)
    filename = "some_temp_file"
    fs_mock.tempfile(directory="test_web_root").AndReturn([f, filename])
    fs_mock.write(f, "some_content")
    fs_mock.close(f)
    fs_mock.chmod(filename, stat.S_IREAD | stat.S_IWRITE | stat.S_IWUSR | stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    fs_mock.rename('some_temp_file', 'test_web_root/some_path_1')

    fs_mock.join('test_web_root', 'some_path_2').AndReturn('test_web_root/some_path_2')
    fs_mock.dirname('test_web_root/some_path_2').AndReturn('test_web_root')
    fs_mock.exists("test_web_root").AndReturn(True)
    filename = "some_temp_file"
    fs_mock.tempfile(directory="test_web_root").AndReturn([f, filename])
    fs_mock.write(f, "some_content")
    fs_mock.close(f)
    fs_mock.chmod(filename, stat.S_IREAD | stat.S_IWRITE | stat.S_IWUSR | stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    fs_mock.rename('some_temp_file', 'test_web_root/some_path_2')

    settings = CustomSettings(WEB_ROOT="test_web_root")

    mox.ReplayAll()

    try:
        get_content_from_path = StaticGenerator.get_content_from_path
        StaticGenerator.get_content_from_path = lambda self, path: "some_content"
        instance = StaticGenerator("some_path_1", "some_path_2",
                                   http_request=http_request,
                                   model_base=model_base,
                                   manager=manager,
                                   model=model,
                                   queryset=queryset,
                                   settings=settings,
                                   fs=fs_mock)

        instance.publish()

        mox.VerifyAll()
    finally:
        StaticGenerator.get_content_from_path = get_content_from_path

def test_delete_loops_through_all_resources():
    mox = Mox()
    http_request, model_base, manager, model, queryset = get_mocks(mox)

    fs_mock = mox.CreateMockAnything()
    fs_mock.join('test_web_root', 'some_path').AndReturn("test_web_root/some_path")
    fs_mock.dirname("test_web_root/some_path").AndReturn("test_web_root")
    fs_mock.exists("test_web_root/some_path").AndReturn(True)
    fs_mock.remove("test_web_root/some_path")
    fs_mock.rmdir("test_web_root")

    fs_mock.join('test_web_root', 'some_path_2').AndReturn("test_web_root/some_path_2")
    fs_mock.dirname('test_web_root/some_path_2').AndReturn("test_web_root")
    fs_mock.exists("test_web_root/some_path_2").AndReturn(True)
    fs_mock.remove("test_web_root/some_path_2")
    fs_mock.rmdir("test_web_root")

    settings = CustomSettings(WEB_ROOT="test_web_root")

    mox.ReplayAll()

    instance = StaticGenerator("some_path", "some_path_2", 
                               http_request=http_request,
                               model_base=model_base,
                               manager=manager,
                               model=model,
                               queryset=queryset,
                               settings=settings,
                               fs=fs_mock)

    instance.delete()

    mox.VerifyAll()
    
def test_can_create_dummy_handler():

    mox = Mox()
    handler = DummyHandler()
    
    handler.load_middleware = lambda: True
    handler.get_response = lambda request: 'bar'
    
    middleware_method = lambda request, response: (request, response)
    
    handler._response_middleware = [middleware_method]
    result = handler('foo')
    
    assert result == ('foo', 'bar')

def test_bad_request_raises_proper_exception():
    mox = Mox()

    http_request, model_base, manager, model, queryset = get_mocks(mox)
    settings = CustomSettings(WEB_ROOT="test_web_root")

    path_mock = 'some_path'

    request_mock = mox.CreateMockAnything()
    request_mock.META = mox.CreateMockAnything()
    request_mock.META.setdefault('SERVER_PORT', 80)
    request_mock.META.setdefault('SERVER_NAME', 'localhost')

    http_request.__call__().AndReturn(request_mock)

    response_mock = mox.CreateMockAnything()
    response_mock.content = 'foo'
    response_mock.status_code = 500

    handler_mock = mox.CreateMockAnything()
    handler_mock.__call__().AndReturn(handler_mock)
    handler_mock.__call__(request_mock).AndReturn(response_mock)

    mox.ReplayAll()

    try:
        dummy_handler = staticgenerator.staticgenerator.DummyHandler
        staticgenerator.staticgenerator.DummyHandler = handler_mock

        instance = StaticGenerator(http_request=http_request,
                                   model_base=model_base,
                                   manager=manager,
                                   model=model,
                                   queryset=queryset,
                                   settings=settings)

        result = instance.get_content_from_path(path_mock)
    except StaticGeneratorException, e:
        assert str(e) == 'The requested page("some_path") returned http code 500. Static Generation failed.'
        mox.VerifyAll()
        return
    finally:
        staticgenerator.staticgenerator.DummyHandler = dummy_handler

    assert False, "Shouldn't have gotten this far."

def test_not_found_raises_proper_exception():
    mox = Mox()

    http_request, model_base, manager, model, queryset = get_mocks(mox)
    settings = CustomSettings(WEB_ROOT="test_web_root")

    path_mock = 'some_path'

    request_mock = mox.CreateMockAnything()
    request_mock.META = mox.CreateMockAnything()
    request_mock.META.setdefault('SERVER_PORT', 80)
    request_mock.META.setdefault('SERVER_NAME', 'localhost')

    http_request.__call__().AndReturn(request_mock)

    response_mock = mox.CreateMockAnything()
    response_mock.content = 'foo'
    response_mock.status_code = 404

    handler_mock = mox.CreateMockAnything()
    handler_mock.__call__().AndReturn(handler_mock)
    handler_mock.__call__(request_mock).AndReturn(response_mock)

    mox.ReplayAll()

    try:
        dummy_handler = staticgenerator.staticgenerator.DummyHandler
        staticgenerator.staticgenerator.DummyHandler = handler_mock

        instance = StaticGenerator(http_request=http_request,
                                   model_base=model_base,
                                   manager=manager,
                                   model=model,
                                   queryset=queryset,
                                   settings=settings)

        result = instance.get_content_from_path(path_mock)
    except StaticGeneratorException, e:
        assert str(e) == 'The requested page("some_path") returned http code 404. Static Generation failed.'
        mox.VerifyAll()
        return
    finally:
        staticgenerator.staticgenerator.DummyHandler = dummy_handler

    assert False, "Shouldn't have gotten this far."

def test_request_exception_raises_proper_exception():
    mox = Mox()

    http_request, model_base, manager, model, queryset = get_mocks(mox)
    settings = CustomSettings(WEB_ROOT="test_web_root")

    path_mock = 'some_path'

    request_mock = mox.CreateMockAnything()
    request_mock.META = mox.CreateMockAnything()
    request_mock.META.setdefault('SERVER_PORT', 80)
    request_mock.META.setdefault('SERVER_NAME', 'localhost')

    http_request.__call__().AndReturn(request_mock)

    handler_mock = mox.CreateMockAnything()
    handler_mock.__call__().AndReturn(handler_mock)
    handler_mock.__call__(request_mock).AndRaise(ValueError("exception"))

    mox.ReplayAll()

    try:
        dummy_handler = staticgenerator.staticgenerator.DummyHandler
        staticgenerator.staticgenerator.DummyHandler = handler_mock

        instance = StaticGenerator(http_request=http_request,
                                   model_base=model_base,
                                   manager=manager,
                                   model=model,
                                   queryset=queryset,
                                   settings=settings)

        result = instance.get_content_from_path(path_mock)
    except StaticGeneratorException, e:
        assert str(e) == 'The requested page("some_path") raised an exception. Static Generation failed. Error: exception'
        mox.VerifyAll()
        return
    finally:
        staticgenerator.staticgenerator.DummyHandler = dummy_handler

    assert False, "Shouldn't have gotten this far."


########NEW FILE########
