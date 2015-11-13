__FILENAME__ = hook-cfn-init
#!/usr/bin/env python
from heat_cfntools.cfntools import cfn_helper
import json
import sys


def main(argv=sys.argv):
    c = json.load(sys.stdin)

    config = c.get('config', {})
    if not isinstance(config, dict):
        config = json.loads(config)
    meta = {'AWS::CloudFormation::Init': config}

    metadata = cfn_helper.Metadata(None, None)
    metadata.retrieve(meta_str=json.dumps(meta))
    metadata.cfn_init()

if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = hook-puppet
#!/usr/bin/env python
import json
import logging
import os
import subprocess
import sys

WORKING_DIR = os.environ.get('HEAT_PUPPET_WORKING',
                             '/var/lib/heat-config/heat-config-puppet')
OUTPUTS_DIR = os.environ.get('HEAT_PUPPET_OUTPUTS',
                             '/var/run/heat-config/heat-config-puppet')


def prepare_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path, 0o700)


def main(argv=sys.argv):
    log = logging.getLogger('heat-config')
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            '[%(asctime)s] (%(name)s) [%(levelname)s] %(message)s'))
    log.addHandler(handler)
    log.setLevel('DEBUG')

    prepare_dir(OUTPUTS_DIR)
    prepare_dir(WORKING_DIR)
    os.chdir(WORKING_DIR)

    c = json.load(sys.stdin)

    facts = {}
    for input in c['inputs']:
        input_name = input['name']
        fact_name = 'FACTER_%s' % input_name
        facts[fact_name] = input.get('value', '')

    fn = os.path.join(WORKING_DIR, '%s.pp' % c['id'])
    heat_outputs_path = os.path.join(OUTPUTS_DIR, c['id'])
    facts['FACTER_heat_outputs_path'] = heat_outputs_path

    env_debug = ' '.join('%s="%s" ' % (k, v) for k, v in facts.items())

    env = os.environ.copy()
    env.update(facts)

    with os.fdopen(os.open(fn, os.O_CREAT | os.O_WRONLY, 0o700), 'w') as f:
        f.write(c.get('config', ''))

    cmd = ['puppet', 'apply', '--detailed-exitcodes', fn]
    log.debug('Running %s %s' % (env_debug, ' '.join(cmd)))
    try:
        subproc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, env=env)
    except OSError:
        log.warn('puppet not installed yet')
        return
    stdout, stderr = subproc.communicate()

    log.info('Return code %s' % subproc.returncode)
    if stdout:
        log.info(stdout)
    if stderr:
        log.info(stderr)

    # returncode of 2 means there were successfull changes
    if subproc.returncode in (0, 2):
        returncode = 0
        log.info('Completed %s' % fn)
    else:
        returncode = subproc.returncode
        log.error("Error running %s. [%s]\n" % (fn, subproc.returncode))

    response = {}

    for output in c.get('outputs') or []:
        output_name = output['name']
        try:
            with open('%s.%s' % (heat_outputs_path, output_name)) as out:
                response[output_name] = out.read()
        except IOError:
            pass

    response.update({
        'deploy_stdout': stdout,
        'deploy_stderr': stderr,
        'deploy_status_code': returncode,
    })

    json.dump(response, sys.stdout)

if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = hook-script
#!/usr/bin/env python
import json
import logging
import os
import subprocess
import sys

WORKING_DIR = os.environ.get('HEAT_SCRIPT_WORKING',
                             '/var/lib/heat-config/heat-config-script')
OUTPUTS_DIR = os.environ.get('HEAT_SCRIPT_OUTPUTS',
                             '/var/run/heat-config/heat-config-script')


def prepare_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path, 0o700)


def main(argv=sys.argv):
    log = logging.getLogger('heat-config')
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            '[%(asctime)s] (%(name)s) [%(levelname)s] %(message)s'))
    log.addHandler(handler)
    log.setLevel('DEBUG')

    prepare_dir(OUTPUTS_DIR)
    prepare_dir(WORKING_DIR)
    os.chdir(WORKING_DIR)

    c = json.load(sys.stdin)

    env = os.environ.copy()
    for input in c['inputs']:
        input_name = input['name']
        env[input_name] = input.get('value', '')
        log.info('%s=%s' % (input_name, env[input_name]))

    fn = os.path.join(WORKING_DIR, c['id'])
    heat_outputs_path = os.path.join(OUTPUTS_DIR, c['id'])
    env['heat_outputs_path'] = heat_outputs_path

    with os.fdopen(os.open(fn, os.O_CREAT | os.O_WRONLY, 0o700), 'w') as f:
        f.write(c.get('config', ''))

    log.debug('Running %s' % fn)
    subproc = subprocess.Popen([fn], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, env=env)
    stdout, stderr = subproc.communicate()

    log.info(stdout)
    log.debug(stderr)

    if subproc.returncode:
        log.error("Error running %s. [%s]\n" % (fn, subproc.returncode))
    else:
        log.info('Completed %s' % fn)

    response = {}

    for output in c.get('outputs') or []:
        output_name = output['name']
        try:
            with open('%s.%s' % (heat_outputs_path, output_name)) as out:
                response[output_name] = out.read()
        except IOError:
            pass

    response.update({
        'deploy_stdout': stdout,
        'deploy_stderr': stderr,
        'deploy_status_code': subproc.returncode,
    })

    json.dump(response, sys.stdout)

if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
