__FILENAME__ = conf
# -*- coding: utf-8 -*-
from better import better_theme_path

extensions = []
templates_path = []
source_suffix = '.rst'
master_doc = 'index'

project = u'pivotal_tools'
copyright = u'2013 Jonathan Tushman and pivotal_tools contributors'
# The short X.Y version.
version = '0.13'
# The full version, including alpha/beta/rc tags.
release = '0.13'
exclude_patterns = ['_build']
pygments_style = 'sphinx'

html_theme_path = [better_theme_path]
html_theme = 'better'
html_theme_options = {
    'inlinecss': """
        #commands h4 {
            font-family: Monaco, Consolas, "Lucida Console", monospace;
        }
    """,
    'cssfiles': [],
    'scriptfiles': [],
    'enablesidebarsearch': False,
    'showrelbartop': False,
    'showrelbarbottom': False,
    'showheader': False,
}
html_title = "{} {}".format(project, release)
html_short_title = "Home"

html_logo = None
html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []
html_show_sphinx = True
html_show_copyright = True
# Output file base name for HTML help builder.
htmlhelp_basename = 'pivotal_toolsdoc'

########NEW FILE########
__FILENAME__ = cli
#!/usr/bin/env python
"""Pivotal Tools

A collection of tools to help with your pivotal workflow


changelog
---------------
List out projects stories that are delivered or finished (not accepted)

show stories
---------------
Lists all stories for a given project (will prompt you if not specified)
Can filter by user with the `for` option
By default show the top 20 stories, can specify more (or less) with the _number_ option

show story
---------------
Show the details for a given story.  passing the project-index parameter will make it faster

open
---------------
Will open the given story in a browser.  passing the project-index parameter will make it faster

scrum
---------------
Will list stories and bugs that team members are working on.  Grouped by team member

poker (aka planning)
---------------
Help to facilitate a planning poker session

create (feature|bug|chore)
---------------
Create a story


Usage:
  pivotal_tools create (feature|bug|chore) <title> [<description>] [--project-index=<pi>]
  pivotal_tools (start|finish|deliver|accept|reject) story <story_id> [--project-index=<pi>]
  pivotal_tools show stories [--project-index=<pi>] [--for=<user_name>] [--number=<number_of_stories>]
  pivotal_tools show story <story_id> [--project-index=<pi>]
  pivotal_tools open <story_id> [--project-index=<pi>]
  pivotal_tools changelog [--project-index=<pi>]
  pivotal_tools scrum [--project-index=<pi>]
  pivotal_tools (planning|poker) [--project-index=<pi>]

Options:
  -h --help             Show this screen.
  --for=<user_name>     Username, or initials
  --project-index=<pi>  If you have multiple projects, this is the index that the project shows up in my prompt
                        This is useful if you do not want to be prompted, and then you can pipe the output

"""

#Core Imports
import os
import webbrowser
from itertools import islice


#3rd Party Imports
from docopt import docopt
from termcolor import colored

from pivotal import Project, Story, InvalidStateException


## Main Methods



def generate_changelog(project):
    """Generate a Changelog for the current project.  It is grouped into 3 sections:
    * New Features
    * Bugs Fixed
    * Known Issues

    The new features section is grouped by label for easy comprehension
    """

    title_string = 'Change Log {}'.format(project.name)

    print
    print bold(title_string)
    print bold('=' * len(title_string))
    print

    print bold('New Features')
    print bold('============')

    finished_features = project.finished_features()
    features_by_label = group_stories_by_label(finished_features)

    for label in features_by_label:
        if len(label) == 0:
            display_label = 'Other'
        else:
            display_label = label
        print bold(display_label.title())
        for story in features_by_label[label]:
            print '    * {:14s} {}'.format('[{}]'.format(story.story_id), story.name)


    def print_stories(stories):
        if len(stories) > 0:
            for story in stories:
                story_string = ""
                if story.labels is not None and len(story.labels) > 0:
                    story_string += "[{}] ".format(story.labels)

                story_string += story.name
                print '* {:14s} {}'.format('[{}]'.format(story.story_id), story_string)
        else:
            print 'None'
            print


    print
    print bold('Bugs Fixed')
    print bold('==========')
    print_stories(project.finished_bugs())

    print
    print bold('Known Issues')
    print bold('==========')
    print_stories(project.known_issues())

    print


def show_stories(project, arguments):
    """Shows the top stories
    By default it will show the top 20.  But that change be changed by the --number arguement
    You can further filter the list by passing the --for argument and pass the initials of the user
    """

    search_string = 'state:unscheduled,unstarted,rejected,started'
    if arguments['--for'] is not None:
        search_string += " owner:{}".format(arguments['--for'])

    stories = project.get_stories(search_string)

    number_of_stories = 20
    if arguments['--number'] is not None:
        number_of_stories = int(arguments['--number'])
    else:
        print
        print "Showing the top 20 stories, if you want to show more, specify number with the --number option"
        print


    if len(stories) == 0:
        print "None"
    else:
        for story in islice(stories, number_of_stories):
            print '{:14s}{:4s}{:9s}{:13s}{:10s} {}'.format('#{}'.format(story.story_id),
                                                           initials(story.owned_by),
                                                           story.story_type,
                                                           story.state,
                                                           estimate_visual(story.estimate),
                                                           story.name)


def show_story(story_id, arguments):
    """Shows the Details for a single story

    Will find the associate project, then look up the story and print of the details
    """

    story = load_story(story_id, arguments)


    print
    print colored('{:12s}{:4s}{:9s}{:10s} {}'.format('#{}'.format(story.story_id),
                                                     initials(story.owned_by),
                                                     story.story_type,
                                                     estimate_visual(story.estimate),
                                                     story.name), 'white', attrs=['bold'])
    print
    print colored("Story Url: ", 'white', attrs=['bold']) + colored(story.url, 'blue', attrs=['underline'])
    print colored("Description: ", 'white', attrs=['bold']) + story.description

    if len(story.notes) > 0:
        print
        print bold("Notes:")
        for note in story.notes:
            print "[{}] {}".format(initials(note.author), note.text)


    if len(story.tasks) > 0:
        print
        print bold("Tasks:")
        for task in story.tasks:
            print "[{}] {}".format(x_or_space(task.complete), task.description)

    if len(story.attachments) > 0:
        print
        print bold("Attachments:")
        for attachment in story.attachments:
            print "{} {}".format(attachment.description, colored(attachment.url,'blue',attrs=['underline']))

    print


def scrum(project):
    """ CLI Visual Aid for running the daily SCRUM meeting.
        Prints an list of stories that people are working on grouped by user
    """

    stories = project.in_progress_stories()
    stories_by_owner = group_stories_by_owner(stories)

    print bold("{} SCRUM -- {}".format(project.name, pretty_date()))
    print

    for owner in stories_by_owner:
        print bold(owner)
        for story in stories_by_owner[owner]:
            print "   #{:12s}{:9s} {:7s} {}".format(story.story_id,
                                                    estimate_visual(story.estimate),
                                                    story.story_type,
                                                    story.name)

        print

    print bold("Bugs")
    bugs = project.open_bugs()
    if len(bugs) == 0:
        print 'Not sure that I believe it, but there are no bugs'
    for bug in bugs:
        print "   #{:12s} {:4s} {}".format(bug.story_id,
                                     initials(bug.owned_by),
                                     bug.name)


def poker(project):
    """CLI driven tool to help facilitate the periodic poker planning session

    Will loop through and display unestimated stories, and prompt the team for an estimate.
    You can also open the current story in a browser for additional editing
    """
    total_stories = len(project.unestimated_stories())
    for idx, story in enumerate(project.unestimated_stories()):
        clear()
        rows, cols = _get_column_dimensions()
        print "{} PLANNING POKER SESSION [{}]".format(project.name.upper(), bold("{}/{} Stories Estimated".format(idx+1, total_stories)))
        print "-" * cols
        pretty_print_story(story)
        prompt_estimation(project, story)
    else:
        print "KaBoom!!! Nice Work Team"


def load_story(story_id, arguments):
    story = None
    if arguments['--project-index'] is not None and arguments['--project-index'].isdigit():
        idx = int(arguments['--project-index']) - 1
        story = Story.find(story_id, project_index=idx)
    else:

        story = Story.find(story_id)
    return story


def browser_open(story_id, arguments):
    """Open the given story in a browser"""

    story = load_story(story_id, arguments)

    webbrowser.open(story.url)

def create_story(project, arguments):

    story = dict()
    story['name'] = arguments['<title>']
    if '<description>' in arguments:
        story['description'] = arguments['<description>']

    if arguments['bug']:
        story['story_type'] = 'bug'
    elif arguments['feature']:
        story['story_type'] = 'feature'
    elif arguments['chore']:
        story['story_type'] = 'chore'

    stories = {'story': story}

    project.create_story(stories)


def update_status(arguments):

    story = None
    if '<story_id>' in arguments:
        story_id = arguments['<story_id>']
        story = load_story(story_id, arguments)

    if story is not None:
        try:

            if arguments['start']:
                story.start()
                print "Story: [{}] {} is STARTED".format(story.story_id, story.name)
            elif arguments['finish']:
                story.finish()
                print "Story: [{}] {} is FINISHED".format(story.story_id, story.name)
            elif arguments['deliver']:
                story.deliver()
                print "Story: [{}] {} is DELIVERED".format(story.story_id, story.name)
            elif arguments['accept']:
                story.accept()
                print "Story: [{}] {} is ACCEPTED".format(story.story_id, story.name)
            elif arguments['reject']:
                story.reject()
                print "Story: [{}] {} is REJECTED".format(story.story_id, story.name)

        except InvalidStateException, e:
            print e.message
    else:
        print "hmmm could not find story"



## Helper Methods



def bold(string):
    return colored(string, 'white', attrs=['bold'])


def prompt_project(arguments):
    """prompts the user for a project, if not passed in as a argument"""
    projects = Project.all()

    # Do not prompt -- and auto select the one project if a account only has one project
    if len(projects) == 1:
        return projects[0]

    if arguments['--project-index'] is not None:
        try:
            idx = int(arguments['--project-index']) - 1
            project = projects[idx]
            return project
        except:
            print 'Yikes, that did not work -- try again?'
            exit()

    while True:
        print "Select a Project:"
        for idx, project in enumerate(projects):
            print "[{}] {}".format(idx+1, project.name)
        s = raw_input('>> ')

        try:
            project = projects[int(s) - 1]
        except:
            print 'Hmmm, that did not work -- try again?'
            continue

        break

    return project


def check_api_token():
    """Check to see if the API Token is set, else give instructions"""

    token = os.getenv('PIVOTAL_TOKEN', None)
    if token is None:
        print """
        You need to have your pivotal developer token set to the 'PIVOTAL_TOKEN' env variable.

        I keep mine in ~/.zshenv
        export PIVOTAL_TOKEN='your token'

        If you do not have one, login to pivotal, and go to your profile page, and scroll to the bottom.
        You'll find it there.
        """
        exit()


def initials(full_name):
    """Return the initials of a passed in name"""

    if full_name is not None and len(full_name) > 0:
        return ''.join([s[0] for s in full_name.split(' ')]).upper()
    else:
        return ''


def estimate_visual(estimate):
    if estimate is not None:
        return '[{:8s}]'.format('*' * estimate)
    else:
        return '[        ]'


def group_stories_by_owner(stories):
    stories_by_owner = {}
    for story in stories:
        if story.owned_by is not None:
            if story.owned_by in stories_by_owner:
                stories_by_owner[story.owned_by].append(story)
            else:
                stories_by_owner[story.owned_by] = [story]
        else:
            continue
    return stories_by_owner


def group_stories_by_label(stories):
    stories_by_label = {}
    for story in stories:
        if story.first_label in stories_by_label:
            stories_by_label[story.first_label].append(story)
        else:
            stories_by_label[story.first_label] = [story]

    return stories_by_label


def pretty_date():
    from datetime import datetime
    return datetime.now().strftime('%b %d, %Y')


def clear():
    """Clears the terminal buffer"""
    os.system('cls' if os.name == 'nt' else 'clear')


def pretty_print_story(story):
    print
    print bold(story.name)
    if len(story.description) > 0:
        print
        print story.description
        print

    if len(story.notes) > 0:
        print
        print bold('Notes:')
        for note in story.notes:
            print "[{}] {}".format(initials(note.author), note.text)

    if len(story.attachments) > 0:
        print
        print bold('Attachments:')
        for attachment in story.attachments:
            if len(attachment.description) > 0:
                print "Description: {}".format(attachment.description)
            print "Url: {}".format(colored(attachment.url, 'blue'))


    if len(story.tasks) > 0:
        print
        print bold("Tasks:")
        for task in story.tasks:
            print "[{}] {}".format(x_or_space(task.complete), task.description)

    if len(story.labels) > 0:
        print
        print "{} {}".format(bold('Labels:'), story.labels)


def prompt_estimation(project, story):
    print
    print bold("Estimate: [{}, (s)kip, (o)pen, (q)uit]".format(','.join(project.point_scale)))
    input_value = raw_input(bold('>> '))

    if input_value in ['s', 'S']:
        #skip move to the next
        return
    elif input_value in ['o', 'O']:
        webbrowser.open(story.url)
        prompt_estimation(project, story)
    elif input_value in ['q','Q']:
        exit()
    elif input_value in project.point_scale:
        value = int(input_value)
        story.assign_estimate(value)
    else:
        print "Invalid Input, Try again"
        prompt_estimation(project, story)


def _get_column_dimensions():
    rows, cols = os.popen('stty size', 'r').read().split()
    return int(rows), int(cols)


def x_or_space(complete):
    if complete:
        return 'X'
    else:
        return ' '


def main():

    arguments = docopt(__doc__)

    check_api_token()

    if arguments['changelog']:
        project = prompt_project(arguments)
        generate_changelog(project)
    elif arguments['show'] and arguments['stories']:
        project = prompt_project(arguments)
        show_stories(project, arguments)
    elif arguments['show'] and arguments['story']:
        show_story(arguments['<story_id>'], arguments)
    elif arguments['open']:
        browser_open(arguments['<story_id>'], arguments)
    elif arguments['scrum']:
        project = prompt_project(arguments)
        scrum(project)
    elif arguments['poker'] or arguments['planning']:
        project = prompt_project(arguments)
        poker(project)
    elif arguments['create']:
        project = prompt_project(arguments)
        create_story(project, arguments)
    elif arguments['story']:
        update_status(arguments)
    else:
        print arguments


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = pivotal
# Core Imports
import os
from urllib import quote
import xml.etree.ElementTree as ET

# 3rd Party Imports
import requests
import dicttoxml

TOKEN = os.getenv('PIVOTAL_TOKEN', None)


def find_project_for_story(story_id):
    """If we have multiple projects, will loop through the projects to find the one with the given story.
    returns None if not found
    """

    for project in Project.all():
        story = project.load_story(story_id)
        if story is not None:
            return project

    #Not found
    print "No project found for story: #{}".format(story_id)
    return None


def get_project_by_index(index):
    return Project.all()[index]


class Note(object):
    """object representation of a Pivotal Note, should be accessed from story.notes"""
    def __init__(self, note_id, text, author):
        self.note_id = note_id
        self.text = text
        self.author = author


class Task(object):
    """object representation of a Pivotal Task, should be accessed from story.tasks"""
    def __init__(self, task_id, description, complete):
        self.task_id = task_id
        self.description = description
        self.complete = complete


class Attachment(object):
    """object representation of a Pivotal attachment, should be accessed from story.attachments"""
    def __init__(self, attachment_id, description, url):
        self.attachment_id = attachment_id
        self.description = description
        self.url = url


class Story(object):
    """object representation of a Pivotal story"""
    def __init__(self):
        self.story_id = None
        self.project_id = None
        self.name = None
        self.description = None
        self.owned_by = None
        self.story_type = None
        self.estimate = None
        self.state = None
        self.url = None
        self.labels = None
        self.notes = []
        self.attachments = []
        self.tasks = []


    @property
    def first_label(self):
        """returns the first label if any from labels.  Used for grouping"""
        return self.labels.split(',')[0]


    @classmethod
    def find(cls, story_id, project_index=None):
        project = None
        if project_index is None:
            project = find_project_for_story(story_id)

        else:
            project = Project.all()[project_index]

        if project is not None:
            return project.load_story(story_id)
        else:
            return None



    @classmethod
    def from_node(cls, node):
        """instantiates a Story object from an elementTree node, build child notes and attachment lists"""

        story = Story()
        story.story_id = _parse_text(node, 'id')
        story.name = _parse_text(node, 'name')
        story.owned_by = _parse_text(node, 'owned_by')
        story.story_type = _parse_text(node, 'story_type')
        story.state = _parse_text(node, 'current_state')
        story.description = _parse_text(node, 'description')
        story.estimate = _parse_int(node, 'estimate')
        story.labels = _parse_text(node, 'labels')
        story.url = _parse_text(node, 'url')
        story.project_id = _parse_text(node, 'project_id')

        note_nodes = node.find('notes')
        if note_nodes is not None:
            for note_node in note_nodes:
                note_id = _parse_text(note_node, 'id')
                text = _parse_text(note_node, 'text')
                author = _parse_text(note_node, 'author')
                story.notes.append(Note(note_id, text, author))

        attachment_nodes = node.find('attachments')
        if attachment_nodes is not None:
            for attachment_node in attachment_nodes:
                attachment_id = _parse_text(attachment_node, 'id')
                description = _parse_text(attachment_node, 'text')
                url = _parse_text(attachment_node, 'url')
                story.attachments.append(Attachment(attachment_id,description,url))

        task_nodes = node.find('tasks')
        if task_nodes is not None:
            for task_node in task_nodes:
                task_id = _parse_text(task_node, 'id')
                description = _parse_text(task_node, 'description')
                complete = _parse_boolean(task_node, 'complete')
                story.tasks.append(Task(task_id, description, complete))



        return story

    def assign_estimate(self, estimate):
        """changes the estimate of a story"""
        update_story_url ="https://www.pivotaltracker.com/services/v3/projects/{}/stories/{}?story[estimate]={}".format(self.project_id, self.story_id, estimate)
        response = _perform_pivotal_put(update_story_url)

    def set_state(self, state):
        """changes the estimate of a story"""
        update_story_url ="https://www.pivotaltracker.com/services/v3/projects/{}/stories/{}?story[current_state]={}".format(self.project_id, self.story_id, state)
        response = _perform_pivotal_put(update_story_url)
        return response

    def finish(self):
        if self.estimate == -1:
            raise InvalidStateException('Story must be estimated')
        self.set_state('finished')

    def start(self):
        if self.estimate == -1:
            raise InvalidStateException('Story must be estimated')
        self.set_state('started')

    def deliver(self):
        if self.estimate == -1:
            raise InvalidStateException('Story must be estimated')
        self.set_state('delivered')

    def accept(self):
        self.set_state('accepted')

    def reject(self):
        self.set_state('rejected')


class InvalidStateException(Exception): pass

class Project(object):
    """object representation of a Pivotal Project"""

    def __init__(self, project_id, name, point_scale):
        self.project_id = project_id
        self.name = name
        self.point_scale = point_scale

    @classmethod
    def from_node(cls, project_node):
        name = _parse_text(project_node, 'name')
        id = _parse_text(project_node, 'id')
        point_scale = _parse_array(project_node, 'point_scale')
        return Project(id, name, point_scale)

    @classmethod
    def all(cls):
        """returns all projects for the given user"""
        projects_url = 'https://www.pivotaltracker.com/services/v3/projects'
        response = _perform_pivotal_get(projects_url)

        root = ET.fromstring(response.text)
        if root is not None:
            return [Project.from_node(project_node) for project_node in root]

    @classmethod
    def load_project(cls, project_id):
        url = "https://www.pivotaltracker.com/services/v3/projects/%s" % project_id
        response = _perform_pivotal_get(url)

        project_node = ET.fromstring(response.text)
        name = _parse_text(project_node, 'name')
        return Project(project_id, name)

    def get_stories(self, filter_string):
        """Given a filter strong, returns an list of stories matching that filter.  If none will return an empty list
        Look at [link](https://www.pivotaltracker.com/help/faq#howcanasearchberefined) for syntax

        """

        story_filter = quote(filter_string, safe='')
        stories_url = "https://www.pivotaltracker.com/services/v3/projects/{}/stories?filter={}".format(self.project_id, story_filter)

        response = _perform_pivotal_get(stories_url)
        stories_root = ET.fromstring(response.text)

        return [Story.from_node(story_node) for story_node in stories_root]

    def load_story(self, story_id):
        """Trys to find a story, returns None is not found"""
        story_url = "https://www.pivotaltracker.com/services/v3/projects/{}/stories/{}".format(self.project_id, story_id)

        resposne = _perform_pivotal_get(story_url)
        # print resposne.text
        if resposne.status_code == 404:
            # Not Found
            return None
        else:
            #Found, parsing story
            root = ET.fromstring(resposne.text)
            return Story.from_node(root)

    def create_story(self,story_dict):
        stories_url = "https://www.pivotaltracker.com/services/v3/projects/{}/stories".format(self.project_id)
        story_xml = dicttoxml.dicttoxml(story_dict, root=False)
        _perform_pivotal_post(stories_url, story_xml)

    def unestimated_stories(self):
        stories = self.get_stories('type:feature state:unstarted')
        return self.open_bugs() + [story for story in stories if int(story.estimate) == -1]

    def open_bugs(self):
        return self.get_stories('type:bug state:unstarted')

    def in_progress_stories(self):
        return self.get_stories('state:started,rejected')

    def finished_features(self):
        return self.get_stories('state:delivered,finished type:feature')

    def finished_bugs(self):
        return self.get_stories('state:delivered,finished type:bug')

    def known_issues(self):
        return self.get_stories('state:unscheduled,unstarted,started,rejected type:bug')


# TODO Handle requests.exceptions.ConnectionError

def _perform_pivotal_get(url):
    headers = {'X-TrackerToken': TOKEN}
    # print url
    response = requests.get(url, headers=headers)
    return response


def _perform_pivotal_put(url):
    headers = {'X-TrackerToken': TOKEN, 'Content-Length': 0}
    response = requests.put(url, headers=headers)
    response.raise_for_status()
    return response

def _perform_pivotal_post(url,payload_xml):
    headers = {'X-TrackerToken': TOKEN, 'Content-type': "application/xml"}
    response = requests.post(url, data=payload_xml, headers=headers)
    response.raise_for_status()
    return response


def _parse_text(node, key):
    """parses test from an ElementTree node, if not found returns empty string"""
    element = node.find(key)
    if element is not None:
        text = element.text
        if text is not None:
            return text.strip()
        else:
            return ''
    else:
        return ''


def _parse_int(node, key):
    """parses an int from an ElementTree node, if not found returns None"""
    element = node.find(key)
    if element is not None:
        return int(element.text)
    else:
        return None


def _parse_array(node, key):
    """parses an int from an ElementTree node, if not found returns None"""
    element = node.find(key)
    if element is not None:
        return element.text.split(',')
    else:
        return None

def _parse_boolean(node, key):
    """parses an boolean from an ElementTree node, if not found returns None"""
    element = node.find(key)
    if element is not None:
        if element.text == 'true':
            return True
        else:
            return False
    else:
        return None
########NEW FILE########
