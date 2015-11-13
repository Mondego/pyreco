__FILENAME__ = tests
import operator
import unittest

from mockio import mockio

from nginxparser import NginxParser, load, loads, dumps


first = operator.itemgetter(0)


class TestNginxParser(unittest.TestCase):
    files = {
        "/etc/nginx/sites-enabled/foo.conf": '''
        user www-data;
        server {
            listen   80;
            server_name foo.com;
            root /home/ubuntu/sites/foo/;

            location /status {
                check_status;
                types {
                    image/jpeg jpg;
                }
            }
        }'''
    }

    def test_assignments(self):
        parsed = NginxParser.assignment.parseString('root /test;').asList()
        self.assertEqual(parsed, ['root', '/test'])
        parsed = NginxParser.assignment.parseString('root /test;'
                                                    'foo bar;').asList()
        self.assertEqual(parsed, ['root', '/test'], ['foo', 'bar'])

    def test_blocks(self):
        parsed = NginxParser.block.parseString('foo {}').asList()
        self.assertEqual(parsed, [[['foo'], []]])
        parsed = NginxParser.block.parseString('location /foo{}').asList()
        self.assertEqual(parsed, [[['location', '/foo'], []]])
        parsed = NginxParser.block.parseString('foo { bar foo; }').asList()
        self.assertEqual(parsed, [[['foo'], [['bar', 'foo']]]])

    def test_nested_blocks(self):
        parsed = NginxParser.block.parseString('foo { bar {} }').asList()
        block, content = first(parsed)
        self.assertEqual(first(content), [['bar'], []])

    def test_dump_as_string(self):
        dumped = dumps([
            ['user', 'www-data'],
            [['server'], [
                ['listen', '80'],
                ['server_name', 'foo.com'],
                ['root', '/home/ubuntu/sites/foo/'],
                [['location','/status'], [
                    ['check_status'],
                    [['types'], [['image/jpeg','jpg']]],
                ]]
            ]]])

        self.assertEqual(dumped,'user www-data;\n' +
                                'server {\n' +
                                '    listen 80;\n' +
                                '    server_name foo.com;\n' +
                                '    root /home/ubuntu/sites/foo/;\n \n' +
                                '    location /status {\n' +
                                '        check_status;\n \n' +
                                '        types {\n' +
                                '            image/jpeg jpg;\n' +
                                '        }\n' +
                                '    }\n' +
                                '}')

    @mockio(files)
    def test_parse_from_file(self):
        parsed = load(open("/etc/nginx/sites-enabled/foo.conf"))
        self.assertEqual(parsed, [
            ['user', 'www-data'],
            [['server'], [
                    ['listen', '80'],
                    ['server_name', 'foo.com'],
                    ['root', '/home/ubuntu/sites/foo/'],
                    [['location','/status'], [
                        ['check_status'],
                        [['types'], [['image/jpeg','jpg']]],
                    ]]
            ]],
            ])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
