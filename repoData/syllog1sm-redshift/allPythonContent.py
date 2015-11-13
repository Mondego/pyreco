__FILENAME__ = fabfile
from fabric.api import local, run, lcd, cd, env
from fabric.operations import get, put
from fabric.contrib.files import exists
from pathlib import Path
import time
import re
from math import sqrt
from os.path import join as pjoin
from os import listdir
from StringIO import StringIO
import scipy.stats

from itertools import combinations

env.use_ssh_config = True

from _paths import REMOTE_REPO, REMOTE_CONLL, REMOTE_MALT, REMOTE_STANFORD, REMOTE_PARSERS
from _paths import REMOTE_SWBD
from _paths import LOCAL_REPO, LOCAL_MALT, LOCAL_STANFORD, LOCAL_PARSERS
from _paths import HOSTS, GATEWAY

env.hosts = HOSTS
env.gateway = GATEWAY


def recompile(runner=local):
    clean()
    make()

def clean():
    with lcd(str(LOCAL_REPO)):
        local('python setup.py clean --all')

def make():
    with lcd(str(LOCAL_REPO)):
        local('python setup.py build_ext --inplace')

def qstat():
    run("qstat -na | grep mhonn")


def deploy():
    clean()
    make()
    with cd(str(REMOTE_REPO)):
        run('git pull')


def test1k(model="baseline", dbg=False):
    with lcd(str(LOCAL_REPO)):
        local(_train('~/work_data/stanford/1k_train.txt',  '~/work_data/parsers/tmp',
                    debug=dbg))
        local(_parse('~/work_data/parsers/tmp', '~/work_data/stanford/dev_auto_pos.parse',
                     '/tmp/parse', gold=True))

        
def beam(name, k=8, n=1, size=0, train_alg="static", feats="zhang", tb='wsj'):
    size = int(size)
    k = int(k)
    n = int(n)
    use_edit = False
    if tb == 'wsj':
        data = str(REMOTE_STANFORD)
        train_name = 'train.txt'
        eval_pos = 'devi.txt'
        eval_parse = 'devr.txt'
    elif tb == 'swbd':
        data = str(REMOTE_SWBD)
        train_name = 'sw.mwe.train'
        eval_pos = 'sw.mwe.devi'
        eval_parse = 'sw.mwe.devr'
        if train_alg != 'static':
            use_edit = True

    exp_dir = str(REMOTE_PARSERS)
    train_n(n, name, exp_dir,
            data, k=k, i=15, feat_str=feats, 
            n_sents=size, train_name=train_name, train_alg=train_alg,
            use_edit=use_edit, dev_names=(eval_pos, eval_parse))
 

def conll_table(name):
    langs = ['arabic', 'basque', 'catalan', 'chinese', 'czech', 'english',
            'greek', 'hungarian', 'italian', 'turkish']
    systems = ['bl', 'exp']
    for lang in langs:
        bl_accs = []
        exp_accs = []
        for system, accs in zip(systems, ([bl_accs, exp_accs])):

            for i in range(20):
                uas_loc = pjoin(str(REMOTE_PARSERS), 'conll', lang, system,
                                str(i), 'dev', 'acc')
                try:
                    text = run('cat %s' % uas_loc, quiet=True).stdout
                    accs.append(_get_acc(text, score='U'))
                except:
                    continue
        if bl_accs:
            bl_n, bl_acc, stdev = _get_stdev(bl_accs)
        if exp_accs:
            exp_n, exp_acc, stdev = _get_stdev(exp_accs)
        if bl_n == exp_n:
            z, p = scipy.stats.wilcoxon(bl_accs, exp_accs)
        else:
            p = 1.0

        print lang, fmt_pc(bl_acc), fmt_pc(exp_acc), '%.4f' % p

def fmt_pc(pc):
    if pc < 1:
        pc *= 100
    return '%.2f' % pc


def conll(name, lang, n=20, debug=False):
    """Run the 20 seeds for the baseline and experiment conditions for a conll lang"""
    data = str(REMOTE_CONLL)
    repo = str(REMOTE_REPO)
    eval_pos = '%s.test.pos' % lang
    eval_parse = '%s.test.malt' % lang
    train_name = '%s.train.proj.malt' % lang
    n = int(n)
    if debug == True: n = 2
    for condition, arg_str in [('bl', ''), ('exp', '-r -d')]:
        for i in range(n):
            exp_name = '%s_%s_%s_%d' % (name, lang, condition, i)
            model = pjoin(str(REMOTE_PARSERS), name, lang, condition, str(i))
            run("mkdir -p %s" % model)
            train_str = _train(pjoin(data, train_name), model, k=0, i=15,
                               add_feats=False, train_alg='online', seed=i, label="conll",
                               args=arg_str)
            parse_str = _parse(model, pjoin(data, eval_pos), pjoin(model, 'dev'), k=0)
            eval_str = _evaluate(pjoin(model, 'dev', 'parses'), pjoin(data, eval_parse))
            grep_str = "grep 'U:' %s >> %s" % (pjoin(model, 'dev', 'acc'),
                                               pjoin(model, 'dev', 'uas')) 
            script = _pbsify(repo, (train_str, parse_str, eval_str, grep_str))
            if debug:
                print script
                continue
            script_loc = pjoin(repo, 'pbs', exp_name)
            with cd(repo):
                put(StringIO(script), script_loc)
                run('qsub -N %s_bl %s' % (exp_name, script_loc))
 

def ngram_add1(name, k=8, n=1, size=10000):
    import redshift.features
    n = int(n)
    k = int(k)
    size = int(size)
    data = str(REMOTE_MALT)
    repo = str(REMOTE_REPO)
    train_name = '0.train'
    eval_pos = '0.testi' 
    eval_parse = '0.test'
    arg_str = 'full'
    train_n(n, 'base', pjoin(str(REMOTE_PARSERS), name), data, k=k, i=15,
            feat_str="full", train_alg='max', label="NONE", n_sents=size,
            ngrams=0, train_name=train_name)
    tokens = 'S0,N0,N1,N2,N0l,N0l2,S0h,S0h2,S0r,S0r2,S0l,S0l2'.split(',')
    ngram_names = ['%s_%s' % (p) for p in combinations(tokens, 2)]
    ngram_names.extend('%s_%s_%s' % (p) for p in combinations(tokens, 3))
    kernel_tokens = redshift.features.get_kernel_tokens()
    ngrams = list(combinations(kernel_tokens, 2))
    ngrams.extend(combinations(kernel_tokens, 3))
    n_ngrams = len(ngrams)
    n_models = n
    for ngram_id, ngram in list(sorted(enumerate(ngrams))):
        ngram_name = ngram_names[ngram_id]
        train_n(n, '%d_%s' % (ngram_id, ngram_name), pjoin(str(REMOTE_PARSERS), name),
                data, k=k, i=15, feat_str="full", train_alg='max', label="NONE",
                n_sents=size, ngrams='_'.join([str(i) for i in ngram]),
                train_name=train_name, dev_names=(eval_pos, eval_parse))
        n_models += n
        # Sleep 5 mins after submitting 50 jobs
        if n_models > 100:
            time.sleep(350)
            n_models = 0


def combine_ngrams(name, k=8, n=5, size=10000):
    def make_ngram_str(ngrams):
        strings = ['_'.join([str(name_to_idx[t]) for t in ngram.split('_')]) for ngram in ngrams]
        return ','.join(strings)
    n = int(n)
    k = int(k)
    size = int(size)
    data = str(REMOTE_MALT)
    repo = str(REMOTE_REPO)
    train_name = '0.train'
    eval_pos = '0.testi' 
    eval_parse = '0.test'
 
    import redshift.features
    kernel_tokens = redshift.features.get_kernel_tokens()
    token_names = 'S0 N0 N1 N2 N0l N0l2 S0h S0h2 S0r S0r2 S0l S0l2'.split()
    name_to_idx = dict((tok, idx) for idx, tok in enumerate(token_names))
    ngrams = ['S0_S0r_S0l', 'S0_S0h_S0r', 'S0_N1_S0r', 'S0_N0l_S0h', 'S0_N0l_S0r',
            'S0_N0_S0r2', 'S0_N0l2_S0r', 'S0_S0h_S0l', 'S0_N0l2_S0h', 'S0_N0_S0h',
            'S0_S0r_S0l2', 'S0_N0_S0r', 'S0_S0r_S0r2', 'S0_N0_N0l2', 'S0_N1_N0l',
            'S0_N0_N0l', 'S0_S0h_S0r2', 'S0_N1_S0h', 'N0_N0l_S0r2', 'S0_N1_S0r2',
            'N0_N0l_S0r', 'S0_N1_S0l', 'S0_S0h_S0l2', 'S0_N0l_S0r2']
    base_set = []
    n_added = 0
    ngram_str = make_ngram_str(base_set)
    exp_dir = pjoin(str(REMOTE_PARSERS), name, str(n_added))
    n_finished = count_finished(exp_dir)
    if n_finished < n: 
        train_n(n, str(n_added), pjoin(str(REMOTE_PARSERS), name),
                data, k=k, i=15, feat_str="full", train_alg='max', label="NONE",
                n_sents=size, ngrams=0, train_name=train_name, 
                dev_names=(eval_pos, eval_parse))
        n_finished = 0
        while n_finished < n:
            time.sleep(60)
            n_finished = count_finished(exp_dir)
    base_accs = get_accs(exp_dir)
    base_avg = sum(base_accs) / len(base_accs)
    print "Base: ", base_avg
    rejected = []
    while True:
        next_ngram = ngrams.pop(0)
        n_added += 1
        print "Testing", next_ngram
        ngram_str = make_ngram_str(base_set + [next_ngram])
        exp_dir = pjoin(str(REMOTE_PARSERS), name, str(n_added))
        n_finished = count_finished(exp_dir)
        if n_finished < n:
            train_n(n, str(n_added), pjoin(str(REMOTE_PARSERS), name),
                    data, k=k, i=15, feat_str="full", train_alg='max',
                    label="NONE", n_sents=size, ngrams=ngram_str, train_name=train_name,
                    dev_names=(eval_pos, eval_parse))
            n_finished = 0
            while n_finished < n:
                time.sleep(60)
                n_finished = count_finished(exp_dir)
        exp_accs = get_accs(exp_dir)
        exp_avg = sum(exp_accs) / len(exp_accs)
        if n >= 20:
            _, p = scipy.stats.wilcoxon(exp_accs, base_accs)
        else:
            p = 0.0
        if exp_avg > base_avg and p < 0.1:
            print "Accepted!", next_ngram, base_avg, exp_avg, p
            base_set.append(next_ngram)
            base_avg = exp_avg
            base_accs = exp_accs
        else:
            print "Rejected!", next_ngram, base_avg, exp_avg, p
            rejected.append(next_ngram)
        print "Current set: ", ' '.join(base_set)
        print "Rejected:", ' '.join(rejected)

def get_best_trigrams(all_trigrams, n=25):
    best = [2, 199, 158, 61, 66, 5, 150, 1, 88, 154, 85, 25, 53, 10, 3, 60, 73,
            175, 114, 4, 6, 148, 205, 197, 0, 71, 127, 200, 142, 84, 43, 89, 45,
            95, 419, 33, 110, 182, 20, 24, 159, 51, 106, 26, 8, 178, 151, 12, 166,
            192, 7, 209, 190, 147, 13, 194, 50, 129, 174, 186, 28, 116, 193, 179,
            262, 23, 44, 172, 133, 191, 562, 38, 124, 195, 123, 72, 202, 187, 101,
            92, 104, 115, 596, 29, 99, 132, 169, 42, 206, 592, 67, 323, 69, 9, 74,
            14, 136, 64, 561, 161, 19, 77, 171, 300, 204, 310, 121, 15, 201, 235,
            657, 70, 198, 22, 68, 48, 153, 54, 286, 83, 162, 100, 506, 98, 80, 433,
            420, 63, 613, 149, 90, 139, 31, 91, 86, 203, 248, 173, 130, 165, 346,
            157, 616, 18, 145, 451, 410, 75, 55, 603, 156, 52, 622, 210, 332, 120]
 

def tritable(name):
    #exp_dir = REMOTE_PARSERS.join(name)
    exp_dir = Path('/data1/mhonniba/').join(name)
    results = []
    with cd(str(exp_dir)):
        ngrams = run("ls %s" % exp_dir, quiet=True).split()
        for ngram in sorted(ngrams):
            base_dir = exp_dir.join(ngram).join('base')
            tri_dir = exp_dir.join(ngram).join('exp')
            base_accs = get_accs(str(base_dir))
            tri_accs = get_accs(str(tri_dir))
            if not base_accs or not tri_accs:
                continue
            if len(base_accs) != len(tri_accs):
                continue
            #z, p = scipy.stats.wilcoxon(base_accs, tri_accs)
            p = 1.0
            delta =  (sum(tri_accs) / len(tri_accs)) - (sum(base_accs) / len(base_accs))
            results.append((delta, ngram, p))
        results.sort(reverse=True)
        good_trigrams = []
        for delta, ngram, p in results:
            ngram = ngram.replace('s0le', 'n0le')
            pieces = ngram.split('_')
            print r'%s & %s & %s & %.1f \\' % (pieces[1], pieces[2], pieces[3], delta)
            if delta > 0.1:
                good_trigrams.append(int(ngram.split('_')[0]))
        print good_trigrams
        print len(good_trigrams)
            

def bitable(name):
    exp_dir = REMOTE_PARSERS.join(name)
    base_accs = get_accs(str(exp_dir.join('0_S0_N0')))
    base_acc = sum(base_accs) / len(base_accs)
    print "Base:", len(base_accs), sum(base_accs) / len(base_accs)
    results = []
    with cd(str(exp_dir)):
        ngrams = run("ls %s" % exp_dir, quiet=True).split()
        for ngram in sorted(ngrams):
            if ngram == 'base' or ngram == '0_S0_N0':
                continue
            accs = get_accs(str(exp_dir.join(ngram)))
            print ngram, len(accs)
            if not accs:
                continue
            _, avg, stdev = _get_stdev(accs)
            z, p = scipy.stats.wilcoxon(accs, base_accs)
            parts = ngram.split('_')
            if ngram.startswith('base'):
                base_acc = avg
            else:
                results.append((avg, ngram, stdev, p))
    good_ngrams = []
    results.sort()
    results.reverse()
    for acc, ngram, stdev, p in results:
        ngram = '_'.join(ngram.split('_')[1:])
        if acc > base_acc and p < 0.01:
            print r'%s & %.3f & %.3f \\' % (ngram, acc - base_acc, p)
            good_ngrams.append(ngram)
    print good_ngrams
    print len(good_ngrams)
        

def vocab_thresholds(name, k=8, n=1, size=10000):
    base_dir = REMOTE_PARSERS.join(name)
    n = int(n)
    k = int(k)
    size = int(size)
    data = str(REMOTE_STANFORD)
    repo = str(REMOTE_REPO)
    train_name = 'train.txt'
    eval_pos = 'devi.txt' 
    eval_parse = 'devr.txt'
 
    thresholds = [75]
    ngram_sizes = [60, 90, 120]
    for n_ngrams in ngram_sizes:
        if n_ngrams == 0:
            feat_name = 'zhang'
        else:
            feat_name = 'full'
        exp_dir = str(base_dir.join('%d_ngrams' % n_ngrams))
        #if n_ngrams < 100:
        #    train_n(n, 'unpruned', exp_dir, data, k=k, i=15, t=0, f=0,
        #            train_alg="max", label="Stanford", n_sents=size, feat_str=feat_name)
        for t in thresholds:
            thresh = 'thresh%d' % t
            train_n(n, thresh, exp_dir, data, k=k, i=15, t=t, f=100,
                    train_alg='max', label="Stanford", n_sents=size,
                    feat_str=feat_name, ngrams=n_ngrams)

def vocab_table(name):
    exp_dir = REMOTE_PARSERS.join(name)
    with cd(str(exp_dir)):
        conditions = run("ls %s" % exp_dir, quiet=True).split()
        for condition in sorted(conditions):
            accs = get_accs(str(exp_dir.join(condition)))
            print condition, len(accs), sum(accs) / len(accs)

# 119_s0_s0r2_s0l2
def train_n(n, name, exp_dir, data, k=1, feat_str="zhang", i=15, upd='max',
            train_alg="online", n_sents=0, static=False, use_edit=False,
            ngrams=0, t=0, f=0, train_name='train.txt', dev_names=('devi.txt', 'devr.txt')):
    exp_dir = str(exp_dir)
    repo = str(REMOTE_REPO)
    for seed in range(n):
        exp_name = '%s_%d' % (name, seed)
        model = pjoin(exp_dir, name, str(seed))
        run("mkdir -p %s" % model, quiet=True)
        train_str = _train(pjoin(data, train_name), model, k=k, i=15,
                           feat_str=feat_str, train_alg=train_alg, seed=seed,
                           n_sents=n_sents, ngrams=ngrams, use_edit=use_edit,
                           vocab_thresh=t, feat_thresh=f)
        parse_str = _parse(model, pjoin(data, dev_names[0]), pjoin(model, 'dev'))
        eval_str = _evaluate(pjoin(model, 'dev', 'parses'), pjoin(data, dev_names[1]))
        grep_str = "grep 'U:' %s >> %s" % (pjoin(model, 'dev', 'acc'),
                                           pjoin(model, 'dev', 'uas')) 
        # Save disk space by removing models
        del_str = "rm %s %s" % (pjoin(model, "model"), pjoin(model, "words"))
        script = _pbsify(repo, (train_str, parse_str, eval_str, grep_str, del_str))
        script_loc = pjoin(repo, 'pbs', exp_name)
        with cd(repo):
            put(StringIO(script), script_loc)
            err_loc = pjoin(model, 'stderr')
            out_loc = pjoin(model, 'stdout')
            run('qsub -N %s %s -e %s -o %s' % (exp_name, script_loc, err_loc, out_loc), quiet=True)


def count_finished(exp_dir):
    with cd(exp_dir):
        samples = [s for s in run("ls %s/*/" % exp_dir, quiet=True).split()
                   if s.endswith('stdout')]
    return len(samples)


def get_accs(exp_dir, eval_name='dev'):
    results = []
    with cd(exp_dir):
        results = [float(s.split()[1]) for s in
                   run("grep 'U:' %s/*/dev/acc" % exp_dir, quiet=True).split('\n')
                   if s.strip()]
    return results


def _train(data, model, debug=False, k=1, feat_str='zhang', i=15,
           train_alg="static", seed=0, args='',
           n_sents=0, ngrams=0, vocab_thresh=0, feat_thresh=10,
           use_edit=False):
    use_edit = '-e' if use_edit else ''
    template = './scripts/train.py -i {i} -a {alg} -k {k} -x {feat_str} {data} {model} -s {seed} -n {n_sents} -g {ngrams} -t {vocab_thresh} -f {feat_thresh} {use_edit} {args}'
    if debug:
        template += ' -debug'
    return template.format(data=data, model=model, k=k, feat_str=feat_str, i=i,
                           vocab_thresh=vocab_thresh, feat_thresh=feat_thresh,
                           alg=train_alg, use_edit=use_edit, seed=seed,
                          args=args, n_sents=n_sents, ngrams=ngrams)


def _parse(model, data, out, gold=False):
    template = './scripts/parse.py {model} {data} {out} '
    if gold:
        template += '-g'
    return template.format(model=model, data=data, out=out)


def _evaluate(test, gold):
    return './scripts/evaluate.py %s %s > %s' % (test, gold, test.replace('parses', 'acc'))


def _pbsify(repo, command_strs, size=5):
    header = """#! /bin/bash
#PBS -l walltime=20:00:00,mem=2gb,nodes=1:ppn={n_procs}
source /home/mhonniba/ev/bin/activate
export PYTHONPATH={repo}:{repo}/redshift:{repo}/svm
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib64:/lib64:/usr/lib64/:/usr/lib64/atlas:{repo}/redshift/svm/lib/
cd {repo}"""
    return header.format(n_procs=size, repo=repo) + '\n' + '\n'.join(command_strs)


uas_re = re.compile(r'U: (\d\d.\d+)')
las_re = re.compile(r'L: (\d\d.\d+)')
# TODO: Hook up LAS arg
def _get_acc(text, score='U'):
    if score == 'U':
        return float(uas_re.search(text).groups()[0])
    else:
        return float(las_re.search(text).groups()[0])


def _get_stdev(scores):
    n = len(scores)
    mean = sum(scores) / n
    var = sum((s - mean)**2 for s in scores)/n
    return n, mean, sqrt(var)

def _get_repair_str(reattach, lower, invert):
    repair_str = []
    if reattach:
        repair_str.append('-r -o')
    if lower:
        repair_str.append('-w')
    if invert:
        repair_str.append('-v')
    return ' '.join(repair_str)


def _get_paths(here):
    if here == True:
        return LOCAL_REPO, LOCAL_STANFORD, LOCAL_PARSERS
    else:
        return REMOTE_REPO, REMOTE_STANFORD, REMOTE_PARSERS


def _get_train_name(data_loc, size):
    if size == 'full':
        train_name = 'train.txt'
    elif size == '1k':
        train_name = '1k_train.txt'
    elif size == '5k':
        train_name = '5k_train.txt'
    elif size == '10k':
        train_name = '10k_train.txt'
    else:
        raise StandardError(size)
    return data_loc.join(train_name)


def run_static(name, size='full', here=True, feats='all', labels="MALT", thresh=5, reattach=False,
              lower=False):
    train_name = _get_train_name(size)
    repair_str = ''
    if reattach:
        repair_str += '-r '
    if lower:   
        repair_str += '-m'
    if feats == 'all':
        feats_flag = ''
    elif feats == 'zhang':
        feats_flag = '-x'
    if here is True:
        data_loc = Path(LOCAL_STANFORD)
        #if labels == 'Stanford':
        #    data_loc = Path(LOCAL_STANFORD)
        #else:
        #    data_loc = Path(LOCAL_CONLL)
        parser_loc = Path(LOCAL_PARSERS).join(name)
        runner = local
        cder = lcd
        repo = LOCAL_REPO
    else:
        if labels == 'Stanford':
            data_loc = Path(REMOTE_STANFORD)
        else:
            data_loc = Path(REMOTE_CONLL)
        parser_loc = Path(REMOTE_PARSERS).join(name)
        runner = run
        cder = cd
        repo = REMOTE_REPO

    train_loc = data_loc.join(train_name)
    with cder(repo):
        #runner('make -C redshift clean')
        runner('make -C redshift')
        if here is not True:
            arg_str = 'PARSER_DIR=%s,DATA_DIR=%s,FEATS="%s,LABELS=%s,THRESH=%s,REPAIRS=%s"' % (parser_loc, data_loc, feats_flag, labels, thresh, repair_str)
            job_name = 'redshift_%s' % name
            err_loc = parser_loc.join('err')
            out_loc = parser_loc.join('log')
            run('qsub -e %s -o %s -v %s -N %s pbs/redshift.pbs' % (err_loc, out_loc, arg_str, job_name))
            print "Waiting 2m for job to initialise"
            time.sleep(120)
            run('qstat -na | grep mhonniba')
            if err_loc.exists():
                print err_loc.open()

        else:
            dev_loc = data_loc.join('devr.txt')
            in_loc = data_loc.join('dev_auto_pos.parse')
            out_dir = parser_loc.join('parsed_dev')
            runner('./scripts/train.py %s -f %d -l %s %s %s %s' % (repair_str, thresh, labels, feats_flag, train_loc, parser_loc))
            runner('./scripts/parse.py -g %s %s %s' % (parser_loc, in_loc, out_dir))
            runner('./scripts/evaluate.py %s %s' % (out_dir.join('parses'), dev_loc)) 

########NEW FILE########
__FILENAME__ = evaluate
#!/usr/bin/env python
import os
import sys
import plac
from collections import defaultdict

def pc(num, den):
    return (num / float(den+1e-100)) * 100

def fmt_acc(label, n, l_corr, u_corr, total_errs):
    l_pc = pc(l_corr, n)
    u_pc = pc(u_corr, n)
    err_pc = pc(n - l_corr, total_errs)
    return '%s\t%d\t%.3f\t%.3f\t%.3f' % (label, n, l_pc, u_pc, err_pc)


def gen_toks(loc):
    sent_strs = open(str(loc)).read().strip().split('\n\n')
    token = None
    i = 0
    for sent_str in sent_strs:
        tokens = [Token(i, tok_str.split()) for i, tok_str in enumerate(sent_str.split('\n'))]
        for token in tokens:
            yield sent_str, token


class Token(object):
    def __init__(self, id_, attrs):
        self.id = id_
        # CoNLL format
        if len(attrs) == 10:
            new_attrs = [str(int(attrs[0]) - 1)]
            new_attrs.append(attrs[1])
            new_attrs.append(attrs[3])
            new_attrs.append(str(int(attrs[6]) - 1))
            new_attrs.append(attrs[7])
            attrs = new_attrs
        self.label = attrs.pop()
        if self.label.lower() == 'root':
            self.label = 'ROOT'
        try:
            head = int(attrs.pop())
        except:
            print orig
            raise
        self.head = head
        # Make head an offset from the token id, for sent variation
        #if head == -1 or self.label.upper() == 'ROOT':
        #    self.head = id_
        #else:
        #    self.head = head - id_
        self.pos = attrs.pop()
        self.word = attrs.pop()
        self.dir = 'R' if head >= 0 and head < self.id else 'L'
    

@plac.annotations(
    eval_punct=("Evaluate punct transitions", "flag", "p")
)
def main(test_loc, gold_loc, eval_punct=False):
    if not os.path.exists(test_loc):
        test_loc.mkdir()
    n_by_label = defaultdict(lambda: defaultdict(int))
    u_by_label = defaultdict(lambda: defaultdict(int))
    l_by_label = defaultdict(lambda: defaultdict(int))
    N = 0
    u_nc = 0
    l_nc = 0
    for (sst, t), (ss, g) in zip(gen_toks(test_loc), gen_toks(gold_loc)):
        if g.label in ["P", 'punct'] and not eval_punct:
            continue
        prev_g = g
        prev_t = t
        u_c = g.head == t.head
        l_c = u_c and g.label == t.label
        N += 1
        l_nc += l_c
        u_nc += u_c
        n_by_label[g.dir][g.label] += 1
        u_by_label[g.dir][g.label] += u_c
        l_by_label[g.dir][g.label] += l_c
    n_l_err = N - l_nc
    for D in ['L', 'R']:
        yield D 
        n_other = 0
        l_other = 0
        u_other = 0
        for label, n in sorted(n_by_label[D].items(), key=lambda i: i[1], reverse=True):
            if n == 0:
                continue
            elif n < 100:
                n_other += n
                l_other += l_by_label[D][label]
                u_other += u_by_label[D][label]
            else:
                l_corr = l_by_label[D][label]
                u_corr = u_by_label[D][label]
                yield fmt_acc(label, n, l_corr, u_corr, n_l_err)
        yield fmt_acc('Other', n_other, l_other, u_other, n_l_err) 
    yield 'U: %.3f' % pc(u_nc, N)
    yield 'L: %.3f' % pc(l_nc, N)

if __name__ == '__main__':
    for line in plac.call(main):
        print line

########NEW FILE########
__FILENAME__ = evaluate_moves
#!/usr/bin/env python
"""Process a best_moves file to give move P/R/F values"""
import plac
from collections import defaultdict 
import re

punct_re = re.compile(r'-P$')
label_re = re.compile(r'-[A-Za-z]*')
def main(moves_loc):
    # TP, FP, FN
    freqs = defaultdict(lambda: [10e-1000, 10e-1000, 10e-1000])
    total = 0
    bad = 0
    for line in open(moves_loc):
        if line.count('\t') == 0: continue
        line = line.replace('\033[91m', '').replace('\033[0m', '')
        try:
            gold, test, _ = line.rstrip().split('\t')
        except:
            print repr(line)
            raise
        if punct_re.search(gold) or punct_re.search(test):
            continue
        total += 1
        if not gold:
            bad += 1
            continue
        gold = label_re.sub('', gold)
        test = label_re.sub('', test)
        gold_moves = gold.split(',')
        # Handle multiple golds by just noting false positive, not false negatives
        if len(gold_moves) > 1:
            if test not in gold_moves:
                freqs[test][1] += 1
            else:
                freqs[test][0] += 1
            continue
        gold = gold_moves[0]
        if test == gold:
            freqs[test][0] += 1
        else:
            freqs[test][1] += 1
            freqs[gold][2] += 1
    print "L\tP\tR\tF"
    for label, (tp, fp, fn) in sorted(freqs.items()):
        p = (float(tp) / (tp + fp + 1e-1000)) if tp + fp > 0 else 0.0
        r = (float(tp) / (tp + fn + 1e-1000)) if tp + fn > 0 else 0.0
        f = (2 * ((p * r) / (p + r + 1e-1000))) if p + r > 0 else 0.0
        print '%s\t%.2f\t%.2f\t%.2f' % (label, p * 100, r * 100, f * 100)
    print '%.2f no good move' % ((float(bad) / total) * 100)
    for repair in ['LU', 'RU', 'RL', 'RR', 'LI']:
        tp, fp, fn = freqs[repair]
        if tp + fp + fn == 0:
            continue
        print '%s %d-%d=%d' % (repair, tp, fp, tp - fp)

if __name__ == '__main__':
    plac.call(main)
        
    

########NEW FILE########
__FILENAME__ = get_repair_stats
#!/usr/bin/env python
"""
Parse a best_moves file to get repair stats.
"""
import plac
from collections import defaultdict

def sort_dict(d):
    return reversed(sorted(d.items(), key=lambda i: i[1]))

@plac.annotations(
    labels=("Print labelled moves", "flag", "l", bool)
)
def main(loc, labels=False):
    true_pos = defaultdict(int)
    false_pos = defaultdict(int)
    false_neg = defaultdict(int)
    true_neg = defaultdict(int)
    for line in open(loc):
        if '<start>' in line:
            continue
        line = line.rstrip()
        if not line:
            continue
        pieces = line.split('\t')
        golds = pieces[0].split(',')
        parse = pieces[1]
        is_punct = any(g.endswith('-P') for g in golds)
        if is_punct:
            continue
        if not labels:
            parse = parse.split('-')[0]
            golds = [g.split('-')[0] for g in golds]
        if len(golds) > 1:
            continue
        gold = golds[0]
        if gold.split('-')[0] == parse.split('-')[0]:
            if '^' in gold:
                true_pos[gold] += 1
            elif gold.startswith('L') or gold.startswith('D'):
                true_neg[gold] += 1
        else:
            if '^' in gold:
                false_neg[gold] += 1
            elif '^' in parse:
                false_pos[parse] += 1
    for label, d in [('TP', true_pos), ('FP', false_pos), ('FN', false_neg), ('TN', true_neg)]:
        print label
        for tag, freq in sort_dict(d):
            print tag, freq


if __name__ == '__main__':
    plac.call(main)

########NEW FILE########
__FILENAME__ = get_train_moves
"""Write gold moves file"""

from redshift.parser import Parser
from redshift.io_parse import read_conll

import plac
from pathlib import Path

@plac.annotations(
    label_set=("Label set to use", "option", "l"),
    allow_reattach=("Allow reattach repair", "flag", "r"),
    allow_moves=("Allow right-lower", "flag", "m")
)
def main(train_loc, out_loc, label_set="MALT", allow_reattach=False, allow_moves=False):
    parser_dir = Path('/tmp').join('parser')
    if not parser_dir.exists():
        parser_dir.mkdir()
    grammar_loc = Path(train_loc).parent().join('rgrammar') if allow_reattach else None
    parser = Parser(str(parser_dir), clean=True, label_set=label_set,
                    allow_reattach=allow_reattach, allow_move=allow_moves,
                    grammar_loc=grammar_loc)
    train = read_conll(open(train_loc).read())
    parser.add_gold_moves(train)
    with open(out_loc, 'w') as out_file:
        train.write_moves(out_file)

if __name__ == '__main__':
    plac.call(main)

########NEW FILE########
__FILENAME__ = get_valencies
"""
Compile valency statistics
"""
import plac

from collections import defaultdict

def main(loc):
    sents = open(loc).read().strip().split('\n\n')
    sents = [[line.split() for line in sent.split('\n')] for sent in sents]
    lvals = defaultdict(lambda: defaultdict(int))
    rvals = defaultdict(lambda: defaultdict(int))
    plvals = defaultdict(lambda: defaultdict(int))
    prvals = defaultdict(lambda: defaultdict(int))
    roots = defaultdict(int)
    seen_pos = set(['ROOT', 'NONE'])
    for sent in sents:
        rdeps = defaultdict(list)
        for i, (w, p, h, l) in enumerate(sent):
            seen_pos.add(p)
            if i > int(h):
                rdeps[int(h)].append(i)
        for head, children in rdeps.items():
            if head == -1:
                head_pos = 'ROOT'
            else:
                head_pos = sent[head][1]
            sib_pos = 'NONE'
            children.sort()
            for i, child in enumerate(children):
                #rvals[head_pos][(sib_pos, sent[child][1])] += 1
                rvals[head_pos][sent[child][1]] += 1
                sib_pos = sent[child][1]
    seen_pos = list(sorted(seen_pos))
    for head in seen_pos:
        for child in seen_pos:
            print head, child, rvals[head][child]
        #for sib in seen_pos:
        #    for child in seen_pos:
        #        print head, sib, child, rvals[head][(sib, child)] 

if __name__ == '__main__':
    plac.call(main)
            

########NEW FILE########
__FILENAME__ = make_folds
import plac
from pathlib import Path
import re

def main(tb_loc, out_loc):
    tb_loc = Path(tb_loc)
    out_loc = Path(out_loc)
    sections = '02,03,04,05,06,07,08,09,10,11,12,13,14,15,16,17,18,19,20,21'.split(',')
    for test_sec in sections:
        train_secs = [s for s in sections if s != test_sec]
        files = []
        for train_sec in train_secs:
            files.extend(f for f in tb_loc.join(train_sec) if f.parts[-1].endswith('.mrg'))
        out_file = out_loc.join('not%s.mrg' % test_sec).open('w')
        for file_ in files:
            out_file.write(file_.open().read().strip())
            out_file.write(u'\n')
        out_file.write(u'\n')
        out_file.close()
        test_file = out_loc.join('%s.mrg' % test_sec).open('w')
        test_text = out_loc.join('%s.txt' % test_sec).open('w')
        sent_re = re.compile(r'^\( \(')
        for file_ in tb_loc.join(test_sec):
            test_file.write(file_.open().read().strip())
            test_file.write(u'\n')
            sentences = sent_re.split(file_.open().read().strip())
            print repr(sentences[0])
        test_file.write(u'\n')
        test_file.close()

if __name__ == '__main__':
    plac.call(main)

########NEW FILE########
__FILENAME__ = parse
#!/usr/bin/env python
import os
import os.path
import sys
import plac
import time
import pstats
import cProfile

import redshift.parser
import redshift.io_parse


def get_pos(conll_str):
    pos_sents = []
    for sent_str in conll_str.strip().split('\n\n'):
        sent = []
        for line in sent_str.split('\n'):
            pieces = line.split()
            if len(pieces) == 5:
                pieces.pop(0)
            word = pieces[0]
            pos = pieces[1]
            sent.append('%s/%s' % (word, pos))
        pos_sents.append(' '.join(sent))
    return '\n'.join(pos_sents)


@plac.annotations(
    use_gold=("Gold-formatted test data", "flag", "g", bool),
    profile=("Do profiling", "flag", "p", bool),
    debug=("Set debug", "flag", "d", bool)
)
def main(parser_dir, text_loc, out_dir, use_gold=False, profile=False, debug=False):
    if debug:
        redshift.parser.set_debug(debug)
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)
    yield "Loading parser"
    parser = redshift.parser.load_parser(parser_dir)
    sentences = redshift.io_parse.read_pos(open(text_loc).read())
    #sentences.connect_sentences(1700)
    if profile:
        cProfile.runctx("parser.add_parses(sentences,gold=gold_sents)",
                        globals(), locals(), "Profile.prof")
        s = pstats.Stats("Profile.prof")
        s.strip_dirs().sort_stats("time").print_stats()
    else:
        t1 = time.time()
        parser.add_parses(sentences)
        t2 = time.time()
        print '%d sents took %0.3f ms' % (sentences.length, (t2-t1)*1000.0)
    sentences.write_parses(open(os.path.join(out_dir, 'parses'), 'w'))


if __name__ == '__main__':
    plac.call(main)

########NEW FILE########
__FILENAME__ = swbd_deps
"""Edit a SWBD conll format file in various ways"""

import plac
import sys

class Token(object):
    def __init__(self, line):
        props = line.split()
        self.id = int(props[0])
        self.word = props[1]
        self.pos = props[3].split('^')[-1]
        self.label = props[7]
        self.head = int(props[6])
        self.is_edit = props[-1] == 'True'

    def to_str(self):
        props = (self.id, self.word, self.pos, self.pos, self.head,
                 self.label, self.is_edit)
        return '%d\t%s\t-\t%s\t%s\t-\t%d\t%s\t-\t%s' % props


class Sentence(object):
    def __init__(self, sent_str):
        self.tokens = [Token(line) for line in sent_str.split('\n')]
        edit_depth = 0
        saw_ip = False
        for i, token in enumerate(self.tokens):
            if token.word == r'\]' and saw_ip == 0:
                continue
            if token.word == r'\[':
                edit_depth += 1
                saw_ip = False
            token.is_edit = edit_depth >= 1 or token.is_edit
            if token.word == r'\+':
                edit_depth -= 1
                saw_ip = True
            if token.word == r'\]' and not saw_ip:
                # Assume prev token is actually repair, not reparandum
                # This should only effect 3 cases
                self.tokens[i - 1].is_edit = False
                edit_depth -= 1
        n_erased = 0
        self.n_dfl = 0
        for token in self.tokens:
            if token.word == r'\[':
                self.n_dfl += 1

    def to_str(self):
        return '\n'.join(token.to_str() for token in self.tokens)

    def label_edits(self):
        for i, token in enumerate(self.tokens):
            if token.pos == 'UH':
                continue
            head = self.tokens[token.head - 1]
            if token.is_edit and (head.pos == '-DFL-' or not head.is_edit):
                token.label = 'erased'

    def label_interregna(self):
        for i, token in enumerate(self.tokens):
            if i == 0: continue
            prev = self.tokens[i - 1]
            if (prev.is_edit or prev.label == 'interregnum') \
              and not token.is_edit \
              and token.label in ('discourse', 'parataxis'):
                token.label = 'interregnum'

    def merge_mwe(self, mwe, parent_label=None, new_label=None):
        strings = mwe.split('_')
        assert len(strings) == 2
        for i, token in enumerate(self.tokens):
            if i == 0: continue
            prev = self.tokens[i - 1]
            if prev.word.lower() != strings[0] or token.word.lower() != strings[1]:
                continue
            if token.head == i:
                child = token
                head = prev
            elif prev.head == (i + 1):
                child = prev
                head = token
            else:
                print prev.word, token.word, prev.head, token.head, i
                continue
            if parent_label is not None and head.label != parent_label:
                continue
            head.word = mwe
            head.pos = 'MWE'
            child.word = '<erased>'
            if new_label is not None:
                head.label = new_label
        self.rm_tokens(lambda t: t.word == '<erased>')

    def rm_tokens(self, rejector):
        # 0 is root in conll format
        id_map = {0: 0}
        rejected = set()
        new_id = 1
        for token in self.tokens:
            id_map[token.id] = new_id
            if not rejector(token):
                new_id += 1
            else:
                rejected.add(token.id)
        for token in self.tokens:
            while token.head in rejected:
                head = self.tokens[token.head - 1]
                token.head = head.head
                token = head
        self.tokens = [token for token in self.tokens if not rejector(token)]
        n = len(self.tokens)
        for token in self.tokens:
            token.id = id_map[token.id]
            try:
                token.head = id_map[token.head]
            except:
                print >> sys.stderr, token.word
                raise
            if token.head > n:
                token.head = 0
            if token.head == token.id:
                token.head -= 1

    def lower_case(self):
        for token in self.tokens:
            token.word = token.word.lower()

@plac.annotations(
    ignore_unfinished=("Ignore unfinished sentences", "flag", "u", bool),
    merge_mwe=("Merge multi-word expressions", "flag", "m", bool),
    excise_edits=("Clean edits entirely", "flag", "e", bool),
    label_edits=("Label edits", "flag", "l", bool),
)
def main(in_loc, ignore_unfinished=False, excise_edits=False, label_edits=False,
        merge_mwe=False):
    sentences = [Sentence(sent_str) for sent_str in
                 open(in_loc).read().strip().split('\n\n')]
    punct = set([',', ':', '.', ';', 'RRB', 'LRB', '``', "''"])
 
    for sent in sentences:
        if ignore_unfinished and sent.tokens[-1].word == 'N_S':
            continue
        orig_str = sent.to_str()
        try:
            if merge_mwe:
                sent.merge_mwe('you_know')
                sent.merge_mwe('i_mean')
                sent.merge_mwe('of_course', new_label='discourse')

            if excise_edits:
                sent.rm_tokens(lambda token: token.is_edit)
                sent.rm_tokens(lambda token: token.label == 'discourse')
            if label_edits:
                sent.label_edits()
            sent.rm_tokens(lambda token: token.word.endswith('-'))
            sent.rm_tokens(lambda token: token.pos in punct)
            sent.rm_tokens(lambda token: token.pos == '-DFL-')
            sent.rm_tokens(lambda token: token.word == 'MUMBLEx')
            sent.label_interregna()
            sent.lower_case()
        except:
            print >> sys.stderr, orig_str
            raise
        if len(sent.tokens) >= 3:
            print sent.to_str()
            print


if __name__ == '__main__':
    plac.call(main)


########NEW FILE########
__FILENAME__ = train
#!/usr/bin/env python

import random
import os
import sys
import plac

import redshift.parser
from redshift.parser import GreedyParser, BeamParser
import redshift.io_parse


def get_train_str(train_loc, n_sents):
    train_sent_strs = open(train_loc).read().strip().split('\n\n')
    if n_sents != 0:
        random.shuffle(train_sent_strs)
        train_sent_strs = train_sent_strs[:n_sents]
    return '\n\n'.join(train_sent_strs)
 

@plac.annotations(
    train_loc=("Training location", "positional"),
    beam_width=("Beam width", "option", "k", int),
    train_oracle=("Training oracle [static, dyn]", "option", "a", str),
    n_iter=("Number of Perceptron iterations", "option", "i", int),
    feat_thresh=("Feature pruning threshold", "option", "f", int),
    allow_reattach=("Allow Left-Arc to override heads", "flag", "r", bool),
    allow_reduce=("Allow reduce when no head is set", "flag", "d", bool),
    seed=("Set random seed", "option", "s", int),
    n_sents=("Number of sentences to train from", "option", "n", int),
    unlabelled=("Learn unlabelled arcs", "flag", "u", bool)
)
def main(train_loc, model_loc, train_oracle="static", n_iter=15, beam_width=1,
         feat_thresh=10, allow_reattach=False, allow_reduce=False, unlabelled=False,
         n_sents=0, seed=0):
    random.seed(seed)
    if beam_width >= 2:
        parser = BeamParser(model_loc, clean=True,
                            train_alg=train_oracle,
                            feat_thresh=feat_thresh, allow_reduce=allow_reduce,
                            allow_reattach=allow_reattach, beam_width=beam_width)
    else:
        parser = GreedyParser(model_loc, clean=True, train_alg=train_oracle,
                              feat_thresh=feat_thresh,
                              allow_reduce=allow_reduce,
                              allow_reattach=allow_reattach)
    train_str = get_train_str(train_loc, n_sents)
    train_data = redshift.io_parse.read_conll(train_str, unlabelled=unlabelled)
    parser.train(train_data, n_iter=n_iter)
    parser.save()


if __name__ == "__main__":
    plac.call(main)

########NEW FILE########
__FILENAME__ = train_iter
#!/usr/bin/env python
"""Do iterative error-based training

Directory structure assumed:

base_dir/
    gold/
        0/
            train.parses
            train.moves
            held_out
        ...
        train.txt
        devr.txt
        devi.txt
    iters/
        0/
            0/
                train/
                    <to compile>parses
                    <to compile>moves
                eval/
                    <to produce>parses
                    <to produce>moves
                    <to produce>acc
                held_out/
                    <to produce>parses
                    <to produce>moves
                parser/
                    <to produce>model
                    <to produce>features
                    <to produce>words
                    <to produce>pos
"""
from pathlib import Path
import plac
import sh
import time
from math import sqrt
import re
import random

random.seed(0)

def split_data(train_loc, n):
    text = train_loc.open().read().strip()
    if n == 1:
        yield unicode(text), unicode(text)
    else:
        instances = text.split('\n\n')
        length = len(instances)
        test_size = length / n
        train_size = length - test_size
        for i in range(n):
            test_start = i * test_size
            test_end = test_start + test_size
            test = instances[test_start:test_end]
            assert len(test) == test_size
            train = instances[:test_start] + instances[test_end:]
            assert len(train) == train_size
            yield u'\n\n'.join(train), u'\n\n'.join(test)


def setup_base_dir(base_dir, data_dir, train_name, n):
    if base_dir.exists():
        sh.rm('-rf', base_dir)
    base_dir.mkdir()
    base_dir.join('iters').mkdir()
    gold_dir = base_dir.join('gold')
    gold_dir.mkdir()
    train_loc = data_dir.join(train_name)
    for i, (train_str, ho_str) in enumerate(split_data(train_loc, n)):
        gold_dir.join(str(i)).mkdir()
        gold_dir.join(str(i)).join('train.parses').open('w').write(train_str)
        gold_dir.join(str(i)).join('held_out').open('w').write(ho_str)
    gold_dir.join('train.txt').open('w').write(train_loc.open().read())
    gold_dir.join('devr.txt').open('w').write(data_dir.join('devr.txt').open().read())
    gold_dir.join('devi.txt').open('w').write(data_dir.join('devi.txt').open().read())
    gold_dir.join('rgrammar').open('w').write(data_dir.join('rgrammar').open().read())


def setup_fold_dir(base_dir, i, f, z, n_folds, add_gold, parse_percent):
    exp_dir = base_dir.join('iters').join(str(i)).join(str(f))
    if exp_dir.exists():
        sh.rm('-rf', str(exp_dir))
    exp_dir.mkdir(parents=True)
    exp_dir.join('name').open('w').write(u'iter%d_fold%d' % (i, f))
    for name in ['parser', 'train', 'held_out', 'eval']:
        subdir = exp_dir.join(name)
        if not subdir.exists():
            subdir.mkdir()
    train_dir = exp_dir.join('train')
    train_dir.join('rgrammar').open('w').write(base_dir.join('gold').join('rgrammar').open().read())
    parses = train_dir.join('parses').open('w')
    moves = train_dir.join('moves').open('w')
    if i == 0:
        gold_parse_loc = base_dir.join('gold').join(str(f)).join('train.parses')
        parses.write(gold_parse_loc.open().read())
        parses.write(u'\n\n')
    if n_folds == 1:
        exp_dir.join('held_out').join('gold').open('w').write(base_dir.join('gold').join('train.txt').open().read())
    else:
        exp_dir.join('held_out').join('gold').open('w').write(
                base_dir.join('gold').join(str(f)).join('held_out').open().read() + u'\n\n')
    dirs = [d for d in base_dir.join('iters') if int(d.parts[-1]) < i]
    dirs.sort()
    for prev_iter_dir in dirs[z * -1:]:
        folds = list(prev_iter_dir)
        for fold in folds:
            if int(str(fold.parts[-1])) != f or n_folds == 1:
                ho_dir = fold.join('held_out')
                ho_parses = ho_dir.join('gold').open().read().strip().split('\n\n')
                ho_moves = ho_dir.join('moves').open().read().strip().split('\n\n')
                assert len(ho_moves) == len(ho_parses)
                for i in range(len(ho_parses)):
                    if random.uniform(0, 1.0) <= parse_percent:
                        parses.write(ho_parses[i] + u'\n\n')
                        moves.write(ho_moves[i] + u'\n\n')
    parses.close()
    moves.close()
    return exp_dir


def train_and_parse_fold(fold_dir, dev_loc, i, label_set, no_extra_features,
    allow_reattach, allow_unshift, allow_move_top, allow_invert):
    name = fold_dir.join('name').open().read().strip()
    train_args = ['BASE_DIR', 'DEV_LOC', 'LABEL_SET', 'FEAT_STR', 'THRESH',
                   'REPAIR_STR']
    if no_extra_features:
        feat_str = '-x'
    else:
        feat_str = ''
    repair_str = []
    if allow_reattach:
        repair_str.append('-r')
    if allow_move_top:
        repair_str.append('-m')
    if allow_unshift:
        repair_str.append('-u')
    if allow_invert:
        repair_str.append('-v')
    repair_str = ' '.join(repair_str)
    thresh = 5 * i if i >= 1 else 5
    arg_vals = [fold_dir, dev_loc, label_set, feat_str, thresh, repair_str]
    env_str = ','.join('%s=%s' % (k, v) for k, v in zip(train_args, arg_vals))
    sh.qsub('pbs/train.sh', o=fold_dir.join('out'), e=fold_dir.join('err'), v=env_str, N=name)


def check_finished(iter_dir, n):
    finished_jobs = [False for i in range(n)]
    n_done = 0
    for i in range(n):
        exp_dir = iter_dir.join(str(i))
        if exp_dir.join('err').exists():
            finished_jobs[i] = True
            errors = exp_dir.join('err').open().read().strip()
            if errors:
                print errors
                raise StandardError
    return all(finished_jobs)


inst_feats_re = re.compile('(\d+) instances, (\d+) features')
def get_iter_summary(iter_dir, i, n_folds):
    accs = []
    for f in range(n_folds):
        acc = iter_dir.join(str(f)).join('eval').join('acc').open().read()
        uas = [l for l in acc.split('\n') if l.startswith('U')][0].split()[1]
        accs.append(float(uas))
    feats = []
    insts = []
    for f in range(n_folds):
        out_str = iter_dir.join(str(f)).join('out').open().read()
        n_i, n_f = inst_feats_re.search(out_str).groups()
        feats.append(int(n_f))
        insts.append(int(n_i))
    return u'%d    %s    %s    %s' % (i, mean_stdev(accs), mean_stdev(insts, ints=True),
                                mean_stdev(feats, ints=True))


def mean_stdev(nums, ints=False):
    avg = sum(nums) / len(nums)
    var = sum((avg - a)**2 for a in nums) / len(nums)
    stdev = sqrt(var)
    if ints:
        return u'%d (+/- %d)' % (avg, stdev)
    else:
        return u'%.2f (+/- %.2f)' % (avg, stdev)


@plac.annotations(
    n_folds=("Number of splits to use for iterative training", "option", "f", int),
    add_gold=("Always add the gold-standard moves to training", "flag", "g", bool),
    base_dir=("Output directory for model/s", "positional", None, Path),
    data_dir=("Directory of parse data", "positional", None, Path),
    resume_after=("Resume training after N iterations", "option", "s", int),
    no_extra_features=("Don't add extra features", "flag", "x", bool),
    label_set=("Name of label set", "option", "l", str),
    n_iter=("Number of training iterations", "option", "i", int),
    horizon=("How many previous iterations to add", "option", "z", int),
    train_name=("Name of training file", "option", "t"),
    parse_percent=("Percent of held-out parses to use", "option", "p", float),
    allow_reattach=("Allow left-clobber", "flag", "r", bool),
    allow_move=("Allow lower/raise of top", "flag", "m", bool),
    allow_unshift=("Allow unshift", "flag", "u", bool),
    allow_invert=("Allow invert", "flag", "v", bool)
)
def main(data_dir, base_dir, n_iter=5, n_folds=1,
         horizon=0, add_gold=False, resume_after=0, no_extra_features=False,
         label_set="MALT", train_name="train.txt", parse_percent=1.0,
         allow_reattach=False, allow_unshift=False, allow_move=False,
         allow_invert=False):
    if resume_after <= 0:
        print 'wiping base'
        setup_base_dir(base_dir, data_dir, train_name, n_folds)
    log = base_dir.join('log').open('w')
    log.write(u'I\tAcc\tInst.\tFeats.\n')
    print 'Iter  Accuracy           Instances            Features'
    for i in range(resume_after):
        summary = get_iter_summary(base_dir.join('iters').join(str(i)), i, n_folds)
        log.write(summary + u'\n')
        print summary
    if n_folds > 1:
        extra_iters = n_iter
    else:
        extra_iters = 0
    for i in range(resume_after, n_iter + extra_iters):
        if i == n_iter:
            n_folds = 1
        for f in range(n_folds):
            fold_dir = setup_fold_dir(base_dir, i, f, horizon, n_folds, add_gold, parse_percent)
            train_and_parse_fold(fold_dir, data_dir, i, label_set, no_extra_features,
                allow_reattach, allow_unshift, allow_move, allow_invert)
        while not check_finished(base_dir.join('iters').join(str(i)), n_folds):
            time.sleep(5)
        summary = get_iter_summary(base_dir.join('iters').join(str(i)), i, n_folds)
        log.write(summary + u'\n')
        print summary
    log.close()


if __name__ == '__main__':
    plac.call(main)

########NEW FILE########
__FILENAME__ = tune_parser_l1
"""
Tune the L1 regularisation parameter for the parser
"""
import plac
from pathlib import Path
import redshift.io_parse

import tagging.optimise
import redshift.parser

def get_pos(conll_str):
    pos_sents = []
    for sent_str in conll_str.strip().split('\n\n'):
        sent = []
        for line in sent_str.split('\n'):
            pieces = line.split()
            if len(pieces) == 5:
                pieces.pop(0)
            word = pieces[0]
            pos = pieces[1]
            sent.append('%s/%s' % (word, pos))
        pos_sents.append(' '.join(sent))
    return '\n'.join(pos_sents)


def make_evaluator(parser_dir, solver_type, train_loc, dev_loc):
    def wrapped(l1):
        parser = redshift.parser.Parser(parser_dir, solver_type=solver_type,
                                        clean=True, C=l1)
        dev_gold = redshift.io_parse.read_conll(dev_loc.open().read())
        train = redshift.io_parse.read_conll(train_loc.open().read())
        parser.train(train)
        dev = redshift.io_parse.read_pos(get_pos(dev_loc.open().read()))
        acc = parser.add_parses(dev, gold=dev_gold) * 100
        wrapped.models[l1] = acc
        return acc
    models = {}
    wrapped.models = models
    return wrapped
        

@plac.annotations(
    first_val=("Lower bound", "option", "l", float),
    last_val=("Upper bound", "option", "u", float),
    initial_results=("Initialise results with these known values", "option", "r", str),
    solver_type=("LibLinear solver. Integers following the LibLinear CL args", "option", "s", int)
)
def main(parser_dir, train_loc, dev_loc, solver_type=None, first_val=None, last_val=None, initial_results=None):
    train_loc = Path(train_loc)
    dev_loc = Path(dev_loc)
    learner = make_evaluator(parser_dir, solver_type, train_loc, dev_loc)
    results = []
    if initial_results is not None:
        for res_str in initial_results.split('_'):
            v, s = res_str.split(',')
            results.append((float(v), float(s)))
    if first_val is not None and first_val not in [r[0] for r in results]:
        results.append((first_val, learner(first_val)))
    if last_val is not None and last_val not in [r[0] for r in results]:
        results.append((last_val, learner(last_val)))
    results.sort(key=lambda i: i[0])
    if len(results) == 2:
        mid_point = (results[0][0] + results[-1][0]) / 2
        results.insert(1, (mid_point, learner(mid_point)))
    best_value, best_score  = tagging.optimise.search(learner, results)
    print best_value
    print best_score
 

if __name__ == '__main__':
    plac.call(main)

########NEW FILE########
__FILENAME__ = write_grammar
"""
Compile valency statistics
"""
import plac

from collections import defaultdict

def main(loc):
    sents = open(loc).read().strip().split('\n\n')
    sents = [[line.split() for line in sent.split('\n')] for sent in sents]
    lvals = defaultdict(lambda: defaultdict(int))
    rvals = defaultdict(lambda: defaultdict(int))
    plvals = defaultdict(lambda: defaultdict(int))
    prvals = defaultdict(lambda: defaultdict(int))
    roots = defaultdict(int)
    seen_pos = set(['ROOT', 'NONE'])
    for sent in sents:
        rdeps = defaultdict(list)
        for i, (w, p, h, l) in enumerate(sent):
            seen_pos.add(p)
            if i > int(h):
                rdeps[int(h)].append(i)
        for head, children in rdeps.items():
            if head == -1:
                head_pos = 'ROOT'
            else:
                head_pos = sent[head][1]
            sib_pos = 'NONE'
            children.sort()
            for i, child in enumerate(children):
                rvals[head_pos][(sib_pos, sent[child][1])] += 1
                sib_pos = sent[child][1]
    seen_pos = list(sorted(seen_pos))
    for head in seen_pos:
        for sib in seen_pos:
            for child in seen_pos:
                print head, sib, child, rvals[head][(sib, child)] 

if __name__ == '__main__':
    plac.call(main)
            

########NEW FILE########
