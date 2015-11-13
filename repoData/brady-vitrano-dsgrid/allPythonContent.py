__FILENAME__ = adapter
import docker


class DockerAdapter:
    def __init__(self):
        self.client = docker.Client(base_url='unix://var/run/docker.sock', version="1.6")

    def find_image(self, repo_name):
        images = self.client.images()
        for image in images:
            name = image.get('Repository', 'unknown')
            if name == repo_name:
                return image

        return None

    def find_container(self, image_name):
        containers = self.client.containers()
        for container in containers:
            name = container.get('Image', 'unknown')
            if name == image_name:
                return container

    def find_all_containers(self, image_name):
        matches = []
        containers = self.client.containers()
        for container in containers:
            name = container.get('Image', 'unknown')
            if name == image_name:
                matches.append(container)
        return matches

    def inspect(self, container_id):
        return self.client.inspect_container(container_id)

    def restart(self, container_id):
        self.client.restart(container_id)

########NEW FILE########
__FILENAME__ = build
from adapter import DockerAdapter
import os


class GridBuilder:

    def __init__(self):
        self.adapter = DockerAdapter()

    def is_installed(self):
        container = self.adapter.find_image('dsgrid/selenium-hub')
        return container

    def build(self, container):
        if container == 'chrome':
            directory = os.path.join('/usr/local/dsgrid', 'files', 'chrome')
            if not os.path.exists(directory):
                print "File not found"
                return False
            self.adapter.client.build(directory, 'dsgrid/chrome-node')
            return True

        if container == 'phantomjs':
            directory = os.path.join('/usr/local/dsgrid', 'files', 'phantomjs')
            if not os.path.exists(directory):
                print "File not found"
                return False
            self.adapter.client.build(directory, 'dsgrid/phantomjs-node')
            return True

        if container == 'firefox':
            directory = os.path.join('/usr/local/dsgrid', 'files', 'firefox')
            if not os.path.exists(directory):
                return False
            self.adapter.client.build(directory, 'dsgrid/firefox-node')
            return True

        if container == 'selenium-hub':
            directory = os.path.join('/usr/local/dsgrid', 'files', 'selenium')
            if not os.path.exists(directory):
                return False
            self.adapter.client.build(directory, 'dsgrid/selenium-hub')
            return True

        return False






########NEW FILE########
__FILENAME__ = hub
import sys
from adapter import DockerAdapter


class HubController:
    def __init__(self):
        self.hub = GridHub()

    @staticmethod
    def is_running():
        hub = GridHub()
        return hub.is_running()

    @staticmethod
    def start():
        """
        @rtype: bool
        @return: True on success
        """
        hub = GridHub()
        try:
            hub.start()
            # TODO: Verify Started
            return True
        except Exception:
            return False

    @staticmethod
    def is_valid_browser(browser):

        if browser in GridHub.VALID_BROWSERS:
            return True
        return False

    @staticmethod
    def add(browser):
        """
        @type browser: string
        @param browser: Browser Name
        @rtype: bool
        @return: True on success
        """
        hub = GridHub()
        return hub.add_node(browser)

    @staticmethod
    def get_status():
        hub = GridHub()

        ff_count = 0
        ph_count = 0
        ch_count = 0

        nodes = hub.get_nodes()
        for node in nodes:
            if "firefox" in node['Image']:
                ff_count += 1
            elif "phantomjs" in node['Image']:
                ph_count +=1
            elif "chrome" in node['Image']:
                ch_count += 1

        status = {
            "Ip": hub.get_ip(),
            "firefox_count": ff_count,
            "phantomjs_count": ph_count,
            "chrome_count": ch_count
        }

        return status

    @staticmethod
    def restart_nodes(browser=None):
        hub = GridHub()
        return hub.restart_nodes(browser)

    @staticmethod
    def stop_nodes():
        hub = GridHub()
        return hub.stop_nodes()

    @staticmethod
    def shutdown():
        hub = GridHub()
        hub.shutdown()


class GridHub:
    VALID_BROWSERS = ('firefox', 'phantomjs', 'chrome')

    def __init__(self):
        self.adapter = DockerAdapter()

    def get_container_info(self):
        container = self.adapter.find_container('dsgrid/selenium-hub:latest')
        if not container:
            # raise exception container not found
            return False
        container_info = self.adapter.inspect(container['Id'])
        container = dict(container.items() + container_info.items())
        return container

    def get_nodes(self):
        nodes = []
        containers = self.adapter.client.containers()

        for container in containers:
            if "node" in container['Image']:
                nodes.append(container)

        return nodes

    def is_running(self):
        container = self.get_container_info()
        if not container:
            # raise exception container not found
            return False
        return "Up" in container['Status']

    def start(self):
        response = self.adapter.client.create_container('dsgrid/selenium-hub', ports={"4444/tcp": {}})
        if response['Id']:
            self.adapter.client.start(response, None, {'4444/tcp': ('', '49044')})

    def get_ip(self):
        container = self.get_container_info()
        return container['NetworkSettings']['IPAddress']

    def add_node(self, browser):
        if not browser in self.VALID_BROWSERS:
            return False
        ip = self.get_ip()
        response = self.adapter.client.create_container('dsgrid/'+browser+'-node', [], environment={"GRID_IP": ip})
        if response['Id']:
            self.adapter.client.start(response)
            return True

    def restart_nodes(self, browser=None):
        containers = self.get_nodes()
        nodes_to_stop = []
        for container in containers:
            if browser is not None and browser not in container['Image']:
                continue
            nodes_to_stop.append(container)

        if len(nodes_to_stop) == 0:
            return False

        for container in nodes_to_stop:
            self.adapter.restart(container)

        return True

    def stop_nodes(self, by_browser=None):
        if by_browser is not None and not by_browser in self.VALID_BROWSERS:
            # raise exception
            return False

        browser = ''
        if by_browser in self.VALID_BROWSERS:
            browser = by_browser + '-'

        containers = self.adapter.client.containers()

        for container in containers:
            if browser + "node" in container['Image']:
                self.adapter.client.stop(container['Id'])
                self.adapter.client.remove_container(container['Id'])

        return True

    def shutdown(self):

        self.stop_nodes()
        container = self.adapter.find_container('dsgrid/selenium-hub:latest')
        if not container:
            # raise exception container not found
            return False
        self.adapter.client.stop(container)
        self.adapter.client.remove_container(container)


########NEW FILE########
__FILENAME__ = shell
import sys
from utils import Message
from hub import HubController
from build import GridBuilder


def fail(message):
    Message.fail(message)
    sys.exit(1)


def ok(message):
    Message.ok(message)


def info(message):
    Message.ok(message)


def warning(message):
    Message.warning(message)


def nodes(subject, argv):

    if len(argv) == 0:
        fail("Missing node action")

    action = argv.pop(0)
    if action == 'add':
        if len(argv) == 0:
            fail("Missing browser, use phantomjs|firefox|chrome")

        browser = argv.pop(0)
        if not HubController.is_valid_browser(browser):
            fail("Invalid browser please use phantomjs|firefox|chrome")

        info("Adding node...")
        status = HubController.add(browser)
        if not status:
            fail("Failed to start node")

        ok("Node Added Successfully!")

    elif action == 'stop':
        info("Stopping nodes...")
        HubController.stop_nodes()
        ok("Nodes stopped")
    elif action == 'restart':
        info("Restarting nodes...")
        browser = None
        if len(argv) == 1 and not HubController.is_valid_browser(argv.pop(0)):
            fail('Restarting by browser requires either phantomjs, chrome or firefox')

        HubController.restart_nodes(browser)
        ok("Nodes restarted")
    elif action == 'rebuild':
        # TODO:
        print "Rebuild Nodes optional by browser"
    else:
        fail("Unknown node action: " + action)


def rebuild(subject, argv):
    fail("TODO: Rebuild the Hub and Browsers")


def start(subject, argv):
    if HubController.is_running():
        warning("Hub already running")
        sys.exit(1)

    info("Starting up grid...")
    status = HubController.start()
    if not status:
        fail("Hub failed to start")
        sys.exit(1)
    ok("Hub is Ready!")


def shutdown(subject, argv):
    if not HubController.is_running():
        fail("Hub is not running")
        sys.exit(1)
    info("Shutting down grid...")
    HubController.shutdown()


def grid_status(subject, argv):
    if not HubController.is_running():
        ok("Grid is not running")
        sys.exit(1)
    grid = HubController.get_status()
    ok("GridIP: " + grid['Ip']
       + ' Firefox Nodes: ' + str(grid['firefox_count'])
       + ' PhantomJS Nodes: ' + str(grid['phantomjs_count'])
       + ' Chrome Nodes: ' + str(grid['chrome_count']))


def unknown(option, argv):
    Message.fail("Unknown Option: " + option)
    sys.exit(1)


def install(option, argv):
    builder = GridBuilder()
    if builder.is_installed():
        fail("Already installed")

    info("Building Selenium Grid, PhantomJS, and Firefox Containers...please be patient")
    info("Installing Selenium Hub...")
    builder.build('selenium-hub')
    ok("Selenium Hub Container Installed")
    info("Installing Firefox...")
    builder.build('firefox')
    ok("Firefox container installed")
    info("Installing PhantomJS...")
    builder.build('phantomjs')
    ok("PhantomJS container installed")
    info("Installing Chrome...")
    builder.build('chrome')
    ok("Chrome container installed")
    ok("Selenium Grid is installed!")


def main():
    if len(sys.argv) < 2:
        print "dsgrid <subject> [action]"
        sys.exit(1)

    argv = sys.argv[1:]
    subject = argv.pop(0)
    {
        "nodes": nodes,
        "start": start,
        "shutdown": shutdown,
        "status": grid_status,
        "install": install

    }.get(subject, unknown)(subject, argv)


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = test_docker_usage
import unittest
import docker
from dsgrid.hub import GridHub
from dsgrid.adapter import DockerAdapter


class TestDockerInterface(unittest.TestCase):
    def test_can_search_container(self):
        adapter = DockerAdapter()
        image = adapter.find_image('brady/selenium-grid')
        if not image:
            print "Not Found"
        print "Found"

    def test_can_check_if_grid_running(self):
        adapter = DockerAdapter()
        container = adapter.find_container('brady/selenium-grid:latest')
        if not container:
            print "Not Found"
        print "Found"
        #print container['Status']
        #print container['Ports']
        #print container['Id']
        if "Up" in container['Status']:
            print "Grid is Running"
        else:
            print "Grid is not Running"

    def test_can_get_grid_ip(self):
        adapter = DockerAdapter()
        container = adapter.find_container('brady/selenium-grid:latest')
        if not container:
            print "Not Found"
            return
        container_info = adapter.inspect(container['Id'])
        container = dict(container.items() + container_info.items())
        print container['NetworkSettings']['IPAddress']

    def test_can_get_nodes(self):
        adapter = DockerAdapter()
        containers = adapter.find_all_containers('brady/firefox-node:latest')
        if len(containers) == 0:
            print "Not Found"
            return

        print "Total of Firefox Nodes: " + str(len(containers))

    @unittest.skip("skipping restart")
    def test_can_restart_node(self):
        adapter = DockerAdapter()
        containers = adapter.find_all_containers('brady/firefox-node:latest')
        if len(containers) == 0:
            print "Not Found"
            return

        container = containers.pop(0)
        adapter.restart(container)

    @unittest.skip("skipping stopping nodes")
    def test_stop_all_nodes(self):
        adapter = DockerAdapter()
        containers = adapter.client.containers()
        for container in containers:
            if "node" in container['Image']:
                print "Stopping container..."
                adapter.client.stop(container['Id'])
                print "Removing container..."
                adapter.client.remove_container(container['Id'])
                #print container['Image']

    def test_start_add_node(self):
        hub = GridHub()
        ip = hub.get_ip()
        print "Grid Hub IP: " + hub.get_ip()
        # sudo docker run -d -e GRID_IP=${GRID_IP} brady/${1}-node
        adapter = DockerAdapter()
        response = adapter.client.create_container('brady/firefox-node', [], environment={"GRID_IP": ip})
        if response['Id']:
            adapter.client.start(response)

    def test_grid_start(self):
        hub = GridHub()
        hub.start()

    def test_grid_shutdown(self):
        hub = GridHub()
        hub.shutdown()




if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_shell
import unittest
import os
from dsgrid import shell
from mock import patch
from dsgrid import hub

devnull = open(os.devnull, 'w')


class TestShell(unittest.TestCase):

    def setUp(self):
        pass


    @patch.object(hub.HubController, 'is_running')
    @patch.object(hub.HubController, 'start')
    def test_start(self, mock_start, mock_is_running):
        """
        Positive
        dsgrid start
        """
        mock_is_running.return_value = False
        mock_start.return_value = True
        shell.main(['start'])

    @patch.object(hub.HubController, 'is_running')
    @patch.object(hub.HubController, 'start')
    def test_start_but_container_fails(self, mock_start, mock_is_running):
        """
        Positive
        dsgrid start
        """
        mock_is_running.return_value = False
        mock_start.return_value = False
        with patch('sys.stdout', devnull):
            with self.assertRaises(SystemExit) as cm:
                shell.main(['start'])

        self.assertEqual(cm.exception.code, 1)


    @patch.object(hub.HubController, 'is_running')
    @patch.object(hub.HubController, 'start')
    def test_start_while_running(self, mock_start, mock_is_running):
        """
        Negative: Grid is running
        dsgrid start
        """
        mock_is_running.return_value = True
        mock_start.return_value = True
        with patch('sys.stdout', devnull):
            with self.assertRaises(SystemExit) as cm:
                shell.main(['start'])

        self.assertEqual(cm.exception.code, 1)

    @patch.object(hub.HubController, 'is_running')
    def test_shutdown(self, mock_method):
        """
        Position
        dsgrid shutdown
        """
        mock_method.return_value = True
        shell.main(['shutdown'])

    @patch.object(hub.HubController, 'is_running')
    def test_shutdown_while_not_running(self, mock_method):
        mock_method.return_value = False
        with patch('sys.stdout', devnull):
            with self.assertRaises(SystemExit) as cm:
                shell.main(['shutdown'])
        self.assertEqual(cm.exception.code, 1)

    @patch.object(hub.HubController, 'add')
    def test_add_valid_browser(self, mock_method):
        mock_method.return_value = True
        shell.main(['nodes', 'add', 'firefox'])

    @patch.object(hub.HubController, 'add')
    def test_add_browser_with_multiple(self, mock_method):
        mock_method.return_value = True
        shell.main(['nodes', 'add', 'firefox', '2'])

    def test_add_node_invalid_browser(self):
        with patch('sys.stdout', devnull):
            with self.assertRaises(SystemExit) as cm:
                shell.main(['nodes', 'add', 'netscape'])

        self.assertEqual(cm.exception.code, 1)

    @patch.object(hub.HubController, 'add')
    def test_add_node_but_container_fails(self, mock_method):
        mock_method.return_value = False
        with patch('sys.stdout', devnull):
            with self.assertRaises(SystemExit) as cm:
                shell.main(['nodes', 'add', 'firefox'])
        self.assertEqual(cm.exception.code, 1)

    def test_restart_nodes(self):
        shell.main(['nodes', 'restart'])

    def test_restart_nodes_specific_browser(self):
        shell.main(['nodes', 'restart', 'firefox'])

    def test_stop_nodes(self):
        shell.main(['nodes', 'stop'])

    def test_nodes_missing_action(self):
        with patch('sys.stdout', devnull):
            with self.assertRaises(SystemExit) as cm:
                shell.main(['nodes'])

        self.assertEqual(cm.exception.code, 1)

    def test_stop_nodes_specific_browser(self):
        shell.main(['nodes', 'stop', 'firefox'])

    def test_nodes_unknown_action(self):
        with self.assertRaises(SystemExit) as cm:
            shell.main(['nodes', 'juggle'])
        self.assertEqual(cm.exception.code, 1)

    @patch.object(hub.HubController, 'is_running')
    def test_status_not_running(self, mock_method):
        mock_method.return_value = False
        #with patch('sys.stdout', devnull):
        with self.assertRaises(SystemExit) as cm:
            shell.main(['status'])
        self.assertEqual(cm.exception.code, 1)

    @patch.object(hub.HubController, 'is_running')
    def test_status_running(self, mock_method):
        mock_method.return_value = True
        shell.main(['status'])

    def test_unknown_option(self):
        with self.assertRaises(SystemExit) as cm:
            shell.main(['shake'])

        self.assertEqual(cm.exception.code, 1)


if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = utils


class Colors:

    HEADER  = '\033[95m'
    OKBLUE  = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL    = '\033[91m'
    END     = '\033[0m'

    def __init__(self):
        pass

    def disable(self):
        self.HEADER  = ''
        self.OKBLUE  = ''
        self.OKGREEN = ''
        self.WARNING = ''
        self.FAIL    = ''
        self.END     = ''


class Message:
    def __init__(self):
        pass

    @staticmethod
    def fail(message):
        print Colors.FAIL + message + Colors.END

    @staticmethod
    def ok(message):
        print Colors.OKGREEN + message + Colors.END

    @staticmethod
    def warning(message):
        print Colors.WARNING + message + Colors.END

########NEW FILE########
__FILENAME__ = test_docker_usage
import unittest
import docker
from dsgrid.hub import GridHub
from dsgrid.adapter import DockerAdapter


class TestDockerInterface(unittest.TestCase):
    def test_can_search_container(self):
        adapter = DockerAdapter()
        image = adapter.find_image('brady/selenium-grid')
        if not image:
            print "Not Found"
        print "Found"

    def test_can_check_if_grid_running(self):
        adapter = DockerAdapter()
        container = adapter.find_container('brady/selenium-grid:latest')
        if not container:
            print "Not Found"
        print "Found"
        #print container['Status']
        #print container['Ports']
        #print container['Id']
        if "Up" in container['Status']:
            print "Grid is Running"
        else:
            print "Grid is not Running"

    def test_can_get_grid_ip(self):
        adapter = DockerAdapter()
        container = adapter.find_container('brady/selenium-grid:latest')
        if not container:
            print "Not Found"
            return
        container_info = adapter.inspect(container['Id'])
        container = dict(container.items() + container_info.items())
        print container['NetworkSettings']['IPAddress']

    def test_can_get_nodes(self):
        adapter = DockerAdapter()
        containers = adapter.find_all_containers('brady/firefox-node:latest')
        if len(containers) == 0:
            print "Not Found"
            return

        print "Total of Firefox Nodes: " + str(len(containers))

    @unittest.skip("skipping restart")
    def test_can_restart_node(self):
        adapter = DockerAdapter()
        containers = adapter.find_all_containers('brady/firefox-node:latest')
        if len(containers) == 0:
            print "Not Found"
            return

        container = containers.pop(0)
        adapter.restart(container)

    @unittest.skip("skipping stopping nodes")
    def test_stop_all_nodes(self):
        adapter = DockerAdapter()
        containers = adapter.client.containers()
        for container in containers:
            if "node" in container['Image']:
                print "Stopping container..."
                adapter.client.stop(container['Id'])
                print "Removing container..."
                adapter.client.remove_container(container['Id'])
                #print container['Image']

    def test_start_add_node(self):
        hub = GridHub()
        ip = hub.get_ip()
        print "Grid Hub IP: " + hub.get_ip()
        # sudo docker run -d -e GRID_IP=${GRID_IP} brady/${1}-node
        adapter = DockerAdapter()
        response = adapter.client.create_container('brady/firefox-node', [], environment={"GRID_IP": ip})
        if response['Id']:
            adapter.client.start(response)

    def test_grid_start(self):
        hub = GridHub()
        hub.start()

    def test_grid_shutdown(self):
        hub = GridHub()
        hub.shutdown()




if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_shell
import unittest
import os
from dsgrid import shell
from mock import patch
from dsgrid import hub

devnull = open(os.devnull, 'w')


class TestShell(unittest.TestCase):

    def setUp(self):
        pass


    @patch.object(hub.HubController, 'is_running')
    @patch.object(hub.HubController, 'start')
    def test_start(self, mock_start, mock_is_running):
        """
        Positive
        dsgrid start
        """
        mock_is_running.return_value = False
        mock_start.return_value = True
        shell.main(['start'])

    @patch.object(hub.HubController, 'is_running')
    @patch.object(hub.HubController, 'start')
    def test_start_but_container_fails(self, mock_start, mock_is_running):
        """
        Positive
        dsgrid start
        """
        mock_is_running.return_value = False
        mock_start.return_value = False
        with patch('sys.stdout', devnull):
            with self.assertRaises(SystemExit) as cm:
                shell.main(['start'])

        self.assertEqual(cm.exception.code, 1)


    @patch.object(hub.HubController, 'is_running')
    @patch.object(hub.HubController, 'start')
    def test_start_while_running(self, mock_start, mock_is_running):
        """
        Negative: Grid is running
        dsgrid start
        """
        mock_is_running.return_value = True
        mock_start.return_value = True
        with patch('sys.stdout', devnull):
            with self.assertRaises(SystemExit) as cm:
                shell.main(['start'])

        self.assertEqual(cm.exception.code, 1)

    @patch.object(hub.HubController, 'is_running')
    def test_shutdown(self, mock_method):
        """
        Position
        dsgrid shutdown
        """
        mock_method.return_value = True
        shell.main(['shutdown'])

    @patch.object(hub.HubController, 'is_running')
    def test_shutdown_while_not_running(self, mock_method):
        mock_method.return_value = False
        with patch('sys.stdout', devnull):
            with self.assertRaises(SystemExit) as cm:
                shell.main(['shutdown'])
        self.assertEqual(cm.exception.code, 1)

    @patch.object(hub.HubController, 'add')
    def test_add_valid_browser(self, mock_method):
        mock_method.return_value = True
        shell.main(['nodes', 'add', 'firefox'])

    @patch.object(hub.HubController, 'add')
    def test_add_browser_with_multiple(self, mock_method):
        mock_method.return_value = True
        shell.main(['nodes', 'add', 'firefox', '2'])

    def test_add_node_invalid_browser(self):
        with patch('sys.stdout', devnull):
            with self.assertRaises(SystemExit) as cm:
                shell.main(['nodes', 'add', 'netscape'])

        self.assertEqual(cm.exception.code, 1)

    @patch.object(hub.HubController, 'add')
    def test_add_node_but_container_fails(self, mock_method):
        mock_method.return_value = False
        with patch('sys.stdout', devnull):
            with self.assertRaises(SystemExit) as cm:
                shell.main(['nodes', 'add', 'firefox'])
        self.assertEqual(cm.exception.code, 1)

    def test_restart_nodes(self):
        shell.main(['nodes', 'restart'])

    def test_restart_nodes_specific_browser(self):
        shell.main(['nodes', 'restart', 'firefox'])

    def test_stop_nodes(self):
        shell.main(['nodes', 'stop'])

    def test_nodes_missing_action(self):
        with patch('sys.stdout', devnull):
            with self.assertRaises(SystemExit) as cm:
                shell.main(['nodes'])

        self.assertEqual(cm.exception.code, 1)

    def test_stop_nodes_specific_browser(self):
        shell.main(['nodes', 'stop', 'firefox'])

    def test_nodes_unknown_action(self):
        with self.assertRaises(SystemExit) as cm:
            shell.main(['nodes', 'juggle'])
        self.assertEqual(cm.exception.code, 1)

    @patch.object(hub.HubController, 'is_running')
    def test_status_not_running(self, mock_method):
        mock_method.return_value = False
        #with patch('sys.stdout', devnull):
        with self.assertRaises(SystemExit) as cm:
            shell.main(['status'])
        self.assertEqual(cm.exception.code, 1)

    @patch.object(hub.HubController, 'is_running')
    def test_status_running(self, mock_method):
        mock_method.return_value = True
        shell.main(['status'])

    def test_unknown_option(self):
        with self.assertRaises(SystemExit) as cm:
            shell.main(['shake'])

        self.assertEqual(cm.exception.code, 1)


if __name__ == '__main__':
    unittest.main()
########NEW FILE########
