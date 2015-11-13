__FILENAME__ = android_clean_app
"""
    clean_app
    ~~~~~~~~~~

    Implements methods for removing unused android resources based on Android
    Lint results.

    :copyright: (c) 2014 by KeepSafe.
    :license: Apache, see LICENSE for more details.
"""

import argparse
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from lxml import etree


class Issue:

    """
    Stores a single issue reported by Android Lint
    """
    pattern = re.compile('The resource (.+) appears to be unused')

    def __init__(self, filepath, remove_file):
        self.filepath = filepath
        self.remove_file = remove_file
        self.elements = []

    def __str__(self):
        return '{0} {1}'.format(self.filepath)

    def __repr__(self):
        return '{0} {1}'.format(self.filepath)

    def add_element(self, message):
        res = re.findall(Issue.pattern, message)[0]
        bits = res.split('.')[-2:]
        self.elements.append((bits[0], bits[1]))


def parse_args():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--lint',
                        help='Path to the ADT lint tool. If not specified it assumes lint tool is in your path',
                        default='lint')
    parser.add_argument('--app',
                        help='Path to the Android app. If not specifies it assumes current directory is your Android '
                             'app directory',
                        default='.')
    parser.add_argument('--xml',
                        help='Path to the list result. If not specifies linting will be done by the script',
                        default=None)
    parser.add_argument('--ignore-layouts',
                        help='Should ignore layouts',
                        action='store_true')
    args = parser.parse_args()
    print(args)
    return args.lint, args.app, args.xml, args.ignore_layouts


def run_lint_command():
    """
    Run lint command in the shell and save results to lint-result.xml
    """
    lint, app_dir, lint_result, ignore_layouts = parse_args()
    if not lint_result:
        lint_result = os.path.join(app_dir, 'lint-result.xml')
        call_result = subprocess.call([lint, app_dir, '--xml', lint_result], shell=True)
        if call_result > 0:
            print('Running the command failed. Try running it from the console. Arguments for subprocess.call: {0}'.format(
                [lint, app_dir, '--xml', lint_result]))
    return lint_result, app_dir, ignore_layouts


def parse_lint_result(lint_result_path):
    """
    Parse lint-result.xml and create Issue for every problem found
    """
    root = ET.parse(lint_result_path).getroot()
    issues = []
    for issue_xml in root.findall('.//issue[@id="UnusedResources"]'):
        for location in issue_xml.findall('location'):
            filepath = location.get('file')
            # if the location contains line and/or column attribute not the entire resource is unused. that's a guess ;)
            # TODO stop guessing
            remove_entire_file = (location.get('line') or location.get('column')) is None
            issue = Issue(filepath, remove_entire_file)
            issue.add_element(issue_xml.get('message'))
            issues.append(issue)
    return issues


def remove_resource_file(issue, filepath, ignore_layouts):
    """
    Delete a file from the filesystem
    """
    if ignore_layouts is False or issue.elements[0][0] != 'layout':
        print('removing resource: {0}'.format(filepath))
        os.remove(os.path.abspath(filepath))


def remove_resource_value(issue, filepath):
    """
    Read an xml file and remove an element which is unused, then save the file back to the filesystem
    """
    for element in issue.elements:
        print('removing {0} from resource {1}'.format(element, filepath))
        parser = etree.XMLParser(remove_blank_text=False, remove_comments=False, remove_pis=False, strip_cdata=False, resolve_entities=False)
        tree = etree.parse(filepath, parser)
        root = tree.getroot()
        for unused_value in root.findall('.//{0}[@name="{1}"]'.format(element[0], element[1])):
            root.remove(unused_value)
        with open(filepath, 'wb') as resource:
            tree.write(resource, encoding='utf-8', xml_declaration=True)


def remove_unused_resources(issues, app_dir, ignore_layouts):
    """
    Remove the file or the value inside the file depending if the whole file is unused or not.
    """
    for issue in issues:
        filepath = os.path.join(app_dir, issue.filepath)
        if issue.remove_file:
            remove_resource_file(issue, filepath, ignore_layouts)
        else:
            remove_resource_value(issue, filepath)


def main():
    lint_result_path, app_dir, ignore_layouts = run_lint_command()
    issues = parse_lint_result(lint_result_path)
    remove_unused_resources(issues, app_dir, ignore_layouts)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_clean_app
import os
import unittest
import android_clean_app as clean_app
import tempfile
import xml.etree.ElementTree as ET


class CleanAppTestCase(unittest.TestCase):
    def test_reads_all_unused_resource_issues(self):
        actual = clean_app.parse_lint_result('./test/android_app/lint-result.xml')
        self.assertEqual(12, len(actual))

    def test_marks_resource_as_save_to_remove(self):
        actual = clean_app.parse_lint_result('./test/android_app/lint-result.xml')
        remove_entire_file = list(filter(lambda issue: issue.remove_file, actual))
        self.assertEqual(11, len(remove_entire_file))

    def test_marks_resource_as_not_save_to_remove_if_it_has_used_values(self):
        actual = clean_app.parse_lint_result('./test/android_app/lint-result.xml')
        not_remove_entire_file = list(filter(lambda issue: not issue.remove_file, actual))
        self.assertEqual(1, len(not_remove_entire_file))

    def test_extracts_correct_info_from_resource(self):
        issues = clean_app.parse_lint_result('./test/android_app/lint-result.xml')
        not_remove_entire_file = list(filter(lambda issue: not issue.remove_file, issues))
        actual = not_remove_entire_file[0]
        self.assertEqual('res\\values\\strings.xml', actual.filepath)
        self.assertGreater(len(actual.elements), 0)
        self.assertEqual(('string', 'missing'), actual.elements[0])

    def test_removes_given_resources_if_safe(self):
        temp, temp_path = tempfile.mkstemp()
        os.close(temp)

        issue = clean_app.Issue(temp_path, True)

        clean_app.remove_unused_resources([issue], os.path.dirname(temp_path), False)
        with self.assertRaises(IOError):
            open(temp_path)

    def test_removes_an_unused_value_from_a_file(self):
        temp, temp_path = tempfile.mkstemp()
        os.write(temp, """
            <resources>
                <string name="app_name">android_app</string>
                <string name="missing">missing</string>
                <string name="app_name1">android_app1</string>
            </resources>
        """.encode('utf-8'))
        os.close(temp)

        issue = clean_app.Issue(temp_path, False)
        issue.add_element('The resource R.string.missing appears to be unused')
        clean_app.remove_unused_resources([issue], os.path.dirname(temp_path), True)

        root = ET.parse(temp_path).getroot()
        self.assertEqual(2, len(root.findall('string')))

    def test_ignores_layouts(self):
        temp, temp_path = tempfile.mkstemp()
        os.write(temp, """
            <resources>
                <string name="app_name">android_app</string>
                <layout name="missing">missing</layout>
                <string name="app_name1">android_app1</string>
            </resources>
        """.encode('UTF-8'))
        os.close(temp)

        issue = clean_app.Issue(temp_path, False)
        issue.add_element('The resource R.string.missing appears to be unused')
        clean_app.remove_unused_resources([issue], os.path.dirname(temp_path), False)

        root = ET.parse(temp_path).getroot()
        self.assertEqual(1, len(root.findall('layout')))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
