__FILENAME__ = main

from __future__ import print_function

import argparse
from sys import stderr, stdout, stdin, exit
import os.path
import logging
import codecs

from runipy.notebook_runner import NotebookRunner, NotebookError
from IPython.nbformat.current import read, write

from IPython.config import Config
from IPython.nbconvert.exporters.html import HTMLExporter

def main():
    log_format = '%(asctime)s %(levelname)s: %(message)s'
    log_datefmt = '%m/%d/%Y %I:%M:%S %p'

    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', nargs='?',
            help='.ipynb file to run (or stdin)')
    parser.add_argument('output_file', nargs='?',
            help='.ipynb file to save cell output to')
    parser.add_argument('--quiet', '-q', action='store_true',
            help='don\'t print anything unless things go wrong')
    parser.add_argument('--overwrite', '-o', action='store_true',
            help='write notebook output back to original notebook')
    parser.add_argument('--html', nargs='?', default=False,
            help='output an HTML snapshot of the notebook')
    parser.add_argument('--template', nargs='?', default=False,
            help='template to use for HTML output')
    parser.add_argument('--pylab', action='store_true',
            help='start notebook with pylab enabled')
    parser.add_argument('--matplotlib', action='store_true',
            help='start notebook with matplotlib inlined')
    parser.add_argument('--skip-exceptions', '-s', action='store_true',
            help='if an exception occurs in a cell, continue running the subsequent cells')
    parser.add_argument('--stdout', action='store_true',
            help='print notebook to stdout (or use - as output_file')
    parser.add_argument('--stdin', action='store_true',
            help='read notebook from stdin (or use - as input_file)')
    parser.add_argument('--no-chdir', action='store_true',
            help="do not change directory to notebook's at kernel startup")
    args = parser.parse_args()


    if args.overwrite:
        if args.output_file is not None:
            print('Error: output_filename must not be provided if '
                    '--overwrite (-o) given', file=stderr)
            exit(1)
        else:
            args.output_file = args.input_file

    if not args.quiet:
        logging.basicConfig(level=logging.INFO, format=log_format, datefmt=log_datefmt)

    working_dir = None

    if args.input_file == '-' or args.stdin:  # force stdin
        payload = stdin
    elif not args.input_file and stdin.isatty():  # no force, empty stdin
        parser.print_help()
        exit()
    elif not args.input_file:  # no file -> default stdin
        payload = stdin
    else:  # must have specified normal input_file
        payload = open(args.input_file)
        working_dir = os.path.dirname(args.input_file)

    if args.no_chdir:
        working_dir = None

    logging.info('Reading notebook %s', payload.name)
    nb = read(payload, 'json')
    nb_runner = NotebookRunner(nb, args.pylab, args.matplotlib, working_dir)

    exit_status = 0
    try:
        nb_runner.run_notebook(skip_exceptions=args.skip_exceptions)
    except NotebookError:
        exit_status = 1

    if args.output_file and args.output_file != '-':
        logging.info('Saving to %s', args.output_file)
        write(nb_runner.nb, open(args.output_file, 'w'), 'json')

    if args.stdout or args.output_file == '-':
        write(nb_runner.nb, stdout, 'json')
        print()

    if args.html is not False:
        if args.html is None:
            # if --html is given but no filename is provided,
            # come up with a sane output name based on the
            # input filename
            if args.input_file.endswith('.ipynb'):
                args.html = args.input_file[:-6] + '.html'
            else:
                args.html = args.input_file + '.ipynb'

        if args.template is False:
            exporter = HTMLExporter()
        else:
            exporter = HTMLExporter(
                    config=Config({'HTMLExporter':{'default_template':args.template}}))

        logging.info('Saving HTML snapshot to %s' % args.html)
        output, resources = exporter.from_notebook_node(nb_runner.nb)
        codecs.open(args.html, 'w', encoding='utf-8').write(output)

    if exit_status != 0:
        logging.warning('Exiting with nonzero exit status')
    exit(exit_status)


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = notebook_runner
from __future__ import print_function

try:
    # python 2
    from Queue import Empty
except:
    # python 3
    from queue import Empty

import platform
from time import sleep
import logging
import os

from IPython.nbformat.current import NotebookNode
from IPython.kernel import KernelManager


class NotebookError(Exception):
    pass


class NotebookRunner(object):
    # The kernel communicates with mime-types while the notebook
    # uses short labels for different cell types. We'll use this to
    # map from kernel types to notebook format types.

    MIME_MAP = {
        'image/jpeg': 'jpeg',
        'image/png': 'png',
        'text/plain': 'text',
        'text/html': 'html',
        'text/latex': 'latex',
        'application/javascript': 'html',
        'image/svg+xml': 'svg',
    }


    def __init__(self, nb, pylab=False, mpl_inline=False, working_dir = None):
        self.km = KernelManager()

        args = []

        if pylab:
            args.append('--pylab=inline')
            logging.warn('--pylab is deprecated and will be removed in a future version')
        elif mpl_inline:
            args.append('--matplotlib=inline')
            logging.warn('--matplotlib is deprecated and will be removed in a future version')

        cwd = os.getcwd()

        if working_dir:
            os.chdir(working_dir)

        self.km.start_kernel(extra_arguments = args)
        
        os.chdir(cwd)

        if platform.system() == 'Darwin':
            # There is sometimes a race condition where the first
            # execute command hits the kernel before it's ready.
            # It appears to happen only on Darwin (Mac OS) and an
            # easy (but clumsy) way to mitigate it is to sleep
            # for a second.
            sleep(1)

        self.kc = self.km.client()
        self.kc.start_channels()

        self.shell = self.kc.shell_channel
        self.iopub = self.kc.iopub_channel
        
        self.nb = nb
        

    def __del__(self):
        self.kc.stop_channels()
        self.km.shutdown_kernel(now=True)


    def run_cell(self, cell):
        '''
        Run a notebook cell and update the output of that cell in-place.
        '''
        logging.info('Running cell:\n%s\n', cell.input)
        self.shell.execute(cell.input)
        reply = self.shell.get_msg()
        status = reply['content']['status']
        if status == 'error':
            traceback_text = 'Cell raised uncaught exception: \n' + \
                '\n'.join(reply['content']['traceback'])
            logging.info(traceback_text)
        else:
            logging.info('Cell returned')

        outs = list()
        while True:
            try:
                msg = self.iopub.get_msg(timeout=1)
                if msg['msg_type'] == 'status':
                    if msg['content']['execution_state'] == 'idle':
                        break
            except Empty:
                # execution state should return to idle before the queue becomes empty,
                # if it doesn't, something bad has happened
                raise

            content = msg['content']
            msg_type = msg['msg_type']

            # IPython 3.0.0-dev writes pyerr/pyout in the notebook format but uses
            # error/execute_result in the message spec. This does the translation
            # needed for tests to pass with IPython 3.0.0-dev
            notebook3_format_conversions = {
                'error': 'pyerr',
                'execute_result': 'pyout'
            }
            msg_type = notebook3_format_conversions.get(msg_type, msg_type)

            out = NotebookNode(output_type=msg_type)

            if 'execution_count' in content:
                cell['prompt_number'] = content['execution_count']
                out.prompt_number = content['execution_count']

            if msg_type in ('status', 'pyin', 'execute_input'):
                continue
            elif msg_type == 'stream':
                out.stream = content['name']
                out.text = content['data']
                #print(out.text, end='')
            elif msg_type in ('display_data', 'pyout'):
                for mime, data in content['data'].items():
                    try:
                        attr = self.MIME_MAP[mime]
                    except KeyError:
                        raise NotImplementedError('unhandled mime type: %s' % mime)

                    setattr(out, attr, data)
                #print(data, end='')
            elif msg_type == 'pyerr':
                out.ename = content['ename']
                out.evalue = content['evalue']
                out.traceback = content['traceback']

                #logging.error('\n'.join(content['traceback']))
            elif msg_type == 'clear_output':
                outs = list()
                continue
            else:
                raise NotImplementedError('unhandled iopub message: %s' % msg_type)
            outs.append(out)
        cell['outputs'] = outs

        if status == 'error':
            raise NotebookError(traceback_text)


    def iter_code_cells(self):
        '''
        Iterate over the notebook cells containing code.
        '''
        for ws in self.nb.worksheets:
            for cell in ws.cells:
                if cell.cell_type == 'code':
                    yield cell


    def run_notebook(self, skip_exceptions=False):
        '''
        Run all the cells of a notebook in order and update
        the outputs in-place.

        If ``skip_exceptions`` is set, then if exceptions occur in a cell, the
        subsequent cells are run (by default, the notebook execution stops).
        '''
        for cell in self.iter_code_cells():
            try:
                self.run_cell(cell)
            except NotebookError:
                if not skip_exceptions:
                    raise


########NEW FILE########
__FILENAME__ = test

import unittest
from glob import glob
from os import path, chdir
import re

from IPython.nbformat.current import read

from runipy.notebook_runner import NotebookRunner

class TestRunipy(unittest.TestCase):
    maxDiff = 100000

    def prepare_cell(self, cell):
        cell = dict(cell)
        if 'metadata' in cell:
            del cell['metadata']
        if 'text' in cell:
            # don't match object's id; also happens to fix incompatible
            # results between IPython2 and IPython3 (which prints "object" instead
            # of "at [id]"
            cell['text'] = re.sub('at 0x[0-9a-f]{7,9}', 'object', cell['text'])
        if 'traceback' in cell:
            cell['traceback'] = [re.sub('\x1b\\[[01];\\d\\dm', '', line) for line in cell['traceback']]
        return cell


    def assert_notebooks_equal(self, expected, actual):
        self.assertEquals(len(expected['worksheets'][0]['cells']),
                len(actual['worksheets'][0]['cells']))

        for expected_out, actual_out in zip(expected['worksheets'][0]['cells'],
                actual['worksheets'][0]['cells']):
            for k in set(expected_out).union(actual_out):
                if k == 'outputs':
                    self.assertEquals(len(expected_out[k]), len(actual_out[k]))
                    for e, a in zip(expected_out[k], actual_out[k]):
                        e = self.prepare_cell(e)
                        a = self.prepare_cell(a)
                        self.assertEquals(a, e)
                    

    def testRunNotebooks(self):
        notebook_dir = path.join('tests', 'input')
        for notebook_path in glob(path.join(notebook_dir, '*.ipynb')):
            notebook_file = path.basename(notebook_path)
            print notebook_file
            expected_file = path.join('tests', 'expected', notebook_file)
            runner = NotebookRunner(read(open(notebook_path), 'json'), working_dir=notebook_dir)
            runner.run_notebook(True)
            expected = read(open(expected_file), 'json')
            self.assert_notebooks_equal(expected, runner.nb)


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
