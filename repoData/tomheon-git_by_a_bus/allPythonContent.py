__FILENAME__ = common
"""
Common and other crappy code used throughout git by a bus.
"""

def safe_author_name(author):
    if author:
        return author.replace(',', '_').replace(':', '_')
    else:
        return author

def safe_int(i):
    if i is None or i == '':
        return None
    else:
        return int(i)

def safe_str(s):
    if s is None:
        return ''
    else:
        return str(s)

def parse_dev_shared(s, num_func):
    dev_shared = []
    if not s:
        return dev_shared
    for ddv in s.split(','):
        segs = ddv.split(':')
        k = segs[:-1]
        v = float(segs[-1])
        dev_shared.append((k, v))

    return dev_shared

def dev_shared_to_str(dev_shared):
    return ','.join([':'.join([':'.join(devs), str(shared)]) for devs, shared in dev_shared])

def parse_dev_exp_str(s, num_func):
    if not s:
        return []
    return [(dd[0], num_func(dd[1]), num_func(dd[2])) for dd in  [d.split(':') for d  in s.split(',')]]

def dev_exp_to_str(devs):
    return ','.join([':'.join([str(x) for x in d]) for d in devs])

def project_name(fname):
    if not fname:
        return None
    return fname.split(':')[0]

 
class FileData(object):
    """
    Represents a single line of data about a single file, can encode / parse to / from tsv.

    fname: the name of the file the data is about

    cnt_lines: the number of lines in the file

    tot_knowledge: total knowledge in the file

    dev_experience: [(dev, lines_added, lines_removed), ...]

    dev_uniq: [([dev1], uniq_knowledge), ([dev1, dev2], uniq_knowledge), ...]

    dev_risk: [([dev1], risk), ([dev1, dev2], risk), ...]

    project: name of the project
    """
    
    num_fields = 6

    def __init__(self, line):
        if line is None:
            line = ''
        line = line.strip('\n\r')
        fields = line.split('\t')
        n_missing_fields = FileData.num_fields - len(fields)
        fields.extend(n_missing_fields * [None])
        
        self.fname, cnt_lines, dev_experience, tot_knowledge, dev_uniq, dev_risk = fields

        self.cnt_lines = safe_int(cnt_lines)
        self.tot_knowledge = safe_int(tot_knowledge)
        
        self.dev_experience = parse_dev_exp_str(dev_experience, int)
        self.dev_uniq = parse_dev_shared(dev_uniq, float)
        self.dev_risk = parse_dev_shared(dev_risk, float)

        self.project = project_name(self.fname)

    def as_line(self):
        return '\t'.join(map(safe_str, [self.fname,
                                        self.cnt_lines,
                                        dev_exp_to_str(self.dev_experience),
                                        self.tot_knowledge,
                                        dev_shared_to_str(self.dev_uniq),
                                        dev_shared_to_str(self.dev_risk)]))

    def __str__(self):
        s = ("fname: %s, cnt_lines: %s, dev_experience: %s, tot_knowledge: %s, dev_uniq: %s, " + \
            "risk: %s ") % (self.fname,
                                              str(self.cnt_lines),
                                              dev_exp_to_str(self.dev_experience),
                                              str(self.tot_knowledge),
                                              dev_shared_to_str(self.dev_uniq),
                                              dev_shared_to_str(self.dev_risk))
        return s
                                                                                                                                                 
def is_interesting(f, interesting, not_interesting):
    if f.strip() == '':
        return False
    has_my_interest = any([i.search(f) for i in interesting])
    if has_my_interest:
        has_my_interest = not any([n.search(f) for n in not_interesting])
    return has_my_interest

def parse_departed_devs(dd_file, departed_devs):
    fil = open(dd_file, 'r')
    for line in fil:
        line = line.strip()
        line = safe_author_name(line)
        if not line:
            continue
        departed_devs.append(line)
    fil.close()


########NEW FILE########
__FILENAME__ = estimate_file_risk
"""
Based on the estimated unique knowledge per dev / group of devs, and
the probabilities supplied that each will be hit by a bus, calculate
the risk associated with each file.

Note that for joint probabilities we assume that probs are independent
that any pair or more of devs will all be hit by a bus, so these
calculations are extra iffy for friends, lovers, conjoined twins, or
carpoolers.
"""

import sys
import optparse

from common import FileData, safe_author_name

def get_bus_risk(dev, bus_risks, def_risk):
    if dev not in bus_risks:
        return def_risk
    else:
        return bus_risks[dev]

def estimate_file_risks(lines, bus_risks, def_bus_risk):
    """
    Estimate the risk in the file as:

    sum(knowledge unique to a group of 1 or more devs * the
    probability that all devs in the group will be hit by a bus)

    We use a simple joint probability and assume that all bus killings
    are independently likely.
    """
    for line in lines:
        fd = FileData(line)
        dev_risk = []
        for devs, shared in fd.dev_uniq:
            risk = shared
            for dev in devs:
                risk = float(risk) * get_bus_risk(dev, bus_risks, def_bus_risk)
            dev_risk.append((devs, risk))
        fd.dev_risk = dev_risk
        yield fd.as_line()

def parse_risk_file(risk_file, bus_risks):
    risk_f = open(risk_file, 'r')
    for line in risk_f:
        line = line.strip()
        if not line:
            continue
        dev, risk = line.split('=')
        dev = safe_author_name(dev)
        bus_risks[dev] = float(risk)
    risk_f.close()

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-b', '--bus-risk', dest='bus_risk', metavar='FLOAT', default=0.1,
                      help='The estimated probability that a dev will be hit by a bus in your analysis timeframe')
    parser.add_option('-r', '--risk-file', dest='risk_file', metavar='FILE',
                      help='File of dev=float lines (e.g. ejorgensen=0.4) with dev bus likelihoods')
    options, args = parser.parse_args()

    bus_risks = {}
    if options.risk_file:
        parse_risk_file(options.risk_file, bus_risks)
    
    for line in estimate_file_risks(sys.stdin, bus_risks, float(options.bus_risk)):
        print line

########NEW FILE########
__FILENAME__ = estimate_unique_knowledge
"""
Estimate the unique knowledge encpsulated in a single FileData line.

Currently uses a sequential strategy like so:

for each revision in the log:

* take the difference of the added and deleted lines of that revision.

* if the difference is positive, add those lines as knowledge for the
  dev that authored the revision.

* if the difference is negative, take the pct of the entire knowledge
  currently in the file represented by the number of negative lines
  and destroy that knowledge proportionally among all
  knowledge-holders.

* take the min of the added and deleted lines.  This represents the
  'churn'--lines that have changed.  Create (knowledge_churn_constant
  * churn) new lines worth of knowledge and assign it to the dev who
  authored the revision.  Take (churn - new_knowledge) lines of
  knowledge proportionally from all knowledge that dev doesn't share
  and move it to a shared account.
"""

import sys
import math
import copy

from optparse import OptionParser

from common import FileData

def sequential_create_knowledge(dev_uniq, dev, adjustment):
    """
    Create adjustment lines of knowledge in dev's account.

    dev is a list of developers who shared this knowledge (may be only
    one).
    """
    if dev not in dev_uniq:
        dev_uniq[dev] = 0
    dev_uniq[dev] += adjustment

def sequential_destroy_knowledge(adjustment, tot_knowledge, dev_uniq):
    """
    Find the percentage of tot_knowledge the adjustment represents and
    destroy that percent knowledge in all knowledge accounts.

    If tot_knowledge is 0, destroys nothing by definition.
    """
    pct_to_destroy = 0
    if tot_knowledge:
        pct_to_destroy = abs(float(adjustment)) / float(tot_knowledge)
    for devs in dev_uniq:
        k = dev_uniq[devs]
        k -= k * pct_to_destroy
        dev_uniq[devs] = k

def sequential_share_knowledge_group(dev, shared_key_exploded, pct_to_share, dev_uniq):
    """
    Share pct_to_share knowledge from all accounts that dev doesn't
    belong to into corresponding accounts dev does belong to.
    """
    old_shared_key = '\0'.join(shared_key_exploded)
    shared_key_exploded.append(dev)
    # make sure the dev names stay alphabetical
    shared_key_exploded.sort()
    new_shared_key = '\0'.join(shared_key_exploded)
    group_knowledge = dev_uniq[old_shared_key]
    amt_to_share = float(pct_to_share) * float(group_knowledge)
    dev_uniq[old_shared_key] -= amt_to_share
    if new_shared_key not in dev_uniq:
        dev_uniq[new_shared_key] = 0
    dev_uniq[new_shared_key] += amt_to_share

def sequential_distribute_shared_knowledge(dev, shared_knowledge, tot_knowledge, dev_uniq):
    """
    Share the percent of knowledge represented by shared_knowledge of
    tot_knowledge from all accounts that dev doesn't belong to into
    (possibly new) accounts that he does.
    """
    pct_to_share = 0
    if tot_knowledge:
        pct_to_share = float(shared_knowledge) / float(tot_knowledge)
    for shared_key in dev_uniq.keys():
        shared_key_exploded = shared_key.split('\0')
        if dev not in shared_key_exploded:
            sequential_share_knowledge_group(dev, shared_key_exploded, pct_to_share, dev_uniq)

def sequential_estimate_uniq(fd, knowledge_churn_constant):
    """
    Estimate the amounts of unique knowledge for each developer who
    has made changes to the path represented by this FileData, using a
    knowledge_churn_constant indicating what pct of churned lines to
    treat as new knowledge.

    Returns a list of [([dev1, dev2...], knowledge), ...], indicating
    the knowledge shared uniquely by the group of devs in the first
    field (there may be only dev in the list or many)
    """
    tot_knowledge = 0
    dev_uniq = {}

    for dev, added, deleted in fd.dev_experience:
        adjustment = added - deleted
        if adjustment > 0:
            sequential_create_knowledge(dev_uniq, dev, adjustment)
        elif adjustment < 0:
            sequential_destroy_knowledge(adjustment, tot_knowledge, dev_uniq)
        churn = min(added, deleted)
        if churn != 0:
            new_knowledge = float(churn) * knowledge_churn_constant
            shared_knowledge = float(churn) - new_knowledge
            sequential_distribute_shared_knowledge(dev, shared_knowledge, tot_knowledge, dev_uniq)
            sequential_create_knowledge(dev_uniq, dev, new_knowledge)            
        tot_knowledge += adjustment + (churn * knowledge_churn_constant)

    dev_uniq = [(shared_key.split('\0'), shared) for shared_key, shared in dev_uniq.items()]
    
    return dev_uniq, int(tot_knowledge)
 
def sequential(lines, model_args):
    """
    Entry point for the sequential algorithm.

    See the description in the file docs.

    Yields FileData objects as tsv lines, with dev_uniq and
    tot_knowledge fields filled in.
    """
    knowledge_churn_constant = float(model_args[0])
    for line in lines:
        fd = FileData(line)
        dev_uniq, tot_knowledge = sequential_estimate_uniq(fd, knowledge_churn_constant)
        fd.dev_uniq = dev_uniq
        fd.tot_knowledge = tot_knowledge
        yield fd.as_line()

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('--model', dest='model', metavar='MODEL[:MARG1[:MARG2]...]', default="sequential:0.1",
                      help='Knowledge model to use, with arguments.')
    options, args = parser.parse_args()

    model = options.model.split(':')
    model_func = locals()[model[0]]
    model_args = model[1:]
    
    for line in model_func(sys.stdin, model_args):
        print line

########NEW FILE########
__FILENAME__ = gen_file_stats
"""
Generate file stats for all interesting files in a project using git (default) or svn.

Run python gen_file_stats.py -h for options.

Prints FileData objects encoded as tsv lines to stdout.  Only the
fname, dev_experience and cnt_lines fields are filled in.
"""

import os
import re

from optparse import OptionParser

import git_file_stats

if __name__ == '__main__':
    usage = "usage: %prog [options] git_controlled_path[=project_name]"
    parser = OptionParser()
    parser.add_option('-i', '--interesting', metavar="REGEXP", dest='interesting', action='append',
                      help='Regular expression to determine which files should be included in calculations.  ' + \
                      'May be repeated, any match is sufficient to indicate interest. ' + \
                      'Defaults are \.java$ \.cs$ \.py$ \.c$ \.cpp$ \.h$ \.hpp$ \.pl$ \.rb$ \.sh$',
                      default=[])
    parser.add_option('-n', '--not-interesting', metavar="REGEXP", dest="not_interesting", action='append',
                      help="Regular expression to override interesting files.  May be repeated, any match is enough to squelch interest.")
    parser.add_option('--case-sensitive', dest='case_sensitive', action='store_true', default=False,
                      help='Use case-sensitive regepxs when finding interesting / uninteresting files (defaults to case-insensitive)')
    parser.add_option('--git-exe', dest='git_exe', default='/usr/bin/env git',
                      help='Path to the git exe (defaults to "/usr/bin/env git")')
    parser.add_option('--svn', dest='use_svn', default=False, action='store_true',
                      help='Use svn intead of git to generate file statistics.  This requires you to install pysvn.')

    options, args = parser.parse_args()

    if len(args) != 1:
        parser.error("You must pass a single git controlled path as the argument.")
        
    path_project = args[0].split('=')

    project = None

    # handle symlinked directories, which git doesn't like.
    # but don't use them for svn.
    if not options.use_svn:
        root = os.path.realpath(path_project[0])
    else:
        root = path_project[0]

    if len(path_project) > 1:
        project = path_project[1]
    else:
        # if they don't specify a project name, use the last piece of
        # the root.
        project = os.path.split(root)[1]

    interesting = options.interesting or r'\.java$ \.cs$ \.py$ \.c$ \.cpp$ \.h$ \.hpp$ \.pl$ \.rb$ \.sh$'.split(' ')
    not_interesting = options.not_interesting or []

    if options.case_sensitive:
        interesting = [re.compile(i) for i in interesting]
        not_interesting = [re.compile(n) for n in not_interesting]
    else:
        interesting = [re.compile(i, re.IGNORECASE) for i in interesting]
        not_interesting = [re.compile(n, re.IGNORECASE) for n in not_interesting]

    gen_stats = git_file_stats.gen_stats

    if options.use_svn:
        # only run the import if they actually try to use svn, since
        # we don't want to import pysvn and fail if we don't have to.
        import svn_file_stats
        gen_stats = svn_file_stats.gen_stats
    
    for line in gen_stats(root, project, interesting, not_interesting, options):
        if line.strip():
            print line

########NEW FILE########
__FILENAME__ = git_by_a_bus
#!/usr/bin/env python
"""
Driver for git by a bus.

Calls gen_file_stats.py, estimate_unique_knowledge.py,
estimate_file_risk.py, summarize.py in a chain, storing output from
each in output_dir/(basename).tsv.

To re-run only a portion of the calculations, you can remove all tsv
downstream and run again with the -c option (this is useful if you
want to manually remove some files from gen_file_stats.tsv, for
instance, rather than run the gen_file_stats.py step, which is slowest
by orders of magnitude).

Writes a summary found at output_dir/index.html.

Run as python git_by_a_bus.py -h for options.
"""

import sys
import os

from optparse import OptionParser
from subprocess import Popen
from string import Template

SCRIPT_PATH=os.path.dirname(os.path.realpath(__file__))
sys.path.append(SCRIPT_PATH)

def exit_with_error(err):
    print >> sys.stderr, "Error: " + err
    exit(1)

def read_projects_file(fname, paths_projects):
    try:
        fil = open(fname, 'r')
        paths_projects.extend([line.strip() for line in fil if line.strip()])
        fil.close()
        return True
    except IOError:
        return False

def output_fname_for(pyfile, output_dir):
    if not pyfile:
        return None
    return os.path.join(output_dir, os.path.splitext(os.path.basename(pyfile))[0] + '.tsv')

def run_chained(cmd_ts, python_cmd, output_dir, verbose):
    for cmd_t in cmd_ts:
        input_pyfile = cmd_t[0]
        output_pyfile = cmd_t[1]
        
        opts_args = ['']
        if len(cmd_t) > 2:
            opts_args = cmd_t[2]

        input_fname = output_fname_for(input_pyfile, output_dir)
        output_fname = output_fname_for(output_pyfile, output_dir)

        # don't re-run if the results exist
        if os.path.isfile(output_fname):
            if verbose:
                print >> sys.stderr, "%s EXISTS, SKIPPING" % output_fname
            continue

        input_f = None
        if input_fname:
            input_f = open(input_fname, 'r')
        output_f = open(output_fname, 'w')

        for opt_args in opts_args:
            cmd = [x for x in ' '.join([python_cmd, output_pyfile, opt_args]).split(' ') if x]
            if verbose:
                print >> sys.stderr, "Input file is: %s" % input_fname
                print >> sys.stderr, "Output file is: %s" % output_fname
                print >> sys.stderr, cmd
            cmd_p = Popen(cmd, stdin=input_f, stdout=output_f)
            cmd_p.communicate()
            
        if input_f:
            input_f.close()
        if output_f:
            output_f.close()

def main(python_cmd, paths_projects, options):
    output_dir = os.path.abspath(options.output or 'output')
    try:
        os.mkdir(output_dir)
    except:
        if not options.continue_last:
            exit_with_error("Output directory exists and you have not specified -c")

    risk_file_option = ''
    if options.risk_file:
        risk_file_option = '-r %s' % options.risk_file

    departed_dev_option = ''
    if options.departed_dev_file:
        departed_dev_option = '-d %s' % options.departed_dev_file

    interesting_file_option = ' '.join(["-i %s" % i for i in options.interesting])
    not_interesting_file_option = ' '.join(["-n %s" % n for n in options.not_interesting])
    case_sensitive_option = ''
    if options.case_sensitive:
        case_sensitive_option = '--case-sensitive'

    svn_option = ''
    if options.use_svn:
        svn_option = '--svn'

    git_exe_option = ''
    if options.git_exe:
        git_exe_option = "--git-exe %s" % options.git_exe

    model_option = "--model %s" % options.model

    # commands to chain together--the stdout of the first becomes the
    # stdin of the next.  You can find the output of gen_file_stats.py
    # in output_dir/gen_file_stats.tsv, and so on.
    cmd_ts = []
    cmd_ts.append([None, os.path.join(SCRIPT_PATH,'gen_file_stats.py'),
                   ['${interesting_file_option} ${not_interesting_file_option} ${case_sensitive_option} ${git_exe_option} ${svn_option} %s' % path_project \
                    for path_project in paths_projects]])
    cmd_ts.append([os.path.join(SCRIPT_PATH,'gen_file_stats.py'),
        os.path.join(SCRIPT_PATH,'estimate_unique_knowledge.py'), '${model_option}'])
    cmd_ts.append([os.path.join(SCRIPT_PATH,'estimate_unique_knowledge.py'),
        os.path.join(SCRIPT_PATH,'estimate_file_risk.py'), '-b ${bus_risk} ${risk_file_option}'])
    cmd_ts.append([os.path.join(SCRIPT_PATH,'estimate_file_risk.py'),
        os.path.join(SCRIPT_PATH,'summarize.py'), '${departed_dev_option} ${output_dir}'])
                  
    for cmd_t in cmd_ts:
        if len(cmd_t) > 2:
            opts_args = cmd_t[2]
            if not isinstance(opts_args, list):
                opts_args = [opts_args]
            opts_args = [Template(s).substitute(python_cmd=python_cmd,
                                                risk_file_option=risk_file_option,
                                                bus_risk=options.bus_risk,
                                                departed_dev_option=departed_dev_option,
                                                interesting_file_option=interesting_file_option,
                                                not_interesting_file_option=not_interesting_file_option,
                                                case_sensitive_option=case_sensitive_option,
                                                git_exe_option=git_exe_option,
                                                svn_option=svn_option,
                                                model_option=model_option,
                                                output_dir=output_dir) \
                         for s in opts_args]
            cmd_t[2] = opts_args

    run_chained(cmd_ts, python_cmd, output_dir, options.verbose)
    
if __name__ == '__main__':
    usage = """usage: %prog [options] [git_controlled_path1[=project_name1], git_controlled_path2[=project_name2],...]

               Analyze each git controlled path and create an html summary of orphaned / at-risk code knowledge.

               Paths must be absolute paths to local git-controlled directories (they may be subdirs in the git repo).
               
               Project names are optional and default to the last directory in the path.

               You may alternatively/additionally specify the list of paths/projects in a file with -p.

               Experimental svn support with --svn and an svn url for project path.
               """
    usage = '\n'.join([line.strip() for line in usage.split('\n')])

    parser = OptionParser(usage=usage)
    parser.add_option('-b', '--bus-risk', dest='bus_risk', metavar='FLOAT', default=0.1,
                      help='The default estimated probability that a dev will be hit by a bus in your analysis timeframe (defaults to 0.1)')
    parser.add_option('-r', '--risk-file', dest='risk_file', metavar='FILE',
                      help='File of dev=float lines (e.g. ejorgensen=0.4) with custom bus risks for devs')
    parser.add_option('-d', '--departed-dev-file', dest='departed_dev_file', metavar='FILE',
                      help='File listing departed devs, one per line')
    parser.add_option('-i', '--interesting', metavar="REGEXP", dest='interesting', action='append',
                      help='Regular expression to determine which files should be included in calculations.  ' + \
                      'May be repeated, any match is sufficient to indicate interest. ' + \
                      'Defaults are \.java$ \.cs$ \.py$ \.c$ \.cpp$ \.h$ \.hpp$ \.pl$ \.rb$', default=[])
    parser.add_option('-n', '--not-interesting', metavar="REGEXP", dest="not_interesting", action='append', default=[],
                      help="Regular expression to override interesting files.  May be repeated, any match is enough to squelch interest.")
    parser.add_option('--case-sensitive', dest='case_sensitive', action='store_true', default=False,
                      help='Use case-sensitive regepxs when finding interesting / uninteresting files (defaults to case-insensitive)')
    parser.add_option('-o', '--output', dest='output', metavar='DIRNAME', default='output',
                      help='Output directory for data files and html summary (defaults to "output"), error if already exists without -c')
    parser.add_option('-p', '--projects-file', dest='projects_file', metavar='FILE',
                      help='File of path[=project_name] lines, where path is an absoluate path to the git-controlled ' + \
                      'directory or svn url to analyze and project_name is the name to use in the output summary (project_name defaults to ' + \
                      'the last directory name in the path)')
    parser.add_option('-c', '--continue-last', dest='continue_last', default=False, action="store_true",
                      help="Continue last run, using existing output files and recreating missing.  You can remove tsv files " + \
                      "in the output dir and modify others to clean up bad runs.")
    parser.add_option('-v', '--verbose', dest='verbose', default=False, action="store_true", help="Print debugging info")
    parser.add_option('--python-exe', dest='python_exe', default='/usr/bin/env python',
                      help='Path to the python interpreter (defaults to "/usr/bin/env python")')
    parser.add_option('--git-exe', dest='git_exe', help='Path to the git exe (defaults to "/usr/bin/env git")')
    parser.add_option('--svn', dest='use_svn', default=False, action='store_true',
                      help='Use svn intead of git to generate file statistics.  This requires you to install pysvn in your PYTHONPATH.')
    parser.add_option('--model', dest='model', metavar='MODEL[:MARG1[:MARG2]...]', default='sequential:0.1',
                      help='Knowledge model to use, with arguments.  Right now only sequential is supported.')

    options, paths_projects = parser.parse_args()

    if options.projects_file:
        if not read_projects_file(options.projects_file, paths_projects):
            exit_with_error("Could not read projects file %s" % options.projects_file)

    if not paths_projects:
        parser.error('No paths/projects!  You must either specify paths/projects on the command line and/or in a file with the -p option.')
    
    main(options.python_exe, paths_projects, options)

########NEW FILE########
__FILENAME__ = git_file_stats
"""
Module to generate file stats using git.

The only function here intended for external consumption is gen_stats.

Output of gen_stats should be exactly the same as the output of
git_file_stats.gen_stats, but in practice they may differ by a line or
two (appears to be whitespace handling, perhaps line endings?)
"""

import sys
import os
import re

from subprocess import Popen, PIPE

from common import is_interesting, FileData, safe_author_name
    
def gen_stats(root, project, interesting, not_interesting, options):
    """
    root: the path a local, git controlled-directory that is the root
    of this project

    project: the name of the project

    interesting: regular expressions that indicate an interesting path
    if they match

    not_interesting: regular expressions that trump interesting and
    indicate a path is not interesting.

    options: from gen_file_stats.py's main, currently only uses
    git_exe.

    Yields FileData objects encoded as tsv lines.  Only the fname,
    dev_experience and cnt_lines fields are filled in.
    """
    git_exe = options.git_exe

    # since git only works once you're in a git controlled path, we
    # need to get into one of those...
    prepare(root, git_exe)

    files = git_ls(root, git_exe)

    for f in files:
        if is_interesting(f, interesting, not_interesting):
            dev_experience = parse_dev_experience(f, git_exe)
            if dev_experience:
                fd = FileData(':'.join([project, f]))
                fd.dev_experience = dev_experience
                fd.cnt_lines = count_lines(f)
                fd_line = fd.as_line()
                if fd_line.strip():
                    yield fd_line


def count_lines(f):
    fil = open(f, 'r')
    count = 0
    for line in fil:
        count += 1
    fil.close()
    return count

def parse_experience(log):
    """
    Parse the dev experience from the git log.
    """
    # list of tuple of shape [(dev, lines_add, lines_removed), ...]
    exp = []

    # entry lines were zero separated with -z
    entry_lines = log.split('\0')

    current_entry = []
    
    for entry_line in entry_lines:
        if not entry_line.strip():
            # blank entry line marks the end of an entry, we're ready to process
            local_entry = current_entry
            current_entry = []
            if len(local_entry) < 2:
                print >> sys.stderr, "Weird entry, cannot parse: %s\n-----" % '\n'.join(local_entry)
                continue
            author, changes = local_entry[:2]
            author = safe_author_name(author)
            try:
                changes_split = re.split(r'\s+', changes)
                # this can be two fields if there were file renames
                # detected, in which case the file names are on the
                # following entry lines, or three fields (third being
                # the filename) if there were no file renames
                lines_added, lines_removed = changes_split[:2]
                lines_added = int(lines_added)
                lines_removed = int(lines_removed)

                # don't record revisions that don't have any removed or
                # added lines...they mean nothing to our algorithm
                if lines_added or lines_removed:
                    exp.append((author, lines_added, lines_removed))
            except ValueError:
                print >> sys.stderr, "Weird entry, cannot parse: %s\n-----" % '\n'.join(local_entry)                    
                continue
        else:
            # continue to aggregate the entry
            lines = entry_line.split('\n')
            current_entry.extend([line.strip() for line in lines])

    # we need the oldest log entries first.
    exp.reverse()
    return exp
            
def parse_dev_experience(f, git_exe):
    """
    Run git log and parse the dev experience out of it.
    """
    # -z = null byte separate logs
    # -w = ignore all whitespace when calculating changed lines
    # --follow = follow file history through renames
    # --numstat = print a final ws separated line of the form 'num_added_lines num_deleted_lines file_name'
    # --format=format:%an = use only the author name for the log msg format
    git_cmd = ("%s log -z -w --follow --numstat --format=format:%%an" % git_exe).split(' ')
    git_cmd.append(f)
    git_p = Popen(git_cmd, stdout=PIPE)
    (out, err) = git_p.communicate()
    return parse_experience(out)

def git_ls(root, git_exe):
    """
    List the entire tree that git is aware of in this directory.
    """
    # --full-tree = allow absolute path for final argument (pathname)
    # --name-only = don't show the git id for the object, just the file name
    # -r = recurse
    git_cmd = ('%s ls-tree --full-tree --name-only -r HEAD' % git_exe).split(' ')
    git_cmd.append(root)
    git_p = Popen(git_cmd, stdout=PIPE)
    files = git_p.communicate()[0].split('\n')
    return files

def git_root(git_exe):
    """
    Given that we have chdir'd into a Git controlled dir, get the git
    root for purposes of adjusting paths.
    """
    git_cmd = ('%s rev-parse --show-toplevel' % git_exe).split(' ')
    git_p = Popen(git_cmd, stdout=PIPE)
    return git_p.communicate()[0].strip()

def prepare(root, git_exe):
    # first we have to get into the git repo to make the git_root work...
    os.chdir(root)
    # then we can change to the git root
    os.chdir(git_root(git_exe))

########NEW FILE########
__FILENAME__ = summarize
"""
Hackish script to generate summary html for file risk data.

Puts the results in output_dir/{devs,files,projects}, with an index at
output_dir/index.html
"""

import sys
import os
import math
import hashlib

from optparse import OptionParser

from common import FileData, parse_departed_devs

# we cut off any value below this as just noise.
GLOBAL_CUTOFF = 10

class Dat(object):
    """
    A single piece of data for the aggregate routines to aggregate,
    using the a_* fields to grab the appropriate keys.
    """
    
    def __init__(self, valtype, file_data, dev, val):
        """
        valtype: arbitrary string indicating the type of the data

        file_data: the FileData object

        dev: the group of 1 or more developers associated with this
        value

        val: the value
        """
        self.valtype = valtype
        self.file_data = file_data
        self.dev = dev
        self.val = val

    def __repr__(self):
        return "valtype: %s, file_data: %s, dev: %s, val: %s " % (self.valtype,
                                                                  self.file_data,
                                                                  self.dev,
                                                                  str(self.val))

# a_* methods.
#
# Used as keys to identify an aggregate (e.g. an aggregate by dev, valtype, and project would be filed under:
#
# (a_dev, a_valtype, a_project)
#
# Then invoked on the aggregate hash to navigate to the appropriate
# destinations / sources of values.

def a_unique(dat):
    return 'unique'

def a_orphaned(dat):
    return 'orphaned'

def a_dev(dat):
    if isinstance(dat.dev, list):
        return ' and '.join(dat.dev)
    else:
        return dat.dev

def a_project(dat):
    return dat.file_data.project

def a_fname(dat):
    return dat.file_data.fname

def a_valtype(dat):
    return dat.valtype

def agg(path, diction, dat):
    """
    dat has the value to aggregate and the data associated with the value (FileData, devs)

    path is a series of a_* keys return values to walk to the right
    point in the aggregation.

    diction is the dictionary to aggregate the value into
    """
    
    orig = diction
    # walk the dictionary to the last key
    for p in path[:-1]:
        k = p(dat)
        if k not in diction:
            diction[k] = {}
        diction = diction[k]

    # aggregate the val
    last_p = path[-1]
    last_k = last_p(dat)
    if last_k not in diction:
        diction[last_k] = 0
    diction[last_k] += dat.val

def agg_all(aggs, dat):
    for path, diction in aggs.items():
        agg(path, diction, dat)

def create_agg(aggs, path):
    aggs[path] = {}

def split_out_dev_vals(dev_vals, departed_devs):
    """
    Split the values in dev_vals into those that are held by only
    non-departed devs and those held by departed devs.

    If value held by departed devs can be aggregated into value held
    by non-departed devs, do so.

    return two lists: the first the values held by non-departed devs,
    the second the values held by departed devs.
    """

    def is_departed(dev):
        return dev in departed_devs

    def is_not_departed(dev):
        return dev not in departed_devs

    def add_dev_val_lookup(devs, lookup, val):
        devs.sort()
        lookup_str = '\0'.join(devs)
        if lookup_str not in lookup:
            lookup[lookup_str] = 0
        lookup[lookup_str] += val
    
    lookup = dict([('\0'.join(devs), val) for (devs, val) in dev_vals])
    departed_lookup = {}
    
    for devs, val in dev_vals:
        present = filter(is_not_departed, devs)
        departed = filter(is_departed, devs)
        if departed:
            departed.sort()                            
            if present:
                # some val has dropped out with departed folks, it
                # needs to be rolled up into the groups of devs who
                # are in the group and still present
                add_dev_val_lookup(present, lookup, val)
            else:
                # the val has nowhere to go...all potential aggregates
                # are gone.  we put it in the departed section to
                # return it.
                add_dev_val_lookup(departed, departed_lookup, val)
            lookup_str = '\0'.join(devs)
            if lookup_str in lookup:
                del lookup[lookup_str]
                
    return [(devs_lookup.split('\0'), val) for devs_lookup, val in lookup.items()], \
           [(dep_lookup.split('\0'), val) for dep_lookup, val in departed_lookup.items()]

def summarize(lines, departed_devs):
    """
    Aggregate the FileData in lines, considering all devs in
    departed_devs to be hit by a bus.
    """
    
    aggs = {}

    # aggregate by valtype and our top-level objects, used by the
    # index page.
    create_agg(aggs, (a_valtype, a_dev))
    create_agg(aggs, (a_valtype, a_project))
    create_agg(aggs, (a_valtype, a_fname))

    # aggregates by project for the projects pages
    create_agg(aggs, (a_project, a_valtype, a_fname))
    create_agg(aggs, (a_project, a_valtype, a_dev))

    # aggregates by dev group of 1 or more for the devs pages.
    create_agg(aggs, (a_dev, a_valtype, a_fname))
    create_agg(aggs, (a_dev, a_valtype, a_project))

    # fname aggregate for the files pages
    create_agg(aggs, (a_fname, a_valtype, a_dev))

    for line in lines:
        fd = FileData(line)

        # we don't do anything with the risk represented by departed
        # devs...the risk has already turned out to be real and the
        # knowledge is gone.
        dev_risk, _ignored = split_out_dev_vals(fd.dev_risk, departed_devs)
        for devs, risk in dev_risk:
            agg_all(aggs, Dat('risk', fd, devs, risk))
        dev_uniq, dev_orphaned = split_out_dev_vals(fd.dev_uniq, departed_devs)
        for devs, uniq in dev_uniq:
            agg_all(aggs, Dat('unique knowledge', fd, devs, uniq))
            # hack: to get the devs with most shared knowledge to show
            # up on the devs pages, explode the devs and aggregate
            # them pairwise here under a different valtype that only
            # the devs pages will use
            for dev1 in devs:
                for dev2 in devs:
                    # don't double count the similarity
                    if dev1 < dev2:
                        agg_all(aggs, Dat('shared knowledge (devs still present)', fd, [dev1, dev2], uniq))
        # if there is knowledge unique to groups of 1 or more devs who
        # are all departed, this knowledge is orphaned.
        for devs, orphaned in dev_orphaned:
            agg_all(aggs, Dat('orphaned knowledge', fd, devs, orphaned))

    return aggs

def tupelize(agg, tuples_and_vals, key_list):
    for k, v in agg.items():
        loc_key = list(key_list)
        loc_key.append(k)
        if not isinstance(v, dict):
            tuples_and_vals.append((tuple(loc_key), v))
        else:
            tupelize(v, tuples_and_vals, loc_key)

def sort_agg(agg, desc):
    tuples_and_vals = []
    tupelize(agg, tuples_and_vals, [])
    tuples_and_vals = [(t[1], t) for t in tuples_and_vals]
    tuples_and_vals.sort()
    if desc:
        tuples_and_vals.reverse()
    tuples_and_vals = [t[1] for t in tuples_and_vals]
    return tuples_and_vals

def by_valtype_html(valtype, nouns, noun, linker, limit):
    html = []
    limit_str = ''
    if limit:
        limit_str = 'Top %d ' % limit
    html.append("<h3>%s%s by highest estimated %s</h3>" % (limit_str, noun, valtype))
    html.append("<table style=\"width: 80%\">")
    html.append("<tr><th>%s</th><th>Total estimated %s</th></tr>" % (noun, valtype))
    max_value = max([n[1] for n in nouns])
    for t, val in nouns:
        if round(val) > GLOBAL_CUTOFF:
            vals_t = (linker(t[0]),
                      int(round(val)),
                      math.ceil(100 * (val / max_value)))
            html.append("<tr><td>%s (%d)</td><td style=\"width: 80%%;\"><div style=\"background-color: LightSteelBlue; width: %d%%;\">&nbsp;</div></td></tr>" % vals_t)
    html.append("</table>") 
    return html

def project_fname(project):
    return os.path.join('projects', "%s.html" % project)

def project_linker(project):
    return "<a href=\"%s\">%s</a>" % (project_fname(project), project)        

def fname_fname(fname):
    return os.path.join('files', "%s.html" % fname.replace(':', '__').replace(os.path.sep, '__'))

def fname_linker(fname):
    return "<a href=\"%s\">%s</a>" % (fname_fname(fname), fname)    

def dev_fname(dev):
    return os.path.join('devs', "%s.html" % hashlib.md5(dev).hexdigest())

def dev_linker(dev):
    return "<a href=\"%s\">%s</a>" % (dev_fname(dev), dev)

def parent_linker(fnamer):
    def f(to_link):
        return "<a href=\"%s\">%s</a>" % (os.path.join('..', fnamer(to_link)), to_link)        
    return f

def summarize_by_valtype(agg_by_single, noun, linker):
    return summarize_top_by_valtype(agg_by_single, noun, linker, None)

def summarize_top_by_valtype(agg_by_single, noun, linker, limit):
    html = []
    for valtype, nouns in agg_by_single.items():
        nouns = sort_agg(nouns, True)
        if limit:
            nouns = nouns[:limit]
        html.extend(by_valtype_html(valtype, nouns, noun, linker, limit))
    return html

def add_global_explanation(html):
    html.append('<p>Note: values smaller than %d have been truncated in the interest of space.</p>' % GLOBAL_CUTOFF)
    html.append('<p>Note: the scale of the bars is relative only within, not across, tables.</p>')

def create_index(aggs, output_dir):
    html = []
    html.append("<html>\n<head><title>Git By a Bus Summary Results</title></head>\n<body>")
    html.append("<h1>Git by a Bus Summary Results</h1>")
    add_global_explanation(html)
    html.extend(summarize_top_by_valtype(aggs[(a_valtype, a_project)], 'Projects', project_linker, 100))
    html.extend(summarize_top_by_valtype(aggs[(a_valtype, a_dev)], 'Devs', dev_linker, 100))
    html.extend(summarize_top_by_valtype(aggs[(a_valtype, a_fname)], 'Files', fname_linker, 100))
    html.append("</body>\n</html>")
    outfil = open(os.path.join(output_dir, 'index.html'), 'w')
    outfil.write('\n'.join(html))
    outfil.close()

def create_detail_page(detail, noun, valtype_args, fname, custom_lines_f):
    html = []
    html.append("<html>\n<head><title>Git By a Bus Summary Results for %s: %s</title></head>\n<body>" % (noun, detail))
    html.append("<p><a href=\"../index.html\">Index</a></p>")
    html.append("<h1>Git by a Bus Summary Results for %s: %s</h1>" % (noun, detail))
    add_global_explanation(html)
    if custom_lines_f:
        html.extend(custom_lines_f(detail, noun, valtype_args, fname))
    for vtarg in valtype_args:
        html.extend(summarize_top_by_valtype(vtarg[0], vtarg[1], vtarg[2], vtarg[3]))
    html.append("</body>\n</html>")
    outfil = open(fname, 'w')
    outfil.write('\n'.join(html))
    outfil.close()

def create_detail_pages(output_dir, subdir, details, noun, detail_fname, aggs_with_nouns, custom_lines_f = None):
    try:
        os.mkdir(os.path.join(output_dir, subdir))
    except:
        pass

    for detail in details:
        outfile_name = os.path.join(output_dir, detail_fname(detail))
        vt_args = [(agg[detail], nouns, linker, None) for agg, nouns, linker in aggs_with_nouns if detail in agg]
        create_detail_page(detail, noun, vt_args, outfile_name, custom_lines_f)

def create_project_pages(aggs, output_dir):
    dev_agg = aggs[(a_project, a_valtype, a_dev)]
    fname_agg = aggs[(a_project, a_valtype, a_fname)]
    projects = fname_agg.keys()
    create_detail_pages(output_dir, 'projects', projects, 'Project', project_fname, [(dev_agg, 'Devs', parent_linker(dev_fname)),                                                                                                                     (fname_agg, 'Files', parent_linker(fname_fname))])



def create_dev_pages(aggs, output_dir, departed_devs):

    # callback to pass into create_detail_pages to make
    #
    # * the links to individual devs making up a group and
    #
    # * the table of devs with most shared knowledge for individual
    # devs
    def dev_custom(devs, noun, valtype_args, fname):
        html = []
        linker = parent_linker(dev_fname)
        the_devs = devs.split(' and ')
        if len(the_devs) > 1:
            html.append("<p>Common knowledge / risk for devs:</p>\n<ul>")
            for the_dev in the_devs:
                html.append("<li>%s</li>\n" % linker(the_dev))
            html.append("</ul>")
        elif len(the_devs) == 1:
            # do a little custom aggregation to show who we share most with
            the_dev = the_devs[0]
            if the_dev in departed_devs:
                return html
            agg = aggs[(a_valtype, a_dev)]
            shared_k_agg = agg.get('shared knowledge (devs still present)',{})
            top_shares = {}
            for dev_devs, shared in shared_k_agg.items():
                the_dev_devs = dev_devs.split(' and ')
                if len(the_dev_devs) != 2:
                    continue
                dev1, dev2 = the_dev_devs
                if dev1 == the_dev:
                    top_shares[dev2] = shared
                elif dev2 == the_dev:
                    top_shares[dev1] = shared
            top_shares = [(shared, odev) for odev, shared in top_shares.items()]
            top_shares.sort()
            top_shares.reverse()
            top_shares = [([ts[1]], ts[0]) for ts in top_shares]
            if top_shares:
                html.extend(by_valtype_html('shared', top_shares, 'devs', parent_linker(dev_fname), 10))
                        
        return html

    project_agg = aggs[(a_dev, a_valtype, a_project)]
    fname_agg = aggs[(a_dev, a_valtype, a_fname)]
    devs = fname_agg.keys()
    create_detail_pages(output_dir, 'devs', devs, 'Dev', dev_fname, [(project_agg, 'Projects', parent_linker(project_fname)),
                                                                     (fname_agg, 'Files', parent_linker(fname_fname))], dev_custom)

def create_file_pages(aggs, output_dir):
    dev_agg = aggs[(a_fname, a_valtype, a_dev)]
    fnames = dev_agg.keys()
    create_detail_pages(output_dir, 'files', fnames, 'File', fname_fname, [(dev_agg, 'Devs', parent_linker(dev_fname))])

def add_dev_dev(dev_dev, dev1, dev2, diff):
    if dev1 not in dev_dev:
        dev_dev[dev1] = {}
    dev_dev[dev1][dev2] = diff

def read_dev_x_cmp(x_cmp_fname, make_sym):
    dev_dev = {}
    fil = open(x_cmp_fname, 'r')
    for line in fil:
        line = line.strip()
        dev1, dev2, diff = line.split('\t')
        diff = float(diff)
        add_dev_dev(dev_dev, dev1, dev2, diff)
        if make_sym:
            add_dev_dev(dev_dev, dev2, dev1, diff)        
    fil.close()
    return dev_dev

def create_summary(lines, output_dir, departed_devs):
    aggs = summarize(lines, departed_devs)
    create_index(aggs, output_dir)
    create_project_pages(aggs, output_dir)
    create_dev_pages(aggs, output_dir, departed_devs)
    create_file_pages(aggs, output_dir)
    
if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-d', '--departed-dev-file', dest='departed_dev_file', metavar='FILE',
                      help='File listing departed devs, one per line')
    options, args = parser.parse_args()

    departed_devs = []
    if options.departed_dev_file:
        parse_departed_devs(options.departed_dev_file, departed_devs)

    create_summary(sys.stdin, args[0], departed_devs)

    # print to the tsv so if folks look there they get redirected
    # correctly
    print "Summary is available at %s/index.html" % args[0]

########NEW FILE########
__FILENAME__ = svn_file_stats
"""
Hackish module to use svn for generating file stats.

The only function here intended for external consumption is gen_stats.

Output of gen_stats should be exactly the same as the output of
git_file_stats.gen_stats, but in practice they may differ by a line or
two (appears to be whitespace handling, perhaps line endings?)
"""

import sys
import os
import re

import pysvn

from common import is_interesting, FileData, safe_author_name

def gen_stats(root, project, interesting, not_interesting, options):
    """
    root: the root svn url of the project we are generating stats for
    (does not need to be the root of the svn repo).  Must be a url,
    not a checkout path.

    project: the project identifier.

    interesting: regular expressions that indicate an interesting path
    if they match

    not_interesting: regular expressions that trump interesting and
    indicate a path is not interesting.

    options: currently unused, options from gen_file_stats.py's main.

    Yields FileData objects encoded as tsv lines.  Only the fname,
    dev_experience and cnt_lines fields are filled in.
    """
    client = pysvn.Client()

    # we need the repo root because the paths returned by svn ls are relative to the repo root,
    # not our project root
    repo_root = client.root_url_from_path(root)

    interesting_fs = [f[0].repos_path for f in client.list(root, recurse=True) if
                      is_interesting(f[0].repos_path, interesting, not_interesting) and f[0].kind == pysvn.node_kind.file]

    for f in interesting_fs:
        dev_experience = parse_dev_experience(f, client, repo_root)
        if dev_experience:
            fd = FileData(':'.join([project, f]))
            # don't take revisions that are 0 lines added and 0 removed, like properties
            fd.dev_experience = [(dev, added, removed) for dev, added, removed in dev_experience if added or removed]
            fd.cnt_lines = count_lines(f, client, repo_root)
            fd_line = fd.as_line()
            if fd_line.strip():
                yield fd_line

def parse_dev_experience(f, client, repo_root):
    """
    f: a path relative to repo_root for a file from whose log we want
    to parse dev experience.

    client: the pysvn client

    repo_root: the root of the svn repository
    """
    # a list of tuples of form (dev, added_lines, deleted_lines), each
    # representing one commit
    dev_experience = []

    # a list of tuples with the paths / revisions we want to run diffs
    # on to reconstruct dev experience
    comps_to_make = []

    # since the name of the file can change through its history due to
    # moves, we need to keep the most recent one we're looking for
    fname_to_follow = f

    added_line_re = re.compile(r'^\+')
    
    # strict_node_history=False: follow copies
    #
    # discover_changed_paths: make the data about copying available in the changed_paths field
    for log in client.log("%s%s" %(repo_root, f), strict_node_history=False, discover_changed_paths=True):
        cp = log.changed_paths

        # even though we are only asking for the log of a single file,
        # svn gives us back all changed paths for that revision, so we
        # have to look for the right one
        for c in cp:
            if fname_to_follow == c.path:
                # since we're going back in time with the log process,
                # a copyfrom_path means we need to follow the old file
                # from now on.
                if c.copyfrom_path:
                    fname_to_follow = c.copyfrom_path                    
                comps_to_make.append((c.path, log.revision, log.author))
                break

    # our logic needs oldest logs first
    comps_to_make.reverse()

    # for the first revision, every line is attributed to the first
    # author as an added line
    txt = client.cat("%s%s" % (repo_root, comps_to_make[0][0]),
                     comps_to_make[0][1])

    exp = txt.count('\n')
    if not txt.endswith('\n'):
        exp += 1
    dev_experience.append((comps_to_make[0][2], exp, 0))

    # for all the other entries, we must diff between revisions to
    # find the number and kind of changes
    for i in range(len(comps_to_make) - 1):
        old_path = "%s%s" % (repo_root, comps_to_make[i][0])
        old_rev = comps_to_make[i][1]

        new_path = "%s%s" % (repo_root, comps_to_make[i + 1][0])
        new_rev = comps_to_make[i + 1][1]
        
        author = comps_to_make[i + 1][2]
        
        try:
            diff = client.diff('.',
                               old_path,
                               revision1=old_rev,
                               url_or_path2=new_path,
                               revision2=new_rev,
                               diff_options=['-w'])
            diff = diff.split('\n')
            ind_dbl_ats = 0
            for i, line in enumerate(diff):
                if line.startswith('@@'):
                    ind_dbl_ats = i
                    break
            added = 0
            removed = 0
            for line in diff[ind_dbl_ats:]:
                if line.startswith('+'):
                    added += 1
                if line.startswith('-'):
                    removed += 1
            dev_experience.append((safe_author_name(author), added, removed))
        except:
            # on one occasion I saw a non-binary item that existed in
            # the filesystem with svn ls but errored out with a diff
            # against that revision.  Note the error and proceed.
            print >> sys.stderr, "Error diffing %s %s and %s %s: " % \
                  (old_path, str(old_rev), new_path, str(new_rev)), sys.exc_info()[0]
        
    return dev_experience

def count_lines(f, client, repo_root):
    """
    Count the lines in the file located at path f under repo root.
    """
    txt = client.cat("%s%s" % (repo_root, f))
    lines = txt.count('\n')
    if not txt.endswith('\n'):
        lines += 1
    return lines

    

    

########NEW FILE########
