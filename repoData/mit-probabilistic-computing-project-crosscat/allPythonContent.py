__FILENAME__ = demonstrate_hadoop_line_processor_local
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import os
#
import crosscat.utils.xnet_utils as xu
import crosscat.settings as S
from crosscat.settings import Hadoop as hs


# settings
n_chains = 20
n_steps = 20
#
filename = os.path.join(S.path.web_resources_data_dir, 'dha_small.csv')
script_name = 'hadoop_line_processor.py'
#
table_data_filename = hs.default_table_data_filename
initialize_input_filename = 'initialize_input'
initialize_output_filename = 'initialize_output'
initialize_args_dict = hs.default_initialize_args_dict
analyze_input_filename = 'analyze_input'
analyze_output_filename = 'analyze_output'
analyze_args_dict = hs.default_analyze_args_dict

# set up
table_data = xu.read_and_pickle_table_data(filename, table_data_filename)

# create initialize input
xu.write_initialization_files(initialize_input_filename,
                              initialize_args_dict=initialize_args_dict,
                              n_chains=n_chains)

# initialize
xu.run_script_local(initialize_input_filename, script_name,
                    initialize_output_filename)

# read initialization output, write analyze input
analyze_args_dict['n_steps'] = n_steps
analyze_args_dict['max_time'] = 20
xu.link_initialize_to_analyze(initialize_output_filename,
                              analyze_input_filename,
                              analyze_args_dict)

# analyze
xu.run_script_local(analyze_input_filename, script_name,
                    analyze_output_filename)

########NEW FILE########
__FILENAME__ = hadoop_line_processor
#!/opt/anaconda/bin/python

#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import os
import numpy
import sys
import itertools
import random
#
import crosscat.utils.data_utils as du
import crosscat.utils.file_utils as fu
import crosscat.utils.hadoop_utils as hu
import crosscat.utils.xnet_utils as xu
import crosscat.utils.general_utils as gu
import crosscat.utils.inference_utils as iu
import crosscat.utils.timing_test_utils as ttu
import crosscat.utils.mutual_information_test_utils as mitu
import crosscat.utils.convergence_test_utils as ctu
import crosscat.utils.LocalEngine as LE
import crosscat.utils.HadoopEngine as HE
from crosscat.settings import Hadoop as hs


def initialize_helper(table_data, data_dict, command_dict):
    M_c = table_data['M_c']
    M_r = table_data['M_r']
    T = table_data['T']
    SEED = data_dict['SEED']
    initialization = command_dict['initialization']
    engine = LE.LocalEngine(SEED)
    X_L, X_D = engine.initialize(M_c, M_r, T, initialization=initialization)
    SEED = engine.get_next_seed()
    #
    ret_dict = dict(SEED=SEED, X_L=X_L, X_D=X_D)
    return ret_dict

def analyze_helper(table_data, data_dict, command_dict):
    M_c = table_data['M_c']
    T = table_data['T']
    SEED = data_dict['SEED']
    X_L = data_dict['X_L']
    X_D = data_dict['X_D']
    kernel_list = command_dict['kernel_list']
    n_steps = command_dict['n_steps']
    c = command_dict['c']
    r = command_dict['r']
    max_time = command_dict['max_time']
    engine = LE.LocalEngine(SEED)
    X_L_prime, X_D_prime = engine.analyze(M_c, T, X_L, X_D, kernel_list=kernel_list,
                                          n_steps=n_steps, c=c, r=r,
                                          max_time=max_time)
    SEED = engine.get_next_seed()
    #
    ret_dict = dict(SEED=SEED, X_L=X_L_prime, X_D=X_D_prime)
    return ret_dict

def chunk_analyze_helper(table_data, data_dict, command_dict):
    original_n_steps = command_dict['n_steps']
    original_SEED = data_dict['SEED']
    chunk_size = command_dict['chunk_size']
    chunk_filename_prefix = command_dict['chunk_filename_prefix']
    chunk_dest_dir = command_dict['chunk_dest_dir']
    #
    steps_done = 0
    while steps_done < original_n_steps:
        steps_remaining = original_n_steps - steps_done
        command_dict['n_steps'] = min(chunk_size, steps_remaining)
        ith_chunk = steps_done / chunk_size
        dict_out = analyze_helper(table_data, data_dict, command_dict)
        data_dict.update(dict_out)
        # write to hdfs
        chunk_filename = '%s_seed_%s_chunk_%s.pkl.gz' \
            % (chunk_filename_prefix, original_SEED, ith_chunk)
        fu.pickle(dict_out, chunk_filename)
        hu.put_hdfs(None, chunk_filename, chunk_dest_dir)
        #
        steps_done += chunk_size
    chunk_filename = '%s_seed_%s_chunk_%s.pkl.gz' \
        % (chunk_filename_prefix, original_SEED, 'FINAL')
    fu.pickle(dict_out, chunk_filename)
    hu.put_hdfs(None, chunk_filename, chunk_dest_dir)
    return dict_out
    
def time_analyze_helper(table_data, data_dict, command_dict):
    # FIXME: this is a kludge
    command_dict.update(data_dict)
    #
    gen_seed = data_dict['SEED']
    num_clusters = data_dict['num_clusters']
    num_cols = data_dict['num_cols']
    num_rows = data_dict['num_rows']
    num_views = data_dict['num_views']

    T, M_c, M_r, X_L, X_D = ttu.generate_clean_state(gen_seed,
                                                 num_clusters,
                                                 num_cols, num_rows,
                                                 num_views,
                                                 max_mean=10, max_std=1)
    table_data = dict(T=T,M_c=M_c)

    data_dict['X_L'] = X_L
    data_dict['X_D'] = X_D
    start_dims = du.get_state_shape(X_L)
    with gu.Timer('time_analyze_helper', verbose=False) as timer:
        inner_ret_dict = analyze_helper(table_data, data_dict, command_dict)
    end_dims = du.get_state_shape(inner_ret_dict['X_L'])
    T = table_data['T']
    table_shape = (len(T), len(T[0]))
    ret_dict = dict(
        table_shape=table_shape,
        start_dims=start_dims,
        end_dims=end_dims,
        elapsed_secs=timer.elapsed_secs,
        kernel_list=command_dict['kernel_list'],
        n_steps=command_dict['n_steps'],
        )
    return ret_dict

def mi_analyze_helper(table_data, data_dict, command_dict):

    gen_seed = data_dict['SEED']
    crosscat_seed = data_dict['CCSEED']
    num_clusters = data_dict['num_clusters']
    num_cols = data_dict['num_cols']
    num_rows = data_dict['num_rows']
    num_views = data_dict['num_views']
    corr = data_dict['corr']
    burn_in = data_dict['burn_in']
    mean_range = float(num_clusters)*2.0

    # 32 bit signed int
    random.seed(gen_seed)
    get_next_seed = lambda : random.randrange(2147483647)

    # generate the stats
    T, M_c, M_r, X_L, X_D, view_assignment = mitu.generate_correlated_state(num_rows,
        num_cols, num_views, num_clusters, mean_range, corr, seed=gen_seed);

    table_data = dict(T=T,M_c=M_c)

    engine = LE.LocalEngine(crosscat_seed)
    X_L_prime, X_D_prime = engine.analyze(M_c, T, X_L, X_D, n_steps=burn_in) 

    X_L = X_L_prime
    X_D = X_D_prime

    view_assignment = numpy.array(X_L['column_partition']['assignments'])
 
    # for each view calclate the average MI between all pairs of columns
    n_views = max(view_assignment)+1
    MI = []
    Linfoot = []
    queries = []
    MI = 0.0
    pairs = 0.0
    for view in range(n_views):
        columns_in_view = numpy.nonzero(view_assignment==view)[0]
        combinations = itertools.combinations(columns_in_view,2)
        for pair in combinations:
            any_pairs = True
            queries.append(pair)
            MI_i, Linfoot_i = iu.mutual_information(M_c, [X_L], [X_D], [pair], n_samples=1000)
            MI += MI_i[0][0]
            pairs += 1.0

    
    if pairs > 0.0:
        MI /= pairs

    ret_dict = dict(
        id=data_dict['id'],
        dataset=data_dict['dataset'],
        sample=data_dict['sample'],
        mi=MI,
        )

    return ret_dict

def convergence_analyze_helper(table_data, data_dict, command_dict):
    gen_seed = data_dict['SEED']
    num_clusters = data_dict['num_clusters']
    num_cols = data_dict['num_cols']
    num_rows = data_dict['num_rows']
    num_views = data_dict['num_views']
    max_mean = data_dict['max_mean']
    n_test = data_dict['n_test']
    num_transitions = data_dict['n_steps']
    block_size = data_dict['block_size']
    init_seed = data_dict['init_seed']


    # generate some data
    T, M_r, M_c, data_inverse_permutation_indices = \
            du.gen_factorial_data_objects(gen_seed, num_clusters,
                    num_cols, num_rows, num_views,
                    max_mean=max_mean, max_std=1,
                    send_data_inverse_permutation_indices=True)
    view_assignment_ground_truth = \
            ctu.determine_synthetic_column_ground_truth_assignments(num_cols,
                    num_views)
    X_L_gen, X_D_gen = ttu.get_generative_clustering(M_c, M_r, T,
            data_inverse_permutation_indices, num_clusters, num_views)
    T_test = ctu.create_test_set(M_c, T, X_L_gen, X_D_gen, n_test, seed_seed=0)
    generative_mean_test_log_likelihood = \
            ctu.calc_mean_test_log_likelihood(M_c, T, X_L_gen, X_D_gen, T_test)

    # additional set up
    engine=LE.LocalEngine(init_seed)
    column_ari_list = []
    mean_test_ll_list = []
    elapsed_seconds_list = []

    # get initial ARI, test_ll
    with gu.Timer('initialize', verbose=False) as timer:
        X_L, X_D = engine.initialize(M_c, M_r, T, initialization='from_the_prior')
    column_ari = ctu.get_column_ARI(X_L, view_assignment_ground_truth)
    column_ari_list.append(column_ari)
    mean_test_ll = ctu.calc_mean_test_log_likelihood(M_c, T, X_L, X_D,
            T_test)
    mean_test_ll_list.append(mean_test_ll)
    elapsed_seconds_list.append(timer.elapsed_secs)

    # run blocks of transitions, recording ARI, test_ll progression
    completed_transitions = 0
    n_steps = min(block_size, num_transitions)
    while (completed_transitions < num_transitions):
        # We won't be limiting by time in the convergence runs
        with gu.Timer('initialize', verbose=False) as timer:
             X_L, X_D = engine.analyze(M_c, T, X_L, X_D, kernel_list=(),
                     n_steps=n_steps, max_time=-1)
        completed_transitions = completed_transitions + block_size
        #
        column_ari = ctu.get_column_ARI(X_L, view_assignment_ground_truth)
        column_ari_list.append(column_ari)
        mean_test_ll = ctu.calc_mean_test_log_likelihood(M_c, T, X_L, X_D,
                T_test)
        mean_test_ll_list.append(mean_test_ll)
        elapsed_seconds_list.append(timer.elapsed_secs)

    ret_dict = dict(
        num_rows=num_rows,
        num_cols=num_cols,
        num_views=num_views,
        num_clusters=num_clusters,
        max_mean=max_mean,
        column_ari_list=column_ari_list,
        mean_test_ll_list=mean_test_ll_list,
        generative_mean_test_log_likelihood=generative_mean_test_log_likelihood,
        elapsed_seconds_list=elapsed_seconds_list,
        n_steps=num_transitions,
        block_size=block_size,
        )
    return ret_dict
    

method_lookup = dict(
    initialize=initialize_helper,
    analyze=analyze_helper,
    time_analyze=time_analyze_helper,
    convergence_analyze=convergence_analyze_helper,
    chunk_analyze=chunk_analyze_helper,
    mi_analyze=mi_analyze_helper
    )


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--table_data_filename', type=str,
                        default=hs.default_table_data_filename)
    parser.add_argument('--command_dict_filename', type=str,
                        default=hs.default_command_dict_filename)
    args = parser.parse_args()
    table_data_filename = args.table_data_filename
    command_dict_filename = args.command_dict_filename
    
    
    table_data = fu.unpickle(table_data_filename)
    command_dict = fu.unpickle(command_dict_filename)
    command = command_dict['command']
    method = method_lookup[command]
    #
    from signal import signal, SIGPIPE, SIG_DFL 
    signal(SIGPIPE,SIG_DFL) 
    for line in sys.stdin:
        key, data_dict = xu.parse_hadoop_line(line)
        ret_dict = method(table_data, data_dict, command_dict)
        xu.write_hadoop_line(sys.stdout, key, ret_dict)

########NEW FILE########
__FILENAME__ = automated_convergence_tests
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import os
import csv
import argparse
import tempfile
import time
import itertools
from collections import namedtuple
#
import numpy
#
import crosscat.utils.data_utils as du
import crosscat.utils.hadoop_utils as hu
import crosscat.utils.file_utils as fu
import crosscat.utils.xnet_utils as xu
import crosscat.LocalEngine as LE
import crosscat.HadoopEngine as HE
import crosscat.cython_code.State as State
import crosscat.convergence_analysis.parse_convergence_results as parse_cr
import crosscat.convergence_analysis.plot_convergence_results as plot_cr


def generate_hadoop_dicts(convergence_run_parameters, args_dict):
    dict_to_write = dict(convergence_run_parameters)
    dict_to_write.update(args_dict)
    yield dict_to_write

def write_hadoop_input(input_filename, convergence_run_parameters, n_steps, block_size, SEED):
    # prep settings dictionary
    convergence_analyze_args_dict = xu.default_analyze_args_dict
    convergence_analyze_args_dict['command'] = 'convergence_analyze'
    convergence_analyze_args_dict['SEED'] = SEED
    convergence_analyze_args_dict['n_steps'] = n_steps
    convergence_analyze_args_dict['block_size'] = block_size
    #
    n_tasks = 0
    with open(input_filename, 'a') as out_fh:
        dict_generator = generate_hadoop_dicts(convergence_run_parameters, convergence_analyze_args_dict)
        for dict_to_write in dict_generator:
            xu.write_hadoop_line(out_fh, key=dict_to_write['SEED'], dict_to_write=dict_to_write)
            n_tasks += 1
    return n_tasks

if __name__ == '__main__':
    default_num_rows_list = [200, 400, 1000]
    default_num_cols_list = [8, 16, 32]
    default_num_clusters_list = [5,10]
    default_num_splits_list = [2, 4]
    default_max_mean_list = [0.5, 1, 2]
    #
    parser = argparse.ArgumentParser()
    parser.add_argument('--gen_seed', type=int, default=0)
    parser.add_argument('--n_steps', type=int, default=500)
    parser.add_argument('--num_chains', type=int, default=50)
    parser.add_argument('--block_size', type=int, default=20)
    parser.add_argument('-do_local', action='store_true')
    parser.add_argument('--which_engine_binary', type=str,
                        default=HE.default_engine_binary)
    parser.add_argument('-do_remote', action='store_true')
    parser.add_argument('-do_plot', action='store_true')
    parser.add_argument('--num_rows_list', type=int, nargs='*',
            default=default_num_rows_list)
    parser.add_argument('--num_cols_list', type=int, nargs='*',
            default=default_num_cols_list)
    parser.add_argument('--num_clusters_list', type=int, nargs='*',
            default=default_num_clusters_list)
    parser.add_argument('--num_splits_list', type=int, nargs='*',
            default=default_num_splits_list)
    parser.add_argument('--max_mean_list', type=float, nargs='*',
            default=default_max_mean_list)
    #
    args = parser.parse_args()
    gen_seed = args.gen_seed
    n_steps = args.n_steps
    do_local = args.do_local
    num_chains = args.num_chains
    do_remote = args.do_remote
    do_plot = args.do_plot
    block_size = args.block_size
    num_rows_list = args.num_rows_list
    num_cols_list = args.num_cols_list
    num_clusters_list = args.num_clusters_list
    num_splits_list = args.num_splits_list
    max_mean_list = args.max_mean_list
    which_engine_binary = args.which_engine_binary
    #
    print 'using num_rows_list: %s' % num_rows_list
    print 'using num_cols_list: %s' % num_cols_list
    print 'using num_clusters_list: %s' % num_clusters_list
    print 'using num_splits_list: %s' % num_splits_list
    print 'using max_mean_list: %s' % max_mean_list
    print 'using engine_binary: %s' % which_engine_binary
    time.sleep(2)


    script_filename = 'hadoop_line_processor.py'
    # some hadoop processing related settings
    dirname = 'convergence_analysis'
    fu.ensure_dir(dirname)
    temp_dir = tempfile.mkdtemp(prefix='convergence_analysis_',
                                dir=dirname)
    print 'using dir: %s' % temp_dir
    #
    table_data_filename = os.path.join(temp_dir, 'table_data.pkl.gz')
    input_filename = os.path.join(temp_dir, 'hadoop_input')
    output_filename = os.path.join(temp_dir, 'hadoop_output')
    output_path = os.path.join(temp_dir, 'output')  
    parsed_out_file = os.path.join(temp_dir, 'parsed_convergence_output.csv')


    parameter_list = [num_rows_list, num_cols_list, num_clusters_list, num_splits_list]

    n_tasks = 0
    gen_seed = -1
    # Iterate over the parameter values and write each run as a line in the hadoop_input file
    take_product_of = [num_rows_list, num_cols_list, num_clusters_list, num_splits_list, max_mean_list]
    for num_rows, num_cols, num_clusters, num_splits, max_mean in itertools.product(*take_product_of):
        if numpy.mod(num_rows, num_clusters) == 0 and numpy.mod(num_cols, num_splits) == 0:
          gen_seed = gen_seed + 1
          for chainindx in range(num_chains):
              convergence_run_parameters = dict(num_rows=num_rows, num_cols=num_cols,
                      num_views=num_splits, num_clusters=num_clusters, max_mean=max_mean,
                      n_test=100,
                      init_seed=chainindx)
              n_tasks += write_hadoop_input(input_filename,
                      convergence_run_parameters,  n_steps, block_size,
                      SEED=gen_seed)

    # Create a dummy table data file
    table_data=dict(T=[],M_c=[],X_L=[],X_D=[])
    fu.pickle(table_data, table_data_filename)

    if do_local:
        xu.run_script_local(input_filename, script_filename, output_filename, table_data_filename)
        print 'Local Engine for automated convergence runs has not been completely implemented/tested'
    elif do_remote:
        hadoop_engine = HE.HadoopEngine(which_engine_binary=which_engine_binary,
                output_path=output_path,
                input_filename=input_filename,
                table_data_filename=table_data_filename)
        xu.write_support_files(table_data, hadoop_engine.table_data_filename,
                              dict(command='convergence_analyze'), hadoop_engine.command_dict_filename)
        hadoop_engine.send_hadoop_command(n_tasks=n_tasks)
        was_successful = hadoop_engine.get_hadoop_results()
        if was_successful:
            hu.copy_hadoop_output(hadoop_engine.output_path, output_filename)
            parse_cr.parse_to_csv(output_filename, parsed_out_file)
        else:
            print 'remote hadoop job NOT successful'
    else:
        # print what the command would be
        hadoop_engine = HE.HadoopEngine(which_engine_binary=which_engine_binary,
                output_path=output_path,
                input_filename=input_filename,
                table_data_filename=table_data_filename)
        cmd_str = hu.create_hadoop_cmd_str(
                hadoop_engine.hdfs_uri, hadoop_engine.hdfs_dir, hadoop_engine.jobtracker_uri,
                hadoop_engine.which_engine_binary, hadoop_engine.which_hadoop_binary,
                hadoop_engine.which_hadoop_jar,
                hadoop_engine.input_filename, hadoop_engine.table_data_filename,
                hadoop_engine.command_dict_filename, hadoop_engine.output_path,
                n_tasks, hadoop_engine.one_map_task_per_line)
        print cmd_str

    if do_plot and (do_local or do_remote):
      convergence_metrics_dict = plot_cr.parse_convergence_metrics_csv(parsed_out_file)
      for run_key, convergence_metrics in convergence_metrics_dict.iteritems():
        save_filename = str(run_key) + '.png'
        fh = plot_cr.plot_convergence_metrics(convergence_metrics,
            title_append=str(run_key), save_filename=save_filename)
            

########NEW FILE########
__FILENAME__ = convergence_test
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import argparse
import csv
import time
#
import crosscat.utils.data_utils as du
import crosscat.CrossCatClient as ccc
import crosscat.utils.file_utils as f_utils
import crosscat.utils.convergence_test_utils as ctu


# Parse input arguments
parser = argparse.ArgumentParser()
parser.add_argument('--filename', default=None,
                    type=str)
parser.add_argument('--ari_logfile', default='daily_ari_logs.csv',
                    type=str)
parser.add_argument('--inf_seed', default=0, type=int)
parser.add_argument('--gen_seed', default=0, type=int)
parser.add_argument('--num_transitions', default=500, type=int)
parser.add_argument('--N_GRID', default=31, type=int)
parser.add_argument('--max_rows', default=1000, type=int)
parser.add_argument('--num_clusters', default=10, type=int)
parser.add_argument('--num_views', default=2, type=int)
parser.add_argument('--num_cols', default=16, type=int)
parser.add_argument('--numChains',default=50, type = int)
parser.add_argument('--block_size',default=20, type = int)
#
args = parser.parse_args()
filename = args.filename
ari_logfile = args.ari_logfile
inf_seed = args.inf_seed
gen_seed = args.gen_seed
num_transitions = args.num_transitions
N_GRID = args.N_GRID
max_rows = args.max_rows
num_clusters = args.num_clusters
num_views = args.num_views
num_cols = args.num_cols
numChains = args.numChains
block_size = args.block_size


engine = ccc.get_CrossCatClient('hadoop', seed = inf_seed)

if filename is not None:
    # Load the data from table and sub-sample entities to max_rows
    T, M_r, M_c = du.read_model_data_from_csv(filename, max_rows, gen_seed)
    truth_flag = 0
else:
    T, M_r, M_c, data_inverse_permutation_indices = \
        du.gen_factorial_data_objects(gen_seed, num_clusters,
                                      num_cols, max_rows, num_views,
                                      max_mean=100, max_std=1,
                                      send_data_inverse_permutation_indices=True)
    view_assignment_truth, X_D_truth = ctu.truth_from_permute_indices(data_inverse_permutation_indices, max_rows,num_cols,num_views, num_clusters)
    truth_flag = 1

        
num_rows = len(T)
num_cols = len(T[0])

ari_table = []
ari_views = []

print 'Initializing ...'
# Call Initialize and Analyze
M_c, M_r, X_L_list, X_D_list = engine.initialize(M_c, M_r, T, n_chains = numChains)
if truth_flag:
    tmp_ari_table, tmp_ari_views = ctu.multi_chain_ARI(X_L_list,X_D_list, view_assignment_truth, X_D_truth)
    ari_table.append(tmp_ari_table)
    ari_views.append(tmp_ari_views)
            
completed_transitions = 0

n_steps = min(block_size, num_transitions)
print 'Analyzing ...'
while (completed_transitions < num_transitions):
    # We won't be limiting by time in the convergence runs
    X_L_list, X_D_list = engine.analyze(M_c, T, X_L_list, X_D_list, kernel_list=(),
                                        n_steps=n_steps, max_time=-1)
    
    if truth_flag:
        tmp_ari_table, tmp_ari_views = ctu.multi_chain_ARI(X_L_list,X_D_list, view_assignment_truth, X_D_truth)
        ari_table.append(tmp_ari_table)
        ari_views.append(tmp_ari_views)
        
    else:
        # Not sure we want to save the models for convergence testing 
        saved_dict = {'T':T, 'M_c':M_c, 'X_L_list':X_L_list, 'X_D_list': X_D_list}
        pkl_filename = 'model_{!s}.pkl.gz'.format(str(completed_transitions))
        f_utils.pickle(saved_dict, filename = pkl_filename)

    completed_transitions = completed_transitions+block_size
    print completed_transitions
    
# Always save the last model
saved_dict = {'T':T, 'M_c':M_c, 'X_L_list':X_L_list, 'X_D_list': X_D_list}
pkl_filename = 'model_{!s}.pkl.gz'.format('last')
f_utils.pickle(saved_dict, filename = pkl_filename)

if truth_flag:
    with open(ari_logfile, 'a') as outfile:
        csvwriter=csv.writer(outfile,delimiter=',')
        csvwriter.writerow([time.ctime(), num_transitions, block_size, max_rows, num_cols, num_views, num_clusters, ari_views, ari_table])

########NEW FILE########
__FILENAME__ = generate_convergence_script
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import itertools
import csv
import os

ari_filename = 'ari_convergence_results.csv'
n_steps = 500
block_size = 20
run_script = False
#
base_str = ' '.join([
  'python convergence_test.py',
  '--max_rows %s',
  '--num_cols %s',
  '--num_clusters %s',
  '--num_views %s',
  '--block_size %s' % block_size,
  '--num_transitions %s' % n_steps,
  '--ari_logfile %s' % ari_filename,
  '>>out 2>>err',
  ])

# num_rows_list = [100, 400, 1000, 4000, 10000]
# num_cols_list = [4, 8, 16, 24, 32]
# num_clusters_list = [10, 20, 30, 40, 50]
# num_splits_list = [1, 2, 3, 4, 5]

num_rows_list = [200, 400]
num_cols_list = [4, 8]
num_clusters_list = [5, 10]
num_splits_list = [2,4]

# First create the headers in the output file - the convergence test script does not write headers
with open(ari_filename, 'w') as outfile:
  csvwriter=csv.writer(outfile,delimiter=',')
  header = ['Time', 'num_transitions', 'block_size', 'num_rows','num_cols','num_views','num_clusters','ari_views','ari_table']
  csvwriter.writerow(header)

outfile.close()
count = 0
script_name = 'convergence_testing_script.sh'
with open(script_name, 'w') as script_file:
    take_product_of = [num_rows_list, num_cols_list, num_clusters_list, num_splits_list]
    for num_rows, num_cols, num_clusters, num_splits \
        in itertools.product(*take_product_of):
        this_base_str = base_str % (num_rows, num_cols, num_clusters, num_splits)
        print this_base_str
        count = count + 1
        script_file.write(this_base_str + '\n')

script_file.close()

if run_script:
  os.system('bash convergence_testing_script.sh')

########NEW FILE########
__FILENAME__ = parse_convergence_results
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import sys
import csv
#
import crosscat.utils.xnet_utils as xu


def get_line_label(parsed_line):
    return int(parsed_line[0])
def extract_variables(parsed_line, variable_names_to_extract):
    variable_dict = parsed_line[1]
    variables = [
            variable_dict[variable_name]
            for variable_name in variable_names_to_extract
            ]
    return variables

def parsed_line_to_output_row(parsed_line, variable_names_to_extract,
        get_line_label=get_line_label):
    line_label = get_line_label(parsed_line)
    variables = extract_variables(parsed_line, variable_names_to_extract)
    ret_list = [line_label] + variables
    return ret_list

def parse_to_csv(in_filename, out_filename='parsed_convergence.csv'):
    variable_names_to_extract = ['num_rows', 'num_cols', 'num_clusters', 'num_views',
            'max_mean', 'n_steps', 'block_size','column_ari_list',
            'generative_mean_test_log_likelihood','mean_test_ll_list',
            'elapsed_seconds_list']
    header = ['experiment'] + variable_names_to_extract
    with open(in_filename) as in_fh:
      with open(out_filename,'w') as out_fh:
        csvwriter = csv.writer(out_fh)
        csvwriter.writerow(header)
        for line in in_fh:
            try:
              parsed_line = xu.parse_hadoop_line(line)
              output_row = parsed_line_to_output_row(parsed_line,
                      variable_names_to_extract=variable_names_to_extract)
              csvwriter.writerow(output_row)
            except Exception, e:
              sys.stderr.write(line + '\n' + str(e) + '\n')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('in_filename', type=str)
    parser.add_argument('--out_filename', type=str,
            default='parsed_convergence.csv')
    args = parser.parse_args()
    in_filename = args.in_filename
    out_filename = args.out_filename
    parse_to_csv(in_filename, out_filename)

########NEW FILE########
__FILENAME__ = plot_convergence_results
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import csv
import argparse
import collections
#
import pylab
pylab.ion()
pylab.show()


# settings
run_key_fields = ['num_rows', 'num_cols', 'num_clusters', 'num_views', 'max_mean']
dict_subset_keys = ['column_ari_list', 'mean_test_ll_list',
        'elapsed_seconds_list']


# set up some helper functions
def get_dict_values_subset(in_dict, keys_subset):
    values_subset = [in_dict[key] for key in keys_subset]
    return values_subset

def get_dict_subset(in_dict, keys_subset):
    values_subset = get_dict_values_subset(in_dict, keys_subset)
    dict_subset = dict(zip(keys_subset, values_subset))
    return dict_subset

def _get_run_key(line_dict):
    values = get_dict_values_subset(line_dict, run_key_fields)
    run_key = tuple(values)
    return run_key

def _get_run_key_dummy(line_dict):
    return 'all'

def get_default_dict():
    ret_dict = dict((key, list()) for key in dict_subset_keys)
    ret_dict['iter_idx_list'] = list()
    return ret_dict

def update_convergence_metrics(convergence_metrics, new_values_dict):
    for key, value in new_values_dict.iteritems():
        convergence_metrics[key].append(value)
    return convergence_metrics

def get_iter_indices(line_dict):
    n_steps = line_dict['n_steps']
    block_size = line_dict['block_size']
    num_blocks = n_steps / block_size + 1
    iter_indices = pylab.arange(num_blocks) * block_size
    return iter_indices

def plot_convergence_metrics(convergence_metrics, title_append='',
        x_is_iters=False, save_filename=None):
    x_variable = None
    x_label = None
    if x_is_iters:
        x_variable = pylab.array(convergence_metrics['iter_idx_list']).T
        x_label = 'iter idx'
    else:
        x_variable = pylab.array(convergence_metrics['elapsed_seconds_list']).T
        x_variable = x_variable.cumsum(axis=0)
        x_label = 'cumulative time (seconds)'
    ari_arr = pylab.array(convergence_metrics['column_ari_list']).T
    mean_test_ll_arr = pylab.array(convergence_metrics['mean_test_ll_list']).T
    #
    fh = pylab.figure()
    pylab.subplot(211)
    pylab.title('convergence diagnostics: %s' % title_append)
    pylab.plot(x_variable, ari_arr)
    pylab.xlabel(x_label)
    pylab.ylabel('column ARI')
    pylab.subplot(212)
    pylab.plot(x_variable, mean_test_ll_arr)
    pylab.xlabel(x_label)
    pylab.ylabel('mean test log likelihood')
    #
    if save_filename is not None:
      pylab.savefig(save_filename)
    return fh

def parse_convergence_metrics_csv(filename, get_run_key=_get_run_key):
    convergence_metrics_dict = collections.defaultdict(get_default_dict)
    with open(filename) as fh:
        csv_reader = csv.reader(fh)
        header = csv_reader.next()
        for line in csv_reader:
            evaled_line = map(eval, line)
            line_dict = dict(zip(header, evaled_line))
            run_key = get_run_key(line_dict)
            convergence_metrics = convergence_metrics_dict[run_key]
            new_values_dict = get_dict_subset(line_dict, dict_subset_keys) 
            new_values_dict['iter_idx_list'] = get_iter_indices(line_dict)
            update_convergence_metrics(convergence_metrics, new_values_dict)
    return convergence_metrics_dict

def filter_join(in_list, joinwith):
    in_list = filter(None, in_list)
    return joinwith.join(in_list)


if __name__ == '__main__':
    # parse some arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', type=str)
    parser.add_argument('-one_plot', action='store_true')
    parser.add_argument('-x_is_iters', action='store_true')
    parser.add_argument('-do_save', action='store_true')
    parser.add_argument('--save_filename_prefix', type=str, default=None)
    #
    args = parser.parse_args()
    filename = args.filename
    one_plot = args.one_plot
    x_is_iters = args.x_is_iters
    do_save = args.do_save
    save_filename_prefix = args.save_filename_prefix
    #
    get_run_key = _get_run_key
    if one_plot:
        get_run_key = _get_run_key_dummy

    # parse the csv
    convergence_metrics_dict = parse_convergence_metrics_csv(filename)

    # actually plot
    fh_list = []
    save_filename = None
    for run_key, convergence_metrics in convergence_metrics_dict.iteritems():
      if do_save:
        n_bins = 20
        cumulative = True
        #
        filename_parts = [save_filename_prefix, str(run_key), 'timeseries.png']
        timeseries_save_filename = filter_join(filename_parts, '_')
        filename_parts = [save_filename_prefix, str(run_key), 'test_ll_hist.png']
        test_ll_hist_save_filename = filter_join(filename_parts, '_')
        filename_parts = [save_filename_prefix, str(run_key), 'runtime_hist.png']
        runtime_hist_save_filename = filter_join(filename_parts, '_')
        #
        pylab.figure()
        test_lls = pylab.array(convergence_metrics['mean_test_ll_list'])
        final_test_lls = test_lls[:, -1]
        pylab.hist(final_test_lls, n_bins, cumulative=cumulative)
        pylab.savefig(test_ll_hist_save_filename)
        #
        pylab.figure()
        final_times = pylab.array(convergence_metrics['elapsed_seconds_list']).T
        final_times = final_times.cumsum(axis=0)
        final_times = final_times[-1, :]
        pylab.hist(final_times, n_bins, cumulative=cumulative)
        pylab.savefig(runtime_hist_save_filename)
      fh = plot_convergence_metrics(convergence_metrics,
          title_append=str(run_key), x_is_iters=x_is_iters,
          save_filename=timeseries_save_filename)
      fh_list.append(fh)
      #


########NEW FILE########
__FILENAME__ = CrossCatClient
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import os
import inspect
#


class CrossCatClient(object):
    """ A client interface that gives a singular interface to all the different
    engines

    Depending on the client_type, dispatch to the appropriate engine constructor

    """

    def __init__(self, engine):
        """Initialize client with given engine

        Not to be called directly!

        """

        self.engine = engine
        return

    def __getattribute__(self, name):
        engine = object.__getattribute__(self, 'engine')
        attr = None
        if hasattr(engine, name):
            attr = getattr(engine, name)
        else:
            attr = object.__getattribute__(self, name)
        return attr

# Maybe this should be in CrossCatClient.__init__
def get_CrossCatClient(client_type, **kwargs):
    """Helper which instantiates the appropriate Engine and returns a Client

    """

    client = None
    if client_type == 'local':
        import crosscat.LocalEngine as LocalEngine
        le = LocalEngine.LocalEngine(**kwargs)
        client = CrossCatClient(le)
    elif client_type == 'hadoop':
        import crosscat.HadoopEngine as HadoopEngine
        he = HadoopEngine.HadoopEngine(**kwargs)
        client = CrossCatClient(he)
    elif client_type == 'jsonrpc':
        import crosscat.JSONRPCEngine as JSONRPCEngine
        je = JSONRPCEngine.JSONRPCEngine(**kwargs)
        client = CrossCatClient(je)
    elif client_type == 'multiprocessing':
        import crosscat.MultiprocessingEngine as MultiprocessingEngine
        me =  MultiprocessingEngine.MultiprocessingEngine(**kwargs)
        client = CrossCatClient(me)
    else:
        raise Exception('unknown client_type: %s' % client_type)
    return client


if __name__ == '__main__':
    import crosscat.utils.data_utils as du
    ccc = get_CrossCatClient('local', seed=0)
    #
    gen_seed = 0
    num_clusters = 4
    num_cols = 8
    num_rows = 16
    num_splits = 1
    max_mean = 10
    max_std = 0.1
    T, M_r, M_c = du.gen_factorial_data_objects(
        gen_seed, num_clusters,
        num_cols, num_rows, num_splits,
        max_mean=max_mean, max_std=max_std,
        )
    #
    X_L, X_D, = ccc.initialize(M_c, M_r, T)
    X_L_prime, X_D_prime = ccc.analyze(M_c, T, X_L, X_D)
    X_L_prime, X_D_prime = ccc.analyze(M_c, T, X_L_prime, X_D_prime)
    #
    ccc = get_CrossCatClient('jsonrpc', seed=0, URI='http://localhost:8007')
    X_L, X_D, = ccc.initialize(M_c, M_r, T)
    X_L_prime, X_D_prime = ccc.analyze(M_c, T, X_L, X_D)
    X_L_prime, X_D_prime = ccc.analyze(M_c, T, X_L_prime, X_D_prime)
    

########NEW FILE########
__FILENAME__ = continuous_component_model_test
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import ContinuousComponentModel as CCM


hyper_map = dict()
hyper_map["mu"] = 1.0
hyper_map["s"] = 1.0
hyper_map["nu"] = 1.0
hyper_map["r"] = 2.0

CCM.set_string_double_map(hyper_map)
component_model = CCM.p_ContinuousComponentModel(hyper_map)
print component_model.calc_marginal_logp()
component_model.insert_element(2.3)
print component_model.calc_marginal_logp()
print component_model
print "component_model.get_draw(0):", component_model.get_draw(0)
print "component_model.get_draw(1):", component_model.get_draw(1)
component_model.remove_element(2.3)
print component_model.calc_marginal_logp()

########NEW FILE########
__FILENAME__ = mixed_state_test
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import argparse
#
import pylab
import numpy
#
import crosscat.cython_code.State as State
import crosscat.utils.data_utils as du


# parse input
parser = argparse.ArgumentParser()
parser.add_argument('--gen_seed', default=0, type=int)
parser.add_argument('--inf_seed', default=0, type=int)
parser.add_argument('--num_clusters', default=4, type=int)
parser.add_argument('--num_cols', default=4, type=int)
parser.add_argument('--num_rows', default=2000, type=int)
parser.add_argument('--num_splits', default=1, type=int)
parser.add_argument('--max_mean', default=10, type=float)
parser.add_argument('--max_std', default=0.3, type=float)
parser.add_argument('--num_transitions', default=100, type=int)
parser.add_argument('--N_GRID', default=31, type=int)
args = parser.parse_args()
#
gen_seed = args.gen_seed
inf_seed = args.inf_seed
num_clusters = args.num_clusters
num_cols = args.num_cols
num_rows = args.num_rows
num_splits = args.num_splits
max_mean = args.max_mean
max_std = args.max_std
num_transitions = args.num_transitions
N_GRID = args.N_GRID

p_multinomial = .5
random_state = numpy.random.RandomState(gen_seed)
is_multinomial = random_state.binomial(1, p_multinomial, num_cols)
multinomial_column_indices = numpy.nonzero(is_multinomial)[0]

# create the data
if True:
    T, M_r, M_c = du.gen_factorial_data_objects(
        gen_seed, num_clusters,
        num_cols, num_rows, num_splits,
        max_mean=max_mean, max_std=max_std,
        )
else:
    with open('SynData2.csv') as fh:
        import numpy
        import csv
        T = numpy.array([
                row for row in csv.reader(fh)
                ], dtype=float).tolist()
        M_r = du.gen_M_r_from_T(T)
        M_c = du.gen_M_c_from_T(T)

T = du.discretize_data(T, multinomial_column_indices)
T, M_c = du.convert_columns_to_multinomial(T, M_c,
                                           multinomial_column_indices)

# create the state
p_State = State.p_State(M_c, T, N_GRID=N_GRID, SEED=inf_seed)
p_State.plot_T(filename='T')
print M_c
print numpy.array(T)
print p_State
print "multinomial_column_indices: %s" % str(multinomial_column_indices)

def summarize_p_State(p_State):
    counts = [
        view_state['row_partition_model']['counts']
        for view_state in p_State.get_X_L()['view_state']
        ]
    format_list = '; '.join([
            "s.num_views: %s",
            "cluster counts: %s",
            "s.column_crp_score: %.3f",
            "s.data_score: %.1f",
            "s.score:%.1f",
            ])
    values_tuple = (
        p_State.get_num_views(),
        str(counts),
        p_State.get_column_crp_score(),
        p_State.get_data_score(),
        p_State.get_marginal_logp(),
        )
    print format_list % values_tuple    
    if not numpy.isfinite(p_State.get_data_score()):
        print "bad data score"
        print p_State

# transition the sampler
for transition_idx in range(num_transitions):
    print "transition #: %s" % transition_idx
    p_State.transition()
    summarize_p_State(p_State)
    iter_idx = None
    pkl_filename = 'last_iter_pickled_state.pkl.gz'
    plot_filename = 'last_iter_X_D'
    if transition_idx % 10 == 0:
        plot_filename = 'iter_%s_X_D' % transition_idx
        pkl_filename = 'iter_%s_pickled_state.pkl.gz' % transition_idx
    p_State.save(filename=pkl_filename, M_c=M_c, T=T)
    p_State.plot(filename=plot_filename)

########NEW FILE########
__FILENAME__ = state_test
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import argparse
#
import pylab
import numpy
#
import crosscat.cython_code.State as State
import crosscat.utils.data_utils as du


# parse input
parser = argparse.ArgumentParser()
parser.add_argument('--gen_seed', default=0, type=int)
parser.add_argument('--inf_seed', default=0, type=int)
parser.add_argument('--num_clusters', default=4, type=int)
parser.add_argument('--num_cols', default=16, type=int)
parser.add_argument('--num_rows', default=300, type=int)
parser.add_argument('--num_splits', default=2, type=int)
parser.add_argument('--max_mean', default=10, type=float)
parser.add_argument('--max_std', default=0.3, type=float)
parser.add_argument('--num_transitions', default=300, type=int)
parser.add_argument('--N_GRID', default=31, type=int)
args = parser.parse_args()
#
gen_seed = args.gen_seed
inf_seed = args.inf_seed
num_clusters = args.num_clusters
num_cols = args.num_cols
num_rows = args.num_rows
num_splits = args.num_splits
max_mean = args.max_mean
max_std = args.max_std
num_transitions = args.num_transitions
N_GRID = args.N_GRID

# create the data
if True:
    T, M_r, M_c = du.gen_factorial_data_objects(
        gen_seed, num_clusters,
        num_cols, num_rows, num_splits,
        max_mean=max_mean, max_std=max_std,
        )
else:
    with open('SynData2.csv') as fh:
        import numpy
        import csv
        T = numpy.array([
                row for row in csv.reader(fh)
                ], dtype=float).tolist()
        M_r = du.gen_M_r_from_T(T)
        M_c = du.gen_M_c_from_T(T)


# create the state
p_State = State.p_State(M_c, T, N_GRID=N_GRID, SEED=inf_seed)
p_State.plot_T(filename='T')

# transition the sampler
print "p_State.get_marginal_logp():", p_State.get_marginal_logp()
for transition_idx in range(num_transitions):
    print "transition #: %s" % transition_idx
    p_State.transition()
    counts = [
        view_state['row_partition_model']['counts']
        for view_state in p_State.get_X_L()['view_state']
        ]
    format_list = '; '.join([
            "s.num_views: %s",
            "cluster counts: %s",
            "s.column_crp_score: %.3f",
            "s.data_score: %.1f",
            "s.score:%.1f",
            ])
    values_tuple = (
        p_State.get_num_views(),
        str(counts),
        p_State.get_column_crp_score(),
        p_State.get_data_score(),
        p_State.get_marginal_logp(),
        )
    print format_list % values_tuple
    plot_filename = 'X_D'
    save_filename = 'last_state.pkl.gz'
    if transition_idx % 10 == 0:
        plot_filename = 'iter_%s_X_D' % transition_idx
        save_filename = 'iter_%s_state.pkl.gz' % transition_idx
    p_State.plot(filename=plot_filename)
    p_State.save(filename=save_filename, M_r=M_r, M_c=M_c, T=T)

# # print the final state
# X_D = p_State.get_X_D()
# X_L = p_State.get_X_L()
# print "X_D:", X_D
# print "X_L:", X_L
# for view_idx, view_state_i in enumerate(p_State.get_view_state()):
#     print "view_state_i:", view_idx, view_state_i
# print p_State

# # test generation of state from X_L, X_D
# p_State_2 = State.p_State(M_c, T, X_L, X_D)
# X_D_prime = p_State_2.get_X_D()
# X_L_prime = p_State_2.get_X_L()

# print "X_D_prime:", X_D_prime
# print "X_L_prime:", X_L_prime

# p_State.transition_views(); p_State.get_X_L()['view_state'][0]['row_partition_model']

########NEW FILE########
__FILENAME__ = test_missing_value
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import numpy
import crosscat.cython_code.ContinuousComponentModel as CCM
import crosscat.cython_code.MultinomialComponentModel as MCM
import crosscat.cython_code.State as State

c_hypers = dict(r=10,nu=10,s=10,mu=10)
ccm = CCM.p_ContinuousComponentModel(c_hypers)
print "empty component model"
print ccm
#
for element in [numpy.nan, 0, 1, numpy.nan, 2]:
    print
    ccm.insert_element(element)
    print "inserted %s" % element
    print ccm

m_hypers = dict(dirichlet_alpha=10,K=3)
mcm = MCM.p_MultinomialComponentModel(m_hypers)
print "empty component model"
print mcm

for element in [numpy.nan, 0, 1, numpy.nan, 2]:
    print
    mcm.insert_element(element)
    print "inserted %s" % element
    print mcm

########NEW FILE########
__FILENAME__ = test_multinomial_impute
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import argparse
import sys
from collections import Counter
#
import numpy
import pylab
pylab.ion()
pylab.show()
#
import crosscat.utils.file_utils as fu
import crosscat.utils.sample_utils as su


# parse some arguments
parser = argparse.ArgumentParser()
parser.add_argument('pkl_name', type=str)
parser.add_argument('--inf_seed', default=0, type=int)
args = parser.parse_args(['/usr/local/crosscat/cython_code/iter_90_pickled_state.pkl.gz'])
pkl_name = args.pkl_name
inf_seed = args.inf_seed

random_state = numpy.random.RandomState(inf_seed)
# FIXME: getting weird error on conversion to int: too large from inside pyx
def get_next_seed(max_val=32767): # sys.maxint):
    return random_state.randint(max_val)

# resume from saved name
save_dict = fu.unpickle(pkl_name)
M_c = save_dict['M_c']
X_L = save_dict['X_L']
X_D = save_dict['X_D']
T = save_dict['T']
num_cols = len(X_L['column_partition']['assignments'])
row_idx = 205
col_idx = 13
Q = [(row_idx, col_idx)]
imputed, confidence = su.impute_and_confidence(
    M_c, X_L, X_D, Y=None, Q=Q, n=400, get_next_seed=get_next_seed)

T_array = numpy.array(T)
which_view_idx = X_L['column_partition']['assignments'][col_idx]
X_D_i = numpy.array(X_D[which_view_idx])
which_cluster_idx = X_D_i[row_idx]
which_rows_match_indices = numpy.nonzero(X_D_i==which_cluster_idx)[0]
cluster_vals = T_array[which_rows_match_indices, col_idx]
all_vals = T_array[:, col_idx]
cluster_counter = Counter(cluster_vals)
cluster_ratio = float(cluster_counter[imputed]) / sum(cluster_counter.values())
all_counter = Counter(all_vals)
all_ratio = float(all_counter[imputed]) / sum(all_counter.values())
print
print 'imputed: %s' % imputed
print 'all_ratio: %s' % all_ratio
print 'cluster_ratio: %s' % cluster_ratio
print 'confidence: %s' % confidence

########NEW FILE########
__FILENAME__ = test_pred_prob_and_density
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import random
import argparse
import sys
from collections import Counter
#
import numpy
import pylab

# import crosscat.utils.file_utils as fu
import crosscat.utils.enumerate_utils as eu
import crosscat.utils.sample_utils as su
import crosscat.utils.plot_utils as pu
import crosscat.utils.data_utils as du

import crosscat.cython_code.State as State

random.seed(None)
inf_seed = random.randrange(32767)
# THIS CODE ONLY TESTS CONTINUOUS DATA

# FIXME: getting weird error on conversion to int: too large from inside pyx
def get_next_seed(max_val=32767): # sys.maxint):
    return random_state.randint(max_val)

random_state = numpy.random.RandomState(inf_seed)

# generate a state with two, very distinct clusters
col = numpy.array([0,0])
row = numpy.array([[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]])

p_State, T, M_c, M_r, X_L, X_D = eu.GenerateStateFromPartitions(col,row,std_gen=10000.0, std_data=0.01)

X_L = p_State.get_X_L()
X_D = p_State.get_X_D()

# move stuff around a little bit
for i in range(100):
	p_State.transition(which_transitions=['column_partition_assignments','row_partition_assignments'])

# quick test just to make sure things output what they're supposed to 
x = 0.0;
query_row = len(row[0]) # tests unobserved
# query_row = 3;		# tests observed
Q = [(query_row,0,x)]


Y = [] # no contraints
# Y = [(1,0,.1),(3,0,.1),(22,0,105),(30,0,100)] # generic constraints

p = su.simple_predictive_probability(M_c, X_L, X_D, Y, Q)

n = 1000;
samples = su.simple_predictive_sample(M_c, X_L, X_D, Y, Q, get_next_seed,n=n)

X = [sample[0] for sample in samples]

pylab.figure(facecolor='white')
pdf, bins, patches = pylab.hist(X,50,normed=True, histtype='bar',label='samples',edgecolor='none')
pylab.show()

pdf_max = max(pdf)

Qs = [];
for i in range(n):
    Qtmp = (query_row,0,X[i])
    Qs.append(Qtmp)

Ps = su.simple_predictive_probability(M_c, X_L, X_D, Y, Qs)
Ps2 = su.simple_predictive_probability_density(M_c, X_L, X_D, Y, Qs)

Ps = (numpy.exp(Ps)/max(numpy.exp(Ps)))*pdf_max
Ps2 = (numpy.exp(Ps2)/max(numpy.exp(Ps2)))*pdf_max

# make a scatterplot
pylab.scatter(X,Ps, c='red',label="p from cdf")

pylab.legend(loc='upper left')
pylab.xlabel('value') 
pylab.ylabel('frequency/probability')
pylab.title('TEST: probability and frequencies are not normalized')
pylab.show()

raw_input("Press Enter when finished with probabilty...")

pylab.clf()
pdf, bins, patches = pylab.hist(X,50,normed=True, histtype='bar',label='samples',edgecolor='none')
pylab.scatter(X,Ps2, c='green',label="pdf")

pylab.legend(loc='upper left')
pylab.xlabel('value') 
pylab.ylabel('frequency/density')
pylab.title('TEST: probability and frequencies are not normalized')
pylab.show()

raw_input("Press Enter when finished with density...")

########NEW FILE########
__FILENAME__ = test_sample
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import argparse
import sys
from collections import Counter
#
import numpy
import pylab
pylab.ion()
pylab.show()
#
import crosscat.utils.file_utils as fu
import crosscat.utils.sample_utils as su
import crosscat.utils.plot_utils as pu
import crosscat.utils.api_utils as au


# parse some arguments
parser = argparse.ArgumentParser()
parser.add_argument('pkl_name', type=str)
parser.add_argument('--inf_seed', default=0, type=int)
parser.add_argument('--hostname', default='127.0.0.1', type=str)
args = parser.parse_args()
pkl_name = args.pkl_name
inf_seed = args.inf_seed
hostname = args.hostname

# FIXME: getting weird error on conversion to int: too large from inside pyx
def get_next_seed(max_val=32767): # sys.maxint):
    return random_state.randint(max_val)

# resume from saved name
save_dict = fu.unpickle(pkl_name)
random_state = numpy.random.RandomState(inf_seed)
M_c = save_dict['M_c']
X_L = save_dict['X_L']
X_D = save_dict['X_D']

# FIXME: test constraints
# Y = [su.Bunch(index=2,value=2.3), su.Bunch(index=0,value=-4.)]
Y = None

# test simple_predictive_sample_observed
views_replicating_samples_params = su.determine_replicating_samples_params(X_L, X_D)
views_samples = []
for replicating_samples_params in views_replicating_samples_params:
    this_view_samples = []
    for replicating_sample_params in replicating_samples_params:
        this_view_this_sample = su.simple_predictive_sample(
            M_c, X_L, X_D, get_next_seed=get_next_seed, **replicating_sample_params)
        this_view_samples.extend(this_view_this_sample)
    views_samples.append(this_view_samples)
for view_idx, view_samples in enumerate(views_samples):
    data_array = numpy.array(view_samples)
    pu.plot_T(data_array)
    pylab.title('simple_predictive_sample observed, view %s on local' % view_idx)

# test simple_predictive_sample_observed REMOTE
# hostname = 'ec2-23-22-208-4.compute-1.amazonaws.com'
URI = 'http://' + hostname + ':8007'
method_name = 'simple_predictive_sample'
#
views_samples = []
for replicating_samples_params in views_replicating_samples_params:
    this_view_samples = []
    for replicating_sample_params in replicating_samples_params:
        args_dict = dict(
            M_c=save_dict['M_c'],
            X_L=save_dict['X_L'],
            X_D=save_dict['X_D'],
            Y=replicating_sample_params['Y'],
            Q=replicating_sample_params['Q'],
            n=replicating_sample_params['n'],
            )
        this_view_this_sample, id = au.call(
            method_name, args_dict, URI)
        print id
        this_view_samples.extend(this_view_this_sample)
    views_samples.append(this_view_samples)
for view_idx, view_samples in enumerate(views_samples):
    data_array = numpy.array(view_samples)
    pu.plot_T(data_array)
    pylab.title('simple_predictive_sample observed, view %s on remote' % view_idx)

# test simple_predictive_sample_unobserved
observed_Q = views_replicating_samples_params[0][0]['Q']
Q = [(int(1E6), old_tuple[1]) for old_tuple in observed_Q]
new_row_samples = []
new_row_sample = su.simple_predictive_sample(
    M_c, X_L, X_D, Y, Q, get_next_seed, n=1000)
new_row_samples.extend(new_row_sample)
new_row_samples = numpy.array(new_row_samples)
pu.plot_T(new_row_samples)

# once more with constraint
Y = [(int(1E6), 0, 100)]
new_row_sample = su.simple_predictive_sample(
    M_c, X_L, X_D, Y, Q, get_next_seed, n=1)

# test impute
# imputed_value = su.impute(M_c, X_L, X_D, Y, [Q[3]], 100, get_next_seed)

########NEW FILE########
__FILENAME__ = EngineTemplate
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import crosscat.utils.general_utils as gu


class EngineTemplate(object):

    def __init__(self, seed=None):
        self.seed_generator = gu.int_generator(seed)

    def get_next_seed(self):
        return self.seed_generator.next()

    def initialize(self, M_c, M_r, T, initialization='from_the_prior'):
        M_c, M_r, X_L, X_D = dict(), dict(), dict(), []
        return X_L, X_D

    def analyze(self, M_c, T, X_L, X_D, kernel_list=(), n_steps=1, c=(), r=(),
                max_iterations=-1, max_time=-1, do_diagnostics=False,
                diagnostics_every_N=1,
                ROW_CRP_ALPHA_GRID=(), COLUMN_CRP_ALPHA_GRID=(),
                S_GRID=(), MU_GRID=(),
                N_GRID=31,
                ):
        X_L_prime, X_D_prime = dict(), []
        return X_L_prime, X_D_prime

    def simple_predictive_sample(self, M_c, X_L, X_D, Y, Q, n=1):
        samples = []
        return samples

    def simple_predictive_probability(self, M_c, X_L, X_D, Y, Q, n):
        p = None
        return p

    def simple_predictive_probability_multistate(self, M_c, X_L_list, X_D_list, Y, Q, n):
        p = None
        return p

    def mutual_information(self, M_c, X_L_list, X_D_list, Q, n_samples=1000):
        return None

    def row_structural_typicality(self, X_L_list, X_D_list, row_id):
        return None

    def column_structural_typicality(self, X_L_list, col_id):
        return None

    def predictive_probability(self, M_c, X_L_list, X_D_list, T, q, n=1):
        return None

    def similarity(self, M_c, X_L_list, X_D_list, given_row_id, target_row_id, target_columns=None):
        return None

    def impute(self, M_c, X_L, X_D, Y, Q, n):
        e = None
        return e

    def impute_and_confidence(self, M_c, X_L, X_D, Y, Q, n):
        e, confidence = None, None
        return e, confidence

    def conditional_entropy(M_c, X_L, X_D, d_given, d_target,
                            n=None, max_time=None):
        e = None
        return e

    def predictively_related(self, M_c, X_L, X_D, d,
                                           n=None, max_time=None):
        m = []
        return m

    def contextual_structural_similarity(self, X_D, r, d):
        s = []
        return s

    def structural_similarity(self, X_D, r):
        s = []
        return s

    def structural_anomalousness_columns(self, X_D):
        a = []
        return a

    def structural_anomalousness_rows(self, X_D):
        a = []
        return a

    def predictive_anomalousness(self, M_c, X_L, X_D, T, q, n):
        a = []
        return a


########NEW FILE########
__FILENAME__ = HadoopEngine
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import os
#
import crosscat.utils.file_utils as fu
import crosscat.utils.general_utils as gu
import crosscat.utils.xnet_utils as xu
import crosscat.utils.hadoop_utils as hu
from crosscat.settings import Hadoop as hs


class HadoopEngine(object):
    """A class to dispatch jobs to a Hadoop cluster

    Requires that a binary, to be run by Hadoop streaming, already exists on the
    cluster.

    Requires specfication of write-able file locations where intermediate Hadoop
    output will be stored before being parsed and returned as X_L and X_D

    """

    def __init__(self, seed=0,
                 which_engine_binary=hs.default_engine_binary,
                 hdfs_dir=hs.default_hdfs_dir,
                 jobtracker_uri=hs.default_jobtracker_uri,
                 hdfs_uri=hs.default_hdfs_uri,
                 which_hadoop_jar=hs.default_hadoop_jar,
                 which_hadoop_binary=hs.default_hadoop_binary,
                 output_path=hs.default_output_path,
                 input_filename=hs.default_input_filename,
                 table_data_filename=hs.default_table_data_filename,
                 command_dict_filename=hs.default_command_dict_filename,
                 one_map_task_per_line=True,
                 ):
        xu.assert_vpn_is_connected()
        #
        self.which_hadoop_binary = which_hadoop_binary
        #
        self.seed_generator = gu.int_generator(seed)
        self.which_engine_binary = which_engine_binary
        self.hdfs_dir = hdfs_dir
        self.jobtracker_uri = jobtracker_uri
        self.hdfs_uri = hdfs_uri
        self.which_hadoop_jar = which_hadoop_jar
        self.output_path = output_path
        self.input_filename = input_filename
        self.table_data_filename = table_data_filename
        self.one_map_task_per_line = one_map_task_per_line
        self.command_dict_filename = command_dict_filename
        return

    def send_hadoop_command(self, n_tasks=1):
        hu.send_hadoop_command(
            self.hdfs_uri, self.hdfs_dir, self.jobtracker_uri,
            self.which_engine_binary, self.which_hadoop_binary, self.which_hadoop_jar,
            self.input_filename, self.table_data_filename,
            self.command_dict_filename, self.output_path,
            n_tasks, self.one_map_task_per_line)
        return

    def get_hadoop_results(self):
        was_successful = hu.get_hadoop_results(self.hdfs_uri, self.output_path, self.hdfs_dir)
        print 'was_successful: %s' % was_successful
        return was_successful

    def initialize(self, M_c, M_r, T, initialization='from_the_prior',
                   n_chains=1):
        """Sample a latent state from prior

        :param M_c: The column metadata
        :type M_c: dict
        :param M_r: The row metadata
        :type M_r: dict
        :param T: The data table in mapped representation (all floats, generated
                  by data_utils.read_data_objects)
        :type T: list of lists
        :returns: X_L, X_D -- the latent state

        """

        output_path = self.output_path
        input_filename = self.input_filename
        table_data_filename = self.table_data_filename
        intialize_args_dict_filename = self.command_dict_filename
        xu.assert_vpn_is_connected()
          #
        table_data = dict(M_c=M_c, M_r=M_r, T=T)
        initialize_args_dict = dict(command='initialize',
                                    initialization=initialization)
        xu.write_initialization_files(input_filename,
                                      table_data, table_data_filename,
                                      initialize_args_dict,
                                      intialize_args_dict_filename,
                                      n_chains)
        os.system('cp %s initialize_input' % input_filename)
        self.send_hadoop_command(n_tasks=n_chains)
        was_successful = self.get_hadoop_results()
        hadoop_output = None
        if was_successful:
            hu.copy_hadoop_output(output_path, 'initialize_output')
            X_L_list, X_D_list = hu.read_hadoop_output(output_path)
            hadoop_output = X_L_list, X_D_list
            return hadoop_output

    def analyze(self, M_c, T, X_L, X_D, kernel_list=(), n_steps=1, c=(), r=(),
                max_iterations=-1, max_time=-1, **kwargs):  
        """Evolve the latent state by running MCMC transition kernels

        :param M_c: The column metadata
        :type M_c: dict
        :param T: The data table in mapped representation (all floats, generated
                  by data_utils.read_data_objects)
        :type T: list of lists
        :param X_L: the latent variables associated with the latent state
        :type X_L: dict
        :param X_D: the particular cluster assignments of each row in each view
        :type X_D: list of lists
        :param kernel_list: names of the MCMC transition kernels to run
        :type kernel_list: list of strings
        :param n_steps: the number of times to run each MCMC transition kernel
        :type n_steps: int
        :param c: the (global) column indices to run MCMC transition kernels on
        :type c: list of ints
        :param r: the (global) row indices to run MCMC transition kernels on
        :type r: list of ints
        :param max_iterations: the maximum number of times ot run each MCMC
                               transition kernel. Applicable only if
                               max_time != -1.
        :type max_iterations: int
        :param max_time: the maximum amount of time (seconds) to run MCMC
                         transition kernels for before stopping to return
                         progress
        :type max_time: float
        :param kwargs: optional arguments to pass to hadoop_line_processor.jar.
                       Currently, presence of a 'chunk_size' kwarg causes
                       different behavior.
        :returns: X_L, X_D -- the evolved latent state
        
        """

        output_path = self.output_path
        input_filename = self.input_filename
        table_data_filename = self.table_data_filename
        analyze_args_dict_filename = self.command_dict_filename
        xu.assert_vpn_is_connected()
        #
        table_data = dict(M_c=M_c, T=T)
        analyze_args_dict = dict(command='analyze', kernel_list=kernel_list,
                                 n_steps=n_steps, c=c, r=r, max_time=max_time)
        # chunk_analyze is a special case of analyze
        if 'chunk_size' in kwargs:
          chunk_size = kwargs['chunk_size']
          chunk_filename_prefix = kwargs['chunk_filename_prefix']
          chunk_dest_dir = kwargs['chunk_dest_dir']
          analyze_args_dict['command'] = 'chunk_analyze'
          analyze_args_dict['chunk_size'] = chunk_size
          analyze_args_dict['chunk_filename_prefix'] = chunk_filename_prefix
          # WARNING: chunk_dest_dir MUST be writeable by hadoop user mapred
          analyze_args_dict['chunk_dest_dir'] = chunk_dest_dir
        if not su.get_is_multistate(X_L, X_D):
            X_L = [X_L]
            X_D = [X_D]
        #
        SEEDS = kwargs.get('SEEDS', None)
        xu.write_analyze_files(input_filename, X_L, X_D,
                               table_data, table_data_filename,
                               analyze_args_dict, analyze_args_dict_filename,
                               SEEDS)
        os.system('cp %s analyze_input' % input_filename)
        n_tasks = len(X_L)
        self.send_hadoop_command(n_tasks)
        was_successful = self.get_hadoop_results()
        hadoop_output = None
        if was_successful:
          hu.copy_hadoop_output(output_path, 'analyze_output')
          X_L_list, X_D_list = hu.read_hadoop_output(output_path)
          hadoop_output = X_L_list, X_D_list
        return hadoop_output

    def simple_predictive_sample(self, M_c, X_L, X_D, Y, Q, n=1):
        pass

    def impute(self, M_c, X_L, X_D, Y, Q, n):
        pass

    def impute_and_confidence(self, M_c, X_L, X_D, Y, Q, n):
        pass

        
if __name__ == '__main__':
    import argparse
    #
    import crosscat.utils.data_utils as du
    #
    parser = argparse.ArgumentParser()
    parser.add_argument('command', type=str)
    parser.add_argument('--base_uri', type=str, default=None)
    parser.add_argument('--hdfs_uri', type=str, default=hs.default_hdfs_uri)
    parser.add_argument('--jobtracker_uri', type=str,
                        default=hs.default_jobtracker_uri)
    parser.add_argument('--hdfs_dir', type=str, default=hs.default_hdfs_dir)
    parser.add_argument('-DEBUG', action='store_true')
    parser.add_argument('--which_engine_binary', type=str, default=hs.default_engine_binary)
    parser.add_argument('--which_hadoop_binary', type=str, default=hs.default_hadoop_binary)
    parser.add_argument('--which_hadoop_jar', type=str, default=hs.default_hadoop_jar)
    parser.add_argument('--n_chains', type=int, default=4)
    parser.add_argument('--n_steps', type=int, default=1)
    parser.add_argument('--chunk_size', type=int, default=1)
    parser.add_argument('--chunk_filename_prefix', type=str, default='chunk')
    parser.add_argument('--chunk_dest_dir', type=str, default='/user/bigdata/SSCI/chunk_dir')
    parser.add_argument('--max_time', type=float, default=-1)
    parser.add_argument('--table_filename', type=str, default='../www/data/dha_small.csv')
    parser.add_argument('--resume_filename', type=str, default=None)
    parser.add_argument('--pkl_filename', type=str, default=None)
    parser.add_argument('--cctypes_filename', type=str, default=None)
    #
    args = parser.parse_args()
    base_uri = args.base_uri
    hdfs_uri = args.hdfs_uri
    jobtracker_uri = args.jobtracker_uri
    hdfs_dir = args.hdfs_dir
    DEBUG = args.DEBUG
    which_engine_binary = args.which_engine_binary
    which_hadoop_binary = args.which_hadoop_binary
    which_hadoop_jar= args.which_hadoop_jar
    n_chains = args.n_chains
    n_steps = args.n_steps
    chunk_size = args.chunk_size
    chunk_filename_prefix = args.chunk_filename_prefix
    chunk_dest_dir = args.chunk_dest_dir
    max_time = args.max_time
    table_filename = args.table_filename
    resume_filename = args.resume_filename
    pkl_filename = args.pkl_filename
    #
    command = args.command
    # assert command in set(gu.get_method_names(HadoopEngine))
    #
    cctypes_filename = args.cctypes_filename
    cctypes = None
    if cctypes_filename is not None:
      cctypes = fu.unpickle(cctypes_filename)

    hdfs_uri, jobtracker_uri = hu.get_uris(base_uri, hdfs_uri, jobtracker_uri)
    T, M_r, M_c = du.read_model_data_from_csv(table_filename, gen_seed=0,
                                              cctypes=cctypes)
    he = HadoopEngine(which_engine_binary=which_engine_binary,
		      which_hadoop_binary=which_hadoop_binary,
		      which_hadoop_jar=which_hadoop_jar,
                      hdfs_dir=hdfs_dir, hdfs_uri=hdfs_uri,
                      jobtracker_uri=jobtracker_uri)
    
    X_L_list, X_D_list = None, None
    if command == 'initialize':
        hadoop_output = he.initialize(M_c, M_r, T,
                                      initialization='from_the_prior',
                                      n_chains=n_chains)
        if hadoop_output is not None:
            X_L_list, X_D_list = hadoop_output
    elif command == 'analyze':
        assert resume_filename is not None
        if fu.is_pkl(resume_filename):
          resume_dict = fu.unpickle(resume_filename)
        else:
          resume_dict = hu.read_hadoop_output_file(resume_filename)
        X_L_list = resume_dict['X_L_list']
        X_D_list = resume_dict['X_D_list']
        hadoop_output = he.analyze(M_c, T, X_L_list, X_D_list,
                                   n_steps=n_steps, max_time=max_time)
        if hadoop_output is not None:
            X_L_list, X_D_list = hadoop_output
    elif command == 'chunk_analyze':
        assert resume_filename is not None
        if fu.is_pkl(resume_filename):
          resume_dict = fu.unpickle(resume_filename)
          X_L_list = resume_dict['X_L_list']
          X_D_list = resume_dict['X_D_list']
        else:
          X_L_list, X_D_list = hu.read_hadoop_output(resume_filename)
        hadoop_output = he.analyze(M_c, T, X_L_list, X_D_list,
                                   n_steps=n_steps, max_time=max_time,
                                   chunk_size=chunk_size,
                                   chunk_filename_prefix=chunk_filename_prefix,
                                   chunk_dest_dir=chunk_dest_dir)
        if hadoop_output is not None:
            X_L_list, X_D_list = hadoop_output
    else:
        print 'Unknown command: %s' % command
        import sys
        sys.exit()
        
    if pkl_filename is not None:
      to_pkl_dict = dict(
            T=T,
            M_c=M_c,
            M_r=M_r,
            X_L_list=X_L_list,
            X_D_list=X_D_list,
            )
      fu.pickle(to_pkl_dict, filename=pkl_filename)

########NEW FILE########
__FILENAME__ = IPClusterEngine
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import functools
#
from IPython.parallel import Client
#
import crosscat
import crosscat.LocalEngine as LE


def partialize(func, args_dict, dview):
    # why is this push necessary?
    dview.push(args_dict, block=True)
    helper = functools.partial(func, **args_dict)
    return helper


class IPClusterEngine(LE.LocalEngine):
    """A simple interface to the Cython-wrapped C++ engine

    IPClusterEngine

    """

    def __init__(self, config_filename=None, profile=None, seed=None, sshkey=None, packer='json'):
        """Initialize a IPClusterEngine

        Do IPython.parallel operations to set up cluster and generate mapper.

        """
        super(IPClusterEngine, self).__init__(seed=seed)
        rc = Client(config_filename, profile=profile, sshkey=sshkey, packer=packer)
        # FIXME: add a warning if environment in direct view is not 'empty'?
        #        else, might become dependent on an object created in
        #        environemnt in a prior run
        dview = rc.direct_view()
        lview = rc.load_balanced_view()
        with dview.sync_imports(local=True):
            import crosscat
        mapper = lambda f, tuples: self.lview.map(f, *tuples)
        # if you're trying to debug issues, consider clearning to start fresh
        # rc.clear(block=True)
        #
        self.rc = rc
        self.dview = dview
        self.lview = lview
        self.mapper = mapper
        self.do_initialize = None
        self.do_analyze = None
        return

    def get_initialize_arg_tuples(self, M_c, M_r, T, initialization,
            row_initialization, n_chains):
        args_dict = dict(M_c=M_c, M_r=M_r, T=T, initialization=initialization,
                row_initialization=row_initialization)
        do_initialize = partialize(crosscat.LocalEngine._do_initialize,
                args_dict, self.dview)
        seeds = [self.get_next_seed() for seed_idx in range(n_chains)]
        arg_tuples = [seeds]
        #
        self.do_initialize = do_initialize
        return arg_tuples

    def get_analyze_arg_tuples(self, M_c, T, X_L, X_D, kernel_list=(), n_steps=1, c=(), r=(),
                max_iterations=-1, max_time=-1, diagnostic_func_dict=None, every_N=1):
        n_chains = len(X_L)
        args_dict = dict(M_c=M_c, T=T, kernel_list=kernel_list, n_steps=n_steps,
                c=c, r=r, max_iterations=max_iterations, max_time=max_time,
                diagnostic_func_dict=diagnostic_func_dict, every_N=every_N)
        do_analyze = partialize(crosscat.LocalEngine._do_analyze_with_diagnostic,
                args_dict, self.dview)
        seeds = [self.get_next_seed() for seed_idx in range(n_chains)]
        arg_tuples = [seeds, X_L, X_D]
        #
        self.do_analyze = do_analyze
        return arg_tuples

########NEW FILE########
__FILENAME__ = JSONRPCEngine
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
from functools import partial
#
import crosscat.EngineTemplate as EngineTemplate
import crosscat.utils.data_utils as du
import crosscat.utils.api_utils as au
import crosscat.utils.general_utils as gu


method_name_to_args = gu.get_method_name_to_args(EngineTemplate.EngineTemplate)
method_names_set = set(gu.get_method_names(EngineTemplate.EngineTemplate))


class JSONRPCEngine(EngineTemplate.EngineTemplate):
    """An 'adapter' for sending commands to an Engine resident on a remote machine.

    JSONRPCEngine supports all methods that the remote engine does.  The remote engine must be listening at the URI specified in the constructor.  Commands are sent via JSONRPC-2.0.

    """

    def __init__(self, seed=None, URI=None):
        super(JSONRPCEngine, self).__init__(seed=seed)
        self.URI = URI
        return

    def dispatch(self, method_name, *args, **kwargs):
        args_names = method_name_to_args[method_name]
        args_dict = dict(zip(args_names, args))
        kwargs.update(args_dict)
        out = au.call(method_name, kwargs, self.URI)
        if isinstance(out, tuple):
            out, id = out
        return out

    def __getattribute__(self, name):
        attr = None
        if name in method_names_set:
            partial_dispatch = partial(self.dispatch, name)
            attr = partial_dispatch
        else:
            attr = object.__getattribute__(self, name)
        return attr


if __name__ == '__main__':
    je = JSONRPCEngine(seed=10, URI='http://localhost:8007')
    #
    gen_seed = 0
    num_clusters = 4
    num_cols = 32
    num_rows = 400
    num_splits = 1
    max_mean = 10
    max_std = 0.1
    T, M_r, M_c = du.gen_factorial_data_objects(
        gen_seed, num_clusters,
        num_cols, num_rows, num_splits,
        max_mean=max_mean, max_std=max_std,
        )
    #
    X_L, X_D, = je.initialize(M_c, M_r, T)
    X_L_prime, X_D_prime = je.analyze(M_c, T, X_L, X_D)
    X_L_prime, X_D_prime = je.analyze(M_c, T, X_L_prime, X_D_prime)

########NEW FILE########
__FILENAME__ = server_jsonrpc
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
from __future__ import print_function
#
#  Copyright (c) 2011 Edward Langley
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#
#  Redistributions of source code must retain the above copyright notice,
#  this list of conditions and the following disclaimer.
#
#  Redistributions in binary form must reproduce the above copyright
#  notice, this list of conditions and the following disclaimer in the
#  documentation and/or other materials provided with the distribution.
#
#  Neither the name of the project's author nor the names of its
#  contributors may be used to endorse or promote products derived from
#  this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
#  FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
#  TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
#  PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
#  LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#  NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#
import functools
from multiprocessing import Process, Queue
#
from twisted.internet import ssl
import traceback
from twisted.internet import reactor
from twisted.web import server
from jsonrpc.server import ServerEvents, JSON_RPC
#
import crosscat.LocalEngine as LE
import crosscat.utils.general_utils as gu


def putter(f, q, *args, **kwargs):
    output = f(*args, **kwargs)
    q.put(output)
    q.close()
    return

def run_in_process(method, seed):
    def wrapped(*args, **kwargs):
        engine = LE.LocalEngine(seed)
        _method = getattr(engine, method)
        #
        q = Queue()
        partial = functools.partial(putter, _method, q)
        p = Process(target=partial, args=args, kwargs=kwargs)
        p.start()
        ret_val = q.get()
        p.join()
        return ret_val
    return wrapped

class ExampleServer(ServerEvents):

    get_next_seed = gu.int_generator(start=0)
    methods = set(gu.get_method_names(LE.LocalEngine))

    # inherited hooks
    def log(self, responses, txrequest, error):
        print(txrequest.code, end=' ')
        if isinstance(responses, list):
            for response in responses:
                msg = self._get_msg(response)
                print(txrequest, msg)
        else:
            msg = self._get_msg(responses)
            print(txrequest, msg)

    def findmethod(self, method, args=None, kwargs=None):
        if method in self.methods:
            next_seed = self.get_next_seed.next()
            wrapped = run_in_process(method, next_seed)
            return wrapped
        else:
            return None

    # helper methods
    def _get_msg(self, response):
        ret_str = str(response)
        if hasattr(response, 'id'):
            ret_str = str(response.id)
            if response.result:
                ret_str += '; result: %s' % str(response.result)
            else:
                ret_str += '; error: %s' % str(response.error)
        return ret_str

root = JSON_RPC().customize(ExampleServer)
site = server.Site(root)


# 8007 is the port you want to run under. Choose something >1024
PORT = 8007
print('Listening on port %d...' % PORT)
reactor.listenTCP(PORT, site)
reactor.run()

########NEW FILE########
__FILENAME__ = stub_client_jsonrpc
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import argparse
import time
#
import crosscat.LocalEngine as LE
import crosscat.utils.data_utils as du
import crosscat.utils.api_utils as au
import crosscat.utils.general_utils as gu


# parse some arguments
parser = argparse.ArgumentParser()
parser.add_argument('--hostname', default='localhost', type=str)
parser.add_argument('--seed', default=0, type=int)
parser.add_argument('--num_clusters', default=2, type=int)
parser.add_argument('--num_cols', default=8, type=int)
parser.add_argument('--num_rows', default=300, type=int)
parser.add_argument('--num_splits', default=2, type=int)
parser.add_argument('--max_mean', default=10, type=float)
parser.add_argument('--max_std', default=0.1, type=float)
parser.add_argument('--start_id', default=0, type=int)
args = parser.parse_args()
hostname = args.hostname
seed = args.seed
num_clusters = args.num_clusters
num_cols = args.num_cols
num_rows = args.num_rows
num_splits = args.num_splits
max_mean = args.max_mean
max_std = args.max_std
id = args.start_id

# settings
URI = 'http://' + hostname + ':8007'
print 'URI: ', URI

T, M_r, M_c = du.gen_factorial_data_objects(
    seed, num_clusters,
    num_cols, num_rows, num_splits,
    max_mean=max_mean, max_std=max_std,
    )

# non-stub functions
non_stub = set(['initialize', 'initialize_and_analyze', 'analyze', 'impute',
                'impute_and_confidence', 'simple_predictive_sample'])

method_name = 'initialize'
args_dict = dict()
args_dict['M_c'] = M_c
args_dict['M_r'] = M_r
args_dict['T'] = T
out, id = au.call(method_name, args_dict, URI)
M_c, M_r, X_L_prime, X_D_prime = out

method_name = 'analyze'
args_dict = dict()
args_dict['M_c'] = M_c
args_dict['T'] = T
args_dict['X_L'] = X_L_prime
args_dict['X_D'] = X_D_prime
args_dict['kernel_list'] = ()
args_dict['n_steps'] = 10
args_dict['c'] = ()
args_dict['r'] = ()
args_dict['max_iterations'] = 'max_iterations'
args_dict['max_time'] = 'max_time'
out, id = au.call(method_name, args_dict, URI)
X_L_prime, X_D_prime = out
time.sleep(1)

method_name = 'simple_predictive_sample'
args_dict = dict()
args_dict['M_c'] = M_c
args_dict['X_L'] = X_L_prime
args_dict['X_D'] = X_D_prime
args_dict['Y'] = None
args_dict['Q'] = [(0,0), (0,1)]
values = []
for idx in range(3):
    out, id = au.call_and_print(method_name, args_dict, URI)
    values.append(out[0])
print values
time.sleep(1)

method_name = 'impute'
args_dict = dict()
args_dict['M_c'] = M_c
args_dict['X_L'] = X_L_prime
args_dict['X_D'] = X_D_prime
args_dict['Y'] = None
args_dict['Q'] = [(0, 0)]
args_dict['n'] = 10
out, id = au.call(method_name, args_dict, URI)
time.sleep(1)

method_name = 'impute_and_confidence'
args_dict = dict()
args_dict['M_c'] = M_c
args_dict['X_L'] = X_L_prime
args_dict['X_D'] = X_D_prime
args_dict['Y'] = None
args_dict['Q'] = [(0, 0)]
args_dict['n'] = 10
out, id = au.call(method_name, args_dict, URI)
time.sleep(1)

# programmatically call all the other method calls
method_name_to_args = gu.get_method_name_to_args(LE.LocalEngine)
for method_name, arg_str_list in method_name_to_args.iteritems():
    if method_name in non_stub:
        print 'skipping non-stub method:', method_name
        print
        continue
    args_dict = dict(zip(arg_str_list, arg_str_list))
    au.call_and_print(method_name, args_dict, URI)
    time.sleep(1)

########NEW FILE########
__FILENAME__ = test_engine
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import argparse
#
import numpy
#
import crosscat.utils.data_utils as du
import crosscat.cython_code.State as State
from crosscat.JSONRPCEngine import JSONRPCEngine


parser = argparse.ArgumentParser()
parser.add_argument('--gen_seed', default=0, type=int)
parser.add_argument('--inf_seed', default=0, type=int)
parser.add_argument('--num_clusters', default=4, type=int)
parser.add_argument('--num_cols', default=16, type=int)
parser.add_argument('--num_rows', default=300, type=int)
parser.add_argument('--num_splits', default=2, type=int)
parser.add_argument('--max_mean', default=10, type=float)
parser.add_argument('--max_std', default=0.3, type=float)
parser.add_argument('--num_transitions', default=30, type=int)
parser.add_argument('--N_GRID', default=31, type=int)
parser.add_argument('--URI', default='http://localhost:8007', type=str)
args = parser.parse_args()
#
gen_seed = args.gen_seed
inf_seed = args.inf_seed
num_clusters = args.num_clusters
num_cols = args.num_cols
num_rows = args.num_rows
num_splits = args.num_splits
max_mean = args.max_mean
max_std = args.max_std
num_transitions = args.num_transitions
N_GRID = args.N_GRID
URI = args.URI


# create the data
T, M_r, M_c = du.gen_factorial_data_objects(
    gen_seed, num_clusters,
    num_cols, num_rows, num_splits,
    max_mean=max_mean, max_std=max_std,
    )

#
engine = JSONRPCEngine(inf_seed, URI=URI)

# initialize
X_L, X_D = engine.initialize(M_c, M_r, T)

# analyze without do_diagnostics or do_timing
X_L, X_D = engine.analyze(M_c, T, X_L, X_D, n_steps=num_transitions)

# analyze with do_diagnostics
X_L, X_D, diagnostics_dict = engine.analyze(M_c, T, X_L, X_D, n_steps=num_transitions, do_diagnostics=True)

# analyze with do_timing
X_L, X_D, timing_list = engine.analyze(M_c, T, X_L, X_D, n_steps=num_transitions, do_timing=True)

## draw sample states
#for sample_idx in range(num_samples):
#    print "starting sample_idx #: %s" % sample_idx
#    X_L, X_D = engine.analyze(M_c, T, X_L, X_D, kernel_list, lag,
#                              c, r, max_iterations, max_time)
#    p_State = State.p_State(M_c, T, X_L, X_D, N_GRID=N_GRID)
#    plot_filename = 'sample_%s_X_D' % sample_idx
#    pkl_filename = 'sample_%s_pickled_state.pkl.gz' % sample_idx
#    p_State.save(filename=pkl_filename, M_c=M_c, T=T)
#    p_State.plot(filename=plot_filename)

########NEW FILE########
__FILENAME__ = test_resume
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import argparse
#
import crosscat.utils.api_utils as au
import crosscat.utils.file_utils as fu


# parse some arguments
parser = argparse.ArgumentParser()
parser.add_argument('pkl_name', type=str)
parser.add_argument('--hostname', default='localhost', type=str)
parser.add_argument('--seed', default=0, type=int)
parser.add_argument('--start_id', default=0, type=int)
args = parser.parse_args()
pkl_name = args.pkl_name
hostname = args.hostname
seed = args.seed
id = args.start_id

# settings
URI = 'http://' + hostname + ':8007'
print 'URI: ', URI

save_dict = fu.unpickle(pkl_name)
method_name = 'analyze'
args_dict = dict()
args_dict['M_c'] = save_dict['M_c']
args_dict['T'] = save_dict['T']
args_dict['X_L'] = save_dict['X_L']
args_dict['X_D'] = save_dict['X_D']
args_dict['kernel_list'] = 'kernel_list'
args_dict['n_steps'] = 1
args_dict['c'] = 'c'
args_dict['r'] = 'r'
args_dict['max_iterations'] = 'max_iterations'
args_dict['max_time'] = 'max_time'
out, id = au.call(method_name, args_dict, URI, id)
X_L_prime, X_D_prime = out

########NEW FILE########
__FILENAME__ = LocalEngine
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import itertools
import collections
#
import numpy
#
import crosscat.cython_code.State as State
import crosscat.EngineTemplate as EngineTemplate
import crosscat.utils.sample_utils as su
import crosscat.utils.general_utils as gu
import crosscat.utils.inference_utils as iu
# for default_diagnostic_func_dict below
import crosscat.utils.diagnostic_utils


class LocalEngine(EngineTemplate.EngineTemplate):

    """A simple interface to the Cython-wrapped C++ engine

    LocalEngine holds no state other than a seed generator.
    Methods use resources on the local machine.

    """

    def __init__(self, seed=None):
        """Initialize a LocalEngine

        This is really just setting the initial seed to be used for
        initializing CrossCat states.  Seeds are generated sequentially

        """
        super(LocalEngine, self).__init__(seed=seed)
        self.mapper = map
        self.do_initialize = _do_initialize_tuple
        self.do_analyze = _do_analyze_tuple
        return

    def get_initialize_arg_tuples(self, M_c, M_r, T, initialization,
                                  row_initialization, n_chains,
                                  ROW_CRP_ALPHA_GRID,
                                  COLUMN_CRP_ALPHA_GRID,
                                  S_GRID, MU_GRID,
                                  N_GRID,
                                  ):
        seeds = [self.get_next_seed() for seed_idx in range(n_chains)]
        arg_tuples = itertools.izip(
            seeds,
            itertools.cycle([M_c]),
            itertools.cycle([M_r]),
            itertools.cycle([T]),
            itertools.cycle([initialization]),
            itertools.cycle([row_initialization]),
            itertools.cycle([ROW_CRP_ALPHA_GRID]),
            itertools.cycle([COLUMN_CRP_ALPHA_GRID]),
            itertools.cycle([S_GRID]),
            itertools.cycle([MU_GRID]),
            itertools.cycle([N_GRID]),
        )
        return arg_tuples

    def initialize(self, M_c, M_r, T, initialization='from_the_prior',
                   row_initialization=-1, n_chains=1,
                   ROW_CRP_ALPHA_GRID=(),
                   COLUMN_CRP_ALPHA_GRID=(),
                   S_GRID=(), MU_GRID=(),
                   N_GRID=31,
                   ):
        """Sample a latent state from prior

        :param M_c: The column metadata
        :type M_c: dict
        :param M_r: The row metadata
        :type M_r: dict
        :param T: The data table in mapped representation (all floats, generated
                  by data_utils.read_data_objects)
        :type T: list of lists
        :returns: X_L, X_D -- the latent state

        """

        # FIXME: why is M_r passed?
        arg_tuples = self.get_initialize_arg_tuples(
            M_c, M_r, T, initialization,
            row_initialization, n_chains,
            ROW_CRP_ALPHA_GRID, COLUMN_CRP_ALPHA_GRID,
            S_GRID, MU_GRID,
            N_GRID,
        )
        chain_tuples = self.mapper(self.do_initialize, arg_tuples)
        X_L_list, X_D_list = zip(*chain_tuples)
        if n_chains == 1:
            X_L_list, X_D_list = X_L_list[0], X_D_list[0]
        return X_L_list, X_D_list

    def get_analyze_arg_tuples(self, M_c, T, X_L_list, X_D_list, kernel_list,
                               n_steps, c, r, max_iterations, max_time, diagnostic_func_dict, every_N,
                               ROW_CRP_ALPHA_GRID, COLUMN_CRP_ALPHA_GRID,
                               S_GRID, MU_GRID,
                               N_GRID,
                               do_timing,
                               CT_KERNEL,
                               ):
        n_chains = len(X_L_list)
        seeds = [self.get_next_seed() for seed_idx in range(n_chains)]
        arg_tuples = itertools.izip(
            seeds,
            X_L_list, X_D_list,
            itertools.cycle([M_c]),
            itertools.cycle([T]),
            itertools.cycle([kernel_list]),
            itertools.cycle([n_steps]),
            itertools.cycle([c]),
            itertools.cycle([r]),
            itertools.cycle([max_iterations]),
            itertools.cycle([max_time]),
            itertools.cycle([diagnostic_func_dict]),
            itertools.cycle([every_N]),
            itertools.cycle([ROW_CRP_ALPHA_GRID]),
            itertools.cycle([COLUMN_CRP_ALPHA_GRID]),
            itertools.cycle([S_GRID]),
            itertools.cycle([MU_GRID]),
            itertools.cycle([N_GRID]),
            itertools.cycle([do_timing]),
            itertools.cycle([CT_KERNEL]),
        )
        return arg_tuples

    def analyze(self, M_c, T, X_L, X_D, kernel_list=(), n_steps=1, c=(), r=(),
                max_iterations=-1, max_time=-1, do_diagnostics=False,
                diagnostics_every_N=1,
                ROW_CRP_ALPHA_GRID=(),
                COLUMN_CRP_ALPHA_GRID=(),
                S_GRID=(), MU_GRID=(),
                N_GRID=31,
                do_timing=False,
                CT_KERNEL=0,
                ):
        """Evolve the latent state by running MCMC transition kernels

        :param M_c: The column metadata
        :type M_c: dict
        :param T: The data table in mapped representation (all floats, generated
                  by data_utils.read_data_objects)
        :param X_L: the latent variables associated with the latent state
        :type X_L: dict
        :param X_D: the particular cluster assignments of each row in each view
        :type X_D: list of lists
        :param kernel_list: names of the MCMC transition kernels to run
        :type kernel_list: list of strings
        :param n_steps: the number of times to run each MCMC transition kernel
        :type n_steps: int
        :param c: the (global) column indices to run MCMC transition kernels on
        :type c: list of ints
        :param r: the (global) row indices to run MCMC transition kernels on
        :type r: list of ints
        :param max_iterations: the maximum number of times ot run each MCMC
                               transition kernel. Applicable only if
                               max_time != -1.
        :type max_iterations: int
        :param max_time: the maximum amount of time (seconds) to run MCMC
                         transition kernels for before stopping to return
                         progress
        :type max_time: float
        :returns: X_L, X_D -- the evolved latent state

        """
        if CT_KERNEL not in [0,1]:
            raise ValueError("CT_KERNEL must be 0 (Gibbs) or 1 (MH)")

        if do_timing:
            # diagnostics and timing are exclusive
            do_diagnostics = False
        diagnostic_func_dict, reprocess_diagnostics_func = do_diagnostics_to_func_dict(
            do_diagnostics)
        X_L_list, X_D_list, was_multistate = su.ensure_multistate(X_L, X_D)
        arg_tuples = self.get_analyze_arg_tuples(M_c, T, X_L_list, X_D_list,
                                                 kernel_list, n_steps, c, r, max_iterations, max_time,
                                                 diagnostic_func_dict, diagnostics_every_N,
                                                 ROW_CRP_ALPHA_GRID,
                                                 COLUMN_CRP_ALPHA_GRID,
                                                 S_GRID, MU_GRID,
                                                 N_GRID,
                                                 do_timing,
                                                 CT_KERNEL,
                                                 )
        chain_tuples = self.mapper(self.do_analyze, arg_tuples)
        X_L_list, X_D_list, diagnostics_dict_list = zip(*chain_tuples)
        if do_timing:
            timing_list = diagnostics_dict_list
        if not was_multistate:
            X_L_list, X_D_list = X_L_list[0], X_D_list[0]
        ret_tuple = X_L_list, X_D_list
        #
        if diagnostic_func_dict is not None:
            diagnostics_dict = munge_diagnostics(diagnostics_dict_list)
            if reprocess_diagnostics_func is not None:
                diagnostics_dict = reprocess_diagnostics_func(diagnostics_dict)
            ret_tuple = ret_tuple + (diagnostics_dict, )
        if do_timing:
            ret_tuple = ret_tuple + (timing_list, )
        return ret_tuple

    def _sample_and_insert(self, M_c, T, X_L, X_D, matching_row_indices):
        p_State = State.p_State(M_c, T, X_L, X_D)
        draws = []
        for matching_row_idx in matching_row_indices:
            random_seed = self.get_next_seed()
            draw = p_State.get_draw(matching_row_idx, random_seed)
            p_State.insert_row(draw, matching_row_idx)
            draws.append(draw)
            T.append(draw)
        X_L, X_D = p_State.get_X_L(), p_State.get_X_D()
        return draws, T, X_L, X_D

    def sample_and_insert(self, M_c, T, X_L, X_D, matching_row_idx):
        matching_row_indices = gu.ensure_listlike(matching_row_idx)
        if len(matching_row_indices) == 0:
            matching_row_indices = range(len(T))
            pass
        was_single_row = len(matching_row_indices) == 1
        draws, T, X_L, X_D = self._sample_and_insert(M_c, T, X_L, X_D,
                matching_row_indices)
        if was_single_row:
            draws = draws[0]
            pass
        return draws, T, X_L, X_D

    def simple_predictive_sample(self, M_c, X_L, X_D, Y, Q, n=1):
        """Sample values from the predictive distribution of the given latent state

        :param M_c: The column metadata
        :type M_c: dict
        :param X_L: the latent variables associated with the latent state
        :type X_L: dict
        :param X_D: the particular cluster assignments of each row in each view
        :type X_D: list of lists
        :param Y: A list of constraints to apply when sampling.  Each constraint
                  is a triplet of (r, d, v): r is the row index, d is the column
                  index and v is the value of the constraint
        :type Y: list of lists
        :param Q: A list of values to sample.  Each value is doublet of (r, d):
                  r is the row index, d is the column index
        :type Q: list of lists
        :param n: the number of samples to draw
        :type n: int
        :returns: list of floats -- samples in the same order specified by Q

        """
        get_next_seed = self.get_next_seed
        samples = _do_simple_predictive_sample(
            M_c, X_L, X_D, Y, Q, n, get_next_seed)
        return samples

    def simple_predictive_probability(self, M_c, X_L, X_D, Y, Q):
        """Calculate the probability of a cell taking a value given a latent state

        :param M_c: The column metadata
        :type M_c: dict
        :param X_L: the latent variables associated with the latent state
        :type X_L: dict
        :param X_D: the particular cluster assignments of each row in each view
        :type X_D: list of lists
        :param Y: A list of constraints to apply when sampling.  Each constraint
                  is a triplet of (r, d, v): r is the row index, d is the column
                  index and v is the value of the constraint
        :type Y: list of lists
        :param Q: A list of values to sample.  Each value is doublet of (r, d):
                  r is the row index, d is the column index
        :type Q: list of lists
        :returns: list of floats -- probabilities of the values specified by Q

        """
        return su.simple_predictive_probability(M_c, X_L, X_D, Y, Q)

    def simple_predictive_probability_multistate(self, M_c, X_L_list, X_D_list, Y, Q):
        """Calculate the probability of a cell taking a value given a latent state

        :param M_c: The column metadata
        :type M_c: dict
        :param X_L_list: list of the latent variables associated with the latent state
        :type X_L_list: list of dict
        :param X_D_list: list of the particular cluster assignments of each row in each view
        :type X_D_list: list of list of lists
        :param Y: A list of constraints to apply when sampling.  Each constraint
                  is a triplet of (r, d, v): r is the row index, d is the column
                  index and v is the value of the constraint
        :type Y: list of lists
        :param Q: A list of values to sample.  Each value is doublet of (r, d):
                  r is the row index, d is the column index
        :type Q: list of lists
        :returns: list of floats -- probabilities of the values specified by Q

        """
        return su.simple_predictive_probability_multistate(M_c, X_L_list, X_D_list, Y, Q)

    def mutual_information(self, M_c, X_L_list, X_D_list, Q, n_samples=1000):
        """
        Return the estimated mutual information for each pair of columns on Q given
        the set of samples.
        
        :param M_c: The column metadata
        :type M_c: dict
        :param X_L_list: list of the latent variables associated with the latent state
        :type X_L_list: list of dict
        :param X_D_list: list of the particular cluster assignments of each row in each view
        :type X_D_list: list of list of lists
        :param Q: List of tuples where each tuple contains the two column indexes to compare
        :type Q: list of two-tuples of ints
        :param n_samples: the number of simple predictive samples to use
        :type n_samples: int
        :returns: list of list, where each sublist is a set of MIs and Linfoots from each crosscat sample.
        """
        return iu.mutual_information(M_c, X_L_list, X_D_list, Q, n_samples)

    def row_structural_typicality(self, X_L_list, X_D_list, row_id):
        """
        Returns the typicality (opposite of anomalousness) of the given row.
        
        :param X_L_list: list of the latent variables associated with the latent state
        :type X_L_list: list of dict
        :param X_D_list: list of the particular cluster assignments of each row in each view
        :type X_D_list: list of list of lists
        :param row_id: id of the target row
        :type row_id: int
        :returns: float, the typicality, from 0 to 1
        """
        return su.row_structural_typicality(X_L_list, X_D_list, row_id)

    def column_structural_typicality(self, X_L_list, col_id):
        """
        Returns the typicality (opposite of anomalousness) of the given column.
        
        :param X_L_list: list of the latent variables associated with the latent state
        :type X_L_list: list of dict
        :param col_id: id of the target col
        :type col_id: int
        :returns: float, the typicality, from 0 to 1
        """
        return su.column_structural_typicality(X_L_list, col_id)

    def similarity(self, M_c, X_L_list, X_D_list, given_row_id, target_row_id, target_columns=None):
        """Computes the similarity of the given row to the target row, averaged over all the
        column indexes given by target_columns.

        :param M_c: The column metadata
        :type M_c: dict
        :param X_L: list of the latent variables associated with the latent state
        :type X_L: list of dicts
        :param X_D: list of the particular cluster assignments of each row in each view
        :type X_D: list of list of lists
        :param given_row_id: the id of one of the rows to measure similarity between
        :type given_row_id: int
        :param target_row_id: the id of the other row to measure similarity between
        :type target_row_id: int
        :param target_columns: the columns to average the similarity over. defaults to all columns.
        :type target_columns: int, string, or list of ints
        :returns: float

        """
        return su.similarity(M_c, X_L_list, X_D_list, given_row_id, target_row_id, target_columns)

    def impute(self, M_c, X_L, X_D, Y, Q, n):
        """Impute values from the predictive distribution of the given latent state

        :param M_c: The column metadata
        :type M_c: dict
        :param X_L: the latent variables associated with the latent state
        :type X_L: dict
        :param X_D: the particular cluster assignments of each row in each view
        :type X_D: list of lists
        :param Y: A list of constraints to apply when sampling.  Each constraint
                  is a triplet of (r, d, v): r is the row index, d is the column
                  index and v is the value of the constraint
        :type Y: list of lists
        :param Q: A list of values to sample.  Each value is doublet of (r, d):
                  r is the row index, d is the column index
        :type Q: list of lists
        :param n: the number of samples to use in the imputation
        :type n: int
        :returns: list of floats -- imputed values in the same order as
                  specified by Q

        """
        e = su.impute(M_c, X_L, X_D, Y, Q, n, self.get_next_seed)
        return e

    def impute_and_confidence(self, M_c, X_L, X_D, Y, Q, n):
        """Impute values and confidence of the value from the predictive
        distribution of the given latent state

        :param M_c: The column metadata
        :type M_c: dict
        :param X_L: the latent variables associated with the latent state
        :type X_L: dict
        :param X_D: the particular cluster assignments of each row in each view
        :type X_D: list of lists
        :param Y: A list of constraints to apply when sampling.  Each constraint
                  is a triplet of (r, d, v): r is the row index, d is the column
                  index and v is the value of the constraint
        :type Y: list of lists
        :param Q: A list of values to sample.  Each value is doublet of (r, d):
                  r is the row index, d is the column index
        :type Q: list of lists
        :param n: the number of samples to use in the imputation
        :type n: int
        :returns: list of lists -- list of (value, confidence) tuples in the
                  same order as specified by Q

        """
        if isinstance(X_L, (list, tuple)):
            assert isinstance(X_D, (list, tuple))
            # TODO: multistate impute doesn't exist yet
            #e,confidence = su.impute_and_confidence_multistate(M_c, X_L, X_D, Y, Q, n, self.get_next_seed)
            e, confidence = su.impute_and_confidence(
                M_c, X_L, X_D, Y, Q, n, self.get_next_seed)
        else:
            e, confidence = su.impute_and_confidence(
                M_c, X_L, X_D, Y, Q, n, self.get_next_seed)
        return (e, confidence)


def do_diagnostics_to_func_dict(do_diagnostics):
    diagnostic_func_dict = None
    reprocess_diagnostics_func = None
    if do_diagnostics:
        if isinstance(do_diagnostics, (dict,)):
            diagnostic_func_dict = do_diagnostics
        else:
            diagnostic_func_dict = dict(default_diagnostic_func_dict)
        if 'reprocess_diagnostics_func' in diagnostic_func_dict:
            reprocess_diagnostics_func = diagnostic_func_dict.pop(
                'reprocess_diagnostics_func')
    return diagnostic_func_dict, reprocess_diagnostics_func


def get_value_in_each_dict(key, dict_list):
    return numpy.array([dict_i[key] for dict_i in dict_list]).T


def munge_diagnostics(diagnostics_dict_list):
    # all dicts should have the same keys
    diagnostic_names = diagnostics_dict_list[0].keys()
    diagnostics_dict = {
        diagnostic_name: get_value_in_each_dict(diagnostic_name, diagnostics_dict_list)
        for diagnostic_name in diagnostic_names
    }
    return diagnostics_dict

# switched ordering so args that change come first
# FIXME: change LocalEngine.initialze to match ordering here


def _do_initialize(SEED, M_c, M_r, T, initialization, row_initialization,
                   ROW_CRP_ALPHA_GRID, COLUMN_CRP_ALPHA_GRID,
                   S_GRID, MU_GRID,
                   N_GRID,
                   ):
    p_State = State.p_State(M_c, T, initialization=initialization,
                            row_initialization=row_initialization, SEED=SEED,
                            ROW_CRP_ALPHA_GRID=ROW_CRP_ALPHA_GRID,
                            COLUMN_CRP_ALPHA_GRID=COLUMN_CRP_ALPHA_GRID,
                            S_GRID=S_GRID,
                            MU_GRID=MU_GRID,
                            N_GRID=N_GRID,
                            )
    X_L = p_State.get_X_L()
    X_D = p_State.get_X_D()
    return X_L, X_D


def _do_initialize_tuple(arg_tuple):
    return _do_initialize(*arg_tuple)

# switched ordering so args that change come first
# FIXME: change LocalEngine.analyze to match ordering here


def _do_analyze(SEED, X_L, X_D, M_c, T, kernel_list, n_steps, c, r,
                max_iterations, max_time,
                ROW_CRP_ALPHA_GRID, COLUMN_CRP_ALPHA_GRID,
                S_GRID, MU_GRID,
                N_GRID,
                CT_KERNEL,
                ):
    p_State = State.p_State(M_c, T, X_L, X_D, SEED=SEED,
                            ROW_CRP_ALPHA_GRID=ROW_CRP_ALPHA_GRID,
                            COLUMN_CRP_ALPHA_GRID=COLUMN_CRP_ALPHA_GRID,
                            S_GRID=S_GRID,
                            MU_GRID=MU_GRID,
                            N_GRID=N_GRID,
                            CT_KERNEL=CT_KERNEL
                            )
    p_State.transition(kernel_list, n_steps, c, r,
                       max_iterations, max_time)
    X_L_prime = p_State.get_X_L()
    X_D_prime = p_State.get_X_D()
    return X_L_prime, X_D_prime


def _do_analyze_tuple(arg_tuple):
    return _do_analyze_with_diagnostic(*arg_tuple)


def get_child_n_steps_list(n_steps, every_N):
    if every_N is None:
        # results in one block of size n_steps
        every_N = n_steps
    missing_endpoint = numpy.arange(0, n_steps, every_N)
    with_endpoint = numpy.append(missing_endpoint, n_steps)
    child_n_steps_list = numpy.diff(with_endpoint)
    return child_n_steps_list.tolist()

none_summary = lambda p_State: None

# switched ordering so args that change come first
# FIXME: change LocalEngine.analyze to match ordering here


def _do_analyze_with_diagnostic(SEED, X_L, X_D, M_c, T, kernel_list, n_steps, c, r,
        max_iterations, max_time, diagnostic_func_dict, every_N,
        ROW_CRP_ALPHA_GRID, COLUMN_CRP_ALPHA_GRID,
        S_GRID, MU_GRID,
        N_GRID,
        do_timing,
        CT_KERNEL,
        ):
    diagnostics_dict = collections.defaultdict(list)
    if diagnostic_func_dict is None:
        diagnostic_func_dict = dict()
        every_N = None
    child_n_steps_list = get_child_n_steps_list(n_steps, every_N)
    #
    p_State = State.p_State(M_c, T, X_L, X_D, SEED=SEED,
                            ROW_CRP_ALPHA_GRID=ROW_CRP_ALPHA_GRID,
                            COLUMN_CRP_ALPHA_GRID=COLUMN_CRP_ALPHA_GRID,
                            S_GRID=S_GRID,
                            MU_GRID=MU_GRID,
                            N_GRID=N_GRID,
                            CT_KERNEL=CT_KERNEL,
                            )
    with gu.Timer('all transitions', verbose=False) as timer:
        for child_n_steps in child_n_steps_list:
            p_State.transition(kernel_list, child_n_steps, c, r,
                               max_iterations, max_time)
            for diagnostic_name, diagnostic_func in diagnostic_func_dict.iteritems():
                diagnostic_value = diagnostic_func(p_State)
                diagnostics_dict[diagnostic_name].append(diagnostic_value)
                pass
            pass
        pass
    X_L_prime = p_State.get_X_L()
    X_D_prime = p_State.get_X_D()
    #
    if do_timing:
        # diagnostics and timing are exclusive
        diagnostics_dict = timer.elapsed_secs
        pass
    return X_L_prime, X_D_prime, diagnostics_dict


def _do_simple_predictive_sample(M_c, X_L, X_D, Y, Q, n, get_next_seed):
    is_multistate = su.get_is_multistate(X_L, X_D)
    if is_multistate:
        samples = su.simple_predictive_sample_multistate(M_c, X_L, X_D, Y, Q,
                                                         get_next_seed, n)
    else:
        samples = su.simple_predictive_sample(M_c, X_L, X_D, Y, Q,
                                              get_next_seed, n)
    return samples


default_diagnostic_func_dict = dict(
    # fully qualify path b/c dview.sync_imports can't deal with 'as'
    # imports
    logscore=crosscat.utils.diagnostic_utils.get_logscore,
    num_views=crosscat.utils.diagnostic_utils.get_num_views,
    column_crp_alpha=crosscat.utils.diagnostic_utils.get_column_crp_alpha,
    # any outputs required by reproess_diagnostics_func must be generated
    # as well
    column_partition_assignments=crosscat.utils.diagnostic_utils.get_column_partition_assignments,
    reprocess_diagnostics_func=crosscat.utils.diagnostic_utils.default_reprocess_diagnostics_func,
)


if __name__ == '__main__':
    import crosscat.utils.data_utils as du
    import crosscat.utils.convergence_test_utils as ctu
    import crosscat.utils.timing_test_utils as ttu

    # settings
    gen_seed = 0
    inf_seed = 0
    num_clusters = 4
    num_cols = 32
    num_rows = 400
    num_views = 2
    n_steps = 1
    n_times = 5
    n_chains = 3
    n_test = 100
    CT_KERNEL = 1

    # generate some data
    T, M_r, M_c, data_inverse_permutation_indices = du.gen_factorial_data_objects(
        gen_seed, num_clusters, num_cols, num_rows, num_views,
        max_mean=100, max_std=1, send_data_inverse_permutation_indices=True)
    view_assignment_truth, X_D_truth = ctu.truth_from_permute_indices(
        data_inverse_permutation_indices, num_rows, num_cols, num_views, num_clusters)

    # There is currently (4/7/2014) no ttu.get_generative_clustering function which 
    # X_L_gen, X_D_gen = ttu.get_generative_clustering(M_c, M_r, T,
    #                                                  data_inverse_permutation_indices, num_clusters, num_views)
    # T_test = ctu.create_test_set(M_c, T, X_L_gen, X_D_gen, n_test, seed_seed=0)
    # #
    # generative_mean_test_log_likelihood = ctu.calc_mean_test_log_likelihood(
    #     M_c, T,
    #     X_L_gen, X_D_gen, T_test)

    # run some tests
    engine = LocalEngine(seed=inf_seed)
    multi_state_ARIs = []
    multi_state_mean_test_lls = []
    X_L_list, X_D_list = engine.initialize(M_c, M_r, T, n_chains=n_chains)
    multi_state_ARIs.append(
        ctu.get_column_ARIs(X_L_list, view_assignment_truth))

    # multi_state_mean_test_lls.append(ctu.calc_mean_test_log_likelihoods(M_c, T,
    #                                                                     X_L_list, X_D_list, T_test))
    for time_i in range(n_times):
        X_L_list, X_D_list = engine.analyze(
            M_c, T, X_L_list, X_D_list, n_steps=n_steps, CT_KERNEL=CT_KERNEL)
        multi_state_ARIs.append(
            ctu.get_column_ARIs(X_L_list, view_assignment_truth))
        # multi_state_mean_test_lls.append(
        #     ctu.calc_mean_test_log_likelihoods(M_c, T,
        #                                        X_L_list, X_D_list, T_test))

    X_L_list, X_D_list, diagnostics_dict = engine.analyze(
        M_c, T, X_L_list, X_D_list,
        n_steps=n_steps, do_diagnostics=True)

    # print results
    ct_kernel_name = 'UNKNOWN'
    if CT_KERNEL==0:
        ct_kernel_name = 'GIBBS'
    elif CT_KERNEL==1:
        ct_kernel_name = 'METROPOLIS'
    
    print 'Running with %s CT_KERNEL' % (ct_kernel_name)
    print 'generative_mean_test_log_likelihood'
    # print generative_mean_test_log_likelihood
    #
    print 'multi_state_mean_test_lls:'
    print multi_state_mean_test_lls
    #
    print 'multi_state_ARIs:'
    print multi_state_ARIs

########NEW FILE########
__FILENAME__ = MultiprocessingEngine
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import multiprocessing
#
import crosscat.LocalEngine as LE
import crosscat.utils.sample_utils as su


class MultiprocessingEngine(LE.LocalEngine):
    """A simple interface to the Cython-wrapped C++ engine

    MultiprocessingEngine holds no state other than a seed generator.
    Methods use resources on the local machine.

    """

    def __init__(self, seed=None, cpu_count=None):
        """Initialize a MultiprocessingEngine

        This is really just setting the initial seed to be used for
        initializing CrossCat states.  Seeds are generated sequentially

        """
        super(MultiprocessingEngine, self).__init__(seed=seed)
        self.pool = multiprocessing.Pool(cpu_count)
        self.mapper = self.pool.map
        return
    
    def __enter__(self):
        return self

    def __del__(self):
        self.pool.terminate()

    def __exit__(self, type, value, traceback):
        self.pool.terminate()


if __name__ == '__main__':
    import crosscat.utils.data_utils as du
    import crosscat.utils.convergence_test_utils as ctu
    import crosscat.utils.timing_test_utils as ttu


    # settings
    gen_seed = 0
    inf_seed = 0
    num_clusters = 4
    num_cols = 32
    num_rows = 400
    num_views = 2
    n_steps = 1
    n_times = 5
    n_chains = 3
    n_test = 100


    # generate some data
    T, M_r, M_c, data_inverse_permutation_indices = du.gen_factorial_data_objects(
            gen_seed, num_clusters, num_cols, num_rows, num_views,
            max_mean=100, max_std=1, send_data_inverse_permutation_indices=True)
    view_assignment_truth, X_D_truth = ctu.truth_from_permute_indices(
            data_inverse_permutation_indices, num_rows, num_cols, num_views, num_clusters)
    X_L_gen, X_D_gen = ttu.get_generative_clustering(M_c, M_r, T,
            data_inverse_permutation_indices, num_clusters, num_views)
    T_test = ctu.create_test_set(M_c, T, X_L_gen, X_D_gen, n_test, seed_seed=0)
    #
    generative_mean_test_log_likelihood = ctu.calc_mean_test_log_likelihood(M_c, T,
            X_L_gen, X_D_gen, T_test)


    # run some tests
    engine = MultiprocessingEngine(seed=inf_seed)
    # single state test
    single_state_ARIs = []
    single_state_mean_test_lls = []
    X_L, X_D = engine.initialize(M_c, M_r, T, n_chains=1)
    single_state_ARIs.append(ctu.get_column_ARI(X_L, view_assignment_truth))
    single_state_mean_test_lls.append(
            ctu.calc_mean_test_log_likelihood(M_c, T, X_L, X_D, T_test)
            )
    for time_i in range(n_times):
        X_L, X_D = engine.analyze(M_c, T, X_L, X_D, n_steps=n_steps)
        single_state_ARIs.append(ctu.get_column_ARI(X_L, view_assignment_truth))
        single_state_mean_test_lls.append(
            ctu.calc_mean_test_log_likelihood(M_c, T, X_L, X_D, T_test)
            )
    # multistate test
    multi_state_ARIs = []
    multi_state_mean_test_lls = []
    X_L_list, X_D_list = engine.initialize(M_c, M_r, T, n_chains=n_chains)
    multi_state_ARIs.append(ctu.get_column_ARIs(X_L_list, view_assignment_truth))
    multi_state_mean_test_lls.append(ctu.calc_mean_test_log_likelihoods(M_c, T,
        X_L_list, X_D_list, T_test))
    for time_i in range(n_times):
        X_L_list, X_D_list = engine.analyze(M_c, T, X_L_list, X_D_list, n_steps=n_steps)
        multi_state_ARIs.append(ctu.get_column_ARIs(X_L_list, view_assignment_truth))
        multi_state_mean_test_lls.append(ctu.calc_mean_test_log_likelihoods(M_c, T,
            X_L_list, X_D_list, T_test))

    # print results
    print 'generative_mean_test_log_likelihood'
    print generative_mean_test_log_likelihood
    #
    print 'single_state_mean_test_lls:'
    print single_state_mean_test_lls
    #
    print 'single_state_ARIs:'
    print single_state_ARIs
    #
    print 'multi_state_mean_test_lls:'
    print multi_state_mean_test_lls
    #
    print 'multi_state_ARIs:'
    print multi_state_ARIs

########NEW FILE########
__FILENAME__ = settings
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
#!python
import os


project_name = 'crosscat'

class path():
    user_home_dir = os.environ['HOME']
    if 'WORKSPACE' in os.environ:
        user_home_dir = os.environ['WORKSPACE']
    # target installation for deployment
    remote_code_dir = os.path.join('/home/crosscat', project_name)
    # where we actually are right now
    this_dir = os.path.dirname(os.path.abspath(__file__))
    this_repo_dir = os.path.abspath(os.path.join(this_dir, '..'))
    install_script_dir = os.path.join(this_repo_dir, 'install_scripts')
    web_resources_dir = os.path.join(this_repo_dir, 'www')
    web_resources_data_dir = os.path.join(web_resources_dir, 'data')
    #
    install_ubuntu_script = os.path.join(install_script_dir,
                                         'install_ubuntu_packages.sh')
    install_boost_script = os.path.join(install_script_dir, 'install_boost.sh')
    virtualenv_setup_script = os.path.join(install_script_dir,
                                           'virtualenv_setup.sh')
    run_server_script = os.path.join(this_repo_dir, 'run_server.sh')
    run_webserver_script = os.path.join(this_repo_dir, 
                                        'run_simplehttpserver.sh')
    # server_script = os.path.join('jsonrpc_http', 'server_jsonrpc.py')
    try:
        os.makedirs(web_resources_dir)
        os.makedirs(web_resources_data_dir)
    except Exception, e:
        pass

class Hadoop():
    DEFAULT_CLUSTER = 'xdata_highmem'
    DEBUG = False
    #
    xdata_hadoop_jar_420 = "/usr/lib/hadoop-0.20-mapreduce/contrib/streaming/hadoop-streaming-2.0.0-mr1-cdh4.2.0.jar"
    xdata_hadoop_jar_412 = "/usr/lib/hadoop-0.20-mapreduce/contrib/streaming/hadoop-streaming-2.0.0-mr1-cdh4.1.2.jar"
    default_xdata_hadoop_jar = xdata_hadoop_jar_420 \
        if os.path.exists(xdata_hadoop_jar_420) else xdata_hadoop_jar_412
    default_xdata_compute_hdfs_uri = "hdfs://10.1.92.51:8020/"
    default_xdata_compute_jobtracker_uri = "10.1.92.53:8021"
    default_xdata_highmem_hdfs_uri = "hdfs://10.1.93.51:8020/"
    default_xdata_highmem_jobtracker_uri = "10.1.93.53:8021"
    #
    default_starcluster_hadoop_jar = "/usr/lib/hadoop-0.20/contrib/streaming/hadoop-streaming-0.20.2-cdh3u2.jar"
    default_starcluster_hdfs_uri = None
    default_starcluster_jobtracker_uri = None
    #
    default_localhost_hadoop_jar = default_xdata_hadoop_jar
    default_localhost_hdfs_uri = None
    default_localhost_jobtracker_uri = None
    #
    if DEFAULT_CLUSTER == 'starcluster':
      default_hadoop_jar = default_starcluster_hadoop_jar
      default_hdfs_uri = default_starcluster_hdfs_uri
      default_jobtracker_uri = default_starcluster_jobtracker_uri
    elif DEFAULT_CLUSTER == 'localhost':
      default_hadoop_jar = default_localhost_hadoop_jar
      default_hdfs_uri = default_localhost_hdfs_uri
      default_jobtracker_uri = default_localhost_jobtracker_uri
    else:
      default_hadoop_jar = default_xdata_hadoop_jar
      if DEFAULT_CLUSTER == 'xdata_compute':
        default_hdfs_uri = default_xdata_compute_hdfs_uri
        default_jobtracker_uri = default_xdata_compute_jobtracker_uri
      else:
        default_hdfs_uri = default_xdata_highmem_hdfs_uri
        default_jobtracker_uri = default_xdata_highmem_jobtracker_uri
    default_hadoop_binary = 'hadoop'
    default_engine_binary = '/user/bigdata/SSCI/hadoop_line_processor.jar'
    default_hdfs_dir = '/user/bigdata/SSCI/'
    default_output_path = 'myOutputDir'
    default_input_filename = 'hadoop_input'
    default_table_data_filename = 'table_data.pkl.gz'
    default_command_dict_filename = 'command_dict.pkl.gz'
    default_table_filename = os.path.join(path.web_resources_data_dir,
      'dha.csv')
    default_analyze_args_dict_filename = 'analyze_args_dict.pkl.gz'
    # 
    default_initialize_args_dict = dict(
        command='initialize',
        initialization='from_the_prior',
        )
    default_analyze_args_dict = dict(
        command='analyze',
        kernel_list=(),
        n_steps=1,
        c=(),
        r=(),
        max_time=-1,
        )

class s3():
    bucket_str = 'mitpcp-tabular-predDB'
    bucket_dir = ''
    ec2_credentials_file = os.path.expanduser('~/.boto')

class gdocs():
    auth_file = os.path.expanduser("~/mh_gdocs_auth")
    gdocs_folder_default = "MH"

class git():
    # repo_prefix = 'https://github.com/'
    # repo_prefix = 'git://github.com/'
    repo_prefix = 'git@github.com:'
    repo_suffix = 'mit-probabilistic-computing-project/' + project_name + '.git'
    repo = repo_prefix + repo_suffix
    branch = 'master'

########NEW FILE########
__FILENAME__ = spark_processing_example
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import sys
import argparse
#
from pyspark import SparkContext
#
import crosscat.utils.data_utils as du
import crosscat.utils.file_utils as fu
import crosscat.utils.xnet_utils as xu
import crosscat.utils.general_utils as gu
import crosscat.LocalEngine as LE


def initialize_helper(table_data, dict_in):
    M_c = table_data['M_c']
    M_r = table_data['M_r']
    T = table_data['T']
    initialization = dict_in['initialization']
    SEED = dict_in['SEED']
    engine = LE.LocalEngine(SEED)
    M_c_prime, M_r_prime, X_L, X_D = \
               engine.initialize(M_c, M_r, T, initialization=initialization)
    #
    ret_dict = dict(X_L=X_L, X_D=X_D)
    return ret_dict

def analyze_helper(table_data, dict_in):
    M_c = table_data['M_c']
    T = table_data['T']
    X_L = dict_in['X_L']
    X_D = dict_in['X_D']
    kernel_list = dict_in['kernel_list']
    n_steps = dict_in['n_steps']
    c = dict_in['c']
    r = dict_in['r']
    SEED = dict_in['SEED']
    engine = LE.LocalEngine(SEED)
    X_L_prime, X_D_prime = engine.analyze(M_c, T, X_L, X_D, kernel_list=kernel_list,
                                          n_steps=n_steps, c=c, r=r)
    #
    ret_dict = dict(X_L=X_L, X_D=X_D)
    return ret_dict

def time_analyze_helper(table_data, dict_in):
    start_dims = du.get_state_shape(dict_in['X_L'])
    with gu.Timer('time_analyze_helper', verbose=False) as timer:
        inner_ret_dict = analyze_helper(table_data, dict_in)
    end_dims = du.get_state_shape(inner_ret_dict['X_L'])
    T = table_data['T']
    table_shape = (len(T), len(T[0]))
    ret_dict = dict(
        table_shape=table_shape,
        start_dims=start_dims,
        end_dims=end_dims,
        elapsed_secs=timer.elapsed_secs,
        kernel_list=dict_in['kernel_list'],
        n_steps=dict_in['n_steps'],
        )
    return ret_dict

method_lookup = dict(
    initialize=initialize_helper,
    analyze=analyze_helper,
    time_analyze=time_analyze_helper,
    )

def process_line(line, table_data):
        key, dict_in = xu.parse_hadoop_line(line)
        if dict_in is None:
            return None, None
        command = dict_in['command']
        method = method_lookup[command]
        ret_dict = method(table_data, dict_in)
        return key, ret_dict

if __name__ == '__main__':
    pass

# read the files
table_data = fu.unpickle('table_data.pkl.gz')
with open('hadoop_input') as fh:
    lines = [line for line in fh]

sc = SparkContext("local", "Simple job")
broadcasted_table_data = sc.broadcast(table_data)
parallelized = sc.parallelize(lines)
map_result = parallelized.map(lambda line: process_line(line, broadcasted_table_data.value)).collect()

print map_result

#

########NEW FILE########
__FILENAME__ = starcluster_plugin
#!python
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import os
#
from starcluster.clustersetup import ClusterSetup
from starcluster.logger import log


project_name = 'crosscat'
#
repo_url = 'https://github.com/mit-probabilistic-computing-project/%s.git' % project_name
get_repo_dir = lambda user: os.path.join('/home', user, project_name)
get_install_script = lambda user: \
        os.path.join(get_repo_dir(user), 'scripts', 'install_scripts', 'install.sh')
get_setup_script = lambda user: os.path.join(get_repo_dir(user), 'setup.py')


class crosscatSetup(ClusterSetup):

    def __init__(self):
        # TODO: Could be generalized to "install a python package plugin"
        pass

    def run(self, nodes, master, user, user_shell, volumes):
        # set up some paths
        repo_dir = get_repo_dir(user)
        install_script = get_install_script(user)
        setup_script = get_setup_script(user)
        for node in nodes:
            # NOTE: nodes includes master
            log.info("Installing %s as root on %s" % (project_name, node.alias))
            #
            cmd_strs = [
                'rm -rf %s' % repo_dir,
                'git clone %s %s' % (repo_url, repo_dir),
                'bash %s' % install_script,
                'python %s install' % setup_script,
                'python %s build_ext --inplace' % setup_script,
                'chown -R %s %s' % (user, repo_dir),
            ]
            for cmd_str in cmd_strs:
                node.ssh.execute(cmd_str + ' >out 2>err')
                pass
            pass
        for node in nodes:
            log.info("Setting up %s as %s on %s" % (project_name, user, node.alias))
            #
            cmd_strs = [
                'mkdir -p ~/.matplotlib',
                'echo backend: Agg > ~/.matplotlib/matplotlibrc',
            ]
            for cmd_str in cmd_strs:
                node.shell(user=user, command=cmd_str)
                pass
            pass
        return

########NEW FILE########
__FILENAME__ = ContinuousComponentModel
import crosscat.cython_code.ContinuousComponentModel as ccm
import math
import random
import sys
import numpy

from scipy.misc import logsumexp as logsumexp
from scipy.stats import norm as norm

next_seed = lambda : random.randrange(2147483647)

LOG_2 = math.log(2.0)
default_hyperparameters = dict(nu=1.0, mu=0.0, s=1.0, r=1.0)
default_data_parameters = dict(mu=0.0, rho=1.0)


###############################################################################
#   Input-checking and exception-handling functions
###############################################################################
def check_type_force_float(x, name):
    """
    If an int is passed, convert it to a float. If some other type is passed, 
    raise an exception.
    """
    if type(x) is int:
        return float(x)
    elif type(x) is not float and type(x) is not numpy.float64:
        raise TypeError("%s should be a float" % name)
    else:
        return x

def check_data_type_column_data(X):
    """
    Makes sure that X is a numpy array and that it is a column vector
    """
    if type(X) is not numpy.ndarray:
        raise TypeError("X should be type numpy.ndarray")

    if len(X.shape) == 2 and X.shape[1] > 1:
        raise TypeError("X should have a single column.")

def check_hyperparams_dict(hypers):
    if type(hypers) is not dict:
        raise TypeError("hypers should be a dict")

    keys = ['mu', 'nu', 'r', 's']

    for key in keys:
        if key not in hypers.keys():
            raise KeyError("missing key in hypers: %s" % key)

    for key, value in hypers.iteritems():
        if key not in keys:
            raise KeyError("invalid hypers key: %s" % key)

        if type(value) is not float \
        and type(value) is not numpy.float64:
            raise TypeError("%s should be float" % key)

        if key in ['nu', 'r', 's']:
            if value <= 0.0:
                raise ValueError("hypers[%s] should be greater than 0" % key)


def check_model_params_dict(params):
    if type(params) is not dict:
        raise TypeError("params should be a dict")

    keys = ['mu', 'rho']

    for key in keys:
        if key not in params.keys():
            raise KeyError("missing key in params: %s" % key)

    for key, value in params.iteritems():
        if key not in keys:
            raise KeyError("invalid params key: %s" % key)

        if type(value) is not float \
        and type(value) is not numpy.float64:
            raise TypeError("%s should be float" % key)

        if key == "rho":
            if value <= 0.0:
                raise ValueError("rho should be greater than 0")
        elif key != "mu":
            raise KeyError("Invalid params key: %s" % key)

###############################################################################
#   The class extension
###############################################################################
class p_ContinuousComponentModel(ccm.p_ContinuousComponentModel):
    
    model_type = 'normal_inverse_gamma'
    cctype = 'continuous'
    
    @classmethod
    def from_parameters(cls, N, data_params=default_data_parameters, hypers=None, gen_seed=0):
        """
        Initialize a continuous component model with sufficient statistics
        generated from random data.
        Inputs:
          N: the number of data points
          data_params: a dict with the following keys
              mu: the mean of the data
              rho: the precision of the data
          hypers: a dict with the following keys
              mu: the prior mean of the data
              s: hyperparameter
              r: hyperparameter
              nu: hyperparameter
          gen_seed: an integer from which the rng is seeded
        """
        
        check_model_params_dict(data_params)

        data_rho = data_params['rho']
        
        data_mean = data_params['mu']
        data_std = (1.0/data_rho)**.5

        random.seed(gen_seed)
        X = [ [random.normalvariate(data_mean, data_std)] for i in range(N)]
        X = numpy.array(X)
        check_data_type_column_data(X)

        if hypers is None:
            hypers = cls.draw_hyperparameters(X, n_draws=1, gen_seed=next_seed())[0]
        
        check_hyperparams_dict(hypers)

        sum_x = numpy.sum(X)
        sum_x_squared = numpy.sum(X**2.0)
        
        hypers['fixed'] = 0.0
                        
        return cls(hypers, float(N), sum_x, sum_x_squared)
        
    @classmethod
    def from_data(cls, X, hypers=None, gen_seed=0):
        """
        Initialize a continuous component model with sufficient statistics
        generated from data X
        Inputs:
            X: a column of data (numpy)
            hypers: dict with the following entries
                mu: the prior mean of the data
                s: hyperparameter
                r: hyperparameter
                nu: hyperparameter
            gen_seed: a int to seed the rng
        """
        check_data_type_column_data(X)
        if type(gen_seed) is not int:
            raise TypeError("gen_seed should be an int")

        random.seed(gen_seed)
            
        if hypers is None:
            hypers = cls.draw_hyperparameters(X, gen_seed=next_seed())[0]
            
        check_hyperparams_dict(hypers)
            
        N = len(X)

        sum_x = numpy.sum(X)
        sum_x_squared = numpy.sum(X**2.0)
        
        hypers['fixed'] = 0.0
                        
        return cls(hypers, float(N), sum_x, sum_x_squared)
        
    def sample_parameters_given_hyper(self, gen_seed=0):
        """
        Samples a Gaussian parameter given the current hyperparameters.
        Inputs:
            gen_seed: integer used to seed the rng
        """
        if type(gen_seed) is not int:
            raise TypeError("gen_seed should be an int")
            
        random.seed(gen_seed)
        
        hypers = self.get_hypers()
        s = hypers['s']
        r = hypers['r']
        nu = hypers['nu']
        m = hypers['mu']
        
        rho = random.gammavariate(nu/2.0, s)
        mu = random.normalvariate(m, (r/rho)**.5)
        
        assert(rho > 0)
        
        params = {'mu': mu, 'rho': rho}
        
        return params
        
    def uncollapsed_likelihood(self, X, parameters):
        """
        Calculates the score of the data X under this component model with mean 
        mu and precision rho. 
        Inputs:
            X: A column of data (numpy)
            parameters: a dict with the following keys
                mu: the Gaussian mean
                rho: the precision of the Gaussian
        """
        check_data_type_column_data(X)
        check_model_params_dict(parameters)

        mu = parameters['mu']
        rho = parameters['rho']
    
        N = float(len(X))
        
        hypers = self.get_hypers()
        s = hypers['s']
        r = hypers['r']
        nu = hypers['nu']
        m = hypers['mu']
        
        sum_err = numpy.sum((mu-X)**2.0)
            
        log_likelihood = self.log_likelihood(X, {'mu':mu, 'rho':rho})   
        log_prior_mu = norm.logpdf(m, (r/rho)**.5)
        log_prior_rho = -(nu/2.0)*LOG_2+(nu/2.0)*math.log(s)+ \
            (nu/2.0-1.0)*math.log(rho)-.5*s*rho-math.lgamma(nu/2.0)
            
        log_p = log_likelihood + log_prior_mu + log_prior_rho
        
        return log_p
                
    @staticmethod
    def log_likelihood(X, parameters):
        """
        Calculates the log likelihood of the data X given mean mu and precision
        rho.
        Inputs:
            X: a column of data (numpy)
            parameters: a dict with the following keys
                mu: the Gaussian mean
                rho: the precision of the Gaussian
        """
        check_data_type_column_data(X)
        check_model_params_dict(parameters)
        
        sigma = (1.0/parameters['rho'])**.5

        log_likelihood = numpy.sum(norm.logpdf(X,parameters['mu'],sigma))
        
        return log_likelihood
        
    @staticmethod
    def log_pdf(X, parameters):
        """
        Calculates the pdf for each point in the data X given mean mu and 
        precision rho.
        Inputs:
            X: a column of data (numpy)
            parameters: a dict with the following keys
                mu: the Gaussian mean
                rho: the precision of the Gaussian
        """
        check_data_type_column_data(X)
        check_model_params_dict(parameters)
        
        sigma = (1.0/parameters['rho'])**.5
        
        return norm.logpdf(X,parameters['mu'],sigma)

    @staticmethod
    def cdf(X, parameters):
        """
        Calculates the cdf for each point in the data X given mean mu and 
        precision rho.
        Inputs:
            X: a column of data (numpy)
            parameters: a dict with the following keys
                mu: the Gaussian mean
                rho: the precision of the Gaussian
        """
        check_data_type_column_data(X)
        check_model_params_dict(parameters)
        
        sigma = (1.0/parameters['rho'])**.5
        
        return norm.cdf(X,parameters['mu'],sigma)
        
    def brute_force_marginal_likelihood(self, X, n_samples=10000, gen_seed=0):
        """
        Calculates the log marginal likelihood via brute force method in which
        parameters (mu and rho) are repeatedly drawn from the prior, the 
        likelihood is calculated for each set of parameters, then the average is
        taken.
        Inputs:
            X: A column of data (numpy)
            n_samples: the number of draws
            gen_Seed: seed for the rng
        """
        check_data_type_column_data(X)

        if type(n_samples) is not int:
            raise TypeError("n_samples should be an int")
        if n_samples <= 0:
            raise ValueError("n_samples should be greater than 0")
        if type(gen_seed) is not int:
            raise TypeError("gen_seed should be an int")
            
        N = float(len(X))
        random.seed(gen_seed)
        log_likelihoods = [0]*n_samples        
        for i in range(n_samples):
            params = self.sample_parameters_given_hyper(gen_seed=next_seed())
            log_likelihoods[i] = self.log_likelihood(X, params)
            
        log_marginal_likelihood = logsumexp(log_likelihoods) - math.log(N)
        
        return log_marginal_likelihood
        
    @staticmethod
    def generate_discrete_support(params, support=0.95, nbins=100):
        """
        returns a set of intervals over which the component model pdf is 
        supported. 
        Inputs:
            params: a dict with entries 'mu' and 'rho'
            nbins: cardinality of the set or the number of grid points in the 
                approximation
            support: a float in (0,1) that describes the amount of probability 
                we want in the range of support 
        """
        if type(nbins) is not int:
            raise TypeError("nbins should be an int")
            
        if nbins <= 0:
            raise ValueError("nbins should be greater than 0")
            
        support = check_type_force_float(support, "support")
        if support <= 0.0 or support >= 1.0:
            raise ValueError("support is a float st: 0 < support < 1")
            
        check_model_params_dict(params)
        
        mu = params['mu']
        sigma = (1.0/params['rho'])**.5
        
        interval = norm.interval(support,mu,sigma)
        
        a = interval[0]
        b = interval[1]
        
        support_range = b - a;
        support_bin_size = support_range/(nbins-1.0)
        
        bins = [a+i*support_bin_size for i in range(nbins)]

        return bins
    
    @staticmethod
    def draw_hyperparameters(X, n_draws=1, gen_seed=0):
        """
        Draws hyperparameters r, nu, mu, and s from the same distribution that 
        generates the grid in the C++ code.
        Inputs:
             X: a column of data (numpy)
             n_draws: the number of draws
             gen_seed: seed the rng
        Output:
            A list of dicts of draws where each entry has keys 'mu', 'r', 'nu',
            and 's'.
        """
        check_data_type_column_data(X)
        if type(n_draws) is not int:
            raise TypeError("n_draws should be an int")
        if type(gen_seed) is not int:
            raise TypeError("gen_seed should be an int")
        
        random.seed(gen_seed)
        
        samples = []
        
        N = float(len(X))
        data_mean = numpy.sum(X)/N
        
        sum_sq_deviation = numpy.sum((data_mean-X)**2.0)
            
        nu_r_draw_range = (0.0, math.log(N))
        mu_draw_range = (numpy.min(X), numpy.max(X))
        s_draw_range = (sum_sq_deviation/100.0, sum_sq_deviation)
            
        for i in range(n_draws):
            nu = math.exp(random.uniform(nu_r_draw_range[0], nu_r_draw_range[1]))
            r = math.exp(random.uniform(nu_r_draw_range[0], nu_r_draw_range[1]))
            mu = random.uniform(mu_draw_range[0], mu_draw_range[1])
            s = random.uniform(s_draw_range[0], s_draw_range[1])
            
            this_draw = dict(nu=nu, r=r, mu=mu, s=s)
            
            samples.append(this_draw)
            
        assert len(samples) == n_draws
        
        return samples

    @staticmethod
    def generate_data_from_parameters(params, N, gen_seed=0):
        """
        Generates data from a gaussina distribution
        Inputs:
            params: a dict with entries 'mu' and 'rho'
            N: number of data points
        """
        if type(N) is not int:
            raise TypeError("N should be an int")
            
        if N <= 0:
            raise ValueError("N should be greater than 0")
            
        check_model_params_dict(params)
        
        mu = params['mu']
        sigma = (1.0/params['rho'])**.5

        X = numpy.array([[random.normalvariate(mu, sigma)] for i in range(N)])

        assert len(X) == N

        return X
    
    @staticmethod
    def get_suffstat_names():
        """
        Returns a list of the names of the sufficient statistics
        """
        params = ['sum_x', 'sum_x_squared']
        return params
    
    @staticmethod
    def get_suffstat_bounds():
        """
        Returns a dict where each key-value pair is a sufficient statistic and a 
        tuple with the lower and upper bounds
        """
        minf = float("-inf")
        inf = float("inf")
        params = dict(sum_x=(minf,inf), sum_x_squared=(0.0 ,inf))
        return params
    
    @staticmethod
    def get_hyperparameter_names():
        """
        Returns a list of the names of the prior hyperparameters
        """
        params = ['mu', 'nu', 'r', 's']
        return params
        
    @staticmethod
    def get_hyperparameter_bounds():
        """
        Returns a dict where each key-value pair is a hyperparameter and a 
        tuple with the lower and upper bounds
        """
        minf = float("-inf")
        inf = float("inf")
        params = dict(mu=(minf,inf), nu=(0.0 ,inf), r=(0.0, inf), s=(0.0, inf))
        return params
        
    @staticmethod
    def get_model_parameter_names():
        """
        Returns a list of the names of the model parameters
        """
        params = ['mu', 'rho']
        return params
        
    @staticmethod
    def get_model_parameter_bounds():
        """
        Returns a dict where each key-value pair is a model parameter and a 
        tuple with the lower and upper bounds
        """
        minf = float("-inf")
        inf = float("inf")
        params = dict(mu=(minf,inf), rho=(0.0 ,inf))
        return params
            
        
########NEW FILE########
__FILENAME__ = MultinomialComponentModel
import crosscat.cython_code.MultinomialComponentModel as mcm
import math
import random
import sys
import numpy

from scipy.misc import logsumexp as logsumexp
from scipy.special import gammaln as gammaln

next_seed = lambda : random.randrange(2147483647)

###############################################################################
#	Input-checking and exception-handling functions
###############################################################################
def check_type_force_float(x, name):
    """
    If an int is passed, convert it to a float. If some other type is passed, 
    raise an exception.
    """
    if type(x) is int:
        return float(x)
    elif type(x) is not float and type(x) is not numpy.float64:
        raise TypeError("%s should be a float" % name)
    else:
        return x

def counts_to_data(counts):
	"""
	Converts a vector of counts to data.
	"""
	assert type(counts) is list or type(counts) is numpy.ndarray
	K = len(counts)
	N = int(sum(counts))
	X = []
	for k in range(K):
		i = 0
		while i < counts[k]:
			X.append([k])
			i += 1

		assert i == counts[k]

	assert len(X) == N

	random.shuffle(X)
	X = numpy.array(X, dtype=float)

	return X


def check_data_type_column_data(X):
    """
    Makes sure that X is a numpy array and that it is a column vector
    """
    if type(X) is list:
    	X = numpy.array(X)

    if type(X) is not numpy.ndarray:
        raise TypeError("X should be type numpy.ndarray or a list")

    if len(X.shape) == 2 and X.shape[1] > 1:
        raise TypeError("X should have a single column.")


def check_model_parameters_dict(model_parameters_dict):
	
	if type(model_parameters_dict) is not dict:
		raise TypeError("model_parameters_dict should be a dict")

	keys = ['weights']

	for key in keys:
		if key not in model_parameters_dict.keys():
			raise KeyError("model_parameters_dict should have key %s" % key)

	for key, value in model_parameters_dict.iteritems():
		if key == "weights":
			if type(value) is not list:
				raise TypeError("model parameters dict key 'weights' should be a list")
			if type(value[0]) is list:
				raise TypeError("weights should not be a list of lists, should be a list of floats")
			if math.fabs(sum(value) - 1.0) > .00000001:
				raise ValueError("model parameters dict key 'weights' should sum to 1.0")
		else:
			raise KeyError("invalid key, %s, for model parameters dict" % key)

def check_hyperparameters_dict(hyperparameters_dict):
	
	# 'fixed' key is not necessary for user-defined hyperparameters
	keys = ['dirichlet_alpha', 'K']

	for key in keys:
		if key not in hyperparameters_dict.keys():
			raise KeyError("hyperparameters_dict should have key %s" % key)

	for key, value in hyperparameters_dict.iteritems():
		if key == "K":
			if type(value) is not int:
				raise TypeError("hyperparameters dict entry K should be an int")

			if value < 1:
				raise ValueError("hyperparameters dict entry K should be greater than 0")
		elif key == "dirichlet_alpha":
			if type(value) is not float \
			and type(value) is not numpy.float64 \
			and type(value) is not int:
				raise TypeError("hyperparameters dict entry dirichlet_alpha should be a float or int")

			if value <= 0.0:
				raise ValueError("hyperparameters dict entry dirichlet_alpha should be greater than 0")

		elif key == "fixed":
			pass
		else:
			raise KeyError("invalid key, %s, for hyperparameters dict" % key)

def check_data_vs_k(X,K):
	if type(X) is numpy.ndarray:
		X = X.flatten(1)
		X = X.tolist()
	K_data = len(set(X))
	if K_data > K:
		raise ValueError("the number of items in the data is greater than K")

###############################################################################
#	The class extension
###############################################################################
class p_MultinomialComponentModel(mcm.p_MultinomialComponentModel):
    
    model_type = 'symmetric_dirichlet_discrete'
    cctype = 'multinomial'

    @classmethod
    def from_parameters(cls, N, params=None, hypers=None, gen_seed=0):
		"""
		Initialize a continuous component model with sufficient statistics
		generated from random data.
		Inputs:
		  N: the number of data points
		  params: a dict with the following keys
		      weights: a K-length list that sums to 1.0
		  hypers: a dict with the following keys
		      K: the number of categories
		      dirichlet_alpha: Dirichlet alpha parameter. The distribution is
		      symmetric so only one value is needed
		  gen_seed: an integer from which the rng is seeded
		"""

		if type(N) is not int:
			raise TypeError("N should be an int")
		if type(gen_seed) is not int:
			raise TypeError("gen_seed should be an int")

		# if the parameters dict or the hypers dict exist, validate them
		if params is not None:
			check_model_parameters_dict(params)

		if hypers is not None:
			check_hyperparameters_dict(hypers)

		random.seed(gen_seed)
		numpy.random.seed(gen_seed)

		# get the number of categories
		if params is None:
			if hypers is None:
				K = int(N/2.0)
			else:
				K = int(hypers['K'])
			weights = numpy.random.random((1,K))
			weights = weights/numpy.sum(weights)
			weights = weights.tolist()[0]
			assert len(weights) == K
			params = dict(weights=weights)

			check_model_parameters_dict(params)
		else:
			K = len(params['weights'])
			if hypers:
				if K != hypers['K']:
					raise ValueError("K in params does not match K in hypers")
	        
        # generate synthetic data
		counts = numpy.array(numpy.random.multinomial(N, params['weights']), dtype=int)

		X = counts_to_data(counts)
		
		check_data_type_column_data(X)

        # generate the sufficient statistics
		suffstats = dict()
		for k in range(K):
			suffstats[str(k)] = counts[k]

		if hypers is None:
			hypers = cls.draw_hyperparameters(X, n_draws=1, gen_seed=next_seed())[0]
			check_hyperparameters_dict(hypers)

		# hypers['K'] = check_type_force_float(hypers['K'], "hypers['K']")
		hypers['dirichlet_alpha'] = check_type_force_float(hypers['dirichlet_alpha'], "hypers['dirichlet_alpha']")
        
		# add fixed parameter to hyperparameters
		hypers['fixed'] = 0.0

		suffstats = {'counts':suffstats}

		return cls(hypers, float(N), **suffstats)

    @classmethod
    def from_data(cls, X, hypers=None, gen_seed=0):
		"""
		Initialize a continuous component model with sufficient statistics
		generated from data X
		Inputs:
		    X: a column of data (numpy)
		    hypers: a dict with the following keys
		      K: the number of categories
		      dirichlet_alpha: Dirichlet alpha parameter. The distribution is
		      symmetric so only one value is needed
		    gen_seed: a int to seed the rng
		"""
		# FIXME: Figure out a wat to accept a list of strings
		check_data_type_column_data(X)
		if type(gen_seed) is not int:
			raise TypeError("gen_seed should be an int")

		random.seed(gen_seed)
		numpy.random.seed(gen_seed)
            
		if hypers is None:
			hypers = cls.draw_hyperparameters(X, gen_seed=next_seed())[0]
			check_hyperparameters_dict(hypers)
		else:
			check_hyperparameters_dict(hypers)
			K = hypers['K']
			check_data_vs_k(X,K)
            
		hypers['dirichlet_alpha'] = check_type_force_float(hypers['dirichlet_alpha'], "hypers['dirichlet_alpha']")
            
		N = len(X)
		K = hypers['K']

		counts = [0]*K
		for x in X:
			try:
				counts[int(x)] += 1
			except IndexError:
				raise IndexError

		# generate the sufficient statistics
		suffstats = dict()
		for k in range(int(K)):
			suffstats[str(k)] = counts[k]

		suffstats = {'counts':suffstats}

		hypers['fixed'] = 0.0
                        
		return cls(hypers, float(N), **suffstats)

    def sample_parameters_given_hyper(self, gen_seed=0):
        """
        Samples weights given the current hyperparameters
        Inputs:
            gen_seed: integer used to seed the rng
        """
        if type(gen_seed) is not int:
            raise TypeError("gen_seed should be an int")
            
        random.seed(gen_seed)
        numpy.random.seed(gen_seed)
        
        hypers = self.get_hypers()
        dirichlet_alpha = hypers['dirichlet_alpha']
        K = hypers['K']

        alpha = numpy.array([dirichlet_alpha]*int(K))

        weights = numpy.random.dirichlet(alpha)
        weights = weights.tolist()
        
        params = {'weights': weights}
        
        return params

    def uncollapsed_likelihood(self, X, params):
        """
        Calculates the score of the data X under this component model with mean 
        mu and precision rho. 
        Inputs:
            X: A column of data (numpy)
            params: a dict with the following keys
                weights: a list of category weights (should sum to 1)
        """
        check_data_type_column_data(X)
        check_model_parameters_dict(params)
        
        hypers = self.get_hypers()

        assert len(params['weights']) == int(hypers['K'])

        dirichlet_alpha = hypers['dirichlet_alpha']
        K = float(hypers['K'])
        check_data_vs_k(X,K)

        weights = numpy.array(params['weights'])

        log_likelihood = self.log_likelihood(X, params)
        logB = gammaln(dirichlet_alpha)*K - gammaln(dirichlet_alpha*K)
        log_prior = -logB + numpy.sum((dirichlet_alpha-1.0)*numpy.log(weights))

        log_p = log_likelihood + log_prior

        return log_p

    @staticmethod
    def log_likelihood(X, params):
        """
        Calculates the log likelihood of the data X given mean mu and precision
        rho.
        Inputs:
            X: a column of data (numpy)
            params: a dict with the following keys
                weights: a list of categories weights (should sum to 1)
        """
        check_data_type_column_data(X)
        check_model_parameters_dict(params)
        
        N = len(X)
        K = len(params['weights'])
        check_data_vs_k(X,K)
        counts= numpy.bincount(X,minlength=K)

        weights = numpy.array(params['weights'])

        A = gammaln(N+1)-numpy.sum(gammaln(counts+1))
        B = numpy.sum(counts*numpy.log(weights));
        
        log_likelihood = A+B

        return log_likelihood

    @staticmethod
    def log_pdf(X, params):
        """
        Calculates the log pdf of the data X given mean mu and precision
        rho.
        Inputs:
            X: a column of data (numpy)
            params: a dict with the following keys
                weights: a list of categories weights (should sum to 1)
        """
        check_data_type_column_data(X)
        check_model_parameters_dict(params)
        
        N = len(X)
        
        weights = numpy.array(params['weights'])

        lpdf = []
        for x in X:
            w = weights[int(x)]
            if w == 0.0 or w == 0:
                lpdf.append(float('-Inf'))
            else:
                lpdf.append(math.log(w))
        
        return numpy.array(lpdf)

    def brute_force_marginal_likelihood(self, X, n_samples=10000, gen_seed=0):
        """
        Calculates the log marginal likelihood via brute force method in which
        parameters (weights) are repeatedly drawn from the prior, the 
        likelihood is calculated for each set of parameters, then the average is
        taken.
        Inputs:
            X: A column of data (numpy)
            n_samples: the number of draws
            gen_Seed: seed for the rng
        """
        check_data_type_column_data(X)

        if type(n_samples) is not int:
            raise TypeError("n_samples should be an int")
        if n_samples <= 0:
            raise ValueError("n_samples should be greater than 0")
        if type(gen_seed) is not int:
            raise TypeError("gen_seed should be an int")
            
        hypers = self.get_hypers()
        K = hypers['K']
        check_data_vs_k(X,K)

        N = float(len(X))

        random.seed(gen_seed)
        log_likelihoods = [0]*n_samples        
        for i in range(n_samples):
            params = self.sample_parameters_given_hyper(gen_seed=next_seed())
            log_likelihoods[i] = self.log_likelihood(X, params)
            
        log_marginal_likelihood = logsumexp(log_likelihoods) - math.log(N)
        
        return log_marginal_likelihood

    @staticmethod
    def generate_discrete_support(params):
        """
        Returns the a sequential list of the number of categories
        Inputs:
            params: a dict with entries 'mu' and 'rho'
        """
        check_model_parameters_dict(params)

        return range(len(params['weights']))


    @staticmethod
    def draw_hyperparameters(X, n_draws=1, gen_seed=0):
        """
        Draws hyperparameters dirichlet_alpha from the same distribution that 
        generates the grid in the C++ code.
        Inputs:
             X: a column of data or an int which acts as K. If a data array is 
             	provided, K is assumed to be max(X)+1
             n_draws: the number of draws
             gen_seed: seed the rng
        Output:
            A list of dicts of draws where each entry has keys 'dirichlet_alpha'
            and 'K'. K is defined by the data and will be the same for each samples
        """
        if type(X) is list or type(X) is numpy.ndarray:
	        check_data_type_column_data(X)
	        K = int(max(X)+1)
        elif type(X) is int:
        	if X < 1:
        		raise ValueError("If X is an int, it should be greatert than 1")
        	K = X
        else:
        	raise TypeError("X should be an array or int")

        if type(n_draws) is not int:
            raise TypeError("n_draws should be an int")

        if type(gen_seed) is not int:
            raise TypeError("gen_seed should be an int")
        
        random.seed(gen_seed)
        
        samples = []
                
        # get draw ranges
        alpha_draw_range = (0.1, math.log(K))
            

        for i in range(n_draws):
            alpha = math.exp(random.uniform(alpha_draw_range[0], alpha_draw_range[1]))

            this_draw = dict(dirichlet_alpha=alpha, K=K)
            
            samples.append(this_draw)
            
        assert len(samples) == n_draws
        
        return samples

    @staticmethod
    def generate_data_from_parameters(params, N, gen_seed=0):
        """
        returns a set of intervals over which the component model pdf is 
        supported. 
        Inputs:
            params: a dict with entries 'weights'
            N: number of data points
        """
        if type(N) is not int:
            raise TypeError("N should be an int")
            
        if N <= 0:
            raise ValueError("N should be greater than 0")
            
        if type(params) is not dict:
            raise TypeError("params should be a dict")
            
        check_model_parameters_dict(params)
        
        # multinomial draw
        counts = numpy.array(numpy.random.multinomial(N, params['weights']), dtype=int)

        X = counts_to_data(counts)

        assert len(X) == N

        return X


########NEW FILE########
__FILENAME__ = cpp_long_tests
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import subprocess
import os

def test_view():
    run_shell_command('test_view')

def test_view_speed():
    run_shell_command('test_view_speed')

def test_state():
    run_shell_command('test_state')

def run_shell_command(name):
    p = subprocess.Popen(['%s/%s' % (os.path.dirname(os.path.abspath(__file__)), name)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    retcode = p.wait()
    out = p.stdout.read()
    err = p.stderr.read()
    if len(err) > 0:
        fail(err)

########NEW FILE########
__FILENAME__ = cpp_unit_tests
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import subprocess
import os

def test_component_model():
    run_shell_command('test_component_model')

def test_continuous_component_model():
    run_shell_command('test_continuous_component_model')

def test_multinomial_component_model():
    run_shell_command('test_multinomial_component_model')

def test_cluster():
    run_shell_command('test_cluster')

def run_shell_command(name):
    p = subprocess.Popen(['%s/%s' % (os.path.dirname(os.path.abspath(__file__)), name)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    retcode = p.wait()
    out = p.stdout.read()
    err = p.stderr.read()
    if len(err) > 0:
        fail(err)


########NEW FILE########
__FILENAME__ = kl_divergence_as_function_of_n

import crosscat.tests.component_model_extensions.ContinuousComponentModel as ccmext
import crosscat.tests.quality_tests.synthetic_data_generator as sdg
import crosscat.tests.quality_tests.quality_test_utils as qtu
import crosscat.utils.data_utils as du
import crosscat.MultiprocessingEngine as mpe

import random
import numpy
import pylab

import pdb

def test_kl_divergence_as_a_function_of_N_and_transitions():

	n_clusters = 3
	n_chains = 8
	do_times = 4

	# N_list = [25, 50, 100, 250, 500, 1000, 2000]
	N_list = [25, 50, 100, 175, 250, 400, 500]

	# max_transitions = 500
	max_transitions = 500
	transition_interval = 50
	t_iterations = max_transitions/transition_interval

	cctype = 'continuous'
	cluster_weights = [1.0/float(n_clusters)]*n_clusters
	separation = .5

	get_next_seed = lambda : random.randrange(2147483647)

	# data grid
	KLD = numpy.zeros((len(N_list), t_iterations+1))

	for _ in range(do_times):
		for n in range(len(N_list)):
			N = N_list[n]
			T, M_c, struc = sdg.gen_data([cctype], N, [0], [cluster_weights], 
							[separation], seed=get_next_seed(), distargs=[None],
							return_structure=True)

			M_r = du.gen_M_r_from_T(T)

			# precompute the support and pdf to speed up calculation of KL divergence
			support = qtu.get_mixture_support(cctype, 
						ccmext.p_ContinuousComponentModel, 
						struc['component_params'][0], nbins=1000, support=.995)
			true_log_pdf = qtu.get_mixture_pdf(support,
						ccmext.p_ContinuousComponentModel, 
						struc['component_params'][0],cluster_weights)

			# intialize a multiprocessing engine
			mstate = mpe.MultiprocessingEngine(cpu_count=8)
			X_L_list, X_D_list = mstate.initialize(M_c, M_r, T, n_chains=n_chains)

			# kl_divergences
			klds = numpy.zeros(len(X_L_list))

			for i in range(len(X_L_list)):
				X_L = X_L_list[i]
				X_D = X_D_list[i]
				KLD[n,0] += qtu.KL_divergence(ccmext.p_ContinuousComponentModel,
						struc['component_params'][0], cluster_weights, M_c, 
						X_L, X_D, n_samples=1000, support=support, 
						true_log_pdf=true_log_pdf)


			# run transition_interval then take a reading. Rinse and repeat.
			for t in range( t_iterations ):
				X_L_list, X_D_list = mstate.analyze(M_c, T, X_L_list, X_D_list,
							n_steps=transition_interval)

				for i in range(len(X_L_list)):
					X_L = X_L_list[i]
					X_D = X_D_list[i]
					KLD[n,t+1] += qtu.KL_divergence(ccmext.p_ContinuousComponentModel,
							struc['component_params'][0], cluster_weights, M_c, 
							X_L, X_D, n_samples=1000, support=support, 
							true_log_pdf=true_log_pdf)


	KLD /= float(n_chains*do_times)

	pylab.subplot(1,3,1)
	pylab.contourf(range(0,max_transitions+1,transition_interval), N_list, KLD)
	pylab.title('KL divergence')
	pylab.ylabel('N')
	pylab.xlabel('# transitions')


	pylab.subplot(1,3,2)
	m_N = numpy.mean(KLD,axis=1)
	e_N = numpy.std(KLD,axis=1)/float(KLD.shape[1])**-.5
	pylab.errorbar(N_list,  m_N, yerr=e_N)
	pylab.title('KL divergence by N')
	pylab.xlabel('N')
	pylab.ylabel('KL divergence')

	pylab.subplot(1,3,3)
	m_t = numpy.mean(KLD,axis=0)
	e_t = numpy.std(KLD,axis=0)/float(KLD.shape[0])**-.5
	pylab.errorbar(range(0,max_transitions+1,transition_interval), m_t, yerr=e_t)
	pylab.title('KL divergence by transitions')
	pylab.xlabel('trasition')
	pylab.ylabel('KL divergence')

	pylab.show()

	return KLD

if __name__ == '__main__':
	test_kl_divergence_as_a_function_of_N_and_transitions()
########NEW FILE########
__FILENAME__ = geweke_on_schemas
import operator
import itertools
from functools import partial
#
import crosscat.utils.geweke_utils as geweke_utils
from crosscat.utils.general_utils import MapperContext, NoDaemonPool, Timer


def _generate_args_list(num_rows, num_iters, ct_kernel, cctypes):
    num_cols = len(cctypes)
    args_list = [
            '--num_rows', str(num_rows),
            '--num_cols', str(num_cols),
            '--CT_KERNEL', str(ct_kernel),
            '--num_iters', str(num_iters),
            '--cctypes'
            ] + cctypes
    return args_list

def _gen_cctypes(*args):
    _cctypes = [[cctype] * N for (cctype, N) in args]
    return reduce(operator.add, _cctypes)

def generate_args_list(base_num_rows, num_iters, do_long=False, _divisor=1.):
    num_cols_list = [1, 10]
    col_type_list = ['continuous', 'multinomial']
    col_type_pairs = sorted(itertools.combinations(col_type_list, 2))
    ct_kernel_list = [0, 1]
    args_list = []

    # single datatype
    iter_over = itertools.product(col_type_list, num_cols_list, ct_kernel_list)
    for col_type, num_cols, ct_kernel in iter_over:
        cctypes = _gen_cctypes((col_type, num_cols))
        args = _generate_args_list(base_num_rows, num_iters, ct_kernel, cctypes)
        args += ['--_divisor', str(_divisor)]
        args_list.append(args)
        pass

    # pairs of datatypes
    iter_over = itertools.product(col_type_pairs, num_cols_list, ct_kernel_list)
    for (col_type_a, col_type_b), num_cols, ct_kernel in iter_over:
        cctypes = _gen_cctypes((col_type_a, num_cols), (col_type_b, num_cols))
        args = _generate_args_list(base_num_rows, num_iters, ct_kernel, cctypes)
        args += ['--_divisor', str(_divisor)]
        args_list.append(args)
        pass

    # hard coded runs
    if do_long:
        num_cols_long = 100
        num_rows_long = 100
        #
        cctypes = _gen_cctypes(('continuous', num_cols_long))
        args = _generate_args_list(num_rows_long, num_iters, cctypes)
        args += ['--_divisor', str(_divisor)]
        args_list.append(args + ['--CT_KERNEL', str(0)])
        args_list.append(args + ['--CT_KERNEL', str(1)])
        #
        cctypes = _gen_cctypes(('multinomial', num_cols_long))
        args = _generate_args_list(num_rows_long, num_iters, cctypes)
        args += ['--_divisor', str(_divisor)]
        args += ['--num_multinomial_values', '2']
        args_list.append(args + ['--CT_KERNEL', str(0)])
        args_list.append(args + ['--CT_KERNEL', str(1)])
        #
#        cctypes = _gen_cctypes(('multinomial', num_cols_long))
#        args = _generate_args_list(num_rows_long, num_iters, cctypes)
#        args += ['--num_multinomial_values', '128']
#        args_list.append(args)
        pass
    return args_list

def plot_results(results, dirname='./'):
    with Timer('plotting') as timer:
        with MapperContext(Pool=NoDaemonPool) as mapper:
            # use non-daemonic mapper since plot_result spawns daemonic processes
            plotter = partial(geweke_utils.plot_result,
                    dirname=dirname)
            mapper(plotter, results)
            pass
        pass
    return

if __name__ == '__main__':
    import argparse
    import experiment_runner.experiment_utils as eu
    from experiment_runner.ExperimentRunner import ExperimentRunner, propagate_to_s3
    parser = argparse.ArgumentParser()
    parser.add_argument('--dirname', default='geweke_on_schemas', type=str)
    parser.add_argument('--base_num_rows', default=10, type=int)
    parser.add_argument('--num_iters', default=2000, type=int)
    parser.add_argument('--no_plots', action='store_true')
    parser.add_argument('--do_long', action='store_true')
    parser.add_argument('--_divisor', default=1., type=float)

    args = parser.parse_args()
    dirname = args.dirname
    base_num_rows = args.base_num_rows
    num_iters = args.num_iters
    do_plots = not args.no_plots
    do_long = args.do_long
    _divisor = args._divisor


    # create configs
    arg_list_to_config = partial(eu.arg_list_to_config,
            geweke_utils.generate_parser(),
            arbitrate_args=geweke_utils.arbitrate_args)
    args_list = generate_args_list(base_num_rows, num_iters, do_long, _divisor)
    config_list = map(arg_list_to_config, args_list)


    # do experiments
    er = ExperimentRunner(geweke_utils.run_geweke, storage_type='fs',
            dirname_prefix=dirname,
            bucket_str='experiment_runner')
    er.do_experiments(config_list)
    # push to s3
    propagate_to_s3(er)


    if do_plots:
        for id in er.frame.index:
            result = er._get_result(id)
            geweke_utils.plot_result(result, dirname)
            pass
        pass

    print er.frame

########NEW FILE########
__FILENAME__ = parse_mi
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import numpy
import csv
import os
import ast
import pickle

import crosscat.utils.inference_utils as iu
import crosscat.utils.xnet_utils as xu

import pdb

def is_hadoop_file(filename):
	name, extension = os.path.splitext(filename)
	if extension is 'gz':
		return True
	else:
		return False

def parse_line(test, mi, linfoot):
	index = test['id']
	num_rows = test['num_rows']
	num_cols = test['num_cols']
	num_views = test['num_views']
	num_clusters = test['num_clusters']
	corr = test['corr']
	
	row = [index, num_rows, num_cols, num_views, num_clusters, corr, mi, linfoot]

	return row

def hadoop_to_dict_generator(test_key_file_object):
	# return read cursor to the start (or this generator cannot be called again)
	test_key_file_object.seek(0)
	for line in test_key_file_object:
		dict_line = xu.parse_hadoop_line(line)
		yield dict_line
	
def parse_data_to_csv(test_key_filename, params_dict, n_tests, output_filename):
	# open input file and convert to list of dicts
	test_key_file_object = open(test_key_filename, 'rb')
	input_lines = hadoop_to_dict_generator(test_key_file_object)

	# open output file and convert to list of dicts
	output_file_object = open(output_filename, 'rb')
	results = hadoop_to_dict_generator(output_file_object)
	
	n_datasets = params_dict['n_datasets']
	n_samples = params_dict['n_samples']

	header = ['id', 'num_rows', 'num_cols', 'num_views', 'num_clusters', 'corr','MI','Linfoot']

	# data_mi = [[[0] for i in range(n_datasets)] for i in range(n_tests)]
	# data_linfoot = [[[0] for i in range(n_datasets)] for i in range(n_tests)]
	# counts = [[[0] for i in range(n_datasets)] for i in range(n_tests)]

	data_mi = [0.0]*n_tests
	data_linfoot = [0.0]*n_tests
	counts = [0.0]*n_tests


	for result in results:
		res = result[1] # because it's a tuple with an id at index 0
		test_idx = res['id']
		test_dataset = res['dataset']
		test_sample = res['sample']
		
		data_mi[test_idx] += float(res['mi']) 
		data_linfoot[test_idx] += float(iu.mutual_information_to_linfoot(res['mi']))
		counts[test_idx] += 1.0
	
	for test_ids in range(n_tests):
		data_mi[test_idx] /= counts[test_idx]
		data_linfoot[test_idx] /= counts[test_idx]

	# # calculate the mean over samples
	# for test in range(n_tests):
		
	# 	for dataset in range(n_datasets):
	# 		try:
	# 			data_mi[test][dataset] = numpy.array(data_mi[test][dataset],dtype=float)
	# 		except ValueError:
	# 			pdb.set_trace()

	# 		try:
	# 			data_mi[test][dataset] = numpy.mean(data_mi[test][dataset],axis=0)
	# 		except TypeError:
	# 			pdb.set_trace()

	# 		data_linfoot[test][dataset] = mi_to_linfoot(data_mi[test][dataset])

	# 		data_mi[test][dataset] = numpy.mean(data_mi[test][dataset])
	# 		data_linfoot[test][dataset] = numpy.mean(data_linfoot[test][dataset])

	# 	# now calculate the mean over datasets
	# 	data_mi[test] = numpy.mean(numpy.array(data_mi[test]))
	# 	data_linfoot[test] = numpy.mean(numpy.array(data_linfoot[test]))
	
	name, extension = os.path.splitext(output_filename)

	outfile = name + '.csv'

	with open(outfile,'w') as csvfile:
		csvwriter = csv.writer(csvfile,delimiter=',')
		csvwriter.writerow(header)
		current_idx = -1
		for test in input_lines:
			res = test[1]
			test_idx = res['id']
			if test_idx != current_idx:
				current_idx = test_idx
				line = parse_line(res, data_mi[test_idx], data_linfoot[test_idx])
				csvwriter.writerow(line)

def mi_to_linfoot(mi):
	#
	# linfoot = numpy.zeros(mi.shape)
	# if len(mi.shape) == 1:
	# 	for entry in range(mi.size):
	# 		linfoot[entry] = iu.mutual_information_to_linfoot(mi[entry])
	# else:
	# 	for r in range(mi.shape[0]):
	# 		for c in range(mi.shape[1]):
	# 			linfoot[r,c] = iu.mutual_information_to_linfoot(mi[r,c])


	# return linfoot
	return [iu.mutual_information_to_linfoot(m) for m in mi]

if __name__ == "__main__":

	import argparse
	parser = argparse.ArgumentParser()

	parser.add_argument('--key_filename', type=str)
	parser.add_argument('--params_filename', type=str)
	parser.add_argument('--n_tests', type=int)
	parser.add_argument('--output_filename', type=str)

	args = parser.parse_args()

	key_filename = args.key_filename
	output_filename = args.output_filename
	n_tests = args.n_tests
	params_filename = args.params_filename
	params_dict = pickle.load( open( params_filename, "rb" ))



	parse_data_to_csv(key_filename, params_dict, n_tests, output_filename)


########NEW FILE########
__FILENAME__ = run_mi_test
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import itertools as it
import time

import argparse
import numpy
import tempfile 
import parse_mi
import pickle

import os

import crosscat.cython_code.State as State
import crosscat.utils.hadoop_utils as hu
import crosscat.utils.file_utils as fu
import crosscat.utils.xnet_utils as xu
import crosscat.LocalEngine as LE
import crosscat.HadoopEngine as HE

import run_mi_test_local

def generate_hadoop_dicts(which_kernels, impute_run_parameters, args_dict):
    for which_kernel in which_kernels:
        kernel_list = (which_kernel, )
        dict_to_write = dict(impute_run_parameters)
        dict_to_write.update(args_dict)
        # must write kernel_list after update
        dict_to_write['kernel_list'] = kernel_list
        yield dict_to_write

def write_hadoop_input(input_filename, impute_run_parameters, SEED):
    # prep settings dictionary
    impute_analyze_args_dict = xu.default_analyze_args_dict
    impute_analyze_args_dict['command'] = 'impute_analyze'
    with open(input_filename, 'a') as out_fh:
        xu.write_hadoop_line(out_fh, key=SEED, dict_to_write=impute_run_parameters)

# # example of how to run a simple test run on hadoop (xdata VM)
# python run_mi_test.py --num_datasets 5 --num_samples 10 --which_engine_binary /user/bigdata/SSCI/be_mi_tests_00.jar \
# --num_rows_list 10 --num_cols_list 2 --num_clusters_list 2 --num_views_list 1 --corr_list .1 .99 -do_remote
# # example of a full run
# python run_mi_test.py --which_engine_binary /user/bigdata/SSCI/be_mi_tests_00.jar -do_remote

# Run
if __name__ == '__main__':

	default_num_rows_list = [100, 500, 1000] 
	default_num_cols_list = [2, 4, 8, 16]	
	default_num_clusters_list = [10, 25, 50]	
	default_num_views_list = [1, 2, 4, 8, 16]
	default_correlation_list = [.1, .5, .9]

	# short test
	# default_num_rows_list = [10] 
	# default_num_cols_list = [2, 4, 8]	
	# default_num_clusters_list = [2]	
	# default_num_views_list = [1]
	# default_correlation_list = [.9]
	
	#
	parser = argparse.ArgumentParser()
	parser.add_argument('--gen_seed', type=int, default=0)
	parser.add_argument('--num_datasets', type=int, default=5)
	parser.add_argument('--num_samples', type=int, default=50)
	parser.add_argument('--burn_in', type=int, default=250)
	parser.add_argument('--which_engine_binary', type=str,
	        default=HE.default_engine_binary)
	parser.add_argument('--jobtracker_uri', type=str,
	        default=HE.default_jobtracker_uri)
		parser.add_argument('--hdfs_uri', type=str,
	        default=HE.default_hdfs_uri)
	parser.add_argument('--which_engine_binary', type=str,
	        default=HE.default_engine_binary)
	parser.add_argument('-do_local', action='store_true')
	parser.add_argument('-do_remote', action='store_true')
	parser.add_argument('--num_rows_list', type=int, nargs='*',
	        default=default_num_rows_list)
	parser.add_argument('--num_cols_list', type=int, nargs='*',
	        default=default_num_cols_list)
	parser.add_argument('--num_clusters_list', type=int, nargs='*',
	        default=default_num_clusters_list)
	parser.add_argument('--num_views_list', type=int, nargs='*',
	        default=default_num_views_list)
	parser.add_argument('--corr_list', type=float, nargs='*',
	        default=default_correlation_list)

	#
	args = parser.parse_args()
	data_seed = args.gen_seed
	do_local = args.do_local
	do_remote = args.do_remote
	burn_in = args.burn_in
	jobtracker_uri = args.jobtracker_uri
	hdfs_uri = args.hdfs_uri
	num_samples = args.num_samples
	num_datasets = args.num_datasets
	num_rows_list = args.num_rows_list
	num_cols_list = args.num_cols_list
	num_clusters_list = args.num_clusters_list
	num_views_list = args.num_views_list
	corr_list = args.corr_list
	which_engine_binary = args.which_engine_binary
	#
	print 'using burn_in: %i' % burn_in
	print 'using num_rows_list: %s' % num_rows_list
	print 'using num_cols_list: %s' % num_cols_list
	print 'using num_clusters_list: %s' % num_clusters_list
	print 'using num_views_list: %s' % num_views_list
	print 'using corr_list: %s' % corr_list
	print 'using engine_binary: %s' % which_engine_binary
	time.sleep(2)

	dirname = 'mi_analysis'
	fu.ensure_dir(dirname)
	directory_path = tempfile.mkdtemp(prefix='mi_analysis_',
                                dir=dirname)

	print 'output sent to %s' % directory_path

	output_path = os.path.join(directory_path, 'output')
	output_filename = os.path.join(directory_path, 'hadoop_output')
	table_data_filename = os.path.join(directory_path, 'table_data.pkl.gz')

	assert(os.path.exists(directory_path))
	
	input_filename = os.path.join(directory_path, "hadoop_input")
	params_filename = os.path.join(directory_path, "test_params.pkl")
	key_filename = os.path.join(directory_path, "test_key.pkl")
	
	# create a parameters dict
	params_dict = {
		'n_rows' 	  : num_rows_list,
		'n_clusters'  : num_clusters_list,
		'n_cols' 	  : num_cols_list,
		'n_views' 	  : num_views_list,
		'corr' 	  	  : corr_list,
		'n_datasets'  : num_datasets,
		'n_samples'   : num_samples,
		'n_datasets'  : num_datasets,
		'burn_in' 	  : burn_in
	}

	# save the params file as pickle
	try:
		pd_file = open( params_filename, "wb" )
	except IOError as err:
		print "Could not create %s. " % params_filename, err
		raise

	pickle.dump( params_dict, pd_file )
	pd_file.close()

	# cartesian product of test parameters. 
	tests = list(it.product(*[num_rows_list, num_clusters_list, num_cols_list, num_views_list, corr_list]))

	testlist = []
	
	print "Writing tests file."	
	test_idx = 0
	for n_rows, n_clusters, n_cols, n_views, corr in tests:	
		if n_rows >= n_clusters and n_cols >= n_views:
			for dataset in range(num_datasets):
				for sample in range(num_samples):
					impute_run_parameters = dict(
							id=test_idx,
							dataset=dataset,
							sample=sample,
							num_clusters=n_clusters,
							num_rows=n_rows,
							num_cols=n_cols,
							num_views=n_views,
							corr=corr,
							burn_in=burn_in,
							SEED=data_seed+dataset,
							CCSEED=data_seed+dataset+sample
						)

					write_hadoop_input(input_filename, impute_run_parameters, SEED=data_seed+dataset)
					if do_local:
						testlist.append(impute_run_parameters)
			test_idx += 1
	
	print "Done."
	
	# table data is empty because we generate it in the mapper
	table_data=dict(T=[],M_c=[],X_L=[],X_D=[])
	fu.pickle(table_data, table_data_filename)

	#####################
	if do_local:
		output_filename = os.path.join(directory_path, "output_local")
		output_file_object = open(output_filename, 'ab')
		with open(input_filename,'rb') as infile:
			for line in infile:
				key, test_dict = xu.parse_hadoop_line(line)
				ret_dict = run_mi_test_local.run_mi_test_local(test_dict)
				xu.write_hadoop_line(output_file_object, key, ret_dict)
				print "%s\n\t%s" % (str(test_dict), str(ret_dict))

		output_file_object.close()
		# generate the csv
		parse_mi.parse_data_to_csv(input_filename, params_dict, test_idx, output_filename)
		print "Done."
	elif do_remote:
		# generate the massive hadoop files
		hadoop_engine = HE.HadoopEngine(output_path=output_path,
                                    input_filename=input_filename,
                                    table_data_filename=table_data_filename,
                                    which_engine_binary=which_engine_binary,
                                    hdfs_uri=hdfs_uri,
                                    jobtracker_uri=jobtracker_uri,
                                    )
	
		xu.write_support_files(table_data, hadoop_engine.table_data_filename,
	                              dict(command='mi_analyze'), hadoop_engine.command_dict_filename)
		t_start = time.time()
		hadoop_engine.send_hadoop_command(n_tasks=len(testlist))
		was_successful = hadoop_engine.get_hadoop_results()
		if was_successful:
			t_end = time.time()
			t_total = t_end-t_start
			print "That took %i seconds." % t_total
			hu.copy_hadoop_output(hadoop_engine.output_path, output_filename)
			parse_mi.parse_data_to_csv(input_filename, params_dict, test_idx, output_filename)
		else:
			print "Hadoop job was NOT successful. Check %s" % output_path

########NEW FILE########
__FILENAME__ = run_mi_test_local
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import itertools
import random
import numpy
import crosscat.LocalEngine as LE
import crosscat.utils.inference_utils as iu
import crosscat.utils.mutual_information_test_utils as mitu

def run_mi_test_local(data_dict):

    gen_seed = data_dict['SEED']
    crosscat_seed = data_dict['CCSEED']
    num_clusters = data_dict['num_clusters']
    num_cols = data_dict['num_cols']
    num_rows = data_dict['num_rows']
    num_views = data_dict['num_views']
    corr = data_dict['corr']
    burn_in = data_dict['burn_in']
    mean_range = float(num_clusters)*2.0

    # 32 bit signed int
    random.seed(gen_seed)
    get_next_seed = lambda : random.randrange(2147483647)

    # generate the stats
    T, M_c, M_r, X_L, X_D, view_assignment = mitu.generate_correlated_state(num_rows,
        num_cols, num_views, num_clusters, mean_range, corr, seed=gen_seed);

    table_data = dict(T=T,M_c=M_c)

    engine = LE.LocalEngine(crosscat_seed)
    X_L_prime, X_D_prime = engine.analyze(M_c, T, X_L, X_D, n_steps=burn_in) 

    X_L = X_L_prime
    X_D = X_D_prime

    view_assignment = numpy.array(X_L['column_partition']['assignments'])
 
    # for each view calclate the average MI between all pairs of columns
    n_views = max(view_assignment)+1
    MI = []
    Linfoot = []
    queries = []
    MI = 0.0
    pairs = 0.0
    for view in range(n_views):
        columns_in_view = numpy.nonzero(view_assignment==view)[0]
        combinations = itertools.combinations(columns_in_view,2)
        for pair in combinations:
            any_pairs = True
            queries.append(pair)
            MI_i, Linfoot_i = iu.mutual_information(M_c, [X_L], [X_D], [pair], n_samples=1000)
            MI += MI_i[0][0]
            pairs += 1.0

    
    if pairs > 0.0:
        MI /= pairs

    ret_dict = dict(
        id=data_dict['id'],
        dataset=data_dict['dataset'],
        sample=data_dict['sample'],
        mi=MI,
        )

    return ret_dict

########NEW FILE########
__FILENAME__ = test_mutual_information
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

# calculated the mutual information of various shapes of data
import numpy
import pylab as pl
import crosscat.utils.sample_utils as su
import crosscat.utils.inference_utils as iu
import crosscat.utils.data_utils as du
import crosscat.cython_code.State as State

import random
import math

def ring(n=200):

	X = numpy.zeros((n,2))
	for i in range(n):
		angle = random.uniform(0,2*math.pi)
		distance = random.uniform(1,1.5)
		X[i,0] = math.cos(angle)*distance
		X[i,1] = math.sin(angle)*distance

	return X

def circle(n=200):

	X = numpy.zeros((n,2))
	for i in range(n):
		angle = random.uniform(0,2*math.pi)
		distance = random.uniform(0,1.5)
		X[i,0] = math.cos(angle)*distance
		X[i,1] = math.sin(angle)*distance

	return X

def square(n=200):

	X = numpy.zeros((n,2))
	for i in range(n):
		x = random.uniform(-1,1)
		y = random.uniform(-1,1)
		X[i,0] = x
		X[i,1] = y

	return X

def diamond(n=200):

	X = square(n=n)
	for i in range(n):
		angle = math.atan(X[i,1]/X[i,0])
		angle += math.pi/4 
		hyp = (X[i,0]**2.0+X[i,1]**2.0)**.5
		x = math.cos(angle)*hyp
		y = math.sin(angle)*hyp
		X[i,0] = x
		X[i,1] = y

	return X

def four_dots(n=200):
	X = numpy.zeros((n,2))
	nb = n/4
	mx = [ -1, 1, -1, 1]
	my = [ -1, -1, 1, 1]
	s = .25
	
	for i in range(n):
		n = random.randrange(4)
		x = random.normalvariate(mx[n], s)
		y = random.normalvariate(my[n], s)
		X[i,0] = x
		X[i,1] = y
		
	return X

def correlated(r,n=200):
	X = numpy.random.multivariate_normal([0,0], [[1, r],[r, 1]], n)
	return X

def sample_from_view(M_c, X_L, X_D, get_next_seed):
    
    view_col = X_L['column_partition']['assignments'][0]
    view_col2 = X_L['column_partition']['assignments'][1]

    same_view = True
    if view_col2 != view_col:
    	same_view = False

    view_state = X_L['view_state'][view_col]
    view_state2 = X_L['view_state'][view_col2]

    cluster_crps = numpy.exp(su.determine_cluster_crp_logps(view_state))
    cluster_crps2 = numpy.exp(su.determine_cluster_crp_logps(view_state2))

    assert( math.fabs(numpy.sum(cluster_crps) - 1) < .00000001 )

    samples = numpy.zeros((n,2))

    
    cluster_idx1 = numpy.nonzero(numpy.random.multinomial(1, cluster_crps))[0][0]
    cluster_model1 = su.create_cluster_model_from_X_L(M_c, X_L, view_col, cluster_idx1)

    if same_view:
    	cluster_idx2 = cluster_idx1
    	cluster_model2 = cluster_model1
    else:
    	cluster_idx2 = numpy.nonzero(numpy.random.multinomial(1, cluster_crps2))[0][0]
    	cluster_model2 = su.create_cluster_model_from_X_L(M_c, X_L, view_col2, cluster_idx2)

    component_model1 = cluster_model1[0]
    x = component_model1.get_draw(get_next_seed())

    component_model2 = cluster_model2[1]
    y = component_model2.get_draw(get_next_seed())
        
    return x, y

def sample_data_from_crosscat(M_c, X_Ls, X_Ds, get_next_seed, n):

	X = numpy.zeros((n,2))
	n_samples = len(X_Ls)
	
	for i in range(n):
		cc = random.randrange(n_samples)
		x, y = sample_from_view(M_c, X_Ls[cc], X_Ds[cc], get_next_seed)
		
		X[i,0] = x
		X[i,1] = y

	return X

def do_test(which_plot, max_plots, n, burn_in, cc_samples, which_test, correlation=0, do_plot=False):
	if which_test is "correlated":
		X = correlated(correlation, n=n)
	elif which_test is "square":
		X = square(n=n)
	elif which_test is "ring":
		X = ring(n=n)
	elif which_test is "circle":
		X = circle(n=n)
	elif which_test is "diamond":
		X = diamond(n=n)
	elif which_test is "blob":
		X = correlated(0.0, n=n)
	elif which_test is "dots":
		X = four_dots(n=n)
	elif which_test is "mixed":
		X = numpy.vstack((correlated(.95, n=n/2),correlated(0, n=n/2)))

	get_next_seed = lambda : random.randrange(32000)

	# Build a state
	M_c = du.gen_M_c_from_T(X.tolist())
	state = State.p_State(M_c, X.tolist())
	X_Ls = []
	X_Ds = []
	
	# collect crosscat samples
	for _ in range(cc_samples):
		state = State.p_State(M_c, X.tolist())
		state.transition(n_steps=burn_in)
		X_Ds.append(state.get_X_D())
		X_Ls.append(state.get_X_L())

	SX = sample_data_from_crosscat(M_c, X_Ls, X_Ds, get_next_seed, n)

	if do_plot:
		pl.subplot(2,max_plots,which_plot)
		pl.scatter(X[:,0],X[:,1],c='blue',alpha=.5)
		pl.title("Original data")
		pl.subplot(2,max_plots,max_plots+which_plot)
		pl.scatter(SX[:,0],SX[:,1],c='red',alpha=.5)
		pl.title("Sampled data")
		pl.show

	return M_c, X_Ls, X_Ds

def MI_test(n, burn_in, cc_samples, which_test, n_MI_samples=500, correlation=0):
	M_c, X_Ls, X_Ds = do_test(0, 0, n, burn_in, cc_samples, "correlated", correlation=correlation, do_plot=False)
	# query column 0 and 1
	MI, Linfoot = iu.mutual_information(M_c, X_Ls, X_Ds, [(0,1)], n_samples=n_MI_samples)

	MI = numpy.mean(MI)
	Linfoot = numpy.mean(Linfoot)
	
	if which_test == "correlated":
		test_strn = "Test: correlation (%1.2f), N: %i, burn_in: %i, samples: %i, MI_samples: %i\n\tMI: %f, Linfoot %f" % (correlation, n, burn_in, cc_samples, n_MI_samples, MI, Linfoot)
	else:
		test_strn = "Test: %s, N: %i, burn_in: %i, samples: %i, MI_samples: %i\n\tMI: %f, Linfoot %f" % (which_test, n, burn_in, cc_samples, n_MI_samples, MI, Linfoot)
		

	print test_strn
	return test_strn

do_plot = False
n_mi_samples = 500

N = [10, 100, 1000] 

burn_in = 200
cc_samples = 10

print " "
for n in N:
	
	strn = MI_test(n, burn_in, cc_samples, "correlated", correlation=.3)
	strn = MI_test(n, burn_in, cc_samples, "correlated", correlation=.6)
	strn = MI_test(n, burn_in, cc_samples, "correlated", correlation=.9)
	strn = MI_test(n, burn_in, cc_samples, "ring")
	strn = MI_test(n, burn_in, cc_samples, "dots")
	strn = MI_test(n, burn_in, cc_samples, "mixed")



########NEW FILE########
__FILENAME__ = test_mutual_information_vs_correlation
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

# calculates mutual information of a 2 column data set with different correlations
import numpy
import pylab as pl
import crosscat.utils.inference_utils as iu
import crosscat.utils.data_utils as du
import crosscat.cython_code.State as State

from scipy.stats import pearsonr as pearsonr

import random

def get_correlations(T, Q):
	T = numpy.array(T)
	corr = []

	for query in Q:
		r, p = scipy.stats.pearsonr(T[:,Q[0]], T[:,Q[1]])
		corr.append(r)

	return corr

def gen_correlated_data( n, r, SEED=0 ):
	numpy.random.seed(SEED)
	T = numpy.random.multivariate_normal([0,0],[[1,r],[r,1]],n)

	return T

get_next_seed = lambda : random.randrange(32000)

correlations = [.0, .1, .2, .3, .4 , .5, .6, .7, .8, .9, 1.0]
# N = [5, 10, 25, 50]
N = [100]
n_samples = 10
n_data_sets = 3
pl.figure()
burn_in = 200

subplot = 0
for n in N:
	subplot += 1
	nr = 0
	
	for r in correlations:
		for d in range(n_data_sets): # 3 data sets
			#
			T = gen_correlated_data( n, r, SEED=get_next_seed())

			pr, p = pearsonr(T[:,0], T[:,1])

			print "num_samples: %i, R: %f, d: %i. Actual R: %f" % (n, r, d+1, pr)

			M_c = du.gen_M_c_from_T(T)
			X_Ls = []
			X_Ds = []

			for _ in range(n_samples):
				state = State.p_State(M_c, T)
				state.transition(n_steps=burn_in)
				X_Ds.append(state.get_X_D())
				X_Ls.append(state.get_X_L())
			
			MI, Linfoot = iu.mutual_information(M_c, X_Ls, X_Ds, [(0,1)], n_samples=200)

			if d == 0:
				data_d = numpy.transpose(Linfoot)
			else:
				data_d = numpy.vstack((data_d, numpy.transpose(Linfoot)))

		if nr == 0:
			data = data_d
		else:
			data = numpy.hstack((data, data_d))
		
		nr += 1


	pl.subplot(1,1,subplot)
	pl.boxplot(data)
	title = "N=%i" % n
	pl.title(title)

pl.show()

########NEW FILE########
__FILENAME__ = quality_test_utils
import crosscat.utils.sample_utils as su

import numpy
import math

import pdb

from scipy.misc import logsumexp

is_discrete = {
    'multinomial' : True,
    'ordinal' : True,
    'continuous' : False
    }

def get_mixture_pdf(X, component_model_class, parameters_list, component_weights):
    """ FIXME: Add doc
    """

    if not isinstance(X, numpy.ndarray) and not isinstance(X, list):
        raise TypeError("X should be a list or numpy array of data")

    if not isinstance(parameters_list, list):
        raise TypeError('parameters_list should be a list')

    if not isinstance(component_weights, list):
        raise TypeError('component_weights should be a lsit')

    if len(parameters_list) != len(component_weights):
        raise ValueError("parameters_list and component_weights should have the\
            same number of elements")

    if math.fabs(sum(component_weights)-1.0) > .0000001:
        raise ValueError("component_weights should sum to 1")

    for w in component_weights:
        assert component_weights >= 0.0

    K = len(component_weights)

    lpdf = numpy.zeros((K,len(X)))

    for k in range(K):
        if component_weights[k] == 0.0:
            lp = 0
        else:
            lp = math.log(component_weights[k])+component_model_class.log_pdf(X,
                    parameters_list[k])

        lpdf[k,:] = lp

    lpdf = logsumexp(lpdf,axis=0)

    assert len(lpdf) == len(X)

    return lpdf

def bincount(X, bins=None):
    """ Counts the elements in X according to bins.
        Inputs:
            - X: A 1-D list or numpt array or integers.
            - bins: (optional): a list of elements. If bins is None, bins will
                be range range(min(X), max(X)+1). If bins is provided, bins
                must contain at least each element in X
        Outputs: 
            - counts: a list of the number of element in each bin
        Ex:
            >>> import quality_test_utils as qtu
            >>> X = [0, 1, 2, 3]
            >>> qtu.bincount(X)
            [1, 1, 1, 1]
            >>> X = [1, 2, 2, 4, 6]
            >>> qtu.bincount(X)
            [1, 2, 0, 1, 0, 1]
            >>> bins = range(7)
            >>> qtu.bincount(X,bins)
            [0, 1, 2, 0, 1, 0, 1]
            >>> bins = [1,2,4,6]
            >>> qtu.bincount(X,bins)
            [1, 2, 1, 1]
    """

    if not isinstance(X, list) and not isinstance(X, numpy.ndarray):
        raise TypeError('X should be a list or a numpy array')

    if isinstance(X, numpy.ndarray):
        if len(X.shape) > 1:
            if X.shape[1] != 1:
                raise ValueError('X should be a vector')

    Y = numpy.array(X, dtype=int)
    if bins == None:
        minval = numpy.min(Y)
        maxval = numpy.max(Y)

        bins = range(minval, maxval+1)

    if not isinstance(bins, list):
        raise TypeError('bins should be a list')

    counts = [0]*len(bins)

    for y in Y:
        bin_index = bins.index(y)
        counts[bin_index] += 1

    assert len(counts) == len(bins)
    assert sum(counts) == len(Y)

    return counts

def get_mixture_support(cctype, component_model_class, parameters_list, support=.95, nbins=500):
    """
    """
    if cctype == 'multinomial':
        discrete_support = component_model_class.generate_discrete_support(
                            parameters_list[0])
    else:
        for k in range(len(parameters_list)):
            model_parameters = parameters_list[k]
            support_k = numpy.array(component_model_class.generate_discrete_support(
                        model_parameters, support=support))
            if k == 0:
                all_support = support_k
            else:
                all_support = numpy.hstack((all_support, support_k))

        discrete_support = numpy.linspace(numpy.min(all_support), 
                            numpy.max(all_support), num=nbins)

        assert len(discrete_support) == nbins

    return numpy.array(discrete_support)

def KL_divergence(component_model_class, parameters_list, component_weights,
    M_c, X_L, X_D, n_samples=1000, true_log_pdf=None, support=None):
    """ FIXME: Add doc
    """

    # FIXME: Add validation code

    cctype = component_model_class.cctype

    # get support (X)
    if support is None:
        support = get_mixture_support(cctype, component_model_class, parameters_list, 
                nbins=n_samples, support=.995)
    elif not isinstance(support, numpy.ndarray):
        raise TypeError("support must be a numpy array (vector)")

    # get true pdf
    if true_log_pdf is None:
        true_log_pdf = get_mixture_pdf(support, component_model_class, parameters_list,
                    component_weights)
    elif not isinstance(true_log_pdf, numpy.ndarray):
        raise TypeError("true_log_pdf should be a numpy array (vector)")

    row = len(X_D[0])
    Q = [ (row,0,x) for x in support ]

    # get predictive probabilities
    pred_probs = su.simple_predictive_probability(M_c, X_L, X_D, []*len(Q), Q)

    kld = KL_divergence_arrays(support, pred_probs, true_log_pdf,
            is_discrete[cctype])

    return float(kld)

def KL_divergence_arrays(support, log_true, log_inferred, is_discrete):
    """
        Separated this function from KL_divergence for testing purposes.
        Inputs:
            - support: numpy array of support intervals
            - log_true: log pdf at support for the "true" distribution
            - log_inferred: log pdf at support for the distribution to test against the
              "true" distribution
            - is_discrete: is this a discrete variable True/False
        Returns:
            - KL divergence
    """

    # KL divergence formula, recall X and Y are log
    F = (log_true-log_inferred)*numpy.exp(log_true)
    if is_discrete:
        kld = numpy.sum(F)
    else:
        # trapezoidal quadrature
        intervals = numpy.diff(support)
        fs = F[:-1] + (numpy.diff(F) / 2.0)
        kld = numpy.sum(intervals*fs)

    return kld


########NEW FILE########
__FILENAME__ = synthetic_data_generator
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import crosscat.utils.data_utils as du
import crosscat.utils.sample_utils as su

import crosscat.tests.component_model_extensions.ContinuousComponentModel as ccmext
import crosscat.tests.component_model_extensions.MultinomialComponentModel as mcmext

import random
import numpy
import math

# default parameters for 'seeding' random categories
default_data_parameters = dict(
    multinomial=dict(weights=[1.0/5.0]*5),
    continuous=dict(mu=0.0, rho=1.0)
    )

get_data_generator = dict(
	multinomial=mcmext.p_MultinomialComponentModel.generate_data_from_parameters,
	continuous=ccmext.p_ContinuousComponentModel.generate_data_from_parameters
	)

NaN = float('nan')

has_key = lambda dictionary, key : key in dictionary.keys()

def p_draw(M):
	r = random.random()
	for i in range(len(M)):
		if r < M[i]:
			return i

def add_missing_data_to_column(X, col, proportion):
	"""	Adds NaN entried to propotion of the data X in column col
	"""
	assert proportion >= 0 and proportion <= 1

	for row in range(X.shape[0]):
		if random.random() < proportion:
			X[row,col] = NaN

	return X

def generate_separated_multinomial_weights(A,C):
	"""Generates a set of multinomial weights B, where sum(abs(B-A)) = C
		Inputs:
			A: a list of multinomial weights
			C: A float, 0 <= C <= 1
	"""

	if not isinstance(A, list):
		raise TypeError("A should be a list")

	if not math.fabs(1-sum(A)) < .0000001:
		raise ValueError("A must sum to 1.")

	if C > 1.0 or C < 0:
		raise ValueError("0 <= C <= 1")

	if C == 0.0:
		return A

	idx = [i[0] for i in sorted(enumerate(A), key=lambda x:x[1])]
	A_sum = [A[i] for i in idx]

	A = numpy.array(A)

	A_sum = numpy.cumsum(numpy.array(A_sum))
	
	B = numpy.copy(A)

	t = numpy.nonzero(A_sum >= .5)[0][0]; 

	err_up = idx[:t]
	err_dn = idx[t:]

	upper_bounds = 1.0-B;
	upper_bounds[err_dn] = 0

	lower_bounds = numpy.copy(B);
	lower_bounds[err_up] = 0

	for _ in range(int(C*10.0)):
		# increase a weight
		ups = numpy.nonzero(upper_bounds >= .05)[0]
		move_up = ups[random.randrange(len(ups))]
		B[move_up] += .05
		upper_bounds[move_up] -= .05

		# decrease a weight
		dns = numpy.nonzero(lower_bounds >= .05)[0]
		# if there is no weight to decrease
		if len(dns) == 0:
			# send the lowest weight to zero, normalize and return
			maxdex = lower_bounds.index(min(lower_bounds))
			B[maxdex] = 0
			B /= numpy.sum(B)
			print('Broke')
			break

		move_down = dns[random.randrange(len(dns))]
		B[move_down] -= .05
		lower_bounds[move_down] -= .05
	
	assert math.fabs(1-numpy.sum(B)) < .0000001
	return B.tolist()

def generate_separated_model_parameters(cctype, C, num_clusters, get_next_seed, distargs=None):
	""" Generates a list of separated component model parameters
	"""
	if cctype == 'continuous':
		# C=1 implies 3 sigma, C=0, implies total overlap, C=.5 implies 1 sigma
		A = 1.7071
		B = .7929
	    # outputs distance in standard deviations that the two clusters should be apart
		d_in_simga = lambda c : A*(c**1.5) + B*c
		rho_to_sigma = lambda rho : (1.0/rho)**.5
		
		# generate the 'seed' component model randomly
		N = 100 # imaginary data
		model = ccmext.p_ContinuousComponentModel.from_parameters(N, gen_seed=get_next_seed())
		params = model.sample_parameters_given_hyper(gen_seed=get_next_seed())
		# track the means and standard deviations

		model_params = [params]
		
		for i in range(0,num_clusters-1):
			params = model.sample_parameters_given_hyper(gen_seed=get_next_seed())
			last_mean = model_params[i]['mu']
			std1 = rho_to_sigma(model_params[i]['rho'])
			std2 = rho_to_sigma(params['rho'])
			sumstd = std1+std2
			push = d_in_simga(C)*sumstd
			params['mu'] = model_params[i]['mu'] + push
			model_params.append(params)

		assert len(model_params) == num_clusters
		random.shuffle(model_params)
		assert len(model_params) == num_clusters
		return model_params

	elif cctype == 'multinomial':
		
		# check the distargs dict	
		if not isinstance(distargs, dict):
			raise TypeError("for cctype 'multinomial' distargs must be a dict")

		try:
			K = distargs['K']
		except KeyError:
			raise KeyError("for cctype 'multinomial' distargs should have key 'K',\
			 the number of categories")

		# generate an inital set of parameters
		# weights = numpy.random.rand(K)
		# weights = weights/numpy.sum(weights)
		weights = numpy.array([1.0/float(K)]*K)
		weights = weights.tolist()

		model_params = [dict(weights=weights)]
		
		for i in range(0,num_clusters-1):
			weights = generate_separated_multinomial_weights(weights,C)
			model_params.append(dict(weights=weights))

		assert len(model_params) == num_clusters
		random.shuffle(model_params)
		assert len(model_params) == num_clusters
		return model_params
	else:
		raise ValueError("Invalid cctype %s." % cctype )


def gen_data(cctypes, n_rows, cols_to_views, cluster_weights, separation, seed=0, distargs=None, return_structure=False):
	"""	Generates a synthetic data.
		Inputs:
			- cctypes: List of strings. Each entry, i, is the cctype of the 
			column i. ex: cctypes = ['continuous','continuous', 'multinomial']
			- n_rows: integer. the number of rows
			- cols_to_views: List of integers. Each entry, i, is the view, v, 
			to which columns i is assigned. v \in [0,...,n_cols-1].
			ex: cols_to_views = [0, 0, 1]
			- cluster_weights: List of lists of floats. A num_views length list
			of list. Each sublist, W, is a list of cluster weights for the 
			view, thus W should always sum to 1.
			ex (two views, first view has 2 clusters, second view has 3 
			clusters):
			cluster_weights = [[.3, .7], [.25, .5, .25]]
			- separation: list of floats. Each entry, i, is the separation, C,
			of the clusters in view i. C \in [0,1] where 0 is no separation and
			1 is well-separated.
			ex (2 views): separation = [ .5, .7]
			- seed: optional
			- distargs: optional (only if continuous). distargs is n_columns
			length list where each entry is either None or a dict appropriate 
			for the cctype in that column. For a normal feature, the entry 
			should be None, for a multinomial feature, the entry should be a 
			dict with the entry K (the number of categories). 
			- return_structure: (bool, optional). Returns also a dict withe the
			data generation structure included. A dict with keys:
				- component_params:  a n_cols length list of lists. Where each 
				list is a set of component model parameters for each cluster in
				the view to which that column belongs
				- cols_to_views: a list assigning each column to a view
				- rows_to_clusters: a n_views length list of list. Each entry,
				rows_to_clusters[v][r] is the cluster to which all rows in 
				columns belonging to view v are assigned
		Returns:
			T, M_c
		Example:
			>>> cctypes = ['continuous','continuous','multinomial','continuous','multinomial']
			>>> disargs = [None, None, dict(K=5), None, dict(K=2)]
			>>> n_rows = 10
			>>> cols_to_views = [0, 0, 1, 1, 2]
			>>> cluster_weights = [[.3, .7],[.5, .5],[.2, .3, .5]]
			>>> separation = [.9, .6, .9]
			>>> T, M_c = gen_data(cctypes, n_rows, cols_to_views, cluster_weights,
				separation, seed=0, distargs=distargs)
	"""

	# check Inputs
	if not isinstance(n_rows, int):
		raise TypeError("n_rows should be an integer")

	if not isinstance(cctypes, list):
		raise TypeError("cctypes should be a list")

	n_cols_cctypes = len(cctypes)
	for cctype in cctypes:
		if not isinstance(cctype, str):
			raise TypeError("cctypes should be a list of strings")

		# NOTE: will have to update when new component models are added
		if cctype not in ['continuous', 'multinomial']:
			raise ValueError("invalid cctypein cctypes: %s." % cctype)

	if not isinstance(cols_to_views, list):
		raise TypeError("cols_to_views should be a list")

	if len(cols_to_views) != n_cols_cctypes:
		raise ValueError("number of columns in cctypes does not match number\
		 of columns in cols_to_views")

	if min(cols_to_views) != 0:
		raise ValueError("min value of cols_to_views should be 0")

	n_views_cols_to_views = max(cols_to_views) + 1

	set_ctv = set(cols_to_views)
	if len(set_ctv) != n_views_cols_to_views:
		raise ValueError("View indices skipped in cols_to_views")

	# check cluster weights
	if not isinstance(cluster_weights, list):
		raise TypeError("cluster_weights should be a list")

	if n_views_cols_to_views != len(cluster_weights):
		raise ValueError("The number of views in cols_to_views and \
			cluster_weights do not agree.")

	# check each set of weights
	for W in cluster_weights:
		if not isinstance(W, list):
			raise TypeError("cluster_weights should be a list of lists")
		if math.fabs(sum(W)-1.0) > .0000001:
			raise ValueError("each vector of weights should sum to 1")

	if not isinstance(separation, list):
		raise TypeError("separation should be a list")

	if len(separation) != n_views_cols_to_views:
		raise ValueError("number of view in separation and cols_to_views do not agree")

	for c in separation:
		if not isinstance(c, float) or c > 1.0 or c < 0.0:
			raise ValueError("each value in separation should be a float from 0 to 1")

	num_views = len(separation)
	n_cols = len(cols_to_views)

	# check the cctypes vs the distargs
	if distargs is None:
		distargs = [None for i in range(n_cols)]

	if not isinstance(distargs, list):
		raise TypeError("distargs should be a list")

	if len(distargs) != n_cols:
		raise ValueError("distargs should have an entry for each column")

	for i in range(n_cols):
		if cctypes[i] == 'continuous':
			if distargs[i] is not None:
				raise ValueError("distargs entry for 'continuous' cctype should be None")
		elif cctypes[i] == 'multinomial':
			if not isinstance(distargs[i], dict):
				raise TypeError("ditargs for cctype 'multinomial' should be a dict")
			if len(distargs[i].keys()) != 1:
				raise KeyError("distargs for cctype 'multinomial' should have one key, 'K'")
			if 'K' not in distargs[i].keys():
				raise KeyError("distargs for cctype 'multinomial' should have the key 'K'")
		else:
			raise ValueError("invalid cctypein cctypes: %s." % cctypes[i])

	random.seed(seed)
	numpy.random.seed(seed)

	# Generate the rows to categories partitions (mutlinomial)
	rows_to_clusters = []
	for W in cluster_weights:

		cW = list(W)
		for i in range(1, len(cW)):
			cW[i] += cW[i-1]

		K = len(cW)

		rows_to_clusters_view = range(K)
		for r in range(K,n_rows):
			rows_to_clusters_view.append(p_draw(cW))

		random.shuffle(rows_to_clusters_view)
		assert len(rows_to_clusters_view) == n_rows

		rows_to_clusters.append(rows_to_clusters_view)


	get_next_seed = lambda : random.randrange(2147483647)

	# start generating the data
	data_table = numpy.zeros((n_rows, n_cols))
	component_params = []
	for col in range(n_cols):
	
		view = cols_to_views[col]

		# get the number of cluster in view
		num_clusters = len(cluster_weights[view])

		cctype = cctypes[col]

		C = separation[view]

		# generate a set of C-separated component model parameters 
		component_parameters = generate_separated_model_parameters(cctype, C,
			num_clusters, get_next_seed, distargs=distargs[col])

		component_params.append(component_parameters)

		# get the data generation function
		gen = get_data_generator[cctype]
		for row in range(n_rows):
			# get the cluster this 
			cluster = rows_to_clusters[view][row]
			params = component_parameters[cluster]
			x = gen(params, 1, gen_seed=get_next_seed())[0]
			data_table[row,col] = x


	T = data_table.tolist()
	M_c = du.gen_M_c_from_T(T, cctypes=cctypes)

	if return_structure:
		structure = dict()
		structure['component_params'] = component_params
		structure['cols_to_views'] = cols_to_views
		structure['rows_to_clusters'] = rows_to_clusters
		structure['cluster_weights'] = cluster_weights
		return T, M_c, structure
	else:
		return T, M_c

def predictive_columns(M_c, X_L, X_D, columns_list, optional_settings=False, seed=0):
	""" Generates rows of data from the inferred distributions
	Inputs:
		- M_c: crosscat metadata (See documentation)
		- X_L: crosscat metadata (See documentation)
		- X_D: crosscat metadata (See documentation)
		- columns_list: a list of columns to sample
		- optinal_settings: list of dicts of optional arguments. Each column
		  in columns_list should have its own list entry which is either None
		  or a dict with possible keys:
			- missing_data: Proportion missing data
	Returns:
		- a num_rows by len(columns_list) numpy array, where n_rows is the
		original number of rows in the crosscat table. 
	"""
	# supported arguments for optional_settings
	supported_arguments = ['missing_data']

	num_rows = len(X_D[0])
	num_cols = len(M_c['column_metadata'])

	if not isinstance(columns_list, list):
		raise TypeError("columns_list should be a list")

	for col in columns_list:
		if not isinstance(col, int):
			raise TypeError("every entry in columns_list shuold be an integer")
		if col < 0 or col >= num_cols:
			raise ValueError("%i is not a valid column. Should be valid entries\
			 are 0-%i" % (col, num_cols))

	if not isinstance(seed, int):
		raise TypeError("seed should be an int")

	if seed < 0:
		raise ValueError("seed should be positive")

	if optional_settings:
		if not isinstance(optional_settings, list):
			raise TypeError("optional_settings should be a list")

		for col_setting in optional_settings:
			if isinstance(col_setting, dict):
				for key, value in col_setting.iteritems():
					if key not in supported_arguments:
						raise KeyError("Invalid key in optional_settings, '%s'" % key)
	else:
		optional_settings = [None]*len(columns_list)

	random.seed(seed)

	X = numpy.zeros((num_rows, len(columns_list)))

	get_next_seed = lambda : random.randrange(2147483647)

	for c in range(len(columns_list)):
		col = columns_list[c]
		for row in range(num_rows):
			X[row,c] = su.simple_predictive_sample(M_c, X_L, X_D, [],
						 [(row,col)], get_next_seed, n=1)[0][0]

		# check if there are optional arguments
		if isinstance(optional_settings[c], dict):
			# missing data argument
			if has_key(optional_settings[c], 'missing_data'):
				proportion = optional_settings[c]['missing_data']
				X = add_missing_data_to_column(X, c, proportion)

	assert X.shape[0] == num_rows
	assert X.shape[1] == len(columns_list)

	return X






########NEW FILE########
__FILENAME__ = test_component_model_quality
import crosscat.cython_code.State as State
import crosscat.utils.sample_utils as su
import crosscat.utils.data_utils as du

import crosscat.tests.component_model_extensions.ContinuousComponentModel as ccmext
import crosscat.tests.component_model_extensions.MultinomialComponentModel as mcmext

import random
import pylab
import numpy

import unittest

from scipy import stats

default_data_parameters = dict(
    symmetric_dirichlet_discrete=dict(weights=[1.0/5.0]*5),
    normal_inverse_gamma=dict(mu=0.0, rho=1.0)
    )

is_discrete = dict(
    symmetric_dirichlet_discrete=True,
    normal_inverse_gamma=False
    )


def main():
    unittest.main()

class TestComponentModelQuality(unittest.TestCase):
    def setUp(self):
        self.show_plot = False

    def test_normal_inverse_gamma_model(self):
        assert(test_one_feature_sampler(ccmext.p_ContinuousComponentModel, 
            show_plot=self.show_plot) > .1)

    def test_dirchlet_multinomial_model(self):
        assert(test_one_feature_sampler(mcmext.p_MultinomialComponentModel, 
            show_plot=self.show_plot) > .1)


def get_params_string(params):
    string = dict()
    for k,v in params.iteritems():
        if isinstance(v, float):
            string[k] = round(v,3)
        elif isinstance(v, list):
            string[k] = [round(val,3) for val in v]

    return str(string)

def cdf_array(X, component_model):
    cdf = numpy.zeros(len(X))
    for i in range(len(X)):
        x = X[i]
        cdf[i] = component_model.get_predictive_cdf(x,[])

    assert i == len(X)-1
    assert i > 0
    return cdf

def test_one_feature_sampler(component_model_type, show_plot=False):
    """
    Tests the ability of component model of component_model_type to capture the
    distribution of the data.
    1. Draws 100 random points from a standard normal distribution
    2. Initializes a component model with that data (and random hyperparameters)
    3. Draws data from that component model
    4. Initialize a crosscat state with that data
    5. Get one sample after 100 transitions
    6. Draw predictive samples
    7. Caluclates the 95 precent support of the continuous distribution or the 
        entire support of the discrete distribution
    8. Calculate the true pdf for each point in the support
    9. Calculate the predictive probability given the sample for each point in
        the support
    10. (OPTIONAL) Plot the original data, predictive samples, pdf, and 
        predictive probabilities 
    11. Calculate goodness of fit stats (returns p value)
    """
    N = 100
    
    get_next_seed = lambda : random.randrange(2147483647)

    data_params = default_data_parameters[component_model_type.model_type]
    
    X = component_model_type.generate_data_from_parameters(data_params, N, gen_seed=get_next_seed())
    
    hyperparameters = component_model_type.draw_hyperparameters(X)[0]
    
    component_model = component_model_type.from_data(X, hyperparameters)
    
    model_parameters = component_model.sample_parameters_given_hyper()
    
    # generate data from the parameters
    T = component_model_type.generate_data_from_parameters(model_parameters, N, gen_seed=get_next_seed())

    # create a crosscat state 
    M_c = du.gen_M_c_from_T(T, cctypes=[component_model_type.cctype])
    
    state = State.p_State(M_c, T)
    
    # transitions
    n_transitions = 100
    state.transition(n_steps=n_transitions)
    
    # get the sample
    X_L = state.get_X_L()
    X_D = state.get_X_D()
    
    # generate samples
    # kstest has doesn't compute the same answer with row and column vectors
    # so we flatten this column vector into a row vector.
    predictive_samples = numpy.array(su.simple_predictive_sample(M_c, X_L, X_D, [], [(N,0)], get_next_seed, n=N)).flatten(1)
    
    # get support
    discrete_support = component_model_type.generate_discrete_support(model_parameters)

    # calculate simple predictive probability for each point
    Q = [(N,0,x) for x in discrete_support]

    probabilities = su.simple_predictive_probability(M_c, X_L, X_D, []*len(Q), Q,)
    
    T = numpy.array(T)

    # get histogram. Different behavior for discrete and continuous types. For some reason
    # the normed property isn't normalizing the multinomial histogram to 1.
    if is_discrete[component_model_type.model_type]:
        T_hist, edges = numpy.histogram(T, bins=len(discrete_support))
        S_hist, _ =  numpy.histogram(predictive_samples, bins=edges)
        T_hist = T_hist/float(numpy.sum(T_hist))
        S_hist = S_hist/float(numpy.sum(S_hist))
        edges = numpy.array(discrete_support,dtype=float)
    else:
        T_hist, edges = numpy.histogram(T, bins=min(20,len(discrete_support)), normed=True)
        S_hist, _ =  numpy.histogram(predictive_samples, bins=edges, normed=True)
        edges = edges[0:-1]

    # Goodness-of-fit-tests
    if not is_discrete[component_model_type.model_type]:
        # do a KS tests if the distribution in continuous
        cdf = lambda x: component_model_type.cdf(x, model_parameters)
        # stat, p = stats.kstest(predictive_samples, cdf)   # 1-sample test
        stat, p = stats.ks_2samp(predictive_samples, T[:,0]) # 2-sample test
        test_str = "KS"
    else:
        # Cressie-Read power divergence statistic and goodness of fit test.
        # This function gives a lot of flexibility in the method <lambda_> used.
        freq_obs = S_hist*N
        freq_exp = numpy.exp(probabilities)*N
        stat, p = stats.power_divergence(freq_obs, freq_exp, lambda_='pearson')
        test_str = "Chi-square"
    
    if show_plot:
        pylab.axes([0.1, 0.1, .8, .7])
        # bin widths
        width = (numpy.max(edges)-numpy.min(edges))/len(edges)
        pylab.bar(edges, T_hist, color='blue', alpha=.5, width=width, label='Original data')
        pylab.bar(edges, S_hist, color='red', alpha=.5, width=width, label='Predictive samples')

        # plot actual pdf of support given data params
        pylab.scatter(discrete_support, 
            numpy.exp(component_model_type.log_pdf(numpy.array(discrete_support), 
            model_parameters)), 
            c="blue", 
            s=100, 
            label="true pdf", 
            alpha=1)
                
        # plot predictive probability of support points
        pylab.scatter(discrete_support, 
            numpy.exp(probabilities), 
            c="red", 
            s=100, 
            label="predictive probability", 
            alpha=1)
            
        pylab.legend()

        ylimits = pylab.gca().get_ylim()
        pylab.ylim([0,ylimits[1]])

        title_string = "%i samples drawn from %s w/ params: \n%s\ninference after %i crosscat transitions\n%s test: p = %f" \
            % (N, component_model_type.cctype, str(get_params_string(model_parameters)), n_transitions, test_str, round(p,4))

        pylab.title(title_string, fontsize=12)

        pylab.show()

    return p

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_impute_quality
import crosscat.cython_code.State as State
import crosscat.utils.sample_utils as su
import crosscat.utils.data_utils as du

import crosscat.tests.component_model_extensions.ContinuousComponentModel as ccmext
import crosscat.tests.component_model_extensions.MultinomialComponentModel as mcmext
import crosscat.tests.quality_tests.synthetic_data_generator as sdg

import crosscat.tests.quality_tests.quality_test_utils as qtu

import random
import pylab
import numpy
from scipy import stats

import unittest

distargs = dict(
	multinomial=dict(K=5),
	continuous=None,
	)

def main():
    unittest.main()

class TestComponentModelQuality(unittest.TestCase):
    def test_normal_inverse_gamma_model(self):
    	mse_sample, mse_ave = test_impute_vs_column_average_single(
    							ccmext.p_ContinuousComponentModel, 2)
        assert mse_sample < mse_ave

def test_impute_vs_column_average_single(component_model_type, num_clusters, seed=0):
	"""	tests predictive row generation vs column average
		Note: This test does not make sense for categorical data
		Inputs:
			- component_model_type: main class from datatype. Ex:
				ccmext.p_ContinuousComponentModel 
			- num_clusters: the number of clusters in the data
			- seed: (optional) int to seed the RNG 
		Returns:
			- the mean square error of the predictive sample column
			- the mean square error of the column average column
	"""

	random.seed(seed)

	N = 100

	get_next_seed = lambda : random.randrange(2147483647)

	C = .9 # highly-separated clusters

	cctype = component_model_type.cctype

	component_model_parameters = sdg.generate_separated_model_parameters(
						cctype, C, num_clusters, get_next_seed,
						distargs=distargs[cctype])

	# generte a partition of rows to clusters (evenly-weighted)
	Z = range(num_clusters)
	for z in range(N-num_clusters):
		Z.append(random.randrange(num_clusters))

	random.shuffle(Z)

	# generate the data
	T = numpy.array([[0]]*N, dtype=float)

	for x in range(N):
		z = Z[x]
		T[x] = component_model_type.generate_data_from_parameters(
				component_model_parameters[z], 1, gen_seed=get_next_seed())[0]

	T_list = T.tolist()

	# intialize the state
	M_c = du.gen_M_c_from_T(T_list, cctypes=[cctype])

	state = State.p_State(M_c, T)

	# transitions
	state.transition(n_steps=100)

	# get the sample
	X_L = state.get_X_L()
	X_D = state.get_X_D()

	# generate a row from the sample
	T_generated = sdg.predictive_columns(M_c, X_L, X_D, [0], seed=get_next_seed())

	# generate a row of column averages
	T_colave = numpy.ones(T.shape)*numpy.mean(T)

	# get the mean squared error
	err_sample = numpy.mean( (T_generated-T)**2.0 )
	err_colave = numpy.mean( (T_colave-T)**2.0 )

	return err_sample, err_colave

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = test_kl_divergence_quality
import crosscat.tests.quality_tests.quality_test_utils as qtu

import pylab
import numpy

from scipy.stats import norm 
from scipy.stats import pearsonr 

import unittest

class TestKLDivergence(unittest.TestCase):
	def test_kl_divergence_estimate_correlates_higly_to_analytical(self):
		assert test_KL_divergence_for_normal_distributions(show_plot=True) < .000001


def main():
	unittest.main()

def actual_KL(m1,s1,m2,s2):
	return numpy.log(s2/s1) + (s1**2.0+(m1-m2)**2.0)/(2*s2**2.0) - .5

def test_KL_divergence_for_normal_distributions(show_plot=True):

	mu_0 = 0
	sigma_0 = 1

	interval = norm.interval(.99,mu_0,sigma_0)

	support = numpy.linspace(interval[0], interval[1], num=2000)

	mus = numpy.linspace(0, 3, num=30)

	p_0 = norm.logpdf(support, mu_0, sigma_0)

	KL_inf = []
	KL_ana = []

	for mu in mus:
		p_1 = norm.logpdf(support, mu, sigma_0)

		kld = qtu.KL_divergence_arrays(support, p_0, p_1, False)

		KL_inf.append(float(kld))
		KL_ana.append(actual_KL(mu_0, sigma_0, mu, sigma_0))


	KL_inf = numpy.array(KL_inf)
	KL_ana = numpy.array(KL_ana)
	KL_diff = KL_ana-KL_inf


	if show_plot:
		pylab.subplot(1,2,1)
		pylab.plot(KL_inf, label='est')
		pylab.plot(KL_ana, label='analytical')
		pylab.title('estimated KL')
		pylab.legend()

		pylab.subplot(1,2,2)
		pylab.plot(KL_diff)
		pylab.title('KL error')

		pylab.show()


	_, p = pearsonr(KL_inf, KL_ana)

	return p


if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = test_mixture_inference_quality
import crosscat.cython_code.State as State
import crosscat.utils.sample_utils as su
import crosscat.utils.data_utils as du

import crosscat.tests.component_model_extensions.ContinuousComponentModel as ccmext
import crosscat.tests.component_model_extensions.MultinomialComponentModel as mcmext
import crosscat.tests.quality_tests.synthetic_data_generator as sdg
import crosscat.tests.quality_tests.quality_test_utils as qtu

import random
import pylab
import numpy

import unittest

from scipy import stats

distargs = dict(
    multinomial=dict(K=5),
    continuous=None,
    )

default_data_parameters = dict(
    symmetric_dirichlet_discrete=dict(weights=[1.0/5.0]*5),
    normal_inverse_gamma=dict(mu=0.0, rho=1.0)
    )

is_discrete = dict(
    symmetric_dirichlet_discrete=True,
    normal_inverse_gamma=False
    )


def main():
    unittest.main()

class TestComponentModelQuality(unittest.TestCase):
    def setUp(self):
        self.show_plot = True

    def test_normal_inverse_gamma_model(self):
        assert(test_one_feature_mixture(ccmext.p_ContinuousComponentModel, 
                show_plot=self.show_plot) > .1)

    def test_dirchlet_multinomial_model(self):
        assert(test_one_feature_mixture(mcmext.p_MultinomialComponentModel, 
                show_plot=self.show_plot) > .1)


def get_params_string(params):
    string = dict()
    for k,v in params.iteritems():
        if isinstance(v, float):
            string[k] = round(v,3)
        elif isinstance(v, list):
            string[k] = [round(val,3) for val in v]

    return str(string)

def cdf_array(X, component_model):
    cdf = numpy.zeros(len(X))
    for i in range(len(X)):
        x = X[i]
        cdf[i] = component_model.get_predictive_cdf(x,[])

    assert i == len(X)-1
    assert i > 0
    return cdf

def test_one_feature_mixture(component_model_type, num_clusters=3, show_plot=False, seed=None):
    """

    """
    random.seed(seed)

    N = 1000
    separation = .9
    
    get_next_seed = lambda : random.randrange(2147483647)

    cluster_weights = [[1.0/float(num_clusters)]*num_clusters]

    cctype = component_model_type.cctype
    T, M_c, structure = sdg.gen_data([cctype], N, [0], cluster_weights,
                        [separation], seed=get_next_seed(),
                        distargs=[distargs[cctype]],
                        return_structure=True)

    T = numpy.array(T)
    T_list = T
    
    # create a crosscat state 
    M_c = du.gen_M_c_from_T(T_list, cctypes=[cctype])
    
    state = State.p_State(M_c, T_list)
    
    # transitions
    state.transition(n_steps=200)
    
    # get the sample
    X_L = state.get_X_L()
    X_D = state.get_X_D()
    
    # generate samples
    # kstest has doesn't compute the same answer with row and column vectors
    # so we flatten this column vector into a row vector.
    predictive_samples = sdg.predictive_columns(M_c, X_L, X_D, [0],
                            seed=get_next_seed()).flatten(1)
    
    # Get support over all component models
    discrete_support = qtu.get_mixture_support(cctype, component_model_type,
                         structure['component_params'][0], nbins=500)

    # calculate simple predictive probability for each point
    Q = [(N,0,x) for x in discrete_support]

    probabilities = su.simple_predictive_probability(M_c, X_L, X_D, []*len(Q), Q)
    
    # get histogram. Different behavior for discrete and continuous types. For some reason
    # the normed property isn't normalizing the multinomial histogram to 1.
    if is_discrete[component_model_type.model_type]:
        bins = range(len(discrete_support))
        T_hist = numpy.array(qtu.bincount(T, bins=bins))
        S_hist = numpy.array(qtu.bincount(predictive_samples, bins=bins))
        T_hist = T_hist/float(numpy.sum(T_hist))
        S_hist = S_hist/float(numpy.sum(S_hist))
        edges = numpy.array(discrete_support,dtype=float)
    else:
        T_hist, edges = numpy.histogram(T, bins=min(20,len(discrete_support)), normed=True)
        S_hist, _ =  numpy.histogram(predictive_samples, bins=edges, normed=True)
        edges = edges[0:-1]

    # Goodness-of-fit-tests
    if not is_discrete[component_model_type.model_type]:
        # do a KS tests if the distribution in continuous
        # cdf = lambda x: component_model_type.cdf(x, model_parameters)
        # stat, p = stats.kstest(predictive_samples, cdf)   # 1-sample test
        stat, p = stats.ks_2samp(predictive_samples, T[:,0]) # 2-sample test
        test_str = "KS"
    else:
        # Cressie-Read power divergence statistic and goodness of fit test.
        # This function gives a lot of flexibility in the method <lambda_> used.
        freq_obs = S_hist*N
        freq_exp = numpy.exp(probabilities)*N
        stat, p = stats.power_divergence(freq_obs, freq_exp, lambda_='pearson')
        test_str = "Chi-square"
    
    if show_plot:
        lpdf = qtu.get_mixture_pdf(discrete_support, component_model_type, 
                structure['component_params'][0], [1.0/num_clusters]*num_clusters)
        pylab.axes([0.1, 0.1, .8, .7])
        # bin widths
        width = (numpy.max(edges)-numpy.min(edges))/len(edges)
        pylab.bar(edges, T_hist, color='blue', alpha=.5, width=width, label='Original data', zorder=1)
        pylab.bar(edges, S_hist, color='red', alpha=.5, width=width, label='Predictive samples', zorder=2)

        # plot actual pdf of support given data params
        pylab.scatter(discrete_support, 
            numpy.exp(lpdf), 
            c="blue", 
            edgecolor="none",
            s=100, 
            label="true pdf", 
            alpha=1,
            zorder=3)
                
        # plot predictive probability of support points
        pylab.scatter(discrete_support, 
            numpy.exp(probabilities), 
            c="red", 
            edgecolor="none",
            s=100, 
            label="predictive probability", 
            alpha=1,
            zorder=4)
            
        pylab.legend()

        ylimits = pylab.gca().get_ylim()
        pylab.ylim([0,ylimits[1]])

        title_string = "%i samples drawn from %i %s components: \ninference after 200 crosscat transitions\n%s test: p = %f" \
            % (N, num_clusters, component_model_type.cctype, test_str, round(p,4))

        pylab.title(title_string, fontsize=12)

        pylab.show()

    return p

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_predictive_confidence
import crosscat.cython_code.State as State
import crosscat.utils.sample_utils as su
import crosscat.utils.data_utils as du

import crosscat.tests.component_model_extensions.ContinuousComponentModel as ccmext
import crosscat.tests.component_model_extensions.MultinomialComponentModel as mcmext
import crosscat.tests.quality_tests.synthetic_data_generator as sdg

import crosscat.tests.quality_tests.quality_test_utils as qtu

import random
import pylab
import numpy

from scipy import stats

import unittest

distargs = dict(
	multinomial=dict(K=8),
	continuous=None,
	)

def main():
    unittest.main()

class TestCondifdence(unittest.TestCase):
	def setUp(self):
		self.show_plot=True

	def test_normal_inverse_gamma_predictive_sample_improves_over_iterations(self):
		improvement = test_predictive_sample_improvement(
						ccmext.p_ContinuousComponentModel, 
						seed=0, show_plot=self.show_plot)
		assert improvement

	def test_dirchlet_multinomial_predictive_sample_improves_over_iterations(self):
		improvement = test_predictive_sample_improvement(
			mcmext.p_MultinomialComponentModel, seed=0, show_plot=self.show_plot)
		assert improvement

def test_predictive_sample_improvement(component_model_type, seed=0, show_plot=True):
	""" Shows the error of predictive sample over iterations.
	"""

	num_transitions = 100
	num_samples = 10	
	num_clusters = 2
	separation = .9	# cluster separation
	N = 150
	
	random.seed(seed)
	get_next_seed = lambda : random.randrange(2147483647)

	# generate a single column of data from the component_model 
	cctype = component_model_type.cctype
	T, M_c, struc = sdg.gen_data([cctype], N, [0], [[.5,.5]], [separation], 
				seed=get_next_seed(), distargs=[distargs[cctype]], 
				return_structure=True)

	T_array = numpy.array(T)

	X = numpy.zeros((N,num_transitions))
	KL = numpy.zeros((num_samples, num_transitions))


	support = qtu.get_mixture_support(cctype, component_model_type, 
					struc['component_params'][0], nbins=1000, support=.995)
	true_log_pdf = qtu.get_mixture_pdf(support, component_model_type, 
					struc['component_params'][0],[.5,.5])

	for s in range(num_samples):
		# generate the state
		state = State.p_State(M_c, T, SEED=get_next_seed())

		for i in range(num_transitions):
			# transition
			state.transition()

			# get partitions and generate a predictive column
			X_L = state.get_X_L()
			X_D = state.get_X_D()

			T_inf = sdg.predictive_columns(M_c, X_L, X_D, [0], 
					seed=get_next_seed())

			if cctype == 'multinomial':
				K = distargs[cctype]['K']
				weights = numpy.zeros(numpy.array(K))
				for params in struc['component_params'][0]:
					weights += numpy.array(params['weights'])*(1.0/num_clusters)
				weights *= float(N)
				inf_hist = qtu.bincount(T_inf, bins=range(K))
				err, _ = stats.power_divergence(inf_hist, weights, lambda_='pearson')
				err = numpy.ones(N)*err
			else:
				err = (T_array-T_inf)**2.0

			KL[s,i] = qtu.KL_divergence(component_model_type, 
						struc['component_params'][0], [.5,.5], M_c, X_L, X_D,
						true_log_pdf=true_log_pdf, support=support)

			for j in range(N):
				X[j,i] += err[j]

	X /= num_samples

	# mean and standard error
	X_mean = numpy.mean(X,axis=0)
	X_err = numpy.std(X,axis=0)/float(num_samples)**.5

	KL_mean = numpy.mean(KL, axis=0)
	KL_err = numpy.std(KL, axis=0)/float(num_samples)**.5

	if show_plot:
		pylab.subplot(1,2,1)
		pylab.errorbar(range(num_transitions), X_mean, yerr=X_err)
		pylab.xlabel('iteration')
		pylab.ylabel('error across each data point')
		pylab.title('error of predictive sample over iterations, N=%i' % N)

		pylab.subplot(1,2,2)
		pylab.errorbar(range(num_transitions), KL_mean, yerr=KL_err)
		pylab.xlabel('iteration')
		pylab.ylabel('KL divergence')
		pylab.title('KL divergence, N=%i' % N)

		pylab.show()

	# error should decrease over time
	return X_mean[0] > X_mean[-1] and KL_mean[0] > KL_mean[-1]

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = test_log_likelihood
import random
import argparse
from functools import partial
#
import numpy
import pylab
#
from crosscat.LocalEngine import LocalEngine
import crosscat.utils.data_utils as du
import crosscat.utils.plot_utils as pu
import crosscat.utils.geweke_utils as gu
import crosscat.utils.convergence_test_utils as ctu
import experiment_runner.experiment_utils as eu


directory_prefix='test_log_likelihood'
#
noneify = set(['n_test'])
base_config = dict(
    gen_seed=0,
    num_rows=100, num_cols=4,
    num_clusters=5, num_views=1,
    n_steps=10, n_test=10,
    )

def runner(config):
    # helpers
    def munge_config(config):
        kwargs = config.copy()
        kwargs['num_splits'] = kwargs.pop('num_views')
        n_steps = kwargs.pop('n_steps')
        n_test = kwargs.pop('n_test')
        return kwargs, n_steps, n_test
    def calc_ll(T, p_State):
        log_likelihoods = map(p_State.calc_row_predictive_logp, T)
        mean_log_likelihood = numpy.mean(log_likelihoods)
        return mean_log_likelihood
    def gen_data(**kwargs):
        T, M_c, M_r, gen_X_L, gen_X_D = du.generate_clean_state(**kwargs)
        #
        engine = LocalEngine()
        sampled_T = gu.sample_T(engine, M_c, T, gen_X_L, gen_X_D)
        T_test = random.sample(sampled_T, n_test)
        gen_data_ll = ctu.calc_mean_test_log_likelihood(M_c, T, gen_X_L, gen_X_D, T)
        gen_test_set_ll = ctu.calc_mean_test_log_likelihood(M_c, T, gen_X_L, gen_X_D, T_test)
        #
        return T, M_c, M_r, T_test, gen_data_ll, gen_test_set_ll
    kwargs, n_steps, n_test = munge_config(config)
    T, M_c, M_r, T_test, gen_data_ll, gen_test_set_ll = gen_data(**kwargs)
    # set up to run inference
    calc_data_ll = partial(calc_ll, T)
    calc_test_set_ll = partial(calc_ll, T_test)
    diagnostic_func_dict = dict(
            data_ll=calc_data_ll,
            test_set_ll=calc_test_set_ll,
            )
    # run inference
    engine = LocalEngine()
    X_L, X_D = engine.initialize(M_c, M_r, T)
    X_L, X_D, diagnostics_dict = engine.analyze(M_c, T, X_L, X_D,
            do_diagnostics=diagnostic_func_dict, n_steps=n_steps)
    # package result
    final_data_ll = diagnostics_dict['data_ll'][-1][-1]
    final_test_set_ll = diagnostics_dict['test_set_ll'][-1][-1]
    summary = dict(
            gen_data_ll=gen_data_ll,
            gen_test_set_ll=gen_test_set_ll,
            final_data_ll=final_data_ll,
            final_test_set_ll=final_test_set_ll,
            )

    result = dict(
            config=config,
            summary=summary,
            diagnostics_dict=diagnostics_dict,
            )
    return result

def plotter(result):
    pylab.figure()
    diagnostics_dict = result['diagnostics_dict']
    gen_data_ll = result['summary']['gen_data_ll']
    gen_test_set_ll = result['summary']['gen_test_set_ll']
    #
    pylab.plot(diagnostics_dict['data_ll'], 'g')
    pylab.plot(diagnostics_dict['test_set_ll'], 'r')
    pylab.axhline(gen_data_ll, color='g', linestyle='--')
    pylab.axhline(gen_test_set_ll, color='r', linestyle='--')
    return

def _generate_parser():
    default_gen_seed = [0]
    default_num_rows = [100, 200, 500]
    default_num_cols = [10, 20]
    default_num_clusters = [1, 10, 20]
    default_num_views = [1, 5]
    default_n_steps = [10]
    default_n_test = [20]
    parser = argparse.ArgumentParser()
    parser.add_argument('--gen_seed', nargs='+', default=default_gen_seed, type=int)
    parser.add_argument('--num_rows', nargs='+', default=default_num_rows, type=int)
    parser.add_argument('--num_cols', nargs='+', default=default_num_cols, type=int)
    parser.add_argument('--num_clusters', nargs='+',
            default=default_num_clusters, type=int)
    parser.add_argument('--num_views', nargs='+', default=default_num_views,
            type=int)
    parser.add_argument('--n_steps', nargs='+', default=default_n_steps, type=int)
    parser.add_argument('--n_test', nargs='+', default=default_n_test, type=int)
    #
    parser.add_argument('--no_plots', action='store_true')
    parser.add_argument('--dirname', default='test_log_likelihood', type=str)
    return parser

def _munge_args(args):
    kwargs = args.__dict__.copy()
    do_plots = not kwargs.pop('no_plots')
    dirname = kwargs.pop('dirname')
    return kwargs, do_plots, dirname

def summary_plotter(results, dirname='./', save=True):
    def _scatter(x, y):
        pylab.figure()
        pylab.scatter(x, y)
        pylab.gca().set_aspect(1)
        xlim = pylab.gca().get_xlim()
        pylab.plot(xlim, xlim)
        return
    def _plot(frame, variable_suffix, filename=None, dirname='./'):
        x = frame['gen_' + variable_suffix]
        y = frame['final_' + variable_suffix]
        _scatter(x, y)
        pylab.title(variable_suffix)
        if filename is not None:
            pu.save_current_figure(filename, dir=dirname, close=True)
            pass
        return
    frame = eu.summaries_to_frame(results)
    for variable_suffix in ['test_set_ll', 'data_ll']:
        filename = variable_suffix if save else None
        _plot(frame, variable_suffix, filename=filename, dirname=dirname)
        pass
    return


if __name__ == '__main__':
    from experiment_runner.ExperimentRunner import ExperimentRunner, propagate_to_s3

    # parse args
    parser = _generate_parser()
    args = parser.parse_args()
    kwargs, do_plots, dirname = _munge_args(args)


    # create configs
    config_list = eu.gen_configs(base_config, **kwargs)


    # do experiments
    er = ExperimentRunner(runner, storage_type='fs',
            dirname_prefix=dirname,
            bucket_str='experiment_runner',
            )
    er.do_experiments(config_list)
    propagate_to_s3(er)


    if do_plots:
        results = er.get_results(er.frame).values()
        summary_plotter(results, dirname=dirname)
#        eu.plot_results(plotter, results, generate_dirname,
#                saver=pu.save_current_figure, filename='over_iters',
#                dirname=dirname)

########NEW FILE########
__FILENAME__ = test_pred_prob_and_density
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import random
import argparse
import tempfile
import sys
from collections import Counter

import numpy
import pylab

import crosscat.utils.enumerate_utils as eu
import crosscat.utils.sample_utils as su
import crosscat.utils.plot_utils as pu
import crosscat.utils.data_utils as du

import crosscat.cython_code.State as State

def get_next_seed(max_val=32767):
    return random_state.randint(max_val)


def run_test(n=1000, d_type='continuous', observed=False):
    if d_type == 'continuous':
        run_test_continuous(n, observed)
    elif d_type == 'multinomial':
        run_test_multinomial(n, observed)

def generate_multinomial_data(next_seed,n_cols,n_rows,n_views):
    # generate the partitions
    random.seed(next_seed)
    
    cols_to_views = [0 for _ in range(n_cols)]
    rows_in_views_to_cols = []
    for view in range(n_views):
        partition = eu.CRP(n_rows,2.0)
        random.shuffle(partition)
        rows_in_views_to_cols.append(partition)

    # generate the data
    data = numpy.zeros((n_rows,n_cols),dtype=float)
    for col in range(n_cols):
        view = cols_to_views[col]
        for row in range(n_rows):
            cluster = rows_in_views_to_cols[view][row]
            data[row,col] = cluster

    T = data.tolist()
    M_r = du.gen_M_r_from_T(T)
    M_c = du.gen_M_c_from_T(T)

    T, M_c = du.convert_columns_to_multinomial(T, M_c, range(n_cols))

    return T, M_r, M_c

def run_test_continuous(n, observed):
    n_rows = 40
    n_cols = 40

    if observed:
        query_row = 10
    else:
        query_row = n_rows

    query_column = 1

    Q = [(query_row, query_column)]

    # do the test with multinomial data
    T, M_r, M_c= du.gen_factorial_data_objects(get_next_seed(),2,2,n_rows,1)

    state = State.p_State(M_c, T)

    T_array = numpy.array(T)

    X_L = state.get_X_L()
    X_D = state.get_X_D()

    Y = [] # no constraints

    # pull n samples
    samples = su.simple_predictive_sample(M_c, X_L, X_D, Y, Q, get_next_seed,n=n)

    X_array = numpy.sort(numpy.array(samples))

    std_X = numpy.std(X_array)
    mean_X = numpy.mean(X_array)

    # filter out extreme values
    X_filter_low = numpy.nonzero(X_array < mean_X-2.*std_X)[0]
    X_filter_high = numpy.nonzero(X_array > mean_X+2.*std_X)[0]
    X_filter = numpy.hstack((X_filter_low, X_filter_high))
    X_array = numpy.delete(X_array, X_filter)

    # sort for area calculation later on
    X_array = numpy.sort(X_array)

    X = X_array.tolist()

    # build the queries
    Qs = [];
    for x in X:
        Qtmp = (query_row, query_column, x)
        Qs.append(Qtmp)

    # get pdf values
    densities = numpy.exp(su.simple_predictive_probability(M_c, X_L, X_D, Y, Qs))

    # test that the area under Ps2 and pdfs is about 1 
    # calculated using the trapezoid rule
    area_density = 0;
    for i in range(len(X)-1):
        area_density += (X[i+1]-X[i])*(densities[i+1]+densities[i])/2.0

    print "Area of PDF (should be close to, but not greater than, 1): " + str(area_density)
    print "*Note: The area will be less than one because the range (integral) is truncated."

    pylab.figure(facecolor='white')

    # PLOT: probability vs samples distribution
    # scale all histograms to be valid PDFs (area=1)
    pdf, bins, patches = pylab.hist(X,100,normed=1, histtype='stepfilled',label='samples', alpha=.5, color=[.5,.5,.5])
    pylab.scatter(X,densities, c="red", label="pdf", edgecolor='none')

    pylab.legend(loc='upper left',fontsize='x-small')
    pylab.xlabel('value') 
    pylab.ylabel('frequency/density')
    pylab.title('TEST: PDF (not scaled)')

    pylab.show()
    fd, fig_filename = tempfile.mkstemp(prefix='run_test_continuous_',
            suffix='.png', dir='.')
    pylab.savefig(fig_filename)


def run_test_multinomial(n, observed):
    n_rows = 40
    n_cols = 40

    if observed:
        query_row = 10
    else:
        query_row = n_rows

    query_column = 1

    Q = [(query_row, query_column)]

    # do the test with multinomial data
    T, M_r, M_c = generate_multinomial_data(get_next_seed(),2,n_rows,1)
    
    state = State.p_State(M_c, T)

    X_L = state.get_X_L()
    X_D = state.get_X_D()

    Y = []

    # pull n samples
    samples = su.simple_predictive_sample(M_c, X_L, X_D, Y, Q, get_next_seed,n=n)
    X_array = numpy.sort(numpy.array(samples))
    X = numpy.unique(X_array)
    X = X.tolist()

    # build the queries
    Qs = [];
    for x in X:
        # Qtmp = (query_row, query_column, x[0])
        Qtmp = (query_row, query_column, x)
        Qs.append(Qtmp)

    # get pdf values
    densities = numpy.exp(su.simple_predictive_probability(M_c, X_L, X_D, Y, Qs))

    print "Sum of densities (should be 1): %f" % (numpy.sum(densities))

    pylab.clf()

    # PLOT: probability vs samples distribution
    # scale all histograms to be valid PDFs (area=1)
    mbins = numpy.unique(X_array)

    mbins = numpy.append(mbins,max(mbins)+1)

    pdf, bins = numpy.histogram(X_array,mbins)

    pdf = pdf/float(numpy.sum(pdf))
    pylab.bar(mbins[0:-1],pdf,label="samples",alpha=.5)
    pylab.scatter(X,densities, c="red", label="pdf", edgecolor='none')

    pylab.legend(loc='upper left',fontsize='x-small')
    pylab.xlabel('value') 
    pylab.ylabel('frequency/density')
    pylab.title('TEST: PDF (not scaled)')

    pylab.show()

    fd, fig_filename = tempfile.mkstemp(prefix='run_test_multinomial_',
            suffix='.png', dir='.')
    pylab.savefig(fig_filename)

random.seed(None) # seed with system time
inf_seed = random.randrange(32767)
random_state = numpy.random.RandomState(inf_seed)


run_test(n=5000, d_type='continuous', observed=False)
run_test(n=5000, d_type='continuous', observed=True)
run_test(n=5000, d_type='multinomial', observed=False)
run_test(n=5000, d_type='multinomial', observed=True)

########NEW FILE########
__FILENAME__ = test_sampler_enumeration
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import numpy as np
import random
import sys

import crosscat.utils.enumerate_utils as eu
import crosscat.cython_code.State as State
import pylab
from scipy.stats import pearsonr as pearsonr

# Do we want to plot the results?
do_plot = True

if do_plot:
	pylab.ion()
	pylab.figure(facecolor="white",figsize=(10,10))


random.seed(None)

# priors
alpha = 1.0;
mu = 0.0;
r = 1.0;
nu = 1.0;
s = 1.0;

# matrix size
n_rows = 3
n_cols = 3

# sampler details
iters = 1000	# number of samples
burns = 20	# burn in before collection

# the number of states to correlate for the test (the n most probable)
n_highest = 20

# enumerate all state partitions
state_partitions = eu.CrossCatPartitions(n_rows, n_cols)
NS = state_partitions.N;

# the number of states to run the test on (randomly seelected)
n_states = 10;

print "Testing the sampler against enumerated answer for data generated from \n%i random states." % n_states

for state in random.sample(state_partitions.states, n_states):
# for state in state_partitions.states:

	progress = "[State %i] Collecting samples..." % (state['idx'])
	sys.stdout.write(progress)

	# Generate data from this state partition
	T, M_r, M_c = eu.GenDataFromPartitions(state['col_parts'], state['row_parts'], 0, 10, .5)
	# calculate the probability of the data under each state
	P = np.exp(eu.CCML(state_partitions, T, mu, r, nu, s, alpha, alpha))
	# print "done."
	
	# initialize state samples counter
	state_count = np.zeros(NS)

	# print "Sampling..."
	# start collecting samples
	# initalize the sampler
	p_State = State.p_State(M_c, T, N_GRID=100)
	X_L = eu.FixPriors(p_State.get_X_L(), alpha, mu, s, r, nu)
	X_D = p_State.get_X_D()
	p_State = State.p_State(M_c, T, N_GRID=100, X_L=X_L, X_D=X_D)


	for b in range(200):
		p_State.transition(which_transitions=['column_partition_assignments','row_partition_assignments'])

	mlen = 0;
	for j in range(iters):
		for b in range(burns):
			p_State.transition(which_transitions=['column_partition_assignments','row_partition_assignments'])

		progress1 = "%i of %i" % (j, iters)
		progress = "%s%s" % ('\b'*mlen, progress1)
		mlen = len(progress1)
		sys.stdout.write(progress)
		sys.stdout.flush()

		# collect a sample
		# get the colum partitions
		scp = p_State.get_column_partition()['assignments']
		# get the row partitions
		srp = p_State.get_X_D()
		# match the state
		state_idx = state_partitions.findState(scp, srp)
		state_count[state_idx] += 1.0

	print "%sdone.%s" % ('\b'*mlen, ' '*mlen)
	# normalize
	state_count = state_count/sum(state_count)
	
	# assert(sum(state_count) == 1.0)
	# assert(sum(P) == 1.0)

	# get the n_highest higest probability states
	sorted_indices = np.argsort(P)
	true_highest_probs = P[sorted_indices[-n_highest:]]
	inferred_highest_probs = state_count[sorted_indices[-n_highest:]]

	assert(len(true_highest_probs) == n_highest)
	assert(len(inferred_highest_probs) == n_highest)

	# correlation (two-tailed p value)
	PR = pearsonr(true_highest_probs, inferred_highest_probs) 

	# print "Higest probability states"
	# print true_highest_probs
	# print "Inferred"
	# print inferred_highest_probs
	print "\tCorrelation, (R,p)" + str(PR)

	if do_plot:
		pylab.clf()

		X = range(NS)
		pylab.subplot(2,1,1,title="All states")
		pylab.plot(X,P, color="blue", linewidth=2.5, linestyle="-", label="enumeration",alpha=.5)
		pylab.plot(X,state_count, color="red", linewidth=2.5, linestyle="-", label="sampler",alpha=.5)
		pylab.xlim(0,NS)
		pylab.legend(loc='upper right')

		X = range(n_highest)
		pylab.subplot(2,1,2,title=("%i highest probability states" % n_highest))
		pylab.plot(X,true_highest_probs[::-1], color="blue", linewidth=2.5, linestyle="-",label="enumeration",alpha=.5)
		pylab.plot(X,inferred_highest_probs[::-1], color="red", linewidth=2.5, linestyle="-",label="sampler",alpha=.5)
		pylab.xlim(0,n_highest)
		pylab.legend(loc='upper right')
		pylab.draw()
		
########NEW FILE########
__FILENAME__ = timing_analysis
import argparse


def _generate_parser():
    default_num_rows = [100, 400, 1000, 4000]
    default_num_cols = [8, 16, 32]
    default_num_clusters = [1, 2]
    default_num_views = [1, 2]
    #
    parser = argparse.ArgumentParser()
    parser.add_argument('--dirname', default='timing_analysis', type=str)
    parser.add_argument('--num_rows', nargs='+', default=default_num_rows, type=int)
    parser.add_argument('--num_cols', nargs='+', default=default_num_cols, type=int)
    parser.add_argument('--num_clusters', nargs='+', default=default_num_clusters, type=int)
    parser.add_argument('--num_views', nargs='+', default=default_num_views, type=int)
    parser.add_argument('--plot_prefix', default=None, type=str)
    parser.add_argument('--no_plots', action='store_true')
    return parser

def _munge_args(args):
    kwargs = args.__dict__.copy()
    dirname = kwargs.pop('dirname')
    plot_prefix = kwargs.pop('plot_prefix')
    generate_plots = not kwargs.pop('no_plots')
    return kwargs, dirname, plot_prefix, generate_plots


if __name__ == '__main__':
    from crosscat.utils.general_utils import Timer
    import crosscat.utils.timing_test_utils as ttu
    from experiment_runner.ExperimentRunner import ExperimentRunner, propagate_to_s3


    # parse args
    parser = _generate_parser()
    args = parser.parse_args()
    kwargs, dirname, plot_prefix, generate_plots = _munge_args(args)


    # create configs
    config_list = ttu.gen_configs(
            kernel_list = ttu._kernel_list,
            n_steps=[10],
            **kwargs
            )


    # do experiments
    er = ExperimentRunner(ttu.runner, storage_type='fs',
            dirname_prefix=dirname,
            bucket_str='experiment_runner')
    with Timer('er.do_experiments') as timer:
        er.do_experiments(config_list)
        pass
    # push to s3
    propagate_to_s3(er)


    if generate_plots:
        ttu.plot_results(er.frame, plot_prefix=plot_prefix, dirname=dirname)

########NEW FILE########
__FILENAME__ = test_continuous_component_model
import crosscat.tests.component_model_extensions.ContinuousComponentModel as ccmext
import random
import math
import numpy

import unittest

def main():
    unittest.main()

class TestContinuousComponentModelExtensions_Constructors(unittest.TestCase):
    def setUp(self):
        N = 10
        self.N = N
        random.seed(0)
        self.X = numpy.array([[random.normalvariate(0.0, 1.0)] for i in range(N)])

        self.params_good = dict(rho=1.0, mu=0.0)
        self.params_empty = dict()
        self.params_missing_rho = dict(mu=0.0)
        self.params_missing_mu = dict(mu=0.0)
        self.params_not_dict = [0.0, 1.0]
        self.params_negative_rho = dict(rho=-1.0, mu=0.0)
        self.params_zero_rho = dict(rho=0.0, mu=0.0)

        self.hypers_good = dict(mu=0.0, nu=1.0, r=1.0, s=1.0)
        self.hypers_missing_mu = dict(nu=1.0, r=1.0, s=1.0)
        self.hypers_missing_nu = dict(mu=0.0, r=1.0, s=1.0)
        self.hypers_missing_r = dict(mu=0.0, nu=1.0, s=1.0)
        self.hypers_missing_s = dict(mu=0.0, nu=1.0, r=1.0)
        self.hypers_low_nu = dict(mu=0.0, nu=-1.0, r=1.0, s=1.0)
        self.hypers_low_r = dict(mu=0.0, nu=1.0, r=-1.0, s=1.0)
        self.hypers_low_s = dict(mu=0.0, nu=1.0, r=1.0, s=-1.0)
        self.hypers_not_dict = [0,1,2,3]

    # Test from_parameters conrtuctor
    def test_from_parameters_contructor_with_good_complete_params_and_hypers(self):
        m = ccmext.p_ContinuousComponentModel.from_parameters(self.N,
            data_params=self.params_good,
            hypers=self.hypers_good,
            gen_seed=0)

        assert m is not None

    def test_from_parameters_contructor_with_no_params_and_hypers(self):
        m = ccmext.p_ContinuousComponentModel.from_parameters(self.N, gen_seed=0)
        assert m is not None

    def test_from_parameters_contructor_with_bad_params_and_good_hypers(self):
        self.assertRaises(KeyError, ccmext.p_ContinuousComponentModel.from_parameters, self.N,
            data_params=self.params_empty,
            hypers=self.hypers_good,
            gen_seed=0)
        self.assertRaises(TypeError, ccmext.p_ContinuousComponentModel.from_parameters, self.N,
            data_params=self.params_not_dict,
            hypers=self.hypers_good,
            gen_seed=0)
        self.assertRaises(KeyError, ccmext.p_ContinuousComponentModel.from_parameters, self.N,
            data_params=self.params_missing_mu,
            hypers=self.hypers_good,
            gen_seed=0)
        self.assertRaises(KeyError, ccmext.p_ContinuousComponentModel.from_parameters, self.N,
            data_params=self.params_missing_rho,
            hypers=self.hypers_good,
            gen_seed=0)
        self.assertRaises(ValueError, ccmext.p_ContinuousComponentModel.from_parameters, self.N,
            data_params=self.params_negative_rho,
            hypers=self.hypers_good,
            gen_seed=0)
        self.assertRaises(ValueError, ccmext.p_ContinuousComponentModel.from_parameters, self.N,
            data_params=self.params_zero_rho,
            hypers=self.hypers_good,
            gen_seed=0)

    def test_from_parameters_contructor_with_good_params_and_bad_hypers(self):
        self.assertRaises(KeyError, ccmext.p_ContinuousComponentModel.from_parameters, self.N,
            data_params=self.params_good,
            hypers=self.hypers_missing_mu,
            gen_seed=0)
        self.assertRaises(KeyError, ccmext.p_ContinuousComponentModel.from_parameters, self.N,
            data_params=self.params_good,
            hypers=self.hypers_missing_nu,
            gen_seed=0)
        self.assertRaises(KeyError, ccmext.p_ContinuousComponentModel.from_parameters, self.N,
            data_params=self.params_good,
            hypers=self.hypers_missing_r,
            gen_seed=0)
        self.assertRaises(KeyError, ccmext.p_ContinuousComponentModel.from_parameters, self.N,
            data_params=self.params_good,
            hypers=self.hypers_missing_s,
            gen_seed=0)
        self.assertRaises(ValueError, ccmext.p_ContinuousComponentModel.from_parameters, self.N,
            data_params=self.params_good,
            hypers=self.hypers_low_nu,
            gen_seed=0)
        self.assertRaises(ValueError, ccmext.p_ContinuousComponentModel.from_parameters, self.N,
            data_params=self.params_good,
            hypers=self.hypers_low_r,
            gen_seed=0)
        self.assertRaises(ValueError, ccmext.p_ContinuousComponentModel.from_parameters, self.N,
            data_params=self.params_good,
            hypers=self.hypers_low_s,
            gen_seed=0)
        self.assertRaises(TypeError, ccmext.p_ContinuousComponentModel.from_parameters, self.N,
            data_params=self.params_good,
            hypers=self.hypers_not_dict,
            gen_seed=0)


    # From data constructor
    def test_from_data_contructor_with_good_complete_hypers(self):
        m = ccmext.p_ContinuousComponentModel.from_data(self.X,
            hypers=self.hypers_good,
            gen_seed=0)
        assert m is not None

    def test_from_data_contructor_with_no_params_and_hypers(self):
        m = ccmext.p_ContinuousComponentModel.from_data(self.X,gen_seed=0)
        assert m is not None

    def test_from_data_contructor_with_bad_hypers(self):
        self.assertRaises(KeyError, ccmext.p_ContinuousComponentModel.from_data, self.X,
            hypers=self.hypers_missing_mu,
            gen_seed=0)
        self.assertRaises(KeyError, ccmext.p_ContinuousComponentModel.from_data, self.X,
            hypers=self.hypers_missing_nu,
            gen_seed=0)
        self.assertRaises(KeyError, ccmext.p_ContinuousComponentModel.from_data, self.X,
            hypers=self.hypers_missing_r,
            gen_seed=0)
        self.assertRaises(KeyError, ccmext.p_ContinuousComponentModel.from_data, self.X,
            hypers=self.hypers_missing_s,
            gen_seed=0)
        self.assertRaises(ValueError, ccmext.p_ContinuousComponentModel.from_data, self.X,
            hypers=self.hypers_low_nu,
            gen_seed=0)
        self.assertRaises(ValueError, ccmext.p_ContinuousComponentModel.from_data, self.X,
            hypers=self.hypers_low_r,
            gen_seed=0)
        self.assertRaises(ValueError, ccmext.p_ContinuousComponentModel.from_data, self.X,
            hypers=self.hypers_low_s,
            gen_seed=0)
        self.assertRaises(TypeError, ccmext.p_ContinuousComponentModel.from_data, self.X,
            hypers=self.hypers_not_dict,
            gen_seed=0)

class TestContinuousComponentModelExtensions_FromParametersConstructor(unittest.TestCase):

    def setUp(self):
        N = 10
        random.seed(0)
        self.X = numpy.array([[random.normalvariate(0.0, 1.0)] for i in range(N)])
        self.component_model = ccmext.p_ContinuousComponentModel.from_parameters(N,gen_seed=0)

    def test_all_hyperparameters_intialized(self):  
        these_hyperparameters = self.component_model.get_hypers()
        # make sure each key exists
        for hyperparameter in ['mu', 'nu', 'r', 's']:
            assert(hyperparameter in these_hyperparameters.keys())

    def test_all_suffstats_intialized(self):
        these_suffstats = self.component_model.get_suffstats()
        # make sure each key exists
        for suffstat in ['sum_x', 'sum_x_squared']:
            assert suffstat in these_suffstats.keys()

    def test_draw_component_model_params(self):
        draw = self.component_model.sample_parameters_given_hyper()
        
        assert type(draw) is dict
        
        model_parameter_bounds = self.component_model.get_model_parameter_bounds()
        
        for key, value in draw.iteritems():
            assert(key in ['mu', 'rho'])
            assert(type(value) is float or type(value) is numpy.float64)
            assert(not math.isnan(value))
            assert(not math.isinf(value))
            if key == 'rho':
                assert(value > 0.0)
    
    def test_uncollapsed_likelihood(self):
        ans = -14.248338610116935
        log_likelihood = self.component_model.uncollapsed_likelihood(self.X, {'mu':0.0, 'rho':1.0})
        assert log_likelihood < 0.0 
        assert math.fabs(ans-log_likelihood) < .00000001


class TestContinuousComponentModelExtensions_FromDataConstructor(unittest.TestCase):

    def setUp(self):
        N = 10
        random.seed(0)
        self.X = numpy.array([[random.normalvariate(0.0, 1.0)] for i in range(N)])
        self.component_model = ccmext.p_ContinuousComponentModel.from_data(self.X,gen_seed=0)

    def test_all_hyperparameters_intialized(self):  
        these_hyperparameters = self.component_model.get_hypers()
        # make sure each key exists
        for hyperparameter in ['mu', 'nu', 'r', 's']:
            assert(hyperparameter in these_hyperparameters.keys())

    def test_all_suffstats_intialized(self):
        these_suffstats = self.component_model.get_suffstats()
        # make sure each key exists
        for suffstat in ['sum_x', 'sum_x_squared']:
            assert suffstat in these_suffstats.keys()

    def test_draw_component_model_params(self):
        draw = self.component_model.sample_parameters_given_hyper()
        
        assert type(draw) is dict
                
        for key, value in draw.iteritems():
            assert(key in ['mu', 'rho'])
            assert(type(value) is float or type(value) is numpy.float64)
            assert(not math.isnan(value))
            assert(not math.isinf(value))
            if key == 'rho':
                assert(value > 0.0)

    def test_uncollapsed_likelihood(self):
        ans = -20.971295328329504
        log_likelihood = self.component_model.uncollapsed_likelihood(self.X, {'mu':0.0, 'rho':1.0})
        assert log_likelihood < 0.0 
        assert math.fabs(ans-log_likelihood) < .00000001

class TestContinuousComponentModelExtensions_static(unittest.TestCase):
    def setUp(self):
        N = 10
        random.seed(0)
        self.X = numpy.array([[random.normalvariate(0.0, 1.0)] for i in range(N)])
        self.component_class = ccmext.p_ContinuousComponentModel

    def test_log_likelihood(self):
        X_1 = numpy.array([[1],[0]])
        parameters = dict(mu=0.0, rho=1.0)
        log_likelihood = self.component_class.log_likelihood(X_1, parameters)
        assert log_likelihood < 0.0 
        assert math.fabs(-2.3378770664093453-log_likelihood) < .00000001

        parameters = dict(mu=2.2, rho=12.1)
        log_likelihood = self.component_class.log_likelihood(X_1, parameters)
        assert log_likelihood < 0.0 
        assert math.fabs(-37.338671613806667-log_likelihood) < .00000001

    def test_log_pdf(self):
        # test some answers
        X_1 = numpy.array([[1],[0]])
        parameters = dict(mu=0.0, rho=1.0)
        log_pdf = self.component_class.log_pdf(X_1, parameters)
        assert len(log_pdf) == 2
        assert math.fabs(-1.4189385332046727-log_pdf[0,0]) < .00000001
        assert math.fabs(-0.91893853320467267-log_pdf[1,0]) < .00000001

        parameters = dict(mu=2.2, rho=12.1)
        log_pdf = self.component_class.log_pdf(X_1, parameters)
        assert len(log_pdf) == 2
        assert math.fabs(-8.38433580690333-log_pdf[0,0]) < .00000001
        assert math.fabs(-28.954335806903334-log_pdf[1,0]) < .00000001

        # points that are farther away from the mean should be less likely
        parameters = dict(mu=0.0, rho=1.0)
        lspc = numpy.linspace(0,10,num=20)
        X_2 = numpy.array([[x] for x in lspc])
        log_pdf = self.component_class.log_pdf(X_2, parameters)
        assert len(log_pdf) == 20
        for n in range(1,20):
            assert log_pdf[n-1,0] > log_pdf[n,0]

    def test_generate_discrete_support(self):
        parameters = dict(mu=0.0, rho=1.0)

        support = self.component_class.generate_discrete_support(parameters, support=0.95, nbins=100)

        assert type(support) is list
        assert len(support) == 100
        # end points should have the same magnitude
        assert support[0] == -support[-1] 
        # the two points stradding the mean should have the same magnitude
        assert support[49] == -support[50]
        assert math.fabs(support[0] + 1.959963984540054) < .00000001
        assert math.fabs(support[-1] - 1.959963984540054) < .00000001

    def test_draw_component_model_hyperparameters_single(self):
        draw_list = self.component_class.draw_hyperparameters(self.X)
        assert type(draw_list) is list
        assert type(draw_list[0]) is dict

        draw = draw_list[0]

        assert type(draw) is dict
        
        for key, value in draw.iteritems():
            assert key in ['mu', 'nu', 'r', 's']
            assert type(value) is float or type(value) is numpy.float64
            assert(not math.isnan(value))
            assert(not math.isinf(value))

            if key in ['nu', 's', 'r']:
                assert value > 0.0

    def test_draw_component_model_hyperparameters_multiple(self):
        n_draws = 3
        draw_list = self.component_class.draw_hyperparameters(self.X, n_draws=n_draws)

        assert type(draw_list) is list
        assert len(draw_list) == 3

        for draw in draw_list:
            assert type(draw) is dict
        
            for key, value in draw.iteritems():
                assert key in ['mu', 'nu', 'r', 's']
                assert type(value) is float or type(value) is numpy.float64
                assert(not math.isnan(value))
                assert(not math.isinf(value))

                if key in ['nu', 's', 'r']:
                    assert value > 0.0

    def test_generate_data_from_parameters(self):
        N = 10
        parameters = dict(mu=0.0, rho=1.0)
        X = self.component_class.generate_data_from_parameters(parameters, N)

        assert type(X) == numpy.ndarray
        assert len(X) == N

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_multinomial_component_model
import crosscat.tests.component_model_extensions.MultinomialComponentModel as mcmext
import random
import math
import numpy

import unittest

def main():
    unittest.main()

class TestMultinomialComponentModelExtensions_Constructors(unittest.TestCase):
    def setUp(self):
        self.N = 10
        self.K = 3

        self.data_params_good = dict(weights=[1.0/3.0, 1/3.0, 1.0/3.0])
        self.data_params_bad_sum = dict(weights=[1.0/3.0, 1/3.0, 1.0/2.0])
        self.data_params_low_k = dict(weights=[1.0/2.0, 1/2.0])
        self.data_params_empty = dict()

        self.hypers_good = dict(K=self.K, dirichlet_alpha=1.0)
        self.hypers_missing_k = dict(dirichlet_alpha=1.0)
        self.hypers_missing_alpha = dict(K=self.K)
        self.hypers_low_k = dict(K=2, dirichlet_alpha=1.0)
        self.hypers_negative_alpha = dict(K=self.K, dirichlet_alpha=-1.0)
        self.hypers_negative_k = dict(K=-self.K, dirichlet_alpha=1.0)

        self.X_good = numpy.array([0, 2, 0, 2, 2, 2, 0, 1, 0, 2])
        self.X_high_k = numpy.array([0, 2, 0, 2, 2, 2, 3, 1, 0, 2])
        # there should be nothing wrong with this (the category exists, but we 
        # never observe it in the data)
        self.X_low_k = numpy.array([0, 1, 0, 0, 1, 1, 0, 1, 0, 0])

    # Test from_parameters conrtuctor
    def test_from_parameters_contructor_with_good_complete_params_and_hypers(self):
        m = mcmext.p_MultinomialComponentModel.from_parameters(self.N,
            params=self.data_params_good,
            hypers=self.hypers_good,
            gen_seed=0)

        assert m is not None

    def test_from_parameters_contructor_with_no_params_and_hypers(self):
        mcmext.p_MultinomialComponentModel.from_parameters(self.N,gen_seed=0)

    def test_from_parameters_contructor_with_bad_params_and_good_hypers(self):
        self.assertRaises(ValueError, mcmext.p_MultinomialComponentModel.from_parameters, self.N,
            params=self.data_params_bad_sum,
            hypers=self.hypers_good,
            gen_seed=0)
        self.assertRaises(KeyError, mcmext.p_MultinomialComponentModel.from_parameters, self.N,
            params=self.data_params_empty,
            hypers=self.hypers_good,
            gen_seed=0)
        self.assertRaises(TypeError, mcmext.p_MultinomialComponentModel.from_parameters, self.N,
            params=[1.0/3.0, 1/3.0, 1.0/3.0],
            hypers=self.hypers_good,
            gen_seed=0)

    def test_from_parameters_contructor_with_good_params_and_bad_hypers(self):
        self.assertRaises(KeyError, mcmext.p_MultinomialComponentModel.from_parameters, self.N,
            params=self.data_params_good,
            hypers=self.hypers_missing_k,
            gen_seed=0)
        self.assertRaises(KeyError, mcmext.p_MultinomialComponentModel.from_parameters, self.N,
            params=self.data_params_good,
            hypers=self.hypers_missing_alpha,
            gen_seed=0)
        self.assertRaises(ValueError, mcmext.p_MultinomialComponentModel.from_parameters, self.N,
            params=self.data_params_good,
            hypers=self.hypers_negative_alpha,
            gen_seed=0)
        self.assertRaises(ValueError, mcmext.p_MultinomialComponentModel.from_parameters, self.N,
            params=self.data_params_good,
            hypers=self.hypers_negative_k,
            gen_seed=0)

    def test_from_parameters_contructor_with_mismiatched_k_in_params_and_hypers(self):
        """
        Makes sure that an error is thrown if the number of categories doesn't match up 
        in the hyperparameters and in the model parameters
        """
        self.assertRaises(ValueError, mcmext.p_MultinomialComponentModel.from_parameters, self.N,
            params=self.data_params_good,
            hypers=self.hypers_low_k,
            gen_seed=0)
        self.assertRaises(ValueError, mcmext.p_MultinomialComponentModel.from_parameters, self.N,
            params=self.data_params_low_k,
            hypers=self.hypers_good,
            gen_seed=0)


    # Test from_data conrtuctor
    def test_from_data_contructor_with_good_and_complete_data_and_hypers(self):
        m = mcmext.p_MultinomialComponentModel.from_data(self.X_good,
            hypers=self.hypers_good,
            gen_seed=0)

        assert m is not None

    def test_from_data_contructor_with_good_data_and_no_hypers(self):
        mcmext.p_MultinomialComponentModel.from_data(self.X_good, gen_seed=0)

    def test_from_data_contructor_with_low_k_data_and_good_hypers(self):
        mcmext.p_MultinomialComponentModel.from_data(self.X_low_k,
            hypers=self.hypers_good,
            gen_seed=0)

    def test_from_data_contructor_with_bad_data_and_good_hypers(self):
        self.assertRaises(ValueError, mcmext.p_MultinomialComponentModel.from_data, self.X_high_k,
            hypers=self.hypers_good,
            gen_seed=0)

    def test_from_data_contructor_with_good_data_and_bad_hypers(self):
        self.assertRaises(KeyError, mcmext.p_MultinomialComponentModel.from_data, self.X_high_k,
            hypers=self.hypers_missing_k,
            gen_seed=0)
        self.assertRaises(KeyError, mcmext.p_MultinomialComponentModel.from_data, self.X_high_k,
            hypers=self.hypers_missing_alpha,
            gen_seed=0)
        self.assertRaises(ValueError, mcmext.p_MultinomialComponentModel.from_data, self.X_high_k,
            hypers=self.hypers_negative_alpha,
            gen_seed=0)
        self.assertRaises(ValueError, mcmext.p_MultinomialComponentModel.from_data, self.X_high_k,
            hypers=self.hypers_negative_k,
            gen_seed=0)


class TestMultinomialComponentModelExtensions_FromParametersConstructor(unittest.TestCase):
    def setUp(self):
        N = 10
        K = 5

        self.X = [3, 4, 1, 2, 4, 0, 3, 0, 1, 2]

        data_params_good = dict(weights=[1.0/5.0]*5)
        hypers_good = dict(K=K, dirichlet_alpha=1.0)

        self.component_model = mcmext.p_MultinomialComponentModel.from_parameters(N,gen_seed=0)
        self.component_model_w_params = mcmext.p_MultinomialComponentModel.from_parameters(N,
            params=data_params_good,
            gen_seed=0)
        self.component_model_w_hypers = mcmext.p_MultinomialComponentModel.from_parameters(N,
            hypers=hypers_good,
            gen_seed=0)
        self.component_model_w_params_and_hypers = mcmext.p_MultinomialComponentModel.from_parameters(N,
            params=data_params_good,
            hypers=hypers_good,
            gen_seed=0)

        assert self.component_model is not None

    def test_all_hyperparameters_intialized(self):  
        these_hyperparameters = self.component_model.get_hypers()
        for hyperparameter in ['K', 'dirichlet_alpha']:
            assert(hyperparameter in these_hyperparameters.keys())

        these_hyperparameters = self.component_model_w_params.get_hypers()
        for hyperparameter in ['K', 'dirichlet_alpha']:
            assert(hyperparameter in these_hyperparameters.keys())

        these_hyperparameters = self.component_model_w_hypers.get_hypers()
        for hyperparameter in ['K', 'dirichlet_alpha']:
            assert(hyperparameter in these_hyperparameters.keys())

        these_hyperparameters = self.component_model_w_params_and_hypers.get_hypers()
        for hyperparameter in ['K', 'dirichlet_alpha']:
            assert(hyperparameter in these_hyperparameters.keys())

    def test_all_suffstats_intialized(self):
        # make sure each key exists (should be keys 0,..,4)
        key_key = [str(i) for i in range(5)]

        _, these_suffstats = self.component_model.get_suffstats()
        for suffstat in key_key:
            assert(suffstat in these_suffstats.keys())

        _, these_suffstats = self.component_model_w_params.get_suffstats()
        for suffstat in key_key:
            assert(suffstat in these_suffstats.keys())

        _, these_suffstats = self.component_model_w_hypers.get_suffstats()
        for suffstat in key_key:
            assert(suffstat in these_suffstats.keys())

        _, these_suffstats = self.component_model_w_params_and_hypers.get_suffstats()
        for suffstat in key_key:
            assert(suffstat in these_suffstats.keys())

    def test_draw_component_model_params(self):
        draw = self.component_model.sample_parameters_given_hyper()
        
        assert type(draw) is dict
        
        for key, value in draw.iteritems():
            assert key in ['weights']
            assert type(value) is list
            assert math.fabs(sum(value)-1.0) < .0000001
            for w in value:
                assert w >= 0.0
    
    def test_uncollapsed_likelihood(self):
        params = dict(weights=[1.0/5.0]*5)
        ans = -1.27764862371727
        lp = self.component_model_w_params_and_hypers.uncollapsed_likelihood(self.X, params)
        assert math.fabs(ans-lp) < .00000001
        lp = self.component_model_w_hypers.uncollapsed_likelihood(self.X, params)
        assert math.fabs(ans-lp) < .00000001

        params = dict(weights=[.1, .1, .4, .2, .2])
        ans = -2.66394298483716
        lp = self.component_model_w_params_and_hypers.uncollapsed_likelihood(self.X, params)
        assert math.fabs(ans-lp) < .00000001
        lp = self.component_model_w_hypers.uncollapsed_likelihood(self.X, params)
        assert math.fabs(ans-lp) < .00000001


class TestMultinomialComponentModelExtensions_FromDataConstructor(unittest.TestCase):
    def setUp(self):
        K = 5
        self.X = [3, 4, 1, 2, 4, 0, 3, 0, 1, 2]

        hypers_good = dict(K=K, dirichlet_alpha=1.0)

        self.component_model = mcmext.p_MultinomialComponentModel.from_data(self.X, gen_seed=0)
        self.component_model_w_hypers = mcmext.p_MultinomialComponentModel.from_data(self.X,
            hypers=hypers_good,
            gen_seed=0)

        assert self.component_model is not None

    def test_all_hyperparameters_intialized(self):  
        these_hyperparameters = self.component_model.get_hypers()
        for hyperparameter in ['K', 'dirichlet_alpha']:
            assert(hyperparameter in these_hyperparameters.keys())

        these_hyperparameters = self.component_model_w_hypers.get_hypers()
        for hyperparameter in ['K', 'dirichlet_alpha']:
            assert(hyperparameter in these_hyperparameters.keys())


    def test_all_suffstats_intialized(self):
        # make sure each key exists (should be keys 0,..,4)
        key_key = [str(i) for i in range(5)]

        _, these_suffstats = self.component_model.get_suffstats()
        for suffstat in key_key:
            assert(suffstat in these_suffstats.keys())

        _, these_suffstats = self.component_model_w_hypers.get_suffstats()
        for suffstat in key_key:
            assert(suffstat in these_suffstats.keys())

    def test_draw_component_model_params(self):
        draw = self.component_model.sample_parameters_given_hyper()
        
        assert type(draw) is dict
        
        for key, value in draw.iteritems():
            assert key in ['weights']
            assert type(value) is list
            assert math.fabs(sum(value)-1.0) < .0000001
            for w in value:
                assert w >= 0.0
    
    def test_uncollapsed_likelihood(self):
        params = dict(weights=[1.0/5.0]*5)
        ans = -1.27764862371727
        lp = self.component_model_w_hypers.uncollapsed_likelihood(self.X, params)
        assert math.fabs(ans-lp) < .00000001

        params = dict(weights=[.1, .1, .4, .2, .2])
        ans = -2.66394298483716
        lp = self.component_model_w_hypers.uncollapsed_likelihood(self.X, params)
        assert math.fabs(ans-lp) < .00000001
        

class TestMultinomialComponentModelExtensions_static(unittest.TestCase):
    def setUp(self):
        N = 10
        random.seed(0)
        self.X = numpy.array([3, 4, 1, 2, 4, 0, 3, 0, 1, 2])
        self.component_class = mcmext.p_MultinomialComponentModel

    def test_log_likelihood(self):
        # the answers below are the result of MATLAB: 
        # log( mnpdf( hist(X,K), weights ) )
        ans = -4.45570245406521
        weights = [.2]*5
        log_likelihood = self.component_class.log_likelihood(self.X, 
            {'weights':weights})
        assert math.fabs(log_likelihood-ans) < .0000001

        ans = -6.78200407367657
        weights = [.1, .2, .5, .1, .1]
        log_likelihood = self.component_class.log_likelihood(self.X, 
            {'weights':weights})
        assert math.fabs(log_likelihood-ans) < .0000001

    def test_generate_discrete_support(self):
        parameters = dict(weights=[1.0/3.0, 1.0/3.0, 1.0/3.0])

        support = self.component_class.generate_discrete_support(parameters)

        assert type(support) is list
        assert len(support) == 3

        for i in range(3):
            assert i == support[i]

    def test_draw_component_model_hyperparameters_single(self):
        # test with data array
        draw_list = self.component_class.draw_hyperparameters(self.X)
        assert type(draw_list) is list
        assert type(draw_list[0]) is dict

        draw = draw_list[0]

        assert type(draw) is dict

        for key, value in draw.iteritems():
            assert key in ['K', 'dirichlet_alpha']

            assert(not math.isnan(value))
            assert(not math.isinf(value))

            if key == 'K':
                assert type(value) is int
                assert value == max(self.X)+1
            elif key == 'dirichlet_alpha':
                assert type(value) is float or type(value) is numpy.float64
                assert value > 0.0
            else:
                raise KeyError("Ivalid model parameters key %s" % key)

        # tests with int
        K = 5
        draw_list = self.component_class.draw_hyperparameters(K)
        assert type(draw_list) is list
        assert type(draw_list[0]) is dict

        draw = draw_list[0]

        assert type(draw) is dict

        for key, value in draw.iteritems():
            assert key in ['K', 'dirichlet_alpha']

            assert(not math.isnan(value))
            assert(not math.isinf(value))

            if key == 'K':
                assert type(value) is int
                assert value == K
            elif key == 'dirichlet_alpha':
                assert type(value) is float or type(value) is numpy.float64
                assert value > 0.0
            else:
                raise KeyError("Ivalid model parameters key %s" % key)

    def test_draw_component_model_hyperparameters_multiple(self):
        # test with data array
        n_draws = 3
        draw_list = self.component_class.draw_hyperparameters(self.X, n_draws=n_draws)

        assert type(draw_list) is list
        assert len(draw_list) == 3

        for draw in draw_list:
            assert type(draw) is dict
        
        for key, value in draw.iteritems():
            assert(not math.isnan(value))
            assert(not math.isinf(value))

            if key == 'K':
                assert type(value) is int
                assert value == max(self.X)+1
            elif key == 'dirichlet_alpha':
                assert type(value) is float or type(value) is numpy.float64
                assert value > 0.0
            else:
                raise KeyError("Ivalid model parameters key %s" % key)

        # test with int
        K = 5
        draw_list = self.component_class.draw_hyperparameters(K, n_draws=n_draws)

        assert type(draw_list) is list
        assert len(draw_list) == 3

        for draw in draw_list:
            assert type(draw) is dict
        
        for key, value in draw.iteritems():
            assert(not math.isnan(value))
            assert(not math.isinf(value))

            if key == 'K':
                assert type(value) is int
                assert value >= 1.0
                assert value == K
            elif key == 'dirichlet_alpha':
                assert type(value) is float or type(value) is numpy.float64
                assert value > 0.0
            else:
                raise KeyError("Ivalid model parameters key %s" % key)

    def test_generate_data_from_parameters(self):
        N = 10
        parameters = dict(weights=[1.0/3.0, 1.0/3.0, 1.0/3.0])
        X = self.component_class.generate_data_from_parameters(parameters, N, gen_seed=0)

        assert type(X) is numpy.ndarray
        assert len(X) == N
        assert max(X) <= 2
        assert min(X) >= 0

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = test_quality_test_utils
import crosscat.tests.component_model_extensions.ContinuousComponentModel as ccmext
import crosscat.tests.component_model_extensions.MultinomialComponentModel as mcmext

import crosscat.tests.quality_tests.quality_test_utils as qtu

import numpy

import unittest

def main():
    unittest.main()

class TestKLDivergence(unittest.TestCase):
	def setUp(self):
		# took these from a random run of test_mixture_inference_quality.py
		self.X_L_cont = {'column_partition': {'assignments': [0], 'counts': [1], 'hypers': {'alpha': 1.0}}, 'column_hypers': [{'mu': 2.0466076397206323, 's': 0.40834476150565313, 'r': 1.0, 'fixed': 0.0, 'nu': 398.1071705534969}], 'view_state': [{'column_component_suffstats': [[{'sum_x': 8.205354246888788, 'sum_x_squared': 16.833421146868414, 'N': 4.0}, {'sum_x': 85.104360592631, 'sum_x_squared': 172.49753798755182, 'N': 42.0}, {'sum_x': 2.0499065159901946, 'sum_x_squared': 4.202116724299058, 'N': 1.0}, {'sum_x': 35.07094431469411, 'sum_x_squared': 72.35772359127941, 'N': 17.0}, {'sum_x': 2.036911322430709, 'sum_x_squared': 4.14900773544642, 'N': 1.0}, {'sum_x': 8.093437784278695, 'sum_x_squared': 16.37599412889093, 'N': 4.0}, {'sum_x': 2.0427083497348937, 'sum_x_squared': 4.172657402076653, 'N': 1.0}, {'sum_x': 223.86208760230662, 'sum_x_squared': 455.7146707336368, 'N': 110.0}, {'sum_x': 75.95148533155684, 'sum_x_squared': 155.93814739763025, 'N': 37.0}, {'sum_x': 236.25363041362004, 'sum_x_squared': 481.2396036033091, 'N': 116.0}, {'sum_x': 673.1481299770528, 'sum_x_squared': 1466.7369323204234, 'N': 309.0}, {'sum_x': 679.817505232329, 'sum_x_squared': 1291.2720311258447, 'N': 358.0}]], 'row_partition_model': {'counts': [4, 42, 1, 17, 1, 4, 1, 110, 37, 116, 309, 358], 'hypers': {'alpha': 1.9952623149688797}}, 'column_names': [0]}]} 
		self.X_D_cont = [[9, 9, 7, 8, 10, 11, 11, 9, 7, 11, 10, 11, 1, 11, 11, 9, 0, 9, 8, 10, 9, 3, 11, 11, 9, 7, 10, 10, 11, 9, 11, 10, 11, 11, 10, 9, 10, 11, 1, 11, 11, 8, 11, 11, 11, 11, 10, 10, 11, 1, 10, 7, 10, 11, 1, 7, 10, 10, 11, 11, 1, 10, 10, 9, 10, 10, 9, 1, 11, 11, 10, 11, 8, 11, 9, 10, 9, 10, 11, 11, 11, 10, 3, 9, 11, 10, 11, 11, 10, 11, 11, 10, 9, 11, 11, 11, 11, 11, 10, 8, 8, 9, 10, 1, 10, 11, 10, 7, 11, 10, 11, 11, 10, 11, 10, 11, 10, 10, 10, 11, 11, 10, 10, 11, 11, 9, 10, 10, 8, 11, 11, 7, 11, 10, 10, 8, 11, 11, 7, 10, 1, 10, 10, 10, 7, 9, 11, 11, 11, 5, 7, 1, 11, 11, 11, 10, 11, 10, 11, 11, 10, 10, 3, 8, 10, 11, 7, 1, 7, 11, 11, 11, 7, 10, 11, 11, 11, 10, 11, 11, 11, 10, 10, 10, 5, 10, 7, 11, 10, 11, 11, 10, 9, 7, 9, 11, 9, 11, 10, 7, 11, 9, 10, 7, 10, 11, 10, 10, 3, 9, 11, 10, 3, 11, 10, 7, 10, 10, 3, 10, 11, 11, 10, 7, 10, 3, 11, 8, 11, 1, 10, 11, 10, 11, 10, 7, 10, 10, 10, 9, 10, 10, 7, 10, 11, 1, 10, 11, 11, 9, 10, 11, 9, 11, 10, 10, 10, 1, 9, 7, 11, 11, 11, 11, 11, 10, 9, 10, 11, 10, 11, 10, 10, 7, 10, 10, 11, 9, 10, 11, 9, 11, 6, 9, 3, 11, 10, 11, 7, 10, 10, 10, 10, 11, 9, 10, 9, 9, 10, 10, 8, 7, 9, 11, 1, 11, 7, 11, 10, 11, 1, 11, 7, 11, 10, 10, 10, 9, 11, 11, 9, 11, 11, 9, 11, 11, 11, 11, 11, 10, 11, 11, 5, 11, 9, 11, 11, 11, 11, 1, 10, 7, 10, 11, 11, 10, 11, 10, 10, 9, 11, 3, 9, 11, 11, 11, 8, 9, 11, 7, 11, 1, 11, 10, 9, 11, 9, 7, 11, 11, 10, 8, 10, 10, 9, 11, 11, 9, 7, 7, 11, 11, 10, 11, 8, 11, 9, 10, 10, 8, 9, 11, 1, 10, 10, 11, 10, 7, 10, 10, 10, 9, 11, 3, 7, 8, 7, 11, 10, 11, 11, 7, 10, 10, 11, 10, 8, 1, 10, 10, 1, 10, 10, 10, 11, 10, 10, 7, 11, 10, 9, 1, 1, 11, 9, 9, 1, 10, 9, 8, 10, 7, 11, 10, 10, 3, 1, 7, 10, 1, 0, 11, 7, 10, 9, 11, 11, 10, 11, 1, 11, 11, 11, 11, 10, 10, 11, 1, 10, 11, 9, 10, 10, 11, 7, 11, 11, 1, 7, 1, 8, 11, 7, 10, 11, 10, 10, 10, 11, 7, 9, 10, 7, 7, 7, 10, 11, 10, 11, 8, 9, 7, 10, 11, 10, 9, 11, 7, 11, 7, 9, 11, 11, 9, 7, 10, 1, 10, 2, 10, 9, 7, 1, 11, 11, 9, 10, 11, 10, 11, 9, 11, 11, 10, 10, 4, 8, 7, 9, 11, 11, 7, 7, 11, 10, 11, 10, 9, 8, 7, 10, 1, 10, 7, 10, 11, 11, 7, 10, 10, 11, 9, 7, 10, 8, 11, 7, 8, 9, 11, 9, 10, 11, 7, 10, 10, 10, 11, 11, 10, 10, 7, 10, 10, 11, 10, 7, 7, 8, 11, 11, 10, 11, 7, 9, 11, 9, 11, 11, 10, 10, 10, 3, 8, 10, 9, 11, 9, 11, 7, 11, 10, 7, 10, 1, 10, 1, 7, 7, 9, 11, 7, 11, 9, 10, 11, 11, 11, 11, 10, 9, 9, 11, 9, 11, 10, 11, 11, 3, 7, 11, 7, 11, 11, 10, 9, 11, 11, 8, 11, 10, 10, 9, 11, 11, 3, 10, 9, 7, 7, 9, 11, 9, 7, 10, 10, 9, 10, 11, 10, 10, 11, 11, 11, 10, 1, 10, 7, 11, 9, 11, 10, 11, 9, 10, 11, 11, 10, 1, 11, 11, 11, 11, 11, 7, 11, 10, 11, 9, 10, 7, 11, 11, 9, 10, 11, 11, 11, 7, 10, 10, 9, 11, 10, 11, 10, 10, 11, 11, 7, 11, 7, 11, 10, 8, 11, 7, 0, 10, 11, 11, 11, 9, 7, 7, 10, 7, 11, 9, 11, 11, 10, 8, 11, 10, 11, 10, 10, 11, 11, 10, 11, 11, 11, 11, 10, 10, 10, 10, 9, 10, 10, 7, 8, 10, 11, 11, 7, 11, 11, 10, 10, 11, 11, 10, 10, 7, 10, 10, 7, 10, 10, 10, 11, 11, 9, 11, 10, 10, 11, 7, 11, 11, 11, 1, 10, 11, 10, 11, 10, 10, 7, 9, 9, 10, 11, 11, 9, 9, 5, 10, 11, 10, 8, 7, 11, 11, 10, 11, 8, 10, 10, 11, 11, 11, 10, 9, 7, 9, 10, 7, 10, 10, 10, 10, 11, 11, 9, 10, 10, 7, 11, 7, 11, 10, 10, 7, 11, 11, 3, 11, 9, 1, 10, 9, 1, 11, 10, 7, 11, 9, 1, 11, 9, 11, 9, 11, 10, 11, 7, 10, 9, 10, 10, 9, 7, 10, 9, 9, 11, 11, 9, 7, 1, 8, 11, 11, 10, 10, 11, 7, 7, 11, 10, 9, 10, 11, 1, 10, 8, 11, 10, 3, 11, 7, 10, 11, 11, 9, 11, 10, 10, 10, 11, 10, 11, 10, 8, 10, 8, 11, 11, 11, 10, 11, 11, 9, 7, 10, 11, 9, 11, 10, 11, 11, 7, 10, 11, 11, 7, 10, 11, 11, 10, 11, 11, 7, 10, 10, 11, 10, 11, 11, 11, 11, 11, 10, 7, 11, 7, 10, 10, 10, 11, 10, 9, 9, 10, 11, 11, 8, 10, 9, 11, 11, 10, 11, 10, 10, 10, 10, 10, 11, 10, 10, 0, 11, 10, 11, 11, 11, 11, 11, 10, 11, 10, 10, 10, 3, 10]]
		self.M_c_cont = {'idx_to_name': {'0': 0}, 'column_metadata': [{'code_to_value': {}, 'value_to_code': {}, 'modeltype': 'normal_inverse_gamma'}], 'name_to_idx': {0: 0}}
		self.params_cont = [{'mu': 2.0355962328365633, 'rho': 993.706739450366}, {'mu': 1.8962271679941651, 'rho': 948.5904506452995}, {'mu': 2.1747970062713993, 'rho': 953.1358923503657}]
		self.weights_cont = [1.0/3.0]*3

		self.X_L_mult = {'column_partition': {'assignments': [0], 'counts': [1], 'hypers': {'alpha': 1.0}}, 'column_hypers': [{'dirichlet_alpha': 1.0, 'K': 5.0, 'fixed': 0.0}], 'view_state': [{'column_component_suffstats': [[{'1': 214.0, '0': 122.0, '3': 3.0, '2': 20.0, '4': 123.0, 'N': 482.0}, {'1': 8.0, '0': 1.0, '2': 2.0, '4': 1.0, 'N': 12.0}, {'1': 6.0, '0': 7.0, '3': 1.0, '2': 13.0, '4': 43.0, 'N': 70.0}, {'1': 2.0, '0': 104.0, '3': 9.0, '2': 24.0, '4': 49.0, 'N': 188.0}, {'1': 2.0, '0': 24.0, '3': 50.0, '2': 28.0, '4': 33.0, 'N': 137.0}, {'1': 2.0, '0': 26.0, '3': 5.0, '2': 5.0, '4': 9.0, 'N': 47.0}, {'0': 9.0, '3': 5.0, '2': 1.0, '4': 1.0, 'N': 16.0}, {'1': 1.0, '0': 6.0, '2': 8.0, 'N': 15.0}, {'1': 2.0, '0': 7.0, '3': 7.0, '2': 4.0, '4': 3.0, 'N': 23.0}, {'0': 1.0, 'N': 1.0}, {'0': 1.0, '2': 1.0, 'N': 2.0}, {'1': 3.0, '0': 2.0, '3': 1.0, 'N': 6.0}, {'2': 1.0, 'N': 1.0}]], 'row_partition_model': {'counts': [482, 12, 70, 188, 137, 47, 16, 15, 23, 1, 2, 6, 1], 'hypers': {'alpha': 1.5848931924611134}}, 'column_names': [0]}]}
		self.X_D_mult = [[2, 3, 3, 5, 0, 0, 2, 3, 4, 0, 0, 4, 0, 0, 0, 0, 0, 2, 0, 0, 0, 5, 0, 0, 0, 0, 4, 0, 0, 4, 4, 8, 8, 3, 0, 4, 0, 0, 3, 3, 2, 3, 6, 7, 0, 4, 0, 3, 0, 4, 0, 0, 4, 4, 4, 0, 4, 5, 0, 6, 0, 0, 3, 3, 0, 0, 0, 3, 0, 3, 0, 4, 4, 3, 0, 4, 0, 1, 3, 0, 0, 3, 0, 4, 0, 0, 0, 0, 0, 4, 5, 0, 4, 3, 3, 3, 0, 5, 6, 0, 3, 0, 2, 0, 3, 3, 5, 8, 0, 4, 2, 0, 3, 0, 4, 3, 0, 1, 0, 3, 0, 3, 4, 4, 0, 2, 0, 3, 0, 3, 11, 0, 4, 3, 4, 5, 0, 0, 0, 0, 5, 0, 0, 3, 0, 4, 3, 0, 4, 4, 2, 0, 0, 0, 3, 0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 4, 3, 0, 11, 3, 7, 0, 3, 0, 4, 1, 3, 8, 0, 4, 0, 3, 0, 3, 3, 0, 3, 2, 0, 0, 0, 0, 0, 4, 0, 8, 0, 0, 3, 3, 0, 3, 0, 4, 0, 0, 3, 4, 0, 0, 0, 0, 3, 0, 0, 0, 4, 2, 4, 0, 0, 0, 0, 0, 0, 3, 0, 8, 5, 3, 0, 0, 4, 0, 0, 5, 4, 11, 2, 0, 0, 3, 0, 0, 0, 0, 0, 3, 4, 8, 3, 0, 5, 5, 2, 2, 0, 4, 0, 3, 5, 4, 8, 6, 0, 0, 4, 0, 3, 2, 3, 0, 0, 0, 0, 7, 3, 3, 0, 4, 2, 0, 5, 0, 0, 2, 2, 0, 0, 0, 0, 3, 0, 1, 0, 0, 3, 3, 0, 0, 1, 0, 7, 0, 0, 0, 0, 0, 4, 2, 2, 0, 4, 7, 1, 5, 0, 0, 0, 0, 0, 0, 0, 2, 4, 0, 3, 0, 3, 5, 3, 4, 4, 0, 0, 0, 0, 2, 3, 0, 0, 2, 0, 4, 3, 0, 5, 4, 0, 8, 12, 0, 0, 4, 0, 3, 2, 0, 2, 6, 4, 0, 0, 0, 4, 2, 0, 0, 2, 4, 4, 0, 0, 3, 0, 8, 0, 0, 0, 4, 0, 0, 4, 2, 0, 0, 3, 0, 4, 0, 8, 0, 2, 0, 0, 3, 0, 0, 0, 4, 3, 6, 0, 2, 6, 0, 3, 0, 0, 3, 0, 5, 3, 0, 0, 3, 3, 3, 0, 4, 4, 3, 0, 0, 2, 2, 2, 0, 8, 0, 4, 0, 5, 3, 0, 0, 4, 0, 0, 0, 1, 0, 1, 0, 0, 0, 4, 0, 4, 3, 2, 3, 0, 3, 3, 2, 0, 0, 3, 0, 0, 4, 5, 7, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 7, 4, 0, 3, 0, 3, 11, 4, 5, 0, 0, 5, 4, 0, 4, 0, 3, 0, 4, 2, 8, 4, 4, 10, 0, 3, 0, 0, 0, 2, 0, 0, 8, 3, 3, 0, 0, 0, 0, 0, 2, 4, 6, 3, 0, 2, 4, 3, 0, 0, 3, 0, 0, 4, 1, 0, 0, 8, 4, 0, 0, 5, 3, 3, 4, 3, 0, 3, 0, 4, 0, 3, 0, 0, 4, 3, 3, 0, 4, 0, 4, 4, 3, 3, 0, 0, 0, 0, 4, 0, 0, 0, 0, 2, 3, 2, 0, 0, 4, 0, 2, 5, 0, 0, 4, 0, 7, 6, 0, 0, 0, 0, 3, 4, 3, 2, 0, 0, 4, 0, 3, 0, 0, 0, 3, 4, 2, 3, 0, 3, 0, 0, 0, 4, 3, 5, 0, 5, 5, 2, 0, 4, 4, 2, 4, 0, 5, 3, 6, 3, 5, 3, 0, 5, 3, 3, 0, 0, 0, 0, 2, 2, 2, 4, 0, 0, 3, 3, 0, 0, 0, 3, 0, 0, 0, 0, 0, 3, 0, 0, 5, 3, 8, 2, 7, 0, 0, 3, 4, 0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 0, 0, 4, 3, 5, 0, 0, 0, 3, 0, 8, 0, 11, 3, 4, 3, 4, 4, 0, 8, 3, 0, 4, 4, 0, 2, 0, 0, 6, 0, 4, 4, 3, 3, 4, 0, 0, 0, 3, 0, 0, 0, 1, 3, 0, 0, 3, 0, 4, 4, 3, 3, 5, 4, 4, 0, 11, 5, 5, 0, 3, 0, 2, 3, 0, 4, 3, 3, 3, 3, 0, 0, 10, 3, 4, 8, 3, 0, 0, 0, 5, 5, 0, 4, 3, 7, 0, 0, 0, 0, 3, 5, 4, 3, 0, 0, 4, 0, 8, 3, 3, 0, 0, 3, 0, 0, 0, 0, 0, 3, 3, 0, 3, 4, 0, 8, 3, 3, 0, 0, 3, 0, 4, 3, 0, 4, 3, 0, 3, 3, 0, 0, 0, 4, 3, 3, 0, 6, 0, 0, 0, 0, 0, 2, 3, 3, 3, 3, 4, 0, 0, 0, 0, 2, 3, 5, 0, 1, 3, 4, 4, 2, 0, 3, 3, 0, 3, 0, 0, 0, 2, 0, 7, 0, 0, 3, 0, 0, 5, 0, 2, 3, 0, 3, 0, 0, 0, 0, 3, 7, 5, 0, 3, 2, 0, 0, 0, 0, 6, 2, 3, 8, 0, 2, 4, 0, 0, 4, 0, 4, 0, 5, 0, 2, 0, 3, 0, 0, 7, 3, 0, 0, 0, 8, 3, 2, 0, 3, 4, 3, 0, 4, 3, 0, 0, 2, 3, 0, 0, 3, 0, 0, 4, 0, 0, 6, 2, 7, 0, 4, 0, 0, 4, 2, 0, 0, 0, 4, 6, 4, 0, 3, 4, 3, 0, 9, 0, 2, 3, 0, 0, 6, 7, 0, 5, 2, 0, 4, 5, 0, 4, 0, 0, 3, 4, 3, 0, 1, 2, 0, 3, 0, 2, 3, 0, 4, 2, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0, 4, 0, 3, 4, 0, 0, 3, 0, 0, 3, 0, 0, 0, 4, 0, 0, 0]]
		self.M_c_mult = {'idx_to_name': {'0': 0}, 'column_metadata': [{'code_to_value': {0.0: 0, 1.0: 1, 2.0: 2, 3.0: 3, 4.0: 4}, 'value_to_code': {0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0, 4: 4.0}, 'modeltype': 'symmetric_dirichlet_discrete'}], 'name_to_idx': {0: 0}}
		self.params_mult = [{'weights': [0.25, 0.15000000000000002, 0.15000000000000002, 0.05000000000000002, 0.39999999999999997]}, {'weights': [0.44999999999999996, 0.39999999999999997, 1.3877787807814457e-17, 1.3877787807814457e-17, 0.15000000000000002]}, {'weights': [0.2, 0.2, 0.2, 0.2, 0.2]}]
		self.weights_mult = [1.0/3.0]*3		

	def test_should_output_single_float_continuous(self):
		kl = qtu.KL_divergence(ccmext.p_ContinuousComponentModel, 
			self.params_cont, self.weights_cont, self.M_c_cont, 
			self.X_L_cont, self.X_D_cont, n_samples=1000)

		assert isinstance(kl, float)
		assert kl >= 0.0

	def test_should_output_single_float_multinomial(self):
		kl = qtu.KL_divergence(mcmext.p_MultinomialComponentModel, 
			self.params_mult, self.weights_mult, self.M_c_mult, 
			self.X_L_mult, self.X_D_mult)

		assert isinstance(kl, float)
		assert kl >= 0.0


class TestGetMixtureSupport(unittest.TestCase):
	def setUp(self):
		self.params_list_normal = [
			{'mu':0.0, 'rho': 2.0},
			{'mu':3.0, 'rho': 2.0},
			{'mu':-3.0, 'rho': 2.0}
		]

		self.params_list_multinomial = [
			{'weights': [0.5, 0.5, 0.0, 0.0, 0.0]},
			{'weights': [0.0, 0.5, 0.5, 0.0, 0.0]},
			{'weights': [0.0, 0.0, 1.0/3.0, 1.0/3.0, 1.0/3.0]},
		]

	def test_continuous_support_should_return_proper_number_of_bins(self):
		X = qtu.get_mixture_support('continuous', 
			ccmext.p_ContinuousComponentModel,
			self.params_list_normal, nbins=500)

		assert len(X) == 500

		X = qtu.get_mixture_support('continuous', 
			ccmext.p_ContinuousComponentModel,
			self.params_list_normal, nbins=522)

		assert len(X) == 522

	def test_multinomial_support_should_return_proper_number_of_bins(self):
		# support should be range(len(weights))
		X = qtu.get_mixture_support('multinomial', 
			mcmext.p_MultinomialComponentModel,
			self.params_list_multinomial)

		assert len(X) == len(self.params_list_multinomial[0]['weights'])

class TestGetMixturePDF(unittest.TestCase):
	def setUp(self):
		self.X_normal = numpy.array([0, .1 , .2 , .4, -.1, -.2])
		self.X_multinomial = numpy.array(range(5))

		self.params_list_normal = [
			{'mu':0.0, 'rho': 2.0},
			{'mu':3.0, 'rho': 2.0},
			{'mu':-3.0, 'rho': 2.0}
		]

		self.params_list_multinomial = [
			{'weights': [0.5, 0.5, 0.0, 0.0, 0.0]},
			{'weights': [0.0, 0.5, 0.5, 0.0, 0.0]},
			{'weights': [0.0, 0.0, 1.0/3.0, 1.0/3.0, 1.0/3.0]},
		]

		self.component_weights = [1.0/3.0]*3

	def test_should_return_value_for_each_element_in_X_contiuous(self):
		X = qtu.get_mixture_pdf(self.X_normal,
			ccmext.p_ContinuousComponentModel,
			self.params_list_normal, 
			self.component_weights)

		assert len(X) == len(self.X_normal)

	def test_should_return_value_for_each_element_in_X_multinomial(self):
		X = qtu.get_mixture_pdf(self.X_multinomial,
			mcmext.p_MultinomialComponentModel,
			self.params_list_multinomial, 
			self.component_weights)

		assert len(X) == len(self.X_multinomial)

	def test_component_weights_that_do_not_sum_to_1_should_raise_exception(self):
		self.assertRaises(ValueError, qtu.get_mixture_pdf,
			self.X_normal, ccmext.p_ContinuousComponentModel,
			self.params_list_normal, [.1]*3)

	def test_length_component_weights_should_match_length_params_list(self):
		self.assertRaises(ValueError, qtu.get_mixture_pdf,
			self.X_normal, ccmext.p_ContinuousComponentModel,
			self.params_list_normal, [.5]*2)

	def test_params_list_not_list_should_raise_exception(self):
		self.assertRaises(TypeError, qtu.get_mixture_pdf,
			self.X_normal, ccmext.p_ContinuousComponentModel, 
			dict(), self.component_weights)

		self.assertRaises(TypeError, qtu.get_mixture_pdf,
			self.X_normal, ccmext.p_ContinuousComponentModel,
			1.0, self.component_weights)

	def test_component_weights_not_list_should_raise_exception(self):
		self.assertRaises(TypeError, qtu.get_mixture_pdf,
			self.X_normal, ccmext.p_ContinuousComponentModel,
			self.params_list_normal, dict())

		self.assertRaises(TypeError, qtu.get_mixture_pdf,
			self.X_normal, ccmext.p_ContinuousComponentModel,
			self.params_list_normal, 1.0)

class TestBincount(unittest.TestCase):
	def test_X_not_list_should_raise_exception(self):
		X = dict()
		self.assertRaises(TypeError, qtu.bincount, X)

		X = 2
		self.assertRaises(TypeError, qtu.bincount, X)

	def test_X_not_vector_should_raise_exception(self):
		X = numpy.zeros((2,2))
		self.assertRaises(ValueError, qtu.bincount, X)

	def test_bins_not_list_should_raise_exception(self):
		X = range(10)
		bins = dict()
		self.assertRaises(TypeError, qtu.bincount, X, bins=bins)

		bins = 12
		self.assertRaises(TypeError, qtu.bincount, X, bins=bins)

		bins = numpy.zeros(10)
		self.assertRaises(TypeError, qtu.bincount, X, bins=bins)

	def test_behavior_X_list(self):
		X = [0, 1, 2, 3]
		counts = qtu.bincount(X)
		assert counts == [1, 1, 1, 1]

		X = [1, 2, 2, 4, 6]
		counts = qtu.bincount(X)
		assert counts == [1, 2, 0, 1, 0, 1]

		bins = range(7)
		counts = qtu.bincount(X,bins)
		assert counts == [0, 1, 2, 0, 1, 0, 1]

		bins = [1,2,4,6]
		counts = qtu.bincount(X,bins)
		assert counts == [1, 2, 1, 1]

	def test_behavior_X_array(self):
		X = numpy.array([0, 1, 2, 3])
		counts = qtu.bincount(X)
		assert counts == [1, 1, 1, 1]

		X = numpy.array([1, 2, 2, 4, 6])
		counts = qtu.bincount(X)
		assert counts == [1, 2, 0, 1, 0, 1]

		bins = range(7)
		counts = qtu.bincount(X,bins)
		assert counts == [0, 1, 2, 0, 1, 0, 1]

		bins = [1,2,4,6]
		counts = qtu.bincount(X,bins)
		assert counts == [1, 2, 1, 1]

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = test_synthetic_data_generator
import crosscat.tests.quality_tests.synthetic_data_generator as sdg
import crosscat.cython_code.State as State
import crosscat.utils.data_utils as du

import unittest
import random
import numpy

def main():
    unittest.main()


class TestPredictiveColumns(unittest.TestCase):
	def setUp(self):
		# generate a crosscat state and pull the metadata
		gen_seed = 0
		num_clusters = 2
		self.num_rows = 10
		self.num_cols = 2
		num_splits = 1

		self.T, self.M_r, self.M_c = du.gen_factorial_data_objects(gen_seed,
							   num_clusters, self.num_cols, 
							   self.num_rows, num_splits)

		state = State.p_State(self.M_c, self.T)
		self.X_L = state.get_X_L()
		self.X_D = state.get_X_D()

	def test_should_return_array_of_proper_size(self):
		columns_list = [0]
		X = sdg.predictive_columns(self.M_c, self.X_L, self.X_D, columns_list)
		assert isinstance(X, numpy.ndarray)
		assert X.shape[0] == self.num_rows
		assert X.shape[1] == len(columns_list)

		columns_list = [0,1]
		X = sdg.predictive_columns(self.M_c, self.X_L, self.X_D, columns_list)
		assert isinstance(X, numpy.ndarray)
		assert X.shape[0] == self.num_rows
		assert X.shape[1] == len(columns_list)

	def test_should_not_generate_data_from_invalid_rows(self):
		columns_list = [0,-1]
		self.assertRaises(ValueError, sdg.predictive_columns, 
			self.M_c, self.X_L, self.X_D, columns_list)

		columns_list = [0,3]
		self.assertRaises(ValueError, sdg.predictive_columns, 
			self.M_c, self.X_L, self.X_D, columns_list)

	def test_should_have_nan_entries_if_specified(self):
		# for one column
		columns_list = [0]
		optargs = [dict(missing_data=1.0)] # every entry will be missing NaN
		X = sdg.predictive_columns(self.M_c, self.X_L, self.X_D, columns_list,
			optional_settings=optargs)

		assert numpy.all(numpy.isnan(X))
		
		# for two columns
		columns_list = [0,1]
		optargs = [dict(missing_data=1.0)]*2 
		X = sdg.predictive_columns(self.M_c, self.X_L, self.X_D, columns_list,
			optional_settings=optargs)

		assert numpy.all(numpy.isnan(X))

		# for one of two columns (no dict means no missing data)
		columns_list = [0,1]
		optargs = [dict(missing_data=1.0), None]
		X = sdg.predictive_columns(self.M_c, self.X_L, self.X_D, columns_list,
			optional_settings=optargs)

		assert numpy.all(numpy.isnan(X[:,0]))
		assert not numpy.any(numpy.isnan(X[:,1]))

		# for one of two columns. Missing data specified 0 for second column
		columns_list = [0,1]
		optargs = [dict(missing_data=1.0), dict(missing_data=0.0)]
		X = sdg.predictive_columns(self.M_c, self.X_L, self.X_D, columns_list,
			optional_settings=optargs)

		assert numpy.all(numpy.isnan(X[:,0]))
		assert not numpy.any(numpy.isnan(X[:,1]))

class TestGenerateGeparatedGodelParameters(unittest.TestCase):
	def setUp(self):
		self.num_clusters = 5
		self.get_next_seed = lambda : random.randrange(32000)
		self.distargs_multinomial = dict(K=5)
		random.seed(0)

	def test_should_return_list_of_params(self):
		ret = sdg.generate_separated_model_parameters('continuous',
			.5, self.num_clusters, self.get_next_seed )

		assert isinstance(ret, list)
		assert len(ret) == self.num_clusters
		for entry in ret:
			assert isinstance(entry, dict)
			for key in entry.keys():
				assert key in ['mu', 'rho']

			assert len(entry.keys()) == 2

		ret = sdg.generate_separated_model_parameters('multinomial',
			.5, self.num_clusters, self.get_next_seed,
			distargs=self.distargs_multinomial)

		assert isinstance(ret, list)
		assert len(ret) == self.num_clusters
		for entry in ret:
			assert isinstance(entry, dict)
			for key in entry.keys():
				assert key in ['weights']

			assert len(entry.keys()) == 1

	def tests_should_not_accept_invalid_cctype(self):
		# peanut is an invalid cctype
		self.assertRaises(ValueError, sdg.generate_separated_model_parameters,
			'peanut', .5, self.num_clusters, self.get_next_seed)

	def test_normal_means_should_be_farther_apart_if_they_have_higer_separation(self):
		random.seed(0)	
		closer = sdg.generate_separated_model_parameters('continuous',
			.1, 2, self.get_next_seed )

		sum_std_close = closer[0]['rho']**(-.5) + closer[1]['rho']**(-.5)
		distance_close = ((closer[0]['mu']-closer[1]['mu'])/sum_std_close)**2.0

		random.seed(0)
		farther = sdg.generate_separated_model_parameters('continuous',
			.5, 2, self.get_next_seed )

		sum_std_far = farther[0]['rho']**(-.5) + farther[1]['rho']**(-.5)
		distance_far = ((farther[0]['mu']-farther[1]['mu'])/sum_std_far)**2.0

		random.seed(0)
		farthest = sdg.generate_separated_model_parameters('continuous',
			1.0, 2, self.get_next_seed )

		sum_std_farthest = farthest[0]['rho']**(-.5) + farthest[1]['rho']**(-.5)
		distance_farthest = ((farthest[0]['mu']-farthest[1]['mu'])/sum_std_farthest)**2.0

		assert distance_far  > distance_close
		assert distance_farthest  > distance_far


class TestsGenerateSeparatedMultinomialWeights(unittest.TestCase):
	def setUp(self):
		self.A_good = [.2]*5
		self.C_good = .5

	def tests_should_return_proper_list(self):
		w = sdg.generate_separated_multinomial_weights(self.A_good,self.C_good)
		assert isinstance(w, list)
		assert len(w) == len(self.A_good)

	def tests_bad_separation_should_raise_exception(self):
		# C is too low
		self.assertRaises(ValueError, sdg.generate_separated_multinomial_weights,
			self.A_good, -.1)
		# C is too high
		self.assertRaises(ValueError, sdg.generate_separated_multinomial_weights,
			self.A_good, 1.2)

	def tests_bad_weights_should_raise_exception(self):
		# weights do not sum to 1
		self.assertRaises(ValueError, sdg.generate_separated_multinomial_weights,
			[.2]*4, .5)

class TestSyntheticDataGenerator(unittest.TestCase):
	def setUp(self):
		self.cctypes_all_contiuous = ['continuous']*5
		self.cctypes_all_multinomial = ['multinomial']*5
		self.cctypes_mixed = ['continuous','continuous','multinomial','continuous','multinomial']
		self.cctypes_wrong_type = dict()

		self.n_rows = 10;

		self.cols_to_views_good = [0, 0, 1, 2, 1]
		self.cols_to_views_bad_start_index = [3, 3, 1, 2, 1]
		self.cols_to_views_skip_value = [0, 0, 1, 3, 1]
		self.cols_to_views_wrong_type = dict()

		self.cluster_weights_good = [[.2, .2, .6],[.5, .5],[.8, .2]]
		self.cluster_weights_missing_view = [[.2, .2, .6],[.8, .2]]
		self.cluster_weights_bad_sum = [[.2, .2, .6],[.1, .5],[.8, .2]]
		self.cluster_weights_wrong_type = dict()

		self.separation_good = [.4, .5, .9];
		self.separation_out_of_range_low = [-1, .5, .9];
		self.separation_out_of_range_high = [1.5, .5, .9];
		self.separation_wrong_number_views = [.5, .9];
		self.separation_wrong_type = dict();


	def test_same_seeds_should_produce_the_same_data(self):
		distargs = [None]*5
		T1, M_c = sdg.gen_data(self.cctypes_all_contiuous,
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_good,
			self.separation_good,
			seed=0,
			distargs=distargs)

		T2, M_c = sdg.gen_data(self.cctypes_all_contiuous,
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_good,
			self.separation_good,
			seed=0,
			distargs=distargs)

		A1 = numpy.array(T1)
		A2 = numpy.array(T2)

		assert numpy.all(A1==A2)

	def test_different_seeds_should_produce_the_different_data(self):
		distargs = [None]*5
		T1, M_c = sdg.gen_data(self.cctypes_all_contiuous,
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_good,
			self.separation_good,
			seed=0,
			distargs=distargs)

		T2, M_c = sdg.gen_data(self.cctypes_all_contiuous,
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_good,
			self.separation_good,
			seed=12345,
			distargs=distargs)

		A1 = numpy.array(T1)
		A2 = numpy.array(T2)
		
		assert not numpy.all(A1==A2)

	def test_proper_set_up_all_continuous(self):
		T, M_c = sdg.gen_data(self.cctypes_all_contiuous,
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_good,
			self.separation_good,
			seed=0,
			distargs=None)

		assert(len(T) == self.n_rows)
		assert(len(T[0]) == len(self.cols_to_views_good))

	def test_proper_set_up_all_multinomial(self):
		distargs = [dict(K=5), dict(K=5), dict(K=5), dict(K=5), dict(K=5)]
		T, M_c = sdg.gen_data(self.cctypes_all_multinomial,
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_good,
			self.separation_good,
			seed=0,
			distargs=distargs)

		assert(len(T) == self.n_rows)
		assert(len(T[0]) == len(self.cols_to_views_good))

	def test_proper_set_up_mixed(self):
		distargs = [ None, None, dict(K=5), None, dict(K=5)]
		T, M_c = sdg.gen_data(self.cctypes_mixed,
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_good,
			self.separation_good,
			seed=0,
			distargs=distargs)

		assert(len(T) == self.n_rows)
		assert(len(T[0]) == len(self.cols_to_views_good))

	def test_bad_cctypes_should_raise_exception(self):
		# wrong type (dict)
		self.assertRaises(TypeError, sdg.gen_data,
			dict(),
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_good,
			self.separation_good,
			seed=0,
			distargs=None)

		# empty list
		self.assertRaises(ValueError, sdg.gen_data,
			[],
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_good,
			self.separation_good,
			seed=0,
			distargs=None)

		# invalid cctype (peanut)
		self.assertRaises(ValueError, sdg.gen_data,
			['continuous','continuous','continuous','continuous','peanut'],
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_good,
			self.separation_good,
			seed=0,
			distargs=None)

		# number of columns too low (should be 5)
		self.assertRaises(ValueError, sdg.gen_data,
			['continuous']*4,
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_good,
			self.separation_good,
			seed=0,
			distargs=None)

		# number of columns too high (should be 5)
		self.assertRaises(ValueError, sdg.gen_data,
			['continuous']*6,
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_good,
			self.separation_good,
			seed=0,
			distargs=None)

	def test_bad_cols_to_views_should_raise_exception(self):
		# start index with 1 instead of 0
		self.assertRaises(ValueError, sdg.gen_data,
			self.cctypes_all_contiuous,
			self.n_rows,
			self.cols_to_views_bad_start_index,
			self.cluster_weights_good,
			self.separation_good,
			seed=0,
			distargs=None)

		# skip indices
		self.assertRaises(ValueError, sdg.gen_data,
			self.cctypes_all_contiuous,
			self.n_rows,
			self.cols_to_views_skip_value,
			self.cluster_weights_good,
			self.separation_good,
			seed=0,
			distargs=None)

		# give a dict instead of a list
		self.assertRaises(TypeError, sdg.gen_data,
			self.cctypes_all_contiuous,
			self.n_rows,
			self.cols_to_views_wrong_type,
			self.cluster_weights_good,
			self.separation_good,
			seed=0,
			distargs=None)

	def test_bad_cluster_weights_should_raise_exception(self):
		# number of views is too low
		self.assertRaises(ValueError, sdg.gen_data,
			self.cctypes_all_contiuous,
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_missing_view,
			self.separation_good,
			seed=0,
			distargs=None)

		# cluster weights do not sum to 1
		self.assertRaises(ValueError, sdg.gen_data,
			self.cctypes_all_contiuous,
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_bad_sum,
			self.separation_good,
			seed=0,
			distargs=None)

		# dict instead of list of lists
		self.assertRaises(TypeError, sdg.gen_data,
			self.cctypes_all_contiuous,
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_wrong_type,
			self.separation_good,
			seed=0,
			distargs=None)

	def test_bad_separation_should_raise_exception(self):
		self.assertRaises(ValueError, sdg.gen_data,
			self.cctypes_all_contiuous,
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_good,
			self.separation_out_of_range_low,
			seed=0,
			distargs=None)

		self.assertRaises(ValueError, sdg.gen_data,
			self.cctypes_all_contiuous,
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_good,
			self.separation_out_of_range_high,
			seed=0,
			distargs=None)

		self.assertRaises(ValueError, sdg.gen_data,
			self.cctypes_all_contiuous,
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_good,
			self.separation_wrong_number_views,
			seed=0,
			distargs=None)

		self.assertRaises(TypeError, sdg.gen_data,
			self.cctypes_all_contiuous,
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_good,
			self.separation_wrong_type,
			seed=0,
			distargs=None)

	def test_bad_distargs_should_raise_exception(self):
		# wrong type
		self.assertRaises(TypeError, sdg.gen_data,
			self.cctypes_all_contiuous,
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_good,
			self.separation_good,
			seed=0,
			distargs=10)

		# wrong number of entries
		self.assertRaises(ValueError, sdg.gen_data,
			self.cctypes_all_contiuous,
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_good,
			self.separation_good,
			seed=0,
			distargs=[None]*4)

		# wrong entry type
		self.assertRaises(ValueError, sdg.gen_data,
			self.cctypes_all_contiuous,
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_good,
			self.separation_good,
			seed=0,
			distargs=[dict(K=5)]*5)

		# wrong entry type
		self.assertRaises(TypeError, sdg.gen_data,
			self.cctypes_all_multinomial,
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_good,
			self.separation_good,
			seed=0,
			distargs=[None]*5)

		# wrong dict entry for multinomial
		self.assertRaises(KeyError, sdg.gen_data,
			self.cctypes_all_multinomial,
			self.n_rows,
			self.cols_to_views_good,
			self.cluster_weights_good,
			self.separation_good,
			seed=0,
			distargs=[dict(P=12)]*5)


if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = automated_runtime_tests
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import os
import csv
import argparse
import tempfile
import time
from collections import namedtuple
import itertools
#
import numpy
#
import crosscat.utils.data_utils as du
import crosscat.utils.file_utils as fu
import crosscat.utils.hadoop_utils as hu
import crosscat.utils.xnet_utils as xu
import crosscat.LocalEngine as LE
import crosscat.HadoopEngine as HE
import crosscat.settings as S
import crosscat.cython_code.State as State
import parse_timing

def generate_hadoop_dicts(which_kernels, timing_run_parameters, args_dict):
    for which_kernel in which_kernels:
        kernel_list = (which_kernel, )
        dict_to_write = dict(timing_run_parameters)
        dict_to_write.update(args_dict)
        # must write kernel_list after update
        dict_to_write['kernel_list'] = kernel_list
        yield dict_to_write

def write_hadoop_input(input_filename, timing_run_parameters, n_steps, SEED):
    # prep settings dictionary
    time_analyze_args_dict = xu.default_analyze_args_dict
    time_analyze_args_dict['command'] = 'time_analyze'
    time_analyze_args_dict['SEED'] = SEED
    time_analyze_args_dict['n_steps'] = n_steps
    # one kernel per line
    all_kernels = State.transition_name_to_method_name_and_args.keys()
    with open(input_filename, 'a') as out_fh:
        dict_generator = generate_hadoop_dicts(all_kernels,timing_run_parameters, time_analyze_args_dict)
        for dict_to_write in dict_generator:
            xu.write_hadoop_line(out_fh, key=dict_to_write['SEED'], dict_to_write=dict_to_write)

def find_regression_coeff(filename, parameter_list, regression_file='daily_regression_coeffs.csv'):

    # Find regression coefficients from the times stored in the parsed csv files
    num_cols = 20
    # Read the csv file
    with open(filename) as fh:
        csv_reader = csv.reader(fh)
        header = csv_reader.next()[:num_cols]
        timing_rows = [row[:num_cols] for row in csv_reader]

    
    num_rows_list = parameter_list[0]
    num_cols_list = parameter_list[1]
    num_clusters_list = parameter_list[2]
    num_views_list = parameter_list[3]


    # Compute regression coefficients over all kernels
    all_kernels = State.transition_name_to_method_name_and_args.keys()
    
    with open(regression_file, 'a') as outfile:
         csvwriter=csv.writer(outfile,delimiter=',')
         
         for kernelindx in range(len(all_kernels)):
             curr_kernel = all_kernels[kernelindx]
             curr_timing_rows = [timing_rows[tmp] for tmp in range(len(timing_rows)) if timing_rows[tmp][5] == curr_kernel]
             # Iterate over the parameter values and finding matching indices in the timing data
             take_product_of = [num_rows_list, num_cols_list, num_clusters_list, num_views_list]
             count = -1
             a_list = []
             b_list = []
             #a_matrix = numpy.ones((len(num_rows_list)*len(num_cols_list)*len(num_clusters_list)*len(num_views_list), 5))
             #b_matrix = numpy.zeros((len(num_rows_list)*len(num_cols_list)*len(num_clusters_list)*len(num_views_list), 1))

             times_only = numpy.asarray([float(curr_timing_rows[i][4]) for i in range(len(curr_timing_rows))])
 
             
             for num_rows, num_cols, num_clusters, num_views in itertools.product(*take_product_of):
                 matchlist = [i for i in range(len(curr_timing_rows)) if curr_timing_rows[i][0] == str(num_rows) and \
                                  curr_timing_rows[i][1]== str(num_cols) and \
                                  curr_timing_rows[i][2]== str(num_clusters) and \
                                  curr_timing_rows[i][3]== str(num_views)]
                 if matchlist != []:
                     for matchindx in range(len(matchlist)):
                         a_list.append([1, num_rows, num_cols*num_clusters, num_rows*num_cols*num_clusters, num_views*num_rows*num_cols])
                         b_list.append(times_only[matchlist[matchindx]])

             a_matrix = numpy.asarray(a_list)
             b_matrix = numpy.asarray(b_list)
             
             x, j1, j2, j3 = numpy.linalg.lstsq(a_matrix,b_matrix)
             csvwriter.writerow([time.ctime(), curr_kernel, x[0], x[1], x[2], x[3], x[4]])
   

if __name__ == '__main__':
    default_num_rows_list = [100, 400, 1000, 4000, 10000]
    default_num_cols_list = [4, 8, 16, 24, 32]
    default_num_clusters_list = [10, 20, 40, 50]
    default_num_splits_list = [2, 3, 4]
    #
    parser = argparse.ArgumentParser()
    parser.add_argument('--gen_seed', type=int, default=0)
    parser.add_argument('--n_steps', type=int, default=10)
    parser.add_argument('--which_engine_binary', type=str,
            default=S.Hadoop.default_engine_binary)
    parser.add_argument('-do_local', action='store_true')
    parser.add_argument('-do_remote', action='store_true')
    parser.add_argument('--num_rows_list', type=int, nargs='*',
            default=default_num_rows_list)
    parser.add_argument('--num_cols_list', type=int, nargs='*',
            default=default_num_cols_list)
    parser.add_argument('--num_clusters_list', type=int, nargs='*',
            default=default_num_clusters_list)
    parser.add_argument('--num_splits_list', type=int, nargs='*',
            default=default_num_splits_list)
    #
    args = parser.parse_args()
    gen_seed = args.gen_seed
    n_steps = args.n_steps
    do_local = args.do_local
    do_remote = args.do_remote
    num_rows_list = args.num_rows_list
    num_cols_list = args.num_cols_list
    num_clusters_list = args.num_clusters_list
    num_splits_list = args.num_splits_list
    which_engine_binary = args.which_engine_binary
    #
    print 'using num_rows_list: %s' % num_rows_list
    print 'using num_cols_list: %s' % num_cols_list
    print 'using num_clusters_list: %s' % num_clusters_list
    print 'using num_splits_list: %s' % num_splits_list
    print 'using engine_binary: %s' % which_engine_binary
    time.sleep(2)


    script_filename = 'hadoop_line_processor.py'
    # some hadoop processing related settings
    dirname = 'runtime_analysis'
    fu.ensure_dir(dirname)
    temp_dir = tempfile.mkdtemp(prefix='runtime_analysis_',
                                dir=dirname)
    print 'using dir: %s' % temp_dir
    #
    table_data_filename = os.path.join(temp_dir, 'table_data.pkl.gz')
    input_filename = os.path.join(temp_dir, 'hadoop_input')
    output_filename = os.path.join(temp_dir, 'hadoop_output')
    output_path = os.path.join(temp_dir, 'output')  
    parsed_out_file = os.path.join(temp_dir, 'parsed_output.csv')

    # Hard code the parameter values for now

    parameter_list = [num_rows_list, num_cols_list, num_clusters_list, num_splits_list]

    # Iterate over the parameter values and write each run as a line in the hadoop_input file
    take_product_of = [num_rows_list, num_cols_list, num_clusters_list, num_splits_list]
    for num_rows, num_cols, num_clusters, num_splits \
            in itertools.product(*take_product_of):
        if numpy.mod(num_rows, num_clusters) == 0 and numpy.mod(num_cols,num_splits)==0:
          timing_run_parameters = dict(num_rows=num_rows, num_cols=num_cols, num_views=num_splits, num_clusters=num_clusters)
          write_hadoop_input(input_filename, timing_run_parameters,  n_steps, SEED=gen_seed)

    n_tasks = len(num_rows_list)*len(num_cols_list)*len(num_clusters_list)*len(num_splits_list)*5
    # Create a dummy table data file
    table_data=dict(T=[],M_c=[],X_L=[],X_D=[])
    fu.pickle(table_data, table_data_filename)

    if do_local:
        xu.run_script_local(input_filename, script_filename, output_filename, table_data_filename)
        print 'Local Engine for automated timing runs has not been completely implemented/tested'
    elif do_remote:
        hadoop_engine = HE.HadoopEngine(which_engine_binary=which_engine_binary,
                output_path=output_path,
                input_filename=input_filename,
                table_data_filename=table_data_filename)
        xu.write_support_files(table_data, hadoop_engine.table_data_filename,
                              dict(command='time_analyze'), hadoop_engine.command_dict_filename)
        hadoop_engine.send_hadoop_command(n_tasks=n_tasks)
        was_successful = hadoop_engine.get_hadoop_results()
        if was_successful:
            hu.copy_hadoop_output(hadoop_engine.output_path, output_filename)
            parse_timing.parse_timing_to_csv(output_filename, outfile=parsed_out_file)
            coeff_list = find_regression_coeff(parsed_out_file, parameter_list)

        else:
            print 'remote hadoop job NOT successful'
    else:
        # print what the command would be
        hadoop_engine = HE.HadoopEngine(which_engine_binary=which_engine_binary,
                output_path=output_path,
                input_filename=input_filename,
                table_data_filename=table_data_filename)
        cmd_str = hu.create_hadoop_cmd_str(
                hadoop_engine.hdfs_uri, hadoop_engine.hdfs_dir, hadoop_engine.jobtracker_uri,
                hadoop_engine.which_engine_binary, hadoop_engine.which_hadoop_binary,
                hadoop_engine.which_hadoop_jar,
                hadoop_engine.input_filename, hadoop_engine.table_data_filename,
                hadoop_engine.command_dict_filename, hadoop_engine.output_path,
                n_tasks, hadoop_engine.one_map_task_per_line)
        print cmd_str

########NEW FILE########
__FILENAME__ = compare_timings
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import os
import csv
import collections


def timing_row_to_config_and_runtime(header, row):
    row_dict = dict(zip(header,row))
    config_tuple = tuple([
            row_dict[column_name]
            for column_name in config_column_names
            ])
    which_kernel = row_dict['which_kernel']
    runtime = float(row_dict['time_per_step'])
    return (config_tuple, which_kernel), runtime

def reparse_parsed_timing_csv(filename):
    with open(filename) as fh:
        csv_reader = csv.reader(fh)
        header = csv_reader.next()
        reparsed_dict = dict(
                timing_row_to_config_and_runtime(header, row)
                for row in csv_reader
                )
    return reparsed_dict

def filter_dict(in_dict, key_filter):
    out_dict = dict()
    for key, value in in_dict.iteritems():
        if key_filter(key):
            out_dict[key] = value
    return out_dict

def get_config(key):
    return key[0]

def get_which_kernel(key):
    return key[1]

def get_config_filter(column_name, filter_func):
    which_index = config_column_names.index(column_name)
    return lambda key: filter_func(get_config(key)[which_index])

def get_key_intersect_dict(dict_1, dict_2):
    intersect_keys = set(dict_1.keys()).intersection(dict_2)
    intersect_dict = dict(
            (key, (dict_1[key], dict_2[key]))
            for key in intersect_keys
            )
    return intersect_dict

def get_complete_configs_dict(in_dict):
    config_kernel_counter = collections.Counter(map(get_config, in_dict.keys()))
    complete_configs = set([
            config
            for config, count in config_kernel_counter.iteritems()
            if count == 5
            ])
    is_complete_config = lambda key: get_config(key) in complete_configs
    complete_configs_dict = filter_dict(in_dict, is_complete_config)
    return complete_configs_dict

timing_div = lambda timing_tuple: timing_tuple[0] / timing_tuple[1]
get_4_digits_str = lambda el: '%.4f' % el

config_column_names = ['num_rows', 'num_cols', 'num_clusters', 'num_views']
which_kernels = ['row_partition_hyperparameters',
    'column_partition_hyperparameter',
    'column_partition_assignments',
    'row_partition_assignments',
    'column_hyperparameters',
    ]


if __name__ == '__main__':
    import argparse
    #
    parser = argparse.ArgumentParser()
    parser.add_argument('timing_filename_1', type=str)
    parser.add_argument('timing_filename_2', type=str)
    args = parser.parse_args()
    #
    timing_filename_1 = args.timing_filename_1
    timing_filename_2 = args.timing_filename_2
#    timing_filename_1 = 'Work/runtime_analysis_W_Y10u_parsed_output.csv'
#    timing_filename_2 = 'Work/runtime_analysis_v96OCK_parsed_output.csv'
    assert(os.path.isfile(timing_filename_1))
    assert(os.path.isfile(timing_filename_2))

    reparsed_dict_1 = reparse_parsed_timing_csv(timing_filename_1)
    reparsed_dict_2 = reparse_parsed_timing_csv(timing_filename_2)
    intersect_dict = get_key_intersect_dict(reparsed_dict_1, reparsed_dict_2)
    complete_configs_dict = get_complete_configs_dict(intersect_dict)
    #
    for which_kernel in which_kernels:
        comparison_dict = complete_configs_dict.copy()
        which_filters = [
                get_config_filter('num_rows', lambda config: int(config) >= 1000),
                get_config_filter('num_cols', lambda config: int(config) >= 32),
                lambda key: get_which_kernel(key) == which_kernel,
                ]
        for which_filter in which_filters:
            comparison_dict = filter_dict(comparison_dict, which_filter)
        cmp_timing_tuples = lambda tuple1, tuple2: \
            cmp(tuple1[1], tuple2[1])
        for key, value in sorted(comparison_dict.iteritems(), cmp=cmp_timing_tuples):
            time_tuple = map(get_4_digits_str, value)
            print key, time_tuple, get_4_digits_str(timing_div(value))

########NEW FILE########
__FILENAME__ = generate_runtime_script
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import itertools


n_steps = 10
#
base_str = ' '.join([
  'python runtime_scripting.py',
  '--num_rows %s',
  '--num_cols %s',
  '--num_clusters %s',
  '--num_splits %s',
  '--n_steps %s' % n_steps,
  '-do_local >>out 2>>err &',
  ])

# num_rows_list = [100, 400, 1000, 4000, 10000]
# num_cols_list = [4, 8, 16, 24, 32]
# num_clusters_list = [10, 20, 30, 40, 50]
# num_splits_list = [1, 2, 3, 4, 5]

num_rows_list = [100, 400]
num_cols_list = [4, 16]
num_clusters_list = [10, 20]
num_splits_list = [1, 2]

take_product_of = [num_rows_list, num_cols_list, num_clusters_list, num_splits_list]
for num_rows, num_cols, num_clusters, num_splits \
    in itertools.product(*take_product_of):
  this_base_str = base_str % (num_rows, num_cols, num_clusters, num_splits)
  print this_base_str

########NEW FILE########
__FILENAME__ = parse_timing
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import sys
import csv
import os
#
import numpy
#
import crosscat.utils.xnet_utils as xu


def assert_row_clustering_count_same(row_cluster_counts):
    baseline = numpy.array(row_cluster_counts[0])
    for row_cluster_count in row_cluster_counts[1:]:
        row_cluster_count = numpy.array(row_cluster_count)
        assert all(baseline==row_cluster_count)
    return

def assert_dims_same(start_dims, end_dims):
    start_num_views = start_dims[0]
    end_num_views = end_dims[0]
    assert start_num_views == end_num_views
    #
    start_row_clustering = numpy.array(start_dims[1])
    end_row_clustering = numpy.array(end_dims[1])
    assert (start_row_clustering == end_row_clustering).all()
    return

def parse_reduced_dims(reduced_line):
    start_dims = reduced_line['start_dims']
    end_dims = reduced_line['end_dims']
    start_row_cluster_counts = start_dims[1]
    assert_row_clustering_count_same(start_row_cluster_counts)
    assert_dims_same(start_dims, end_dims)
    #
    start_num_views = start_dims[0]
    start_num_clusters = len(start_dims[1][0])
    return start_num_clusters, start_num_views

def parse_reduced_line(reduced_line):
    num_clusters, num_views = parse_reduced_dims(reduced_line)
    (num_rows, num_cols) = reduced_line['table_shape']
    kernel_list = reduced_line['kernel_list']
    assert len(kernel_list) == 1
    which_kernel = kernel_list[0]
    time_per_step = reduced_line['elapsed_secs'] / reduced_line['n_steps']
    return num_rows, num_cols, num_clusters, num_views, \
        time_per_step, which_kernel

def parse_timing_to_csv(filename, outfile='parsed_timing.csv'):
   #drive, path = os.path.splitdrive(filename)
   #outpath, file_nameonly = os.path.split(path)

   with open(filename) as fh:
        lines = []
        for line in fh:
            lines.append(xu.parse_hadoop_line(line))

   header = ['num_rows', 'num_cols', 'num_clusters', 'num_views', 'time_per_step', 'which_kernel']
   
   reduced_lines = map(lambda x: x[1], lines)
      
   with open(outfile,'w') as csvfile:
	csvwriter = csv.writer(csvfile,delimiter=',')
	csvwriter.writerow(header)
    	for reduced_line in reduced_lines:
            try:
            	parsed_line = parse_reduced_line(reduced_line)
	    	csvwriter.writerow(parsed_line)
            except Exception, e:
                pass


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', type=str)
    args = parser.parse_args()
    filename = args.filename

    with open(filename) as fh:
        lines = []
        for line in fh:
            lines.append(xu.parse_hadoop_line(line))

    header = 'num_rows,num_cols,num_clusters,num_views,time_per_step,which_kernel'
    print header
    reduced_lines = map(lambda x: x[1], lines)
    for reduced_line in reduced_lines:
        try:
            parsed_line = parse_reduced_line(reduced_line)
            print ','.join(map(str, parsed_line))
        except Exception, e:
            pass


########NEW FILE########
__FILENAME__ = plot_parsed_output
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import argparse
from collections import namedtuple
from collections import defaultdict
from collections import Counter
#
import pylab
#
import crosscat.utils.data_utils as du
import crosscat.utils.plot_utils as pu


get_time_per_step = lambda timing_row: float(timing_row.time_per_step)
get_num_rows = lambda timing_row: timing_row.num_rows
get_num_cols = lambda timing_row: timing_row.num_cols
get_num_views = lambda timing_row: timing_row.num_views
get_num_clusters = lambda timing_row: timing_row.num_clusters
do_strip = lambda string: string.strip()
#
def parse_timing_file(filename):
    header, rows = du.read_csv(filename)
    _timing_row = namedtuple('timing_row', ' '.join(header))
    timing_rows = []
    for row in rows:
        row = map(do_strip, row)
        timing_row = _timing_row(*row)
        timing_rows.append(timing_row)
    return timing_rows

def group_results(timing_rows, get_fixed_parameters, get_variable_parameter):
    dict_of_dicts = defaultdict(dict)
    for timing_row in these_timing_rows:
        fixed_parameters = get_fixed_parameters(timing_row)
        variable_parameter = get_variable_parameter(timing_row)
        dict_of_dicts[fixed_parameters][variable_parameter] = timing_row
    return dict_of_dicts

num_cols_to_color = {'4':'b', '16':'r', '32':'m', '64':'g', '128':'c', '256':'k'}
num_rows_to_color = {'100':'b', '400':'r', '1000':'m', '4000':'y', '10000':'g'}
num_clusters_to_marker = {'10':'x', '20':'o', '40':'s', '50':'v'}
num_views_to_marker = {'1':'x', '2':'o', '4':'v'}
num_rows_to_marker = {'100':'x', '400':'o', '1000':'v', '4000':'1', '10000':'*'}
num_cols_to_marker = {'4':'x', '16':'o', '32':'v', '64':'1', '128':'*',
    '256':'s'}
#
plot_parameter_lookup = dict(
    rows=dict(
        vary_what='rows',
        which_kernel='row_partition_assignments',
        get_fixed_parameters=lambda timing_row: 'Co=%s;Cl=%s;V=%s' % \
            (timing_row.num_cols, timing_row.num_clusters,
             timing_row.num_views),
        get_variable_parameter=get_num_rows,
        get_color_parameter=get_num_cols,
        color_dict=num_cols_to_color,
        color_label_prepend='#Col=',
        get_marker_parameter=get_num_clusters,
        marker_dict=num_clusters_to_marker,
        marker_label_prepend='#Clust=',
        ),
    cols=dict(
        vary_what='cols',
        which_kernel='column_partition_assignments',
        get_fixed_parameters=lambda timing_row: 'R=%s;Cl=%s;V=%s' % \
            (timing_row.num_rows, timing_row.num_clusters,
             timing_row.num_views),
        get_variable_parameter=get_num_cols,
        get_color_parameter=get_num_rows,
        color_dict=num_rows_to_color,
        color_label_prepend='#Row=',
        get_marker_parameter=get_num_clusters,
        marker_dict=num_clusters_to_marker,
        marker_label_prepend='#Clust=',
        ),
    clusters=dict(
        vary_what='clusters',
        which_kernel='row_partition_assignments',
        get_fixed_parameters=lambda timing_row: 'R=%s;Co=%s;V=%s' % \
            (timing_row.num_rows, timing_row.num_cols,
             timing_row.num_views),
        get_variable_parameter=get_num_clusters,
        get_color_parameter=get_num_rows,
        color_dict=num_rows_to_color,
        color_label_prepend='#Row=',
        get_marker_parameter=get_num_views,
        marker_dict=num_views_to_marker,
        marker_label_prepend='#View=',
        ),
    views=dict(
        vary_what='views',
        which_kernel='column_partition_assignments',
        get_fixed_parameters=lambda timing_row: 'R=%s;Co=%s;Cl=%s' % \
            (timing_row.num_rows, timing_row.num_cols,
             timing_row.num_clusters),
        get_variable_parameter=get_num_views,
        get_color_parameter=get_num_rows,
        color_dict=num_rows_to_color,
        color_label_prepend='#Row=',
        get_marker_parameter=get_num_cols,
        marker_dict=num_cols_to_marker,
        marker_label_prepend='#Col=',
        ),
    )

get_first_label_value = lambda label: label[1+label.index('='):label.index(';')]
label_cmp = lambda x, y: cmp(int(get_first_label_value(x)), int(get_first_label_value(y)))
def plot_grouped_data(dict_of_dicts, plot_parameters, plot_filename=None):
    get_color_parameter = plot_parameters['get_color_parameter']
    color_dict = plot_parameters['color_dict']
    color_label_prepend = plot_parameters['color_label_prepend']
    timing_row_to_color = lambda timing_row: \
        color_dict[get_color_parameter(timing_row)]
    get_marker_parameter = plot_parameters['get_marker_parameter']
    marker_dict = plot_parameters['marker_dict']
    marker_label_prepend = plot_parameters['marker_label_prepend']
    timing_row_to_marker = lambda timing_row: \
        marker_dict[get_marker_parameter(timing_row)]
    vary_what = plot_parameters['vary_what']
    which_kernel = plot_parameters['which_kernel']
    #
    fh = pylab.figure()
    for configuration, run_data in dict_of_dicts.iteritems():
        x = sorted(run_data.keys())
        _y = [run_data[el] for el in x]
        y = map(get_time_per_step, _y)
        #
        plot_args = dict()
        first_timing_row = run_data.values()[0]
        color = timing_row_to_color(first_timing_row)
        plot_args['color'] = color
        marker = timing_row_to_marker(first_timing_row)
        plot_args['marker'] = marker
        label = str(configuration)
        plot_args['label'] = label
        #
        pylab.plot(x, y, **plot_args)
    #
    pylab.xlabel('# %s' % vary_what)
    pylab.ylabel('time per step (seconds)')
    pylab.title('Timing analysis for kernel: %s' % which_kernel)

    # pu.legend_outside(bbox_to_anchor=(0.5, -.1), ncol=4, label_cmp=label_cmp)
    pu.legend_outside_from_dicts(marker_dict, color_dict,
                                 marker_label_prepend=marker_label_prepend, color_label_prepend=color_label_prepend,
                                 bbox_to_anchor=(0.5, -.1), label_cmp=label_cmp)
                                 
                                 

    if plot_filename is not None:
        pu.savefig_legend_outside(plot_filename)
    else:
        pylab.ion()
        pylab.show()
    return fh

if __name__ == '__main__':
    # parse some arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--vary_what', type=str, default='views')
    parser.add_argument('--input_filename', type=str, default='parsed_output')
    parser.add_argument('--plot_filename', type=str, default=None)
    args = parser.parse_args()
    input_filename = args.input_filename
    vary_what = args.vary_what
    plot_filename = args.plot_filename

    # configure parsing/plotting
    plot_parameters = plot_parameter_lookup[vary_what]
    which_kernel = plot_parameters['which_kernel']
    get_fixed_parameters = plot_parameters['get_fixed_parameters']
    get_variable_parameter = plot_parameters['get_variable_parameter']

    # some helper functions
    get_is_this_kernel = lambda timing_row: \
        timing_row.which_kernel == which_kernel
    is_one_view = lambda timing_row: timing_row.num_views == '1'

    # parse the timing data
    timing_rows = parse_timing_file(input_filename)
    these_timing_rows = filter(get_is_this_kernel, timing_rows)
    # these_timing_rows = filter(is_one_view, these_timing_rows)
    dict_of_dicts = group_results(these_timing_rows, get_fixed_parameters,
                                  get_variable_parameter)
    
    # plot
    plot_grouped_data(dict_of_dicts, plot_parameters, plot_filename)

########NEW FILE########
__FILENAME__ = runtime_scripting
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import os
import argparse
import tempfile
#
import numpy
#
import crosscat.utils.data_utils as du
import crosscat.utils.xnet_utils as xu
import crosscat.utils.hadoop_utils as hu
import crosscat.LocalEngine as LE
import crosscat.HadoopEngine as HE
import crosscat.cython_code.State as State
from crosscat.settings import Hadoop as hs


def get_generative_clustering(M_c, M_r, T,
                              data_inverse_permutation_indices,
                              num_clusters, num_views):
    # NOTE: this function only works because State.p_State doesn't use
    #       column_component_suffstats
    num_rows = len(T)
    num_cols = len(T[0])
    X_D_helper = numpy.repeat(range(num_clusters), (num_rows / num_clusters))
    gen_X_D = [
        X_D_helper[numpy.argsort(data_inverse_permutation_index)]
        for data_inverse_permutation_index in data_inverse_permutation_indices
        ]
    gen_X_L_assignments = numpy.repeat(range(num_views), (num_cols / num_views))
    # initialize to generate an X_L to manipulate
    local_engine = LE.LocalEngine()
    bad_X_L, bad_X_D = local_engine.initialize(M_c, M_r, T,
                                                         initialization='apart')
    bad_X_L['column_partition']['assignments'] = gen_X_L_assignments
    # manually constrcut state in in generative configuration
    state = State.p_State(M_c, T, bad_X_L, gen_X_D)
    gen_X_L = state.get_X_L()
    gen_X_D = state.get_X_D()
    # run inference on hyperparameters to leave them in a reasonable state
    kernel_list = (
        'row_partition_hyperparameters',
        'column_hyperparameters',
        'column_partition_hyperparameter',
        )
    gen_X_L, gen_X_D = local_engine.analyze(M_c, T, gen_X_L, gen_X_D, n_steps=1,
                                            kernel_list=kernel_list)
    #
    return gen_X_L, gen_X_D

def generate_clean_state(gen_seed, num_clusters,
                         num_cols, num_rows, num_splits,
                         max_mean=10, max_std=1,
                         plot=False):
    # generate the data
    T, M_r, M_c, data_inverse_permutation_indices = \
        du.gen_factorial_data_objects(gen_seed, num_clusters,
                                      num_cols, num_rows, num_splits,
                                      max_mean=10, max_std=1,
                                      send_data_inverse_permutation_indices=True)
    # recover generative clustering
    X_L, X_D = get_generative_clustering(M_c, M_r, T,
                                         data_inverse_permutation_indices,
                                         num_clusters, num_splits)
    return T, M_c, M_r, X_L, X_D

def generate_hadoop_dicts(which_kernels, X_L, X_D, args_dict):
    for which_kernel in which_kernels:
        kernel_list = (which_kernel, )
        dict_to_write = dict(X_L=X_L, X_D=X_D)
        dict_to_write.update(args_dict)
        # must write kernel_list after update
        dict_to_write['kernel_list'] = kernel_list
        yield dict_to_write

def write_hadoop_input(input_filename, X_L, X_D, n_steps, SEED):
    # prep settings dictionary
    time_analyze_args_dict = hs.default_analyze_args_dict
    time_analyze_args_dict['command'] = 'time_analyze'
    time_analyze_args_dict['SEED'] = SEED
    time_analyze_args_dict['n_steps'] = n_steps
    # one kernel per line
    all_kernels = State.transition_name_to_method_name_and_args.keys()
    n_tasks = 0
    with open(input_filename, 'w') as out_fh:
        dict_generator = generate_hadoop_dicts(all_kernels, X_L, X_D, time_analyze_args_dict)
        for dict_to_write in dict_generator:
            xu.write_hadoop_line(out_fh, key=dict_to_write['SEED'], dict_to_write=dict_to_write)
            n_tasks += 1
    return n_tasks


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--gen_seed', type=int, default=0)
    parser.add_argument('--num_clusters', type=int, default=20)
    parser.add_argument('--num_rows', type=int, default=1000)
    parser.add_argument('--num_cols', type=int, default=20)
    parser.add_argument('--num_splits', type=int, default=2)
    parser.add_argument('--n_steps', type=int, default=10)
    parser.add_argument('-do_local', action='store_true')
    parser.add_argument('-do_remote', action='store_true')
    #
    args = parser.parse_args()
    gen_seed = args.gen_seed
    num_clusters = args.num_clusters
    num_cols = args.num_cols
    num_rows = args.num_rows
    num_splits = args.num_splits
    n_steps = args.n_steps
    do_local = args.do_local
    do_remote = args.do_remote


    script_filename = 'hadoop_line_processor.py'
    # some hadoop processing related settings
    temp_dir = tempfile.mkdtemp(prefix='runtime_analysis_',
                                dir='runtime_analysis')
    print 'using dir: %s' % temp_dir
    #
    table_data_filename = os.path.join(temp_dir, 'table_data.pkl.gz')
    input_filename = os.path.join(temp_dir, 'hadoop_input')
    output_filename = os.path.join(temp_dir, 'hadoop_output')
    output_path = os.path.join(temp_dir, 'output')
    print table_data_filename
    # generate data
    T, M_c, M_r, X_L, X_D = generate_clean_state(gen_seed,
                                                 num_clusters,
                                                 num_cols, num_rows,
                                                 num_splits,
                                                 max_mean=10, max_std=1)

    # write table_data
    table_data = dict(M_c=M_c, M_r=M_r, T=T)
    fu.pickle(table_data, table_data_filename)
    # write hadoop input
    n_tasks = write_hadoop_input(input_filename, X_L, X_D, n_steps, SEED=gen_seed)

    # actually run
    if do_local:
        xu.run_script_local(input_filename, script_filename, output_filename, table_data_filename)
    elif do_remote:
        hadoop_engine = HE.HadoopEngine(output_path=output_path,
                                        input_filename=input_filename,
                                        table_data_filename=table_data_filename,
                                        )
        hadoop_engine.send_hadoop_command(n_tasks)
        was_successful = hadoop_engine.get_hadoop_results()
        if was_successful:
            hu.copy_hadoop_output(output_path, output_filename)
        else:
            print 'remote hadoop job NOT successful'
    else:
        hadoop_engine = HE.HadoopEngine()
        # print what the command would be
        print HE.create_hadoop_cmd_str(hadoop_engine, n_tasks=n_tasks)

########NEW FILE########
__FILENAME__ = api_utils
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import requests
import json


global_id = 0

def create_message(method_name, params, id):
    id += 1
    message = {
        'jsonrpc': '2.0',
        'method': method_name,
        'params': params,
        'id': str(id),
        }
    json_message = json.dumps(message)
    return json_message, id

def call(method_name, args_dict, URI, id=None, print_message=False):
    global global_id
    if id is None: id = global_id
    message, id = create_message(method_name, args_dict, id)
    global_id = global_id + 1
    if print_message: print 'trying message:', message
    r = requests.put(URI, data=message)
    r.raise_for_status()
    out = json.loads(r.content)
    #
    if isinstance(out, dict) and 'result' in out:
        out = out['result']
    else:
        print "call(%s, <args_dict>, %s): ERROR" % (method_name, URI)
    return out, id

def call_and_print(method_name, args_dict, URI, id=0):
    out, id = call(method_name, args_dict, URI, id=id, print_message=True)
    print out
    print
    return out, id

########NEW FILE########
__FILENAME__ = convergence_test_utils
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import numpy
from sklearn import metrics
#
import crosscat.cython_code.State as State
import crosscat.utils.general_utils as gu
import crosscat.utils.sample_utils as su


def determine_synthetic_column_ground_truth_assignments(num_cols, num_views):
    num_cols_per_view = num_cols / num_views
    view_assignments = []
    for view_idx in range(num_views):
        view_assignments.extend([view_idx] * num_cols_per_view)
    return view_assignments

def truth_from_permute_indices(data_inverse_permutation_indices, num_rows,num_cols,num_views, num_clusters):
    # We assume num_rows is divisible by num_clusters and num_cols is divisible by num_views
    num_cols_per_view = num_cols/num_views
    view_assignments = []
    for viewindx in range(num_views):
        view_assignments = view_assignments + [viewindx]*num_cols_per_view

    num_rows_per_cluster = num_rows/num_clusters
    
    reference_list = []
    for clusterindx in range(num_clusters):
        reference_list = reference_list + [clusterindx]*num_rows_per_cluster
        
    X_D_truth = []
    for viewindx in range(num_views):
        X_D_truth.append([a for (b,a) in sorted(zip(data_inverse_permutation_indices[viewindx], reference_list))])
        
        
    return view_assignments, X_D_truth

def ARI_CrossCat(Xc, Xrv, XRc, XRrv):
    ''' Adjusted Rand Index (ARI) calculation for a CrossCat clustered table
    
    To calculate ARI based on the CrossCat partition, each cell in the
    table is considered as an instance to be assigned to a cluster. A cluster
    is defined by both the view index AND the category index. In other words,
    if, and only if, two cells, regardless of which columns and rows they belong
    to, are lumped into the same view and category, the two cells are considered
    to be in the same cluster. 

    For a table of size Nrow x Ncol
    Xc: (1 x Ncol) array of view assignment for each column.
        Note: It is assumed that the view indices are consecutive integers
        starting from 0. Hence, the number of views is equal to highest
        view index plus 1.
    Xrv: (Nrow x Nview) array where each row is the assignmennt of categories for the
        corresponding row in the data table. The i-th element in a row
        corresponds to the category assignment of the i-th view of that row.
    XRc and XRrv have the same format as Xr and Xrv respectively.
    The ARI index is calculated from the comparison of the table clustering
    define by (XRc, XRrv) and (Xc, Xrv).
    '''
    Xrv = Xrv.T
    XRrv = XRrv.T
    # Find the highest category index of all views
    max_cat_index = numpy.max(Xrv)
    # re-assign category indices so that they have different values in
    # different views
    Xrv = Xrv + numpy.arange(0,Xrv.shape[1])*(max_cat_index+1)
    
    # similarly for the reference partition
    max_cat_index = numpy.max(XRrv)
    XRrv = XRrv + numpy.arange(0,XRrv.shape[1])*(max_cat_index+1)
    
    # Table clustering assignment for the first partition
    CellClusterAssgn = numpy.zeros((Xrv.shape[0], Xc.size))
    for icol in range(Xc.size):
        CellClusterAssgn[:,icol]=Xrv[:,Xc[icol]]
    # Flatten the table to a 1-D array compatible with the ARI function 
    CellClusterAssgn = CellClusterAssgn.reshape(CellClusterAssgn.size)
        
    # Table clustering assignment for the second partition
    RefCellClusterAssgn = numpy.zeros((Xrv.shape[0], Xc.size))
    for icol in range(Xc.size):
        RefCellClusterAssgn[:,icol]=XRrv[:,XRc[icol]]
    # Flatten the table
    RefCellClusterAssgn = RefCellClusterAssgn.reshape(RefCellClusterAssgn.size)
        
    # Compare the two partitions using ARI
    ARI = metrics.adjusted_rand_score(RefCellClusterAssgn, CellClusterAssgn)
    ARI_viewonly = metrics.adjusted_rand_score(Xc, XRc)

    return ARI, ARI_viewonly

def get_column_ARI(X_L, view_assignment_truth):
    view_assignments = X_L['column_partition']['assignments']
    ARI = metrics.adjusted_rand_score(view_assignments, view_assignment_truth)
    return ARI

def get_column_ARIs(X_L_list, view_assignment_truth):
    get_column_ARI_helper = lambda X_L: \
            get_column_ARI(X_L, view_assignment_truth)
    ARIs = map(get_column_ARI_helper, X_L_list)
    return ARIs

def multi_chain_ARI(X_L_list, X_D_List, view_assignment_truth, X_D_truth, return_list=False):
    num_chains = len(X_L_list)
    ari_table = numpy.zeros(num_chains)
    ari_views = numpy.zeros(num_chains)
    for chainindx in range(num_chains):
        view_assignments = X_L_list[chainindx]['column_partition']['assignments']
        curr_ari_table, curr_ari_views = ARI_CrossCat(numpy.asarray(view_assignments), numpy.asarray(X_D_List[chainindx]), numpy.asarray(view_assignment_truth), numpy.asarray(X_D_truth))
        ari_table[chainindx] = curr_ari_table
        ari_views[chainindx] = curr_ari_views

    ari_table_mean = numpy.mean(ari_table)
    ari_views_mean = numpy.mean(ari_views)
    if return_list:
        return ari_table, ari_views
    else:
        return ari_table_mean, ari_views_mean

def create_test_set(M_c, T, X_L, X_D, n_test, seed_seed=0):
    sample_row_idx = len(T) + 1
    n_cols = len(T[0])
    Y = []
    Q = [(sample_row_idx, col_idx) for col_idx in range(n_cols)]
    int_generator = gu.int_generator(seed_seed)
    get_next_seed = lambda: int_generator.next()
    samples = su.simple_predictive_sample(M_c, X_L, X_D, Y, Q, get_next_seed, n=n_test)
    return samples

# FIXME: remove dependence on T as input
#        by making p_State constructor actually use only suffstats
def calc_mean_test_log_likelihood(M_c, T, X_L, X_D, T_test):
    state = State.p_State(M_c, T, X_L, X_D)
    test_log_likelihoods = map(state.calc_row_predictive_logp, T_test)
    mean_test_log_likelihood = numpy.mean(test_log_likelihoods)
    return mean_test_log_likelihood
def calc_mean_test_log_likelihoods(M_c, T, X_L_list, X_D_list, T_test):
    mean_test_log_likelihoods = []
    for X_L, X_D in zip(X_L_list, X_D_list):
        mean_test_log_likelihood = calc_mean_test_log_likelihood(M_c, T, X_L,
                X_D, T_test)
        mean_test_log_likelihoods.append(mean_test_log_likelihood)
    return mean_test_log_likelihoods

########NEW FILE########
__FILENAME__ = data_utils
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import sys
import csv
import copy
#
import numpy


def get_generative_clustering(M_c, M_r, T,
                              data_inverse_permutation_indices,
                              num_clusters, num_views):
    from crosscat.LocalEngine import LocalEngine
    import crosscat.cython_code.State as State
    # NOTE: this function only works because State.p_State doesn't use
    #       column_component_suffstats
    num_rows = len(T)
    num_cols = len(T[0])
    X_D_helper = numpy.repeat(range(num_clusters), (num_rows / num_clusters))
    gen_X_D = [
        X_D_helper[numpy.argsort(data_inverse_permutation_index)]
        for data_inverse_permutation_index in data_inverse_permutation_indices
        ]
    gen_X_L_assignments = numpy.repeat(range(num_views), (num_cols / num_views))
    # initialize to generate an X_L to manipulate
    local_engine = LocalEngine()
    bad_X_L, bad_X_D = local_engine.initialize(M_c, M_r, T,
                                                         initialization='apart')
    bad_X_L['column_partition']['assignments'] = gen_X_L_assignments
    # manually constrcut state in in generative configuration
    state = State.p_State(M_c, T, bad_X_L, gen_X_D)
    gen_X_L = state.get_X_L()
    gen_X_D = state.get_X_D()
    # run inference on hyperparameters to leave them in a reasonable state
    kernel_list = (
        'row_partition_hyperparameters',
        'column_hyperparameters',
        'column_partition_hyperparameter',
        )
    gen_X_L, gen_X_D = local_engine.analyze(M_c, T, gen_X_L, gen_X_D, n_steps=1,
                                            kernel_list=kernel_list)
    #
    return gen_X_L, gen_X_D

def generate_clean_state(gen_seed, num_clusters,
                         num_cols, num_rows, num_splits,
                         max_mean=10, max_std=1,
                         plot=False):
    # generate the data
    T, M_r, M_c, data_inverse_permutation_indices = \
        gen_factorial_data_objects(gen_seed, num_clusters,
                                      num_cols, num_rows, num_splits,
                                      max_mean=10, max_std=1,
                                      send_data_inverse_permutation_indices=True)
    # recover generative clustering
    X_L, X_D = get_generative_clustering(M_c, M_r, T,
                                         data_inverse_permutation_indices,
                                         num_clusters, num_splits)
    return T, M_c, M_r, X_L, X_D

def get_ith_ordering(in_list, i):
    temp_list = [in_list[j::(i+1)][:] for j in range(i+1)]
    return [el for sub_list in temp_list for el in sub_list]

def gen_data(gen_seed, num_clusters,
             num_cols, num_rows, max_mean_per_category=10, max_std=1,
             max_mean=None):
    if max_mean is None:
       max_mean = max_mean_per_category * num_clusters
    n_grid = 11
    mu_grid = numpy.linspace(-max_mean, max_mean, n_grid)
    sigma_grid = 10 ** numpy.linspace(-1, numpy.log10(max_std), n_grid)
    num_rows_per_cluster = num_rows / num_clusters
    zs = numpy.repeat(range(num_clusters), num_rows_per_cluster)
    #
    random_state = numpy.random.RandomState(gen_seed)
    #
    data_size = (num_clusters,num_cols)
    which_mus = random_state.randint(len(mu_grid), size=data_size)
    which_sigmas = random_state.randint(len(sigma_grid), size=data_size)
    mus = mu_grid[which_mus]
    sigmas = sigma_grid[which_sigmas]
    clusters = []
    for row_mus, row_sigmas in zip(mus, sigmas):
        cluster_columns = []
        for mu, sigma in zip(row_mus, row_sigmas):
            cluster_column = random_state.normal(mu, sigma,
                                                 num_rows_per_cluster)
            cluster_columns.append(cluster_column)
        cluster = numpy.vstack(cluster_columns).T
        clusters.append(cluster)
    xs = numpy.vstack(clusters)
    return xs, zs

def gen_factorial_data(gen_seed, num_clusters,
        num_cols, num_rows, num_splits,
		max_mean_per_category=10, max_std=1,
        max_mean=None
        ):
    random_state = numpy.random.RandomState(gen_seed)
    data_list = []
    inverse_permutation_indices_list = []
    for data_idx in xrange(num_splits):
        data_i, zs_i = gen_data(
            gen_seed=random_state.randint(sys.maxint),
            num_clusters=num_clusters,
            num_cols=num_cols/num_splits,
            num_rows=num_rows,
            max_mean_per_category=max_mean_per_category,
            max_std=max_std,
            max_mean=max_mean
            )
        permutation_indices = random_state.permutation(xrange(num_rows))
        # permutation_indices = get_ith_ordering(range(num_rows), data_idx)
        inverse_permutation_indices = numpy.argsort(permutation_indices)
        inverse_permutation_indices_list.append(inverse_permutation_indices)
        data_list.append(numpy.array(data_i)[permutation_indices])
    data = numpy.hstack(data_list)
    return data, inverse_permutation_indices_list

def gen_M_r_from_T(T):
    num_rows = len(T)
    num_cols = len(T[0])
    #
    name_to_idx = dict(zip(map(str, range(num_rows)), range(num_rows)))
    idx_to_name = dict(zip(map(str, range(num_rows)), range(num_rows)))
    M_r = dict(name_to_idx=name_to_idx, idx_to_name=idx_to_name)
    return M_r

def gen_continuous_metadata(column_data):
    return dict(
        modeltype="normal_inverse_gamma",
        value_to_code=dict(),
        code_to_value=dict(),
        )

def gen_multinomial_metadata(column_data):
    def get_is_not_nan(el):
        if isinstance(el, str):
            return el.upper() != 'NAN'
        else:
            return True
    # get_is_not_nan = lambda el: el.upper() != 'NAN'
    #
    unique_codes = list(set(column_data))
    unique_codes = filter(get_is_not_nan, unique_codes)
    #
    values = range(len(unique_codes))
    value_to_code = dict(zip(values, unique_codes))
    code_to_value = dict(zip(unique_codes, values))
    return dict(
        modeltype="symmetric_dirichlet_discrete",
        value_to_code=value_to_code,
        code_to_value=code_to_value,
        )

metadata_generator_lookup = dict(
    continuous=gen_continuous_metadata,
    multinomial=gen_multinomial_metadata,
)

def gen_M_c_from_T(T, cctypes=None, colnames=None):
    num_rows = len(T)
    num_cols = len(T[0])
    if cctypes is None:
        cctypes = ['continuous'] * num_cols
    if colnames is None:
        colnames = range(num_cols)
    #
    T_array_transpose = numpy.array(T).T
    column_metadata = []
    for cctype, column_data in zip(cctypes, T_array_transpose):
        metadata_generator = metadata_generator_lookup[cctype]
        metadata = metadata_generator(column_data)
        column_metadata.append(metadata)
    name_to_idx = dict(zip(colnames, range(num_cols)))
    idx_to_name = dict(zip(map(str, range(num_cols)), colnames))
    M_c = dict(
        name_to_idx=name_to_idx,
        idx_to_name=idx_to_name,
        column_metadata=column_metadata,
        )
    return M_c

def gen_M_c_from_T_with_colnames(T, colnames):
    num_rows = len(T)
    num_cols = len(T[0])
    #
    gen_continuous_metadata = lambda: dict(modeltype="normal_inverse_gamma",
                                           value_to_code=dict(),
                                           code_to_value=dict())
    column_metadata = [
        gen_continuous_metadata()
        for col_idx in range(num_cols)
        ]
    name_to_idx = dict(zip(colnames, range(num_cols)))
    idx_to_name = dict(zip(map(str, range(num_cols)),colnames))
    M_c = dict(
        name_to_idx=name_to_idx,
        idx_to_name=idx_to_name,
        column_metadata=column_metadata,
        )
    return M_c

def gen_factorial_data_objects(gen_seed, num_clusters,
                               num_cols, num_rows, num_splits,
                               max_mean=10, max_std=1,
                               send_data_inverse_permutation_indices=False):
    T, data_inverse_permutation_indices = gen_factorial_data(
        gen_seed, num_clusters,
        num_cols, num_rows, num_splits, max_mean, max_std)
    T  = T.tolist()
    M_r = gen_M_r_from_T(T)
    M_c = gen_M_c_from_T(T)
    if not send_data_inverse_permutation_indices:
        return T, M_r, M_c
    else:
        return T, M_r, M_c, data_inverse_permutation_indices

def discretize_data(T, discretize_indices):
    T_array = numpy.array(T)
    discretize_indices = numpy.array(discretize_indices)
    T_array[:, discretize_indices] = \
        numpy.array(T_array[:, discretize_indices], dtype=int)
    return T_array.tolist()

def convert_columns_to_multinomial(T, M_c, multinomial_indices):
    multinomial_indices = numpy.array(multinomial_indices)
    modeltype = 'symmetric_dirichlet_discrete'
    T_array = numpy.array(T)
    for multinomial_idx in multinomial_indices:
        multinomial_column = T_array[:, multinomial_idx]
        multinomial_column = multinomial_column[~numpy.isnan(multinomial_column)]
        multinomial_values = list(set(multinomial_column))
        K = len(multinomial_values)
        code_to_value = dict(zip(range(K), multinomial_values))
        value_to_code = dict(zip(multinomial_values, range(K)))
        multinomial_column_metadata = M_c['column_metadata'][multinomial_idx]
        multinomial_column_metadata['modeltype'] = modeltype
        multinomial_column_metadata['code_to_value'] = code_to_value
        multinomial_column_metadata['value_to_code'] = value_to_code
    return T, M_c

# UNTESTED
def convert_columns_to_continuous(T, M_c, continuous_indices):
    continuous_indices = numpy.array(continuous_indices)
    modeltype = 'normal_inverse_gamma'
    T_array = numpy.array(T)
    for continuous_idx in continuous_indices:
        code_to_value = dict()
        value_to_code = dict()
        continuous_column_metadata = M_c['column_metadata'][continuous_idx]
        continuous_column_metadata['modeltype'] = modeltype
        continuous_column_metadata['code_to_value'] = code_to_value
        continuous_column_metadata['value_to_code'] = value_to_code
    return T, M_c

def at_most_N_rows(T, N, gen_seed=0):
    num_rows = len(T)
    if (N is not None) and (num_rows > N):
        random_state = numpy.random.RandomState(gen_seed)
        which_rows = random_state.permutation(xrange(num_rows))
        which_rows = which_rows[:N]
        T = [T[which_row] for which_row in which_rows]
    return T

def read_csv(filename, has_header=True):
    with open(filename) as fh:
        csv_reader = csv.reader(fh)
        header = None
        if has_header:
            header = csv_reader.next()
        rows = [row for row in csv_reader]
    return header, rows

def write_csv(filename, T, header = None):
    with open(filename,'w') as fh:
        csv_writer = csv.writer(fh, delimiter=',')
        if header != None:
            csv_writer.writerow(header)
        [csv_writer.writerow(T[i]) for i in range(len(T))]

def all_continuous_from_file(filename, max_rows=None, gen_seed=0, has_header=True):
    header, T = read_csv(filename, has_header=has_header)
    T = numpy.array(T, dtype=float).tolist()
    T = at_most_N_rows(T, N=max_rows, gen_seed=gen_seed)
    M_r = gen_M_r_from_T(T)
    M_c = gen_M_c_from_T(T)
    return T, M_r, M_c, header

def continuous_or_ignore_from_file_with_colnames(filename, cctypes, max_rows=None, gen_seed=0):
    header = None
    T, M_r, M_c = None, None, None
    colmask = map(lambda x: 1 if x != 'ignore' else 0, cctypes)
    with open(filename) as fh:
        csv_reader = csv.reader(fh)
        header = csv_reader.next()
        T = numpy.array([
                [col for col, flag in zip(row, colmask) if flag] for row in csv_reader
                ], dtype=float).tolist()
        num_rows = len(T)
        if (max_rows is not None) and (num_rows > max_rows):
            random_state = numpy.random.RandomState(gen_seed)
            which_rows = random_state.permutation(xrange(num_rows))
            which_rows = which_rows[:max_rows]
            T = [T[which_row] for which_row in which_rows]
        M_r = gen_M_r_from_T(T)
        M_c = gen_M_c_from_T_with_colnames(T, [col for col, flag in zip(header, colmask) if flag])
    return T, M_r, M_c, header

def convert_code_to_value(M_c, cidx, code):
    """
    For a column with categorical data, this function takes the 'code':
    the integer used to represent a specific value, and returns the corresponding
    raw value (e.g. 'Joe' or 234.23409), which is always encoded as a string.

    Note that the underlying store 'value_to_code' is unfortunately named backwards.
    TODO: fix the backwards naming.
    """
    if M_c['column_metadata'][cidx]['modeltype'] == 'normal_inverse_gamma':
        return float(code)
    else:
        try:
            return M_c['column_metadata'][cidx]['value_to_code'][int(code)]
        except KeyError:
            return M_c['column_metadata'][cidx]['value_to_code'][str(int(code))]

def convert_value_to_code(M_c, cidx, value):
    """
    For a column with categorical data, this function takes the raw value
    (e.g. 'Joe' or 234.23409), which is always encoded as a string, and returns the
    'code': the integer used to represent that value in the underlying representation.

    Note that the underlying store 'code_to_value' is unfortunately named backwards.
    TODO: fix the backwards naming.
    """
    if M_c['column_metadata'][cidx]['modeltype'] == 'normal_inverse_gamma':
        return float(value)
    else:
        return M_c['column_metadata'][cidx]['code_to_value'][str(value)] 

def map_from_T_with_M_c(coordinate_value_tuples, M_c):
    coordinate_code_tuples = []
    column_metadata = M_c['column_metadata']
    for row_idx, col_idx, value in coordinate_value_tuples:
        datatype = column_metadata[col_idx]['modeltype']
        # FIXME: make this robust to different datatypes
        if datatype == 'symmetric_dirichlet_discrete':
            # FIXME: casting key to str is a hack
            value = column_metadata[col_idx]['value_to_code'][str(int(value))]
        coordinate_code_tuples.append((row_idx, col_idx, value))
    return coordinate_code_tuples

def map_to_T_with_M_c(T_uncast_array, M_c):
    T_uncast_array = numpy.array(T_uncast_array)
    # WARNING: array argument is mutated
    for col_idx in range(T_uncast_array.shape[1]):
        modeltype = M_c['column_metadata'][col_idx]['modeltype']
        if modeltype != 'symmetric_dirichlet_discrete': continue
        # copy.copy else you mutate M_c
        mapping = copy.copy(M_c['column_metadata'][col_idx]['code_to_value'])
        mapping['NAN'] = numpy.nan
        col_data = T_uncast_array[:, col_idx]
        to_upper = lambda el: el.upper()
        is_nan_str = numpy.array(map(to_upper, col_data))=='NAN'
        col_data[is_nan_str] = 'NAN'
        # FIXME: THIS IS WHERE TO PUT NAN HANDLING
        mapped_values = [mapping[el] for el in col_data]
        T_uncast_array[:, col_idx] = mapped_values
    T = numpy.array(T_uncast_array, dtype=float).tolist()
    return T

def do_pop_list_indices(in_list, pop_indices):
    pop_indices = sorted(pop_indices, reverse=True)
    _do_pop = lambda x: in_list.pop(x)
    map(_do_pop, pop_indices)
    return in_list

def get_list_indices(in_list, get_indices_of):
    lookup = dict(zip(in_list, range(len(in_list))))
    indices = map(lookup.get, get_indices_of)
    indices = filter(None, indices)
    return indices

def transpose_list(in_list):
    return zip(*in_list)

def get_pop_indices(cctypes, colnames):
    assert len(colnames) == len(cctypes)
    pop_columns = [
            colname
            for (cctype, colname) in zip(cctypes, colnames)
            if cctype == 'ignore'
            ]
    pop_indices = get_list_indices(colnames, pop_columns)
    return pop_indices

def do_pop_columns(T, pop_indices):
    T_by_columns = transpose_list(T)
    T_by_columns = do_pop_list_indices(T_by_columns, pop_indices)
    T = transpose_list(T_by_columns)
    return T

def remove_ignore_cols(T, cctypes, colnames):
    pop_indices = get_pop_indices(cctypes, colnames)
    T = do_pop_columns(T, pop_indices)
    colnames = do_pop_list_indices(colnames[:], pop_indices)
    cctypes = do_pop_list_indices(cctypes[:], pop_indices)
    return T, cctypes, colnames

nan_set = set(['', 'null', 'n/a'])
_convert_nan = lambda el: el if el.strip().lower() not in nan_set else 'NAN'
_convert_nans = lambda in_list: map(_convert_nan, in_list)
convert_nans = lambda in_T: map(_convert_nans, in_T)

def read_data_objects(filename, max_rows=None, gen_seed=0,
                      cctypes=None, colnames=None):
    header, raw_T = read_csv(filename, has_header=True)
    header = [h.lower().strip() for h in header]
    # FIXME: why both accept colnames argument and read header?
    if colnames is None:
        colnames = header
        pass
    # remove excess rows
    raw_T = at_most_N_rows(raw_T, N=max_rows, gen_seed=gen_seed)
    raw_T = convert_nans(raw_T)
    # remove ignore columns
    if cctypes is None:
        cctypes = ['continuous'] * len(header)
        pass
    T_uncast_arr, cctypes, header = remove_ignore_cols(raw_T, cctypes, header)
    # determine value mappings and map T to continuous castable values
    M_r = gen_M_r_from_T(T_uncast_arr)
    M_c = gen_M_c_from_T(T_uncast_arr, cctypes, colnames)
    T = map_to_T_with_M_c(T_uncast_arr, M_c)
    #
    return T, M_r, M_c, header

def get_can_cast_to_float(column_data):
    can_cast = True
    try:
        [float(datum) for datum in column_data]
    except ValueError, e:
        can_cast = False
    return can_cast
    
def guess_column_type(column_data, count_cutoff=20, ratio_cutoff=0.02):
    num_distinct = len(set(column_data))
    num_data = len(column_data)
    distinct_ratio = float(num_distinct) / num_data
    above_count_cutoff = num_distinct > count_cutoff
    above_ratio_cutoff = distinct_ratio > ratio_cutoff
    can_cast = get_can_cast_to_float(column_data)
    if above_count_cutoff and above_ratio_cutoff and can_cast:
        column_type = 'continuous'
    else:
        column_type = 'multinomial'
    return column_type

def guess_column_types(T, count_cutoff=20, ratio_cutoff=0.02):
    T_transposed = transpose_list(T)
    column_types = []
    for column_data in T_transposed:
        column_type = guess_column_type(column_data, count_cutoff, ratio_cutoff)
        column_types.append(column_type)
    return column_types
        
def read_model_data_from_csv(filename, max_rows=None, gen_seed=0,
                             cctypes=None):
    colnames, T = read_csv(filename)
    T = at_most_N_rows(T, max_rows, gen_seed)
    T = convert_nans(T)
    if cctypes is None:
        cctypes = guess_column_types(T)
    M_c = gen_M_c_from_T(T, cctypes, colnames)
    T = map_to_T_with_M_c(numpy.array(T), M_c)
    M_r = gen_M_r_from_T(T)
    return T, M_r, M_c

extract_view_count = lambda X_L: len(X_L['view_state'])
extract_cluster_count = lambda view_state_i: view_state_i['row_partition_model']['counts']
extract_cluster_counts = lambda X_L: map(extract_cluster_count, X_L['view_state'])
get_state_shape = lambda X_L: (extract_view_count(X_L), extract_cluster_counts(X_L))

########NEW FILE########
__FILENAME__ = diagnostic_utils
import numpy
#
import crosscat.utils.convergence_test_utils


def get_logscore(p_State):
    return p_State.get_marginal_logp()

def get_num_views(p_State):
    return len(p_State.get_X_D())

def get_column_crp_alpha(p_State):
    return p_State.get_column_crp_alpha()

def get_ari(p_State):
    # requires environment: {view_assignment_truth}
    # requires import: {crosscat.utils.convergence_test_utils}
    X_L = p_State.get_X_L()
    ctu = crosscat.utils.convergence_test_utils
    return ctu.get_column_ARI(X_L, view_assignment_truth)

def get_mean_test_ll(p_State):
    # requires environment {M_c, T, T_test}
    # requires import: {crosscat.utils.convergence_test_utils}
    X_L = p_State.get_X_L()
    X_D = p_State.get_X_D()
    ctu = crosscat.utils.convergence_test_utils
    return ctu.calc_mean_test_log_likelihood(M_c, T, X_L, X_D, T_test)

def get_column_partition_assignments(p_State):
    return p_State.get_X_L()['column_partition']['assignments']

def column_chain_to_ratio(column_chain_arr, j, i=0):
    chain_i_j = column_chain_arr[[i, j], :]
    is_same = numpy.diff(chain_i_j, axis=0)[0] == 0
    n_chains = len(is_same)
    is_same_count = sum(is_same)
    ratio = is_same_count / float(n_chains)
    return ratio

def column_partition_assignments_to_f_z_statistic(column_partition_assignments,
        j, i=0):
    iter_column_chain_arr = column_partition_assignments.transpose((1, 0, 2))
    helper = lambda column_chain_arr: column_chain_to_ratio(column_chain_arr, j, i)
    as_list = map(helper, iter_column_chain_arr)
    return numpy.array(as_list)[:, numpy.newaxis]

def default_reprocess_diagnostics_func(diagnostics_arr_dict):
    column_partition_assignments = diagnostics_arr_dict.pop('column_partition_assignments')
    # column_paritition_assignments are column, iter, chain
    D = column_partition_assignments.shape[0] - 1
    f_z_statistic_0_1 = column_partition_assignments_to_f_z_statistic(column_partition_assignments, 1, 0)
    f_z_statistic_0_D = column_partition_assignments_to_f_z_statistic(column_partition_assignments, D, 0)
    diagnostics_arr_dict['f_z[0, 1]'] = f_z_statistic_0_1
    diagnostics_arr_dict['f_z[0, D]'] = f_z_statistic_0_D
    #
    return diagnostics_arr_dict

########NEW FILE########
__FILENAME__ = enumerate_utils
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# A set of utilities that help with generating random states and calculating
# their probabilities.
# Functions list: 
#  1.GenerateRandomState(): Generates a random state and fills with gaussian data
#  2.GenerateRandomPartition(): Generates a random state (partitions only)
#  3.CRP(): Generates an assignment vector according to the CRP
#  4.pflip(): flips an n-dimensional hypercoin
#  5.GenDataFromPartitions(): generates data adhearing to a partitioning scheme
#  6.Bell(): Returns the Bell number
#  7.Stirling2nd(): Returns the Stirling number of the 2nd kind, s(n,k)
#  8.lcrp(): returns the log probability of a partition under the CRP
#  9.NGML(): calculates the Normal-Gamma marginal likelihood
# 10.CCML(): Calculates the marginal likelihood of a continuous data array under CrossCat
# 11.FixPriors(): Changes the priors in X_L
# 12.vectorToCHMat(): converts Assignment vector to cohabitation matrix (for state matching)
# 13.(class) CrossCatPartitions: Partition object. Enumerates all states.
# 14.(class) Partition: Used to enumerate partitions for CrossCatPartitions

from time import time

import math

import random as rand
import numpy as np
import scipy as sp
import itertools

from scipy.special import binom

import crosscat.cython_code.State as State
import crosscat.utils.data_utils as du


# generates from a state with the columns to views partition col_parts, and 
# the rows in views to cats partition row_parts (X_D). Accepts partitions
# as numpy array or lists. Returns a state; the data table, T; and M_c
# Arguments:
#	col_parts : vector of length n_cols assigning columns to views
#	row_parts : a list of vectors (or numpy array) with n_views rows where
#				each row, i, is a vector assigning the rows of the columns 
#				in view i to categories
#	mean_gen  : the mean of the means of data clusters
#	std_gen   : the standard deviation of cluster means
#	std_data  : the standard deviation of the individual clusters
def GenerateStateFromPartitions(col_parts, row_parts, mean_gen=0.0, std_gen=1.0, std_data=0.1):
	
	T, M_r, M_c = GenDataFromPartitions(col_parts, row_parts, mean_gen=mean_gen, std_gen=std_gen, std_data=std_data)
	state = State.p_State(M_c, T, N_GRID=100)

	X_L = state.get_X_L()
	X_D = state.get_X_D()

	if type(col_parts) is not list:
		X_L['column_partition']['assignments'] = col_parts.tolist()

	if type(row_parts) is not list:
		X_D = row_parts.tolist()

	# create a new state with the updated X_D and X_L
	state = State.p_State(M_c, T, X_L=X_L, X_D=X_D, N_GRID=100)

	return state, T, M_c, M_r, X_L, X_D

# generates a random state with n_rows rows and n_cols columns, fills it with 
# normal data and the specified alphas, and prepares it for running. Returns 
# a State.p_state object and the table of data and M_c
# Arguments:
#	n_rows    : the number of rows
#	n_cols    : the number of columns
#	mean_gen  : the mean of the means of data clusters
#	std_gen   : the standard deviation of cluster means
#	std_data  : the standard deviation of the individual clusters
#	alpha_col : the CRP parameter for columns to views
# 	alpha_rows: the CRP parameter for rows into categories
def GenerateRandomState(n_rows, n_cols, mean_gen=0.0, std_gen=1.0, std_data=0.1, alpha_col=1.0, alpha_rows=1.0):

	# check the inputs 
	assert(type(n_rows) is int)
	assert(type(n_cols) is int)
	assert(type(mean_gen) is float)
	assert(type(std_gen) is float)
	assert(type(std_data) is float)
	assert(type(alpha_col) is float)
	assert(type(alpha_rows) is float)
	assert(n_rows > 0)
	assert(n_cols > 0)
	assert(std_gen > 0.0)
	assert(std_data > 0.0)
	assert(alpha_col > 0.0)
	assert(alpha_rows > 0.0)

	# generate the partitioning
	part = GenerateRandomPartition(n_rows, n_cols, alpha_col, alpha_rows)

	# fill it with data
	T, M_r, M_c = GenDataFromPartitions(part['col_parts'], part['row_parts'], mean_gen, std_gen, std_data)

	# this part is kind of hacky:
	# generate a state from the prior 
	state = State.p_State(M_c, T, N_GRID=100)
	# get the X_L and X_D and implant part['col_parts'], part['row_parts'], then 
	# create a new state with the new X_L and X_D defined
	X_L = state.get_X_L()
	X_D = state.get_X_D()

	# this should be all we need to change for 
	# State.transform_latent_state_to_constructor_args(X_L, X_D) to be able
	# to construct the arguments to intialize a state
	X_L['column_partition']['assignments'] = part['col_parts'].tolist()
	X_D = part['row_parts'].tolist()

	# hack in the alpha values supplied (or not) by the user
	X_L['column_partition']['hypers']['alpha'] = alpha_col
	for i in range(len(X_L['view_state'])):
		X_L['view_state'][i]['row_partition_model']['hypers']['alpha'] = alpha_col
	for i in range(n_cols):
		X_L['column_hypers'][i]['alpha'] = alpha_rows

	# create a new state with the updated X_D and X_L
	state = State.p_State(M_c, T, X_L=X_L, X_D=X_D, N_GRID=100)

	return state, T, M_r, M_c

# generates a random partitioning of n_rows rows and n_cols columns based on the
# CRP. The resulting partition is a dict with two entries: ['col_parts'] and
# ['row_parts']. See CrossCatPartitions for details on these.
def GenerateRandomPartition(n_rows, n_cols, alpha_col=1.0, alpha_rows=1.0):
	assert(type(n_rows) is int)
	assert(type(n_cols) is int)
	assert(type(alpha_col) is float)
	assert(type(alpha_rows) is float)
	assert(n_rows > 0)
	assert(n_cols > 0)
	assert(alpha_col > 0.0)
	assert(alpha_rows > 0.0)

	column_partition = CRP(n_cols, alpha_col)
	n_views = max(column_partition)+1;	

	row_partition = np.zeros(shape=(n_views,n_rows),dtype=int)

	for i in range(n_views):
		row_partition_tmp = CRP(n_rows, alpha_rows)
		row_partition[i] = row_partition_tmp

	partition = dict();
	partition['col_parts'] = column_partition;
	partition['row_parts'] = row_partition;

	assert(len(column_partition)==n_cols)
	assert(row_partition.shape[0]==n_views)
	assert(row_partition.shape[1]==n_rows)

	return partition

# Generates an N-length partitioning through the Chinese Restauraunt Process 
# with discount parameter alpha
def CRP(N,alpha):
	assert(type(N) is int)
	assert(type(alpha) is float)
	assert(N > 0)
	assert(alpha > 0.0)

	partition = np.zeros(N,dtype=int);

	for i in range(1,N):
		K = max(partition[0:i])+1;
		ps = np.zeros(K+1)
		for k in range(K):
			# get the number of people sitting at table k
			Nk = np.count_nonzero(partition[0:i]==k);
			ps[k] = Nk/(i+alpha)
		
		ps[K] = alpha/(i+alpha)

		assignment = pflip(ps)

		partition[i] = assignment

	assert(len(partition)==N)

	return partition

# flips an n-sided hypercoin
def pflip(P):
	# seed the RNG with system time
	rand.seed(None)
	if type(P) is float:
		if P > 1 or P < 0:
			print "Error: pflip: P is a single value not in [0,1]. P=" + str(P)
		else:
			return 1 if rand.random() > .5 else 0
	elif type(P) is np.ndarray:
		# normalize the list
		P = P/sum(P)
		P = np.cumsum(P)
		rdex = rand.random()
		# return the first entry greater than rdex	
		return np.nonzero(P>rdex)[0][0]
	else:
		print "Error: pflip: P is an invalid type."

# Generates T, M_c, and M_r fitting the state defined by col_part and row_part.
# Generates only continuous data.
def GenDataFromPartitions(col_part,row_parts,mean_gen,std_gen,std_data):
	n_cols = len(col_part)
	n_rows = row_parts.shape[1]

	seed = int(time()*100)
	np.random.seed(seed)

	T = np.zeros((n_rows,n_cols))

	for col in range(n_cols):
		view = col_part[col]
		row_part = row_parts[view,:]
		cats = max(row_part)+1
		for cat in range(cats):
			row_dex = np.nonzero(row_part==cat)[0]
			n_rows_cat = len(row_dex)
			mean = np.random.normal(mean_gen,std_gen)
			X = np.random.normal(mean,std_data,(n_rows_cat,1))
			i = 0
			for row in row_dex:
				T[row,col] = X[i]
				i += 1

	
	T = T.tolist()
	M_r = du.gen_M_r_from_T(T)
	M_c = du.gen_M_c_from_T(T)

	return T, M_r, M_c

# CrossCatPartitions 
# enumerates all states with n_rows rows and n_cols columns. This should not be 
# used for anything bigger than 4-by-4. If you want to generate large states, 
# generate them randomly using GenerateRandomPartition
#
# Attributes:
#	.N 		- The number of states
# 	.states - A list of state dicts. Each state has:
#		['idx'] 	 : an integer index of the state
#		['col_parts']: a n_cols length vector assigning columns to views.
#			Ex. state['col_parts'] = [0 0 1] implies that columns 0 and 1 are 
#				assigned to view 0 and column 2 is assigned to view 1.
#		['row_parts']: a n_views-length list of n_rows-length vectors. 
#			Each entry, i, assigns the row to a category. 
#			Ex. state['row_parts'] = [ [0 0 1], [0 0 0] ] implies that there are
#				two views. In the first view, the rows 0 and 1 are assigned to 
#				category 0 and row 2 is assigned to category 1. In the second 
#				view, all rows are assigned to category 0.
class CrossCatPartitions(object):

	def __init__(self,n_rows, n_cols):
		# Holds the total number of partitionings
		self.N = 0;
		Bn = Bell(n_rows);

		# Generate the column partitons (views)
		self.col_partition = Partition.EnumeratePartitions(n_cols)

		# Generate the possible row partition
		self.row_partition = Partition.EnumeratePartitions(n_rows)

		# each entry of the list row_perms holds the permutation of 
		# row_partition for for each view. So if row_perm[1][2] = (0,2) it means
		# that there are two views in the second view  partitioning and that in 
		# the third permutation that the rows in view 0 are partitions according
		# to self.row_partition[0] and that the rows in the second view are 
		# partitioned according to self.row_partition[2]
		self.row_perms = [];

		# for each partition, generate the partitioning of the rows of each view 
		# into categories (cells)
		for i in range(0,self.col_partition.shape[1]):
			# get the number of partitions
			K = i+1
			r = range(1,int(Bn)+1)

			# generate the permutations with replacement
			perms = [];
			for t in itertools.product(r, repeat = K):
				perms.append(t)

			self.row_perms.append(perms)


		for i in range(0,self.col_partition.shape[0]):
			K = int(self.col_partition[i].max()+1)
			self.N += int(pow(Bn,K))

		self.states = []
		state_idx = 0
		for col_part in range(self.col_partition.shape[0]):
			K = int(max(self.col_partition[col_part])+1)
			n_views = int(max(self.col_partition[col_part])+1)
			# self.states[state_idx]= dict()
			for rprt in range(len(self.row_perms[n_views-1])):
				temp_state = dict()
				temp_state['idx'] = state_idx
				temp_state['col_parts'] = self.col_partition[col_part]
				
				this_row_partition = self.row_perms[n_views-1][rprt][0]-1
				temp_row_parts = np.array([self.row_partition[this_row_partition]])
				for view in range(1,n_views):
					this_row_partition = self.row_perms[n_views-1][rprt][view]-1
					temp_row_parts = np.vstack((temp_row_parts,self.row_partition[this_row_partition]))
				temp_state['row_parts'] = temp_row_parts
				self.states.append(temp_state)
				
				state_idx += 1


	def getState(self, state_num):
		if state_num < 0 or state_num > self.N-1:
			return None
		else:
			return self.states[state_num]

	def findState(self, col_part, row_parts):

		n_views = len(row_parts)

		col_part_cm = vectorToCHMat(col_part);

		for state in range(len(self.states)):
			this_col_part = self.states[state]['col_parts']
			if max(this_col_part) != n_views-1:
				continue

			if not np.all(col_part_cm == vectorToCHMat(this_col_part)):
				continue

			for view in range(n_views):
				this_row_part = self.states[state]['row_parts'][view]
				if np.all(vectorToCHMat(row_parts[view])==vectorToCHMat(this_row_part)):
					if view == n_views-1:
						return self.states[state]['idx']
				else:
					break
			
		print "Error: no state match found"
		return None

	def test(self):
		print "Testing CrossCatPartitions"
		error = False
		# make sure findState returns the appropriate state number
		for state in self.states:
			cols = state['col_parts']
			rows = state['row_parts']
			found_index = self.findState(cols,rows)
			if state['idx'] != found_index:
				error = True
				print " "
				print "findState returned incorrect state (%i instead of %i). " % found_index, state['idx']
				print "Found state: "
				print "Cols"
				print(self.states[found_index]['col_parts'])
				print "Rows"
				print(self.states[found_index]['row_parts'])
				print "Actual state: "
				print "Cols"
				print(cols)
				print "Rows"
				print(rows)
				print " "
			# make sure state mathces after set to zero index
			cols = cols - 1
			rows = rows - 1
			found_index = self.findState(cols,rows)
			if state['idx'] != found_index:
				error = True
				print " "
				print "findState returned incorrect for relabled state (%i instead of %i). " % found_index, state['idx']
				print "Found state: "
				print "Cols"
				print(self.states[found_index]['col_parts'])
				print "Rows"
				print(self.states[found_index]['row_parts'])
				print "Actual state: "
				print "Cols"
				print(cols)
				print "Rows"
				print(rows)
				print " "

		if error:
			print("Test failed.")
		else:
			print("All tests passed.")

# partition class
# The thing we want is the EnumeratePartitions static  method. The Next function 
# doesn't actually stop itself so know that if you're going to try to use this 
# code elsewhere
class Partition(object):

	def __init__(self, N):
		self.N = N
		self.proceed = True
		self.s = np.ones(N, dtype=int)
		self.m = np.ones(N, dtype=int)
		
	# Enumerates the set of all partitionings of N points
	@staticmethod
	def EnumeratePartitions(N):
		p = Partition(N)

		expectedPartitions = Bell(N)
		currentPartition = 2

		C = np.copy(p.s-1)
	    
		while p.proceed:
			p.Next()
			if p.proceed:
				C = np.vstack([C,p.s-1]);
				currentPartition += 1
			else:
				break

			if currentPartition > expectedPartitions:
				break

		return C

	# generates the next partition
	def Next(self):
		n = self.N
		i = 0;
		self.s[i] = self.s[i] + 1;
		while (i < n) and (self.s[i] > self.m[i+1] + 1):
			self.s[i] = 1;
			i += 1;
			self.s[i] += 1
	    
		if self.s[i] > self.m[i]:
			self.m[i] = self.s[i]
        
		for j in range(i-1,-1,-1):
			self.m[j] = self.m[i]
        
		self.proceed = True;
	    

# returns B_N, the Nth Bell number. Uses the definition as a sum of Striling 
# numbers of the second kind. http://en.wikipedia.org/wiki/Bell_number
def Bell(N):
	B_N = 0.0;
	# range(n) produces an array 0,1,...,n-1
	for k in range(N+1):
		snk = Stirling2nd(N,k)
		B_N += snk
	
	return B_N

# Returns the Striling number of the second kind. Math taken from Wikipedia:
# http://en.wikipedia.org/wiki/Stirling_numbers_of_the_second_kind
def Stirling2nd(n,k):
	snk = 0.0;
	const = (1.0/math.factorial(k));
	for j in range(k+1):
		p1 = math.pow(-1,k-j)
		p2 = sp.special.binom(k,j)
		p3 = math.pow(j,n)
		snk += p1*p2*p3
	
	return const*snk

# Log CRP
# log probability of the partitioning, prt, under the CRP with concentration 
# parameter, alpha.
def lcrp(prt,alpha):
	# generate a histogram of prt
	k = max(prt)+1
	ns = np.zeros(k)
	n = len(prt)
	for i in range(n):
		ns[prt[i]] += 1.0

	lp = sum(sp.special.gammaln(ns))+k*math.log(alpha)+sp.special.gammaln(alpha)-sp.special.gammaln(n+alpha)

	if np.any(np.isnan(lp)) or np.any(np.isinf(lp)):
		print("prt: ")
		print(prt)
		print("ns: ")
		print(ns)
		print("n: " + str(n))
		print("k: " + str(k))
		print(range(k))
		print(" ")

	return lp

# Normal-Gamma marginal likelihood 
# Taken from Yee Whye Teh's "The Normal Exponential Family with 
# Normal-Inverse-Gamma Prior"
# http://www.stats.ox.ac.uk/~teh/research/notes/GaussianInverseGamma.pdf
def NGML(X,mu,r,nu,s):

	X = np.array(X.flatten(1))

	# constant
	LOGPI = np.log(math.pi)

	n = float(len(X)) 	# number of data points
	xbar = np.mean(X)	

	# update parameters
	rp  = r + n;
	nup = nu + n;
	mup = (r*mu+sum(X))/(r+n);
	spr = s + sum(X**2)+r*mu**2-rp*mup**2

	# the log answer
	lp1 = (-n/2)*LOGPI - (1/2)*np.log(rp)-(nup/2)*np.log(spr)+sp.special.gammaln(nup/2);
	lp2 = -(1/2)*np.log(r)-(nu/2)*np.log(s)+sp.special.gammaln(nu/2);
	lp = lp1-lp2;

	if np.isnan(lp):
		# print "X"
		# print(X)
		# print "X-xbar"
		# print(X-xbar)
		# print"sum((X-xbar)**2): %f" % sum((X-xbar)**2)
		print "xbar: %f" % xbar
		print "nu_n: %f" % nu_n
		print "mu_n: %f" % mu_n
		print "k_n: %f" % k_n
		print "s_n: %f" % s_n
		print "lp1: %f" % lp1
		print "lp2: %f" % lp2

		sys.exit(0)


	return lp

# CrossCat Marginal Likelihood
# Computes the marginal likelihood of the array of data in ccmat given all 
# possible partitionings of columns and rows of ccmat into views and categories.
# Goes through each partitioning, divides the data up and sequentially sends 
# that data and the priors to NGML, then sums these answers (they're log).
# 	Takes the data array ccmat; the prior mean, M0; the prior variance, V0; the 
# inverse-gamma hyperparameters A0 and B0; and the CRP concentration parameter, 
# alpha.
# 	Returns the log marginal likelohood.
def CCML(ccpart,ccmat,mu,r,nu,s,row_alpha,col_alpha):
	lp = []
	
	ccmat = np.array(ccmat)

	state = ccpart.states[1]

	# loop through the states
	for state in ccpart.states:
		all_cols = state['col_parts']
		all_rows = state['row_parts']

		K = max(all_cols)+1
				
		lp_temp = lcrp(all_cols,col_alpha)
		for view in range(K):
			row_part = all_rows[view,:]
			lp_temp += lcrp(row_part,row_alpha)
			cols_view = np.nonzero(all_cols==view)[0]
			for col in cols_view:
				for cat in range(row_part.max()+1):
					X = ccmat[np.nonzero(row_part==cat)[0],col]
					lp_temp += NGML(X,mu,r,nu,s)

		lp.append(lp_temp);

	# return the normalized probabilities
	return lp-sp.misc.logsumexp(lp)

# Fixes the prior
def FixPriors(X_L,alpha,mu,s,r,nu):
	num_cols = len(X_L['column_partition']['assignments'])
	X_L['column_partition']['hypers']['alpha'] = alpha
	# print(new_X_L)
	for i in range(len(X_L['view_state'])):
		X_L['view_state'][i]['row_partition_model']['hypers']['alpha'] = alpha
	for i in range(num_cols):
		X_L['column_hypers'][i]['alpha'] = alpha
		X_L['column_hypers'][i]['mu']    = mu
		X_L['column_hypers'][i]['s']     = s
		X_L['column_hypers'][i]['r']     = r
		X_L['column_hypers'][i]['nu']    = nu

	return X_L

# Convert assignment vector to cohabitation matrix. A cohabitation matrix is an 
# N-by-N matrix where entry [i,j] = 1 is data points i and j belong to the same
# category and 0 otherwise. This function is used to match sampled states with
# enumerated states to compare the sampler with the enumerated answers.
def vectorToCHMat(col_partition):
	# print(col_partition)
	N = len(col_partition)
	
	chmat = np.zeros((N,N))
	for i in range(N):
		for j in range(N):
			if col_partition[i] == col_partition[j]:
				chmat[i,j] = 1
	return chmat

########NEW FILE########
__FILENAME__ = file_utils
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import cPickle
import gzip
import os
import sys


def is_gz(filename):
    ext = os.path.splitext(filename)[-1]
    return ext == '.gz'

def is_pkl(filename):
    if is_gz(filename):
        filename = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[-1]
    return ext == '.pkl'

def my_open(filename):
    opener = open
    if is_gz(filename):
        opener = gzip.open
    return opener

def pickle(variable, filename, dir=''):
    full_filename = os.path.join(dir, filename)
    opener = my_open(full_filename)
    with opener(full_filename, 'wb') as fh:
        cPickle.dump(variable, fh)

def unpickle(filename, dir=''):
    full_filename = os.path.join(dir, filename)
    opener = my_open(full_filename)
    with opener(full_filename, 'rb') as fh:
        variable = cPickle.load(fh)
    return variable

def rm_local(path, DEBUG=False):
    cmd_str = 'rm -rf %s'
    cmd_str %= path
    if DEBUG:
        print cmd_str
    else:
        os.system(cmd_str)
    return

def ensure_dir(dir):
  try:
    os.makedirs(dir)
  except Exception, e:
    if e.strerror.upper()=='FILE EXISTS':
      pass
    else:
      sys.stderr.write('Could not create dir: %s\n' % dir)
      raise e
  return

########NEW FILE########
__FILENAME__ = general_utils
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import itertools
import inspect
from timeit import default_timer
import datetime
import random
import multiprocessing
import multiprocessing.pool

#http://stackoverflow.com/questions/6974695/python-process-pool-non-daemonic
class NoDaemonProcess(multiprocessing.Process):
    # make 'daemon' attribute always return False
    def _get_daemon(self):
        return False
    def _set_daemon(self, value):
        pass
    daemon = property(_get_daemon, _set_daemon)

class NoDaemonPool(multiprocessing.pool.Pool):
    Process = NoDaemonProcess

class Timer(object):
    def __init__(self, task='action', verbose=True):
        self.task = task
        self.verbose = verbose
        self.timer = default_timer
        self.start = None
    def get_elapsed_secs(self):
        end = self.timer()
        return end - self.start
    def __enter__(self):
        self.start = self.timer()
        return self
    def __exit__(self, *args):
        self.elapsed_secs = self.get_elapsed_secs()
        self.elapsed = self.elapsed_secs * 1000 # millisecs
        if self.verbose:
            print '%s took:\t% 7d ms' % (self.task, self.elapsed)

class MapperContext(object):
    def __init__(self, do_multiprocessing=True, Pool=multiprocessing.Pool,
            *args, **kwargs):
        self.pool = None
        self.map = map
        if do_multiprocessing:
            self.pool = Pool(*args, **kwargs)
            self.map = self.pool.map
            pass
        return

    def __enter__(self):
        return self.map

    def __exit__(self, exc_type, exc_value, traceback):
        if self.pool is not None:
            self.pool.close()
            self.pool.join()
            pass
        return False

def int_generator(start=None):
    if start is None:
        start = random.randrange(32767)
    next_i = start
    while True:
        yield next_i
        next_i += 1

def roundrobin(*iterables):
    "roundrobin('ABC', 'D', 'EF') --> A D E B F C"
    # Recipe credited to George Sakkis
    pending = len(iterables)
    nexts = itertools.cycle(iter(it).next for it in iterables)
    while pending:
        try:
            for next in nexts:
                yield next()
        except StopIteration:
            pending -= 1
            nexts = itertools.cycle(itertools.islice(nexts, pending))

def divide_N_fairly(N, num_partitions):
    _n = N / num_partitions
    ns = [_n] * num_partitions
    delta = N - sum(ns)
    for idx in range(delta):
        ns[idx] += 1
    return ns

# introspection helpers
def is_obj_method_name(obj, method_name):
    attr = getattr(obj, method_name)
    is_method = inspect.ismethod(attr)
    return is_method
#
def get_method_names(obj):
    is_this_obj_method_name = lambda method_name: \
        is_obj_method_name(obj, method_name)
    #
    this_obj_attrs = dir(obj)
    this_obj_method_names = filter(is_this_obj_method_name, this_obj_attrs)
    return this_obj_method_names
#
def get_method_name_to_args(obj):
    method_names = get_method_names(obj)
    method_name_to_args = dict()
    for method_name in method_names:
        method = obj.__dict__[method_name]
        arg_str_list = inspect.getargspec(method).args[1:]
        method_name_to_args[method_name] = arg_str_list
    return method_name_to_args

def get_getname(name):
    return lambda in_dict: in_dict[name]

def print_ts(in_str):
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print_str = '%s:: %s' % (now_str, in_str)
    print print_str

def ensure_listlike(input):
    if not isinstance(input, (list, tuple,)):
        input = [input]
    return input

def get_dict_as_text(parameters, join_with='\n'):
    create_line = lambda (key, value): key + ' = ' + str(value)
    lines = map(create_line, parameters.iteritems())
    text = join_with.join(lines)
    return text

########NEW FILE########
__FILENAME__ = geweke_utils
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import matplotlib
matplotlib.use('Agg')
#
import multiprocessing
import collections
import functools
import operator
import re
import os
import argparse
#
import numpy
import pylab
#
import crosscat.LocalEngine as LE
import crosscat.utils.general_utils as gu
import crosscat.utils.data_utils as du
import crosscat.utils.plot_utils as pu
import crosscat.tests.quality_tests.quality_test_utils as qtu
import experiment_runner.experiment_utils as eu


image_format = 'png'
default_n_grid=31
dirname_prefix='geweke_on_schemas'
result_filename = 'result.pkl'


def sample_T(engine, M_c, T, X_L, X_D):
    row_indices = range(len(T))
    generated_T, T, X_L, X_D = engine.sample_and_insert(M_c, T, X_L, X_D,
            row_indices)
    return generated_T

def collect_diagnostics(X_L, diagnostics_data, diagnostics_funcs):
    for key, func in diagnostics_funcs.iteritems():
        diagnostics_data[key].append(func(X_L))
    return diagnostics_data

def generate_diagnostics_funcs_for_column(X_L, column_idx):
    discard_keys = ['fixed', 'K']
    keys = set(X_L['column_hypers'][column_idx].keys())
    keys = keys.difference(discard_keys)
    def helper(column_idx, key):
        func_name = 'col_%s_%s' % (column_idx, key)
        func = lambda X_L: X_L['column_hypers'][column_idx][key]
        return func_name, func
    diagnostics_funcs = { helper(column_idx, key) for key in keys }
    return diagnostics_funcs

def run_posterior_chain_iter(engine, M_c, T, X_L, X_D, diagnostics_data,
        diagnostics_funcs,
        ROW_CRP_ALPHA_GRID,
        COLUMN_CRP_ALPHA_GRID,
        S_GRID, MU_GRID,
        N_GRID,
        CT_KERNEL
        ):
    X_L, X_D = engine.analyze(M_c, T, X_L, X_D,
                S_GRID=S_GRID,
                ROW_CRP_ALPHA_GRID=ROW_CRP_ALPHA_GRID,
                COLUMN_CRP_ALPHA_GRID=COLUMN_CRP_ALPHA_GRID,
                MU_GRID=MU_GRID,
                N_GRID=N_GRID,
                CT_KERNEL=CT_KERNEL,
                )
    diagnostics_data = collect_diagnostics(X_L, diagnostics_data,
            diagnostics_funcs)
    T = sample_T(engine, M_c, T, X_L, X_D)
    return M_c, T, X_L, X_D

def arbitrate_plot_rand_idx(plot_rand_idx, num_iters):
    if plot_rand_idx is not None:
        if type(plot_rand_idx) == bool:
            if plot_rand_idx:
                plot_rand_idx = numpy.random.randint(num_iters)
            else:
                plot_rand_idx = None
                pass
            pass
        pass
    return plot_rand_idx

get_column_crp_alpha = lambda X_L: X_L['column_partition']['hypers']['alpha']
get_view_0_crp_alpha = lambda X_L: X_L['view_state'][0]['row_partition_model']['hypers']['alpha']
default_diagnostics_funcs = dict(
        column_crp_alpha=get_column_crp_alpha,
        view_0_crp_alpha=get_view_0_crp_alpha,
        )
def generate_diagnostics_funcs(X_L, probe_columns):
    diagnostics_funcs = default_diagnostics_funcs.copy()
    for probe_column in probe_columns:
        funcs_to_add = generate_diagnostics_funcs_for_column(X_L, probe_column)
        diagnostics_funcs.update(funcs_to_add)
        pass
    return diagnostics_funcs

def run_posterior_chain(seed, M_c, T, num_iters,
        probe_columns=(0,),
        ROW_CRP_ALPHA_GRID=(), COLUMN_CRP_ALPHA_GRID=(),
        S_GRID=(), MU_GRID=(),
        N_GRID=default_n_grid,
        CT_KERNEL=0,
        plot_rand_idx=None,
        ):
    plot_rand_idx = arbitrate_plot_rand_idx(plot_rand_idx, num_iters)
    engine = LE.LocalEngine(seed)
    M_r = du.gen_M_r_from_T(T)
    X_L, X_D = engine.initialize(M_c, M_r, T, 'from_the_prior',
            ROW_CRP_ALPHA_GRID=ROW_CRP_ALPHA_GRID,
            COLUMN_CRP_ALPHA_GRID=COLUMN_CRP_ALPHA_GRID,
            S_GRID=S_GRID,
            MU_GRID=MU_GRID,
            N_GRID=N_GRID,
            )
    diagnostics_funcs = generate_diagnostics_funcs(X_L, probe_columns)
    diagnostics_data = collections.defaultdict(list)
    for idx in range(num_iters):
        M_c, T, X_L, X_D = run_posterior_chain_iter(engine, M_c, T, X_L, X_D, diagnostics_data,
                diagnostics_funcs,
                ROW_CRP_ALPHA_GRID,
                COLUMN_CRP_ALPHA_GRID,
                S_GRID, MU_GRID,
                N_GRID=N_GRID,
                CT_KERNEL=CT_KERNEL,
                )
        if idx == plot_rand_idx:
            # This DOESN'T work with multithreading
            filename = 'T_%s' % idx
            pu.plot_views(numpy.array(T), X_D, X_L, M_c, filename=filename,
                    dir='./', close=True, format=image_format)
            pass
        pass
    return diagnostics_data

def run_posterior_chains(M_c, T, num_chains, num_iters, probe_columns,
        row_crp_alpha_grid, column_crp_alpha_grid,
        s_grid, mu_grid,
        N_GRID=default_n_grid,
        CT_KERNEL=0,
        ):
    # run geweke: transition-erase loop
    helper = functools.partial(run_posterior_chain, M_c=M_c, T=T, num_iters=num_iters,
            probe_columns=probe_columns,
            ROW_CRP_ALPHA_GRID=row_crp_alpha_grid,
            COLUMN_CRP_ALPHA_GRID=column_crp_alpha_grid,
            S_GRID=s_grid,
            MU_GRID=mu_grid,
            N_GRID=N_GRID,
            CT_KERNEL=CT_KERNEL,
            # this breaks with multiprocessing
            plot_rand_idx=(num_chains==1),
            )
    seeds = range(num_chains)
    do_multiprocessing = num_chains != 1
    with gu.MapperContext(do_multiprocessing) as mapper:
        diagnostics_data_list = mapper(helper, seeds)
        pass
    return diagnostics_data_list

def _forward_sample_from_prior(inf_seed_and_n_samples, M_c, T,
        probe_columns=(0,),
        ROW_CRP_ALPHA_GRID=(), COLUMN_CRP_ALPHA_GRID=(),
        S_GRID=(), MU_GRID=(),
        N_GRID=default_n_grid,
        ):
    inf_seed, n_samples = inf_seed_and_n_samples
    T = numpy.zeros(numpy.array(T).shape).tolist()
    M_r = du.gen_M_r_from_T(T)
    engine = LE.LocalEngine(inf_seed)
    diagnostics_data = collections.defaultdict(list)
    diagnostics_funcs = None
    for sample_idx in range(n_samples):
        X_L, X_D = engine.initialize(M_c, M_r, T,
                ROW_CRP_ALPHA_GRID=ROW_CRP_ALPHA_GRID,
                COLUMN_CRP_ALPHA_GRID=COLUMN_CRP_ALPHA_GRID,
                S_GRID=S_GRID,
                MU_GRID=MU_GRID,
                N_GRID=N_GRID,
                )
        if diagnostics_funcs is None:
            diagnostics_funcs = generate_diagnostics_funcs(X_L, probe_columns)
        diagnostics_data = collect_diagnostics(X_L, diagnostics_data,
                diagnostics_funcs)
        pass
    return diagnostics_data

def forward_sample_from_prior(inf_seed, n_samples, M_c, T,
        probe_columns=(0,),
        ROW_CRP_ALPHA_GRID=(), COLUMN_CRP_ALPHA_GRID=(),
        S_GRID=(), MU_GRID=(),
        do_multiprocessing=True,
        N_GRID=default_n_grid,
        ):
    helper = functools.partial(_forward_sample_from_prior, M_c=M_c, T=T,
            probe_columns=probe_columns,
            ROW_CRP_ALPHA_GRID=ROW_CRP_ALPHA_GRID,
            COLUMN_CRP_ALPHA_GRID=COLUMN_CRP_ALPHA_GRID,
            S_GRID=S_GRID,
            MU_GRID=MU_GRID,
            N_GRID=N_GRID,
            )
    cpu_count = 1 if not do_multiprocessing else multiprocessing.cpu_count()
    with gu.MapperContext(do_multiprocessing) as mapper:
        seeds = numpy.random.randint(32676, size=cpu_count)
        n_samples_list = gu.divide_N_fairly(n_samples, cpu_count)
        forward_sample_data_list = mapper(helper, zip(seeds, n_samples_list))
        forward_sample_data = condense_diagnostics_data_list(forward_sample_data_list)
    return forward_sample_data

def condense_diagnostics_data_list(diagnostics_data_list):
    def get_key_condensed(key):
        get_key = lambda x: x.get(key)
        return reduce(operator.add, map(get_key, diagnostics_data_list))
    keys = diagnostics_data_list[0].keys()
    return { key : get_key_condensed(key) for key in keys}

def generate_bins_unique(data):
    bins = sorted(set(data))
    delta = bins[-1] - bins[-2]
    bins.append(bins[-1] + delta)
    return bins

def do_hist_labelling(variable_name):
    title_str = 'Histogram for %s' % variable_name
    pylab.title(title_str)
    pylab.xlabel(variable_name)
    pylab.ylabel('frequency')
    return

def do_log_hist_bin_unique(variable_name, diagnostics_data, new_figure=True,
        do_labelling=True,
        ):
    data = diagnostics_data[variable_name]
    bins = generate_bins_unique(data)
    if new_figure:
        pylab.figure()
    hist_ret = pylab.hist(data, bins=bins)
    if do_labelling:
        do_hist_labelling(variable_name)
    pylab.gca().set_xscale('log')
    return hist_ret

def do_hist(variable_name, diagnostics_data, n_bins=31, new_figure=True,
        do_labelling=True,
        ):
    data = diagnostics_data[variable_name]
    if new_figure:
        pylab.figure()
    pylab.hist(data, bins=n_bins)
    if do_labelling:
        do_hist_labelling(variable_name)
    return

hyper_name_mapper = dict(
        s='precision hyperparameter value',
        nu='precision hyperparameter psuedo count',
        mu='mean hyperparameter value',
        r='mean hyperparameter psuedo count',
        )
col_hyper_re = re.compile('^col_([^_]*)_(.*)$')
def map_variable_name(variable_name):
    mapped_variable_name = variable_name
    match = col_hyper_re.match(variable_name)
    if match is not None:
        column_idx, hyper_name = match.groups()
        mapped_hyper_name = hyper_name_mapper.get(hyper_name, hyper_name)
        mapped_variable_name = 'column %s %s' % (column_idx, mapped_hyper_name)
        pass
    return mapped_variable_name

plotter_lookup = collections.defaultdict(lambda: do_log_hist_bin_unique,
        col_0_s=do_hist,
        col_0_mu=do_hist,
        col_0_r=do_hist,
        col_0_nu=do_hist,
        )

def plot_diagnostic_data(forward_diagnostics_data, diagnostics_data_list,
        kl_series_list, variable_name,
        parameters=None, save_kwargs=None,
        ):
    plotter = plotter_lookup[variable_name]
    mapped_variable_name = map_variable_name(variable_name)
    which_idx = numpy.random.randint(len(diagnostics_data_list))
    diagnostics_data = diagnostics_data_list[which_idx]
    forward = forward_diagnostics_data[variable_name]
    not_forward_list = [el[variable_name] for el in diagnostics_data_list]
    pylab.figure()
    #
    pylab.subplot(311)
    pylab.title('Geweke analysis for %s' % mapped_variable_name)
    plotter(variable_name, forward_diagnostics_data, new_figure=False,
            do_labelling=False)
    pylab.ylabel('Forward samples\n mass')
    #
    pylab.subplot(312)
    plotter(variable_name, diagnostics_data, new_figure=False,
            do_labelling=False)
    pylab.ylabel('Posterior samples\n mass')
    #
    pylab.subplot(313)
    map(pylab.plot, kl_series_list)
    pylab.xlabel('iteration')
    pylab.ylabel('KL')
    # FIXME: remove, or do something "better"
    pylab.gca().set_ylim((0., 0.1))
    if parameters is not None:
        pu.show_parameters(parameters)
        pass
    if save_kwargs is not None:
        filename = variable_name + '_hist.png'
        pu.save_current_figure(filename, format=image_format, **save_kwargs)
        #
        filename = variable_name + '_pp.png'
        pylab.figure()
        for not_forward in not_forward_list:
            pp_plot(forward, not_forward, 100)
            pass
        pu.save_current_figure(filename, format=image_format, **save_kwargs)
        pass
    return

def plot_all_diagnostic_data(forward_diagnostics_data, diagnostics_data_list,
        kl_series_list_dict,
        parameters=None, save_kwargs=None,
        ):
    for variable_name in forward_diagnostics_data.keys():
        print 'plotting for variable: %s' % variable_name
        try:
            kl_series_list = kl_series_list_dict[variable_name]
            plot_diagnostic_data(forward_diagnostics_data, diagnostics_data_list,
                    kl_series_list,
                    variable_name, parameters, save_kwargs)
        except Exception, e:
            print 'Failed to plot_diagnostic_data for %s' % variable_name
            print e
            pass
    return

def make_same_length(*args):
    return zip(*zip(*args))

def get_count((values, bins)):
    return numpy.histogram(values, bins)[0]

def get_log_density_series(values, bins):
    bin_widths = numpy.diff(bins)
    #
    with gu.MapperContext() as mapper:
        counts = mapper(get_count, [(el, bins) for el in values])
        pass
    counts = numpy.vstack(counts).cumsum(axis=0)
    #
    ratios = counts / numpy.arange(1., len(counts) + 1.)[:, numpy.newaxis]
    densities = ratios / bin_widths[numpy.newaxis, :]
    log_densities = numpy.log(densities)
    return log_densities

def _get_kl(grid, true_series, inferred_series):
    kld = numpy.nan
    bad_value = -numpy.inf
    has_support = lambda series: sum(series==bad_value) == 0
    true_has_support = has_support(true_series)
    inferred_has_support = has_support(inferred_series)
    if true_has_support and inferred_has_support:
        kld = qtu.KL_divergence_arrays(grid, true_series,
                inferred_series, False)
        pass
    return kld

def _get_kl_tuple((grid, true_series, inferred_series)):
    return _get_kl(grid, true_series, inferred_series)

def get_fixed_gibbs_kl_series(forward, not_forward):
    forward, not_forward = make_same_length(forward, not_forward)
    forward, not_forward = map(numpy.array, (forward, not_forward))
    grid = numpy.array(sorted(set(forward).union(not_forward)))
    kls = numpy.repeat(numpy.nan, len(forward))
    try:
        bins = numpy.append(grid, grid[-1] + numpy.diff(grid)[-1])
        #
        log_true_series = get_log_density_series(forward, bins)
        log_inferred_series = get_log_density_series(not_forward, bins)
        arg_tuples = [
                (grid, x, y)
                for x, y in zip(log_true_series, log_inferred_series)
                ]
        with gu.MapperContext() as mapper:
            kls = mapper(_get_kl_tuple, arg_tuples)
            pass
    except Exception, e:
        # this definitley happens if len(grid) == 1; as in column crp alpha for
        # single column model
        pass
    return kls

def arbitrate_mu_s(num_rows, max_mu_grid=100, max_s_grid=None):
    if max_s_grid == -1:
        max_s_grid = (max_mu_grid ** 2.) / 3. * num_rows
    return max_mu_grid, max_s_grid

def write_parameters_to_text(parameters, filename, dirname='./'):
    full_filename = os.path.join(dirname, filename)
    text = gu.get_dict_as_text(parameters)
    with open(full_filename, 'w') as fh:
        fh.writelines(text + '\n')
        pass
    return

def gen_M_c(cctypes, num_values_list):
    num_cols = len(cctypes)
    colnames = range(num_cols)
    col_indices = range(num_cols)
    def helper(cctype, num_values):
        metadata_generator = du.metadata_generator_lookup[cctype]
        faux_data = range(num_values)
        return metadata_generator(faux_data)
    #
    name_to_idx = dict(zip(colnames, col_indices))
    idx_to_name = dict(zip(map(str, col_indices), colnames))
    column_metadata = map(helper, cctypes, num_values_list)
    M_c = dict(
        name_to_idx=name_to_idx,
        idx_to_name=idx_to_name,
        column_metadata=column_metadata,
        )
    return M_c

def pp_plot(_f, _p, nbins):
    ff, edges = numpy.histogram(_f, bins=nbins, density=True)
    fp, _ = numpy.histogram(_p, bins=edges, density=True)
    Ff = numpy.cumsum(ff*(edges[1:]-edges[:-1]))
    Fp = numpy.cumsum(fp*(edges[1:]-edges[:-1]))
    pylab.plot([0,1],[0,1],c='black', ls='--')
    pylab.plot(Ff,Fp, c='black')
    pylab.xlim([0,1])
    pylab.ylim([0,1])
    return

def generate_kl_series_list_dict(forward_diagnostics_data,
        diagnostics_data_list):
    kl_series_list_dict = dict()
    for variable_name in forward_diagnostics_data:
        forward = forward_diagnostics_data[variable_name]
        not_forward_list = [el[variable_name] for el in diagnostics_data_list]
        kl_series_list = [
                get_fixed_gibbs_kl_series(forward, not_forward)
                for not_forward in not_forward_list
                ]
        kl_series_list_dict[variable_name] = kl_series_list
        pass
    return kl_series_list_dict

def post_process(forward_diagnostics_data, diagnostics_data_list):
    get_final = lambda indexable: indexable[-1]
    #
    kl_series_list_dict = generate_kl_series_list_dict(forward_diagnostics_data,
            diagnostics_data_list)
    final_kls = {
            key : map(get_final, value)
            for key, value in kl_series_list_dict.iteritems()
            }
    summary_kls = {
            key : numpy.mean(value)
            for key, value in final_kls.iteritems()
            }
    return dict(
            kl_series_list_dict=kl_series_list_dict,
            final_kls=final_kls,
            summary_kls=summary_kls,
            )

def run_geweke(config):
    num_rows = config['num_rows']
    num_cols = config['num_cols']
    inf_seed = config['inf_seed']
    gen_seed = config['gen_seed']
    num_chains = config['num_chains']
    num_iters = config['num_iters']
    row_crp_alpha_grid = config['row_crp_alpha_grid']
    column_crp_alpha_grid = config['column_crp_alpha_grid']
    max_mu_grid = config['max_mu_grid']
    max_s_grid = config['max_s_grid']
    n_grid = config['n_grid']
    cctypes = config['cctypes']
    num_multinomial_values = config['num_multinomial_values']
    probe_columns = config['probe_columns']
    CT_KERNEL=config['CT_KERNEL']


    num_values_list = [num_multinomial_values] * num_cols
    M_c = gen_M_c(cctypes, num_values_list)
    T = numpy.random.uniform(0, 10, (num_rows, num_cols)).tolist()
    # may be an issue if this n_grid doesn't match the other grids in the c++
    mu_grid = numpy.linspace(-max_mu_grid, max_mu_grid, n_grid)
    s_grid = numpy.linspace(1, max_s_grid, n_grid)

    # run geweke: forward sample only
    with gu.Timer('generating forward samples') as timer:
        forward_diagnostics_data = forward_sample_from_prior(inf_seed,
                num_iters, M_c, T, probe_columns,
                row_crp_alpha_grid, column_crp_alpha_grid,
                s_grid, mu_grid,
                do_multiprocessing=True,
                N_GRID=n_grid,
                )
    # run geweke: transition-erase loop
    with gu.Timer('generating posterior samples') as timer:
        diagnostics_data_list = run_posterior_chains(M_c, T, num_chains, num_iters, probe_columns,
                row_crp_alpha_grid, column_crp_alpha_grid,
                s_grid, mu_grid,
                N_GRID=n_grid,
                CT_KERNEL=CT_KERNEL,
                )
    # post process data
    with gu.Timer('post prcessing data') as timer:
        processed_data = post_process(forward_diagnostics_data, diagnostics_data_list)
    result = dict(
            config=config,
            summary=processed_data['summary_kls'],
            forward_diagnostics_data=forward_diagnostics_data,
            diagnostics_data_list=diagnostics_data_list,
            processed_data=processed_data,
            )
    return result

parameters_to_show = ['num_rows', 'num_cols', 'max_mu_grid', 'max_s_grid',
    'n_grid', 'num_iters', 'num_chains', 'CT_KERNEL',]
def plot_result(result, dirname='./'):
    # extract variables
    config = result['config']
    forward_diagnostics_data = result['forward_diagnostics_data']
    diagnostics_data_list = result['diagnostics_data_list']
    processed_data = result['processed_data']
    kl_series_list_dict = processed_data['kl_series_list_dict']
    #
    _dirname = eu._generate_dirname(dirname_prefix, 10, config)
    save_kwargs = dict(dir=os.path.join(dirname, _dirname))
    get_tuple = lambda parameter: (parameter, config[parameter])
    parameters = dict(map(get_tuple, parameters_to_show))
    if 'cctypes' in config:
        # FIXME: remove this kludgy if statement
        counter = collections.Counter(config['cctypes'])
        parameters['Counter(cctypes)'] = dict(counter.items())
        pass
    #
    plot_all_diagnostic_data(
            forward_diagnostics_data, diagnostics_data_list,
            kl_series_list_dict,
            parameters, save_kwargs)
    return

def generate_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--num_rows', default=10, type=int)
    parser.add_argument('--num_cols', default=2, type=int)
    parser.add_argument('--inf_seed', default=0, type=int)
    parser.add_argument('--gen_seed', default=0, type=int)
    parser.add_argument('--num_chains', default=None, type=int)
    parser.add_argument('--num_iters', default=1000, type=int)
    parser.add_argument('--row_crp_alpha_grid', nargs='+', default=None, type=float)
    parser.add_argument('--column_crp_alpha_grid', nargs='+', default=None, type=float)
    parser.add_argument('--_divisor', default=1., type=float)

    parser.add_argument('--max_mu_grid', default=10, type=int)
    parser.add_argument('--max_s_grid', default=100, type=int)
    parser.add_argument('--n_grid', default=31, type=int)
    parser.add_argument('--CT_KERNEL', default=0, type=int)
    parser.add_argument('--num_multinomial_values', default=2, type=int)
    parser.add_argument('--cctypes', nargs='*', default=None, type=str)
    parser.add_argument('--probe_columns', nargs='*', default=None, type=str)
    return parser

def _gen_grid(N, n_grid, _divisor=1.):
    return numpy.linspace(1., N / _divisor, n_grid).tolist()

def arbitrate_args(args):
    if args.num_chains is None:
        args.num_chains = min(4, multiprocessing.cpu_count())
    if args.probe_columns is None:
        args.probe_columns = (0, 1) if args.num_cols > 1 else (0,)
    if args.cctypes is None:
        args.cctypes = ['continuous'] + ['multinomial'] * (args.num_cols - 1)
    assert len(args.cctypes) == args.num_cols
    args.max_mu_grid, args.max_s_grid = arbitrate_mu_s(args.num_rows,
            args.max_mu_grid, args.max_s_grid)
    if args.row_crp_alpha_grid is None:
       args.row_crp_alpha_grid = _gen_grid(args.num_rows, args.n_grid,
               args._divisor)
    if args.column_crp_alpha_grid is None:
        args.column_crp_alpha_grid = _gen_grid(args.num_cols, args.n_grid,
                args._divisor)
    return args

def get_chisquare(not_forward, forward=None):
    def get_sorted_counts(values):
        get_count = lambda (value, count): count
        tuples = sorted(collections.Counter(values).items())
        return map(get_count, counts)
    args = (not_forward, forward)
    args = filter(None, args)
    args = map(get_sorted_counts, args)
    return stats.chisquare(*args)

def generate_ks_stats_list(diagnostics_data_list, forward_diagnostics_data):
    from scipy import stats
    ks_stats_list = list()
    for diagnostics_data in diagnostics_data_list:
        ks_stats = dict()
        for variable_name in diagnostics_data.keys():
            stat, p = stats.ks_2samp(diagnostics_data[variable_name],
                    forward_diagnostics_data[variable_name])
            ks_stats[variable_name] = stat, p
            pass
        ks_stats_list.append(ks_stats)
        pass
    return ks_stats_list

def generate_chi2_stats_list(diagnostics_data_list, forward_diagnostics_data):
    chi2_stats_list = list()
    for diagnostics_data in diagnostics_data_list:
        chi2_stats = dict()
        for variable_name in forward_diagnostics_data.keys():
            not_forward = diagnostics_data[variable_name]
            forward = forward_diagnostics_data[variable_name]
            #chi2 = get_chisquare(not_forward, forward)
            chi2 = get_chisquare(not_forward)
            chi2_stats[variable_name] = chi2
            pass
        chi2_stats_list.append(chi2_stats)
        pass
    return chi2_stats_list


if __name__ == '__main__':
    # parse input
    parser = generate_parser()
    args = parser.parse_args()
    args = arbitrate_args(args)
    config = args.__dict__

    # the bulk of the work
    result_dict = run_geweke(config)
    plot_result(result_dict)
    #write_result(result_dict)

########NEW FILE########
__FILENAME__ = hadoop_utils
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import os
#
import crosscat.utils.xnet_utils as xu
import crosscat.utils.file_utils as fu


def rm_hdfs(hdfs_uri, path, hdfs_base_dir='', DEBUG=False):
    rm_infix_args = '-rmr'
    # rm_infix_args = '-rm -r -f'
    hdfs_path = os.path.join(hdfs_base_dir, path)
    fs_str = ('-fs "%s"' % hdfs_uri) if hdfs_uri is not None else ''
    cmd_str = 'hadoop fs %s %s %s >rm_hdfs.out 2>rm_hdfs.err'
    cmd_str %= (fs_str, rm_infix_args, hdfs_path)
    if DEBUG:
        print cmd_str
        return cmd_str
    else:
        os.system(cmd_str)
    return

def get_hdfs(hdfs_uri, path, hdfs_base_dir='', DEBUG=False):
    hdfs_path = os.path.join(hdfs_base_dir, path)
    # clear local path
    fu.rm_local(path)
    # get from hdfs
    fs_str = ('-fs "%s"' % hdfs_uri) if hdfs_uri is not None else ''
    cmd_str = 'hadoop fs %s -get %s %s'
    cmd_str %= (fs_str, hdfs_path, path)
    if DEBUG:
        print cmd_str
        return cmd_str
    else:
        os.system(cmd_str)
    return

def ensure_dir_hdfs(fs_str, hdfs_path, DEBUG=False):
  dirname = os.path.split(hdfs_path)[0]
  cmd_str = 'hadoop fs %s -mkdir %s'
  cmd_str %= (fs_str, dirname)
  if DEBUG:
    print cmd_str
    return cmd_str
  else:
    os.system(cmd_str)
  return

def put_hdfs(hdfs_uri, path, hdfs_base_dir='', DEBUG=False):
    hdfs_path = os.path.join(hdfs_base_dir, path)
    # clear hdfs path
    rm_hdfs(hdfs_uri, path, hdfs_base_dir)
    # put to hdfs
    fs_str = ('-fs "%s"' % hdfs_uri) if hdfs_uri is not None else ''
    ensure_dir_hdfs(fs_str, hdfs_path)
    cmd_str = 'hadoop fs %s -put %s %s >put_hdfs.out 2>put_hdfs.err'
    cmd_str %= (fs_str, path, hdfs_path)
    if DEBUG:
        print cmd_str
        return cmd_str
    else:
        os.system(cmd_str)
    return

def create_hadoop_cmd_str(hdfs_uri, hdfs_dir, jobtracker_uri,
        which_engine_binary, which_hadoop_binary, which_hadoop_jar,
        input_filename, table_data_filename, command_dict_filename, output_path,
        n_tasks=1, one_map_task_per_line=True,
        task_timeout=60000000):
    if hdfs_uri is None:
        hdfs_uri = "hdfs://"
    hdfs_path = os.path.join(hdfs_uri, hdfs_dir)
    # note: hdfs_path is hdfs_dir is omitted
    archive_path = hdfs_uri + which_engine_binary
    engine_binary_infix = os.path.splitext(os.path.split(which_engine_binary)[-1])[0]
    ld_library_path = os.environ.get('LD_LIBRARY_PATH', '')
    ld_library_path = './%s.jar:%s' % (engine_binary_infix, ld_library_path)
    mapper_path = '%s.jar/%s' % (engine_binary_infix, 'hadoop_line_processor') # engine_binary_infix)
    #
    jar_str = '%s jar %s' % (which_hadoop_binary,
                             which_hadoop_jar)
    archive_str = '-archives "%s"' % archive_path
    cmd_env_str = '-cmdenv LD_LIBRARY_PATH=%s' % ld_library_path
    #
    fs_str = '-fs "%s"' % hdfs_uri if hdfs_uri is not None else ''
    jt_str = '-jt "%s"' % jobtracker_uri if jobtracker_uri is not None else ''
    #
    input_format_str = '-inputformat org.apache.hadoop.mapred.lib.NLineInputFormat' if one_map_task_per_line else ''
    hadoop_cmd_str = ' '.join([
            jar_str,
            '-D mapred.task.timeout=%s' % task_timeout,
            '-D mapred.map.tasks=%s' % n_tasks,
            '-D mapred.child.java.opts=-Xmx8G',
            archive_str,
            fs_str,
	    jt_str,
            input_format_str,
            '-input "%s"' % os.path.join(hdfs_path, input_filename),
            '-output "%s"' % os.path.join(hdfs_path, output_path),
            '-mapper "%s"' % mapper_path,
            '-reducer /bin/cat',
            '-file %s' % table_data_filename,
            '-file %s' % command_dict_filename,
            cmd_env_str,
            ])
    print hadoop_cmd_str
    return hadoop_cmd_str

def get_was_successful(output_path):
    success_file = os.path.join(output_path, '_SUCCESS')
    was_successful = os.path.isfile(success_file)
    return was_successful

def send_hadoop_command(hdfs_uri, hdfs_dir, jobtracker_uri,
      which_engine_binary, which_hadoop_binary, which_hadoop_jar,
      input_filename, table_data_filename, command_dict_filename, output_path,
      n_tasks=1, one_map_task_per_line=True,
      task_timeout=60000000, DEBUG=False):
  # make sure output_path doesn't exist
  rm_hdfs(hdfs_uri, output_path, hdfs_base_dir=hdfs_dir)
  # send up input
  put_hdfs(hdfs_uri, input_filename, hdfs_base_dir=hdfs_dir)
  # actually send
  hadoop_cmd_str = create_hadoop_cmd_str(hdfs_uri, hdfs_dir, jobtracker_uri,
      which_engine_binary, which_hadoop_binary, which_hadoop_jar,
      input_filename, table_data_filename, command_dict_filename, output_path,
      n_tasks, one_map_task_per_line,
      task_timeout)
  was_successful = None
  if DEBUG:
    print hadoop_cmd_str
    return hadoop_cmd_str
  else:
    fu.ensure_dir(output_path)
    output_path_dotdot = os.path.split(output_path)[0]
    out_filename = os.path.join(output_path_dotdot, 'out')
    err_filename = os.path.join(output_path_dotdot, 'err')
    redirect_str = '>>%s 2>>%s'
    redirect_str %= (out_filename, err_filename)
    # could I nohup and check hdfs for presence of _SUCCESS every N seconds?
    # cmd_str = ' '.join(['nohup', hadoop_cmd_str, redirect_str, '&'])
    cmd_str = ' '.join([hadoop_cmd_str, redirect_str])
    os.system(cmd_str)
  return

def get_hadoop_results(hdfs_uri, output_path, hdfs_dir):
    get_hdfs(hdfs_uri, output_path,
             hdfs_base_dir=hdfs_dir)
    was_successful = get_was_successful(output_path)
    return was_successful
  
def write_hadoop_input():
    pass

def get_hadoop_output_filename(output_path):
    hadoop_output_filename = os.path.join(output_path, 'part-00000')
    return hadoop_output_filename
def read_hadoop_output_file(hadoop_output_filename):
    with open(hadoop_output_filename) as fh:
        ret_dict = dict([xu.parse_hadoop_line(line) for line in fh])
    return ret_dict
def copy_hadoop_output(output_path, copy_to_filename):
    hadoop_output_filename = get_hadoop_output_filename(output_path)
    cmd_str = 'cp %s %s' % (hadoop_output_filename, copy_to_filename)
    os.system(cmd_str)
    return
def read_hadoop_output(output_path):
    hadoop_output_filename = get_hadoop_output_filename(output_path)
    hadoop_output = read_hadoop_output_file(hadoop_output_filename)
    X_L_list = [el['X_L'] for el in hadoop_output.values()]
    X_D_list = [el['X_D'] for el in hadoop_output.values()]
    return X_L_list, X_D_list

def get_uris(base_uri, hdfs_uri, jobtracker_uri):
    if base_uri is not None:
        hdfs_uri = 'hdfs://%s:8020/' % base_uri
        jobtracker_uri = '%s:8021' % base_uri
    return hdfs_uri, jobtracker_uri

########NEW FILE########
__FILENAME__ = inference_utils
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
from scipy.misc import logsumexp
import numpy
import random
import math

import crosscat.cython_code.ContinuousComponentModel as CCM
import crosscat.cython_code.MultinomialComponentModel as MCM
import crosscat.utils.sample_utils as su


def mutual_information_to_linfoot(MI):
    return (1.0-math.exp(-2.0*MI))**0.5

# return the estimated mutual information for each pair of columns on Q given
# the set of samples in X_Ls and X_Ds. Q is a list of tuples where each tuple
# contains X and Y, the columns to compare. 
# Q = [(X_1, Y_1), (X_2, Y_2), ..., (X_n, Y_n)]
# Returns a list of list where each sublist is a set of MI's and Linfoots from
# each crosscat posterior sample. 
# See tests/test_mutual_information.py and 
# tests/test_mutual_information_vs_correlation.py for useage examples
def mutual_information(M_c, X_Ls, X_Ds, Q, n_samples=1000):
    #
    assert(len(X_Ds) == len(X_Ls))
    n_postertior_samples = len(X_Ds)

    n_rows = len(X_Ds[0][0])
    n_cols = len(M_c['column_metadata'])

    MI = []
    Linfoot = []
    NMI = []

    get_next_seed = lambda: random.randrange(32767)

    for query in Q:
        assert(len(query) == 2)
        assert(query[0] >= 0 and query[0] < n_cols)
        assert(query[1] >= 0 and query[1] < n_cols)

        X = query[0]
        Y = query[1]

        MI_sample = []
        Linfoot_sample = []
        
        for sample in range(n_postertior_samples):
            
            X_L = X_Ls[sample]
            X_D = X_Ds[sample]

            MI_s = estimiate_MI_sample(X, Y, M_c, X_L, X_D, get_next_seed, n_samples=n_samples)

            linfoot = mutual_information_to_linfoot(MI_s)
            
            MI_sample.append(MI_s)

            Linfoot_sample.append(linfoot)

        MI.append(MI_sample)
        Linfoot.append(Linfoot_sample)

         
    assert(len(MI) == len(Q))
    assert(len(Linfoot) == len(Q))

    return MI,  Linfoot

# estimates the mutual information for columns X and Y.
def estimiate_MI_sample(X, Y, M_c, X_L, X_D, get_next_seed, n_samples=1000):
    
    get_view_index = lambda which_column: X_L['column_partition']['assignments'][which_column]

    view_X = get_view_index(X)
    view_Y = get_view_index(Y)

    # independent
    if view_X != view_Y:
        return 0.0

    # get cluster logps
    view_state = X_L['view_state'][view_X]
    cluster_logps = su.determine_cluster_crp_logps(view_state)
    cluster_crps = numpy.exp(cluster_logps) # get exp'ed values for multinomial
    n_clusters = len(cluster_crps)

    # get components models for each cluster for columns X and Y
    component_models_X = [0]*n_clusters
    component_models_Y = [0]*n_clusters
    for i in range(n_clusters):
        cluster_models = su.create_cluster_model_from_X_L(M_c, X_L, view_X, i)
        component_models_X[i] = cluster_models[X]
        component_models_Y[i] = cluster_models[Y]

    MI = 0.0    # mutual information

    for _ in range(n_samples):
        # draw a cluster 
        cluster_idx = numpy.nonzero(numpy.random.multinomial(1, cluster_crps))[0][0]

        # get a sample from each cluster
        x = component_models_X[cluster_idx].get_draw(get_next_seed())
        y = component_models_Y[cluster_idx].get_draw(get_next_seed())

        # calculate marginal logs
        Pxy = numpy.zeros(n_clusters)   # P(x,y), Joint distribution
        Px = numpy.zeros(n_clusters)    # P(x)
        Py = numpy.zeros(n_clusters)    # P(y)

        # get logp of x and y in each cluster. add cluster logp's
        for j in range(n_clusters):

            Px[j] = component_models_X[j].calc_element_predictive_logp(x)
            Py[j] = component_models_Y[j].calc_element_predictive_logp(y)
            Pxy[j] = Px[j] + Py[j] + cluster_logps[j]   # \sum_c P(x|c)P(y|c)P(c), Joint distribution
            Px[j] += cluster_logps[j]                   # \sum_c P(x|c)P(c)
            Py[j] += cluster_logps[j]                   # \sum_c P(y|c)P(c)    

        # pdb.set_trace()
        
        # sum over clusters
        Px = logsumexp(Px)
        Py = logsumexp(Py)
        Pxy = logsumexp(Pxy)

        # add to MI
        MI += Pxy - (Px + Py)

    # average
    MI /= float(n_samples)

    # ignore MI < 0
    if MI <= 0.0:
        MI = 0.0
        
    return MI

# Histogram estimations are biased and shouldn't be used, this is just for testing purposes.
def estimiate_MI_sample_hist(X, Y, M_c, X_L, X_D, get_next_seed, n_samples=10000):
    
    get_view_index = lambda which_column: X_L['column_partition']['assignments'][which_column]

    view_X = get_view_index(X)
    view_Y = get_view_index(Y)

    # independent
    if view_X != view_Y:        
        return 0.0

    # get cluster logps
    view_state = X_L['view_state'][view_X]
    cluster_logps = su.determine_cluster_crp_logps(view_state)
    cluster_crps = numpy.exp(cluster_logps)
    n_clusters = len(cluster_crps)

    # get components models for each cluster for columns X and Y
    component_models_X = [0]*n_clusters
    component_models_Y = [0]*n_clusters
    for i in range(n_clusters):
        cluster_models = su.create_cluster_model_from_X_L(M_c, X_L, view_X, i)
        component_models_X[i] = cluster_models[X]
        component_models_Y[i] = cluster_models[Y]

    MI = 0.0
    samples = numpy.zeros((n_samples,2), dtype=float)
    samples_x = numpy.zeros(n_samples, dtype=float)
    samples_y = numpy.zeros(n_samples, dtype=float)

    # draw the samples
    for i in range(n_samples):
        # draw a cluster 
        cluster_idx = numpy.nonzero(numpy.random.multinomial(1, cluster_crps))[0][0]

        x = component_models_X[cluster_idx].get_draw(get_next_seed())
        y = component_models_Y[cluster_idx].get_draw(get_next_seed())

        samples[i,0] = x
        samples[i,1] = y
        samples_x[i] = x
        samples_y[i] = y

    # calculate the number of bins and ranges
    N = float(n_samples)
    r,_ = corr(samples_x, samples_y)
    k = round(.5+.5*(1+4*((6*N*r**2.)/(1-r**2.))**.5)**.5)+1
    sigma_x = numpy.std(samples_x)
    mu_x = numpy.mean(samples_x)
    sigma_y = numpy.std(samples_y)
    mu_y = numpy.mean(samples_y)
    range_x = numpy.linspace(mu_x-3.*sigma_x,mu_x+3*sigma_x,k)
    range_y = numpy.linspace(mu_y-3.*sigma_y,mu_y+3*sigma_y,k)


    PXY, _, _ = numpy.histogram2d(samples[:,0], samples[:,1], bins=[range_x,range_y])
    PX,_ = numpy.histogram(samples_x,bins=range_x)
    PY,_ = numpy.histogram(samples_y,bins=range_y)

    MI = 0

    for i_x in range(PXY.shape[0]):
        for i_y in range(PXY.shape[1]):            
            Pxy = PXY[i_x,i_y]
            Px = PX[i_x]
            Py = PY[i_y]
            
            if Pxy > 0.0 and Px > 0.0 and Py > 0.0:
                MI += (Pxy/N)*math.log(Pxy*N/(Px*Py))
            


    # ignore MI < 0
    if MI <= 0.0:
        MI = 0.0
        
    return MI

########NEW FILE########
__FILENAME__ = mutual_information_test_utils
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import crosscat.utils.data_utils as du
import crosscat.cython_code.State as State
import random
import numpy

# Generates a num_rows by num_cols array of data with covariance matrix I^{num_cols}*corr
def generate_correlated_data(num_rows, num_cols, means, corr, seed=0):
	assert(corr <= 1 and corr >= 0)
	assert(num_cols == len(means))

	numpy.random.seed(seed=seed)

	mu = numpy.array(means)
	sigma = numpy.ones((num_cols,num_cols),dtype=float)*corr
	for i in range(num_cols):
		sigma[i,i] = 1 
	X = numpy.random.multivariate_normal(mu, sigma, num_rows)

	return X

def generate_correlated_state(num_rows, num_cols, num_views, num_clusters, mean_range, corr, seed=0):
	#

	assert(num_clusters <= num_rows)
	assert(num_views <= num_cols)
	T = numpy.zeros((num_rows, num_cols))

	random.seed(seed)
	numpy.random.seed(seed=seed)
	get_next_seed = lambda : random.randrange(2147483647)

	# generate an assignment of columns to views (uniform)
	cols_to_views = range(num_views)
	view_counts = numpy.ones(num_views, dtype=int)
	for i in range(num_views, num_cols):
		r = random.randrange(num_views)
		cols_to_views.append(r)
		view_counts[r] += 1

	random.shuffle(cols_to_views)

	assert(len(cols_to_views) == num_cols)
	assert(max(cols_to_views) == num_views-1)

	# for each view, generate an assignment of rows to num_clusters
	row_to_clusters = []
	cluster_counts = []
	for view in range(num_views):
		row_to_cluster = range(num_clusters)
		cluster_counts_i = numpy.ones(num_clusters,dtype=int)
		for i in range(num_clusters, num_rows):
			r = random.randrange(num_clusters)
			row_to_cluster.append(r)
			cluster_counts_i[r] += 1

		random.shuffle(row_to_cluster)

		assert(len(row_to_cluster) == num_rows)
		assert(max(row_to_cluster) == num_clusters-1)

		row_to_clusters.append(row_to_cluster)
		cluster_counts.append(cluster_counts_i)

	assert(len(row_to_clusters) == num_views)

	# generate the correlated data
	for view in range(num_views):
		for cluster in range(num_clusters):
			cell_cols = view_counts[view]
			cell_rows = cluster_counts[view][cluster]
			means = numpy.random.uniform(-mean_range/2.0,mean_range/2.0,cell_cols)
			X =  generate_correlated_data(cell_rows, cell_cols, means, corr, seed=get_next_seed())
			# get the indices of the columns in this view
			col_indices = numpy.nonzero(numpy.array(cols_to_views)==view)[0]
			# get the indices of the rows in this view and this cluster
			row_indices = numpy.nonzero(numpy.array(row_to_clusters[view])==cluster)[0]
			# insert the data
			for col in range(cell_cols):
				for row in range(cell_rows):
					r = row_indices[row]
					c = col_indices[col]
					T[r,c] = X[row,col]


	M_c = du.gen_M_c_from_T(T)
	M_r = du.gen_M_r_from_T(T)
	X_L, X_D = generate_X_L_and_X_D(T, M_c, cols_to_views, row_to_clusters, seed=get_next_seed())

	return  T, M_c, M_r, X_L, X_D, cols_to_views

def generate_X_L_and_X_D(T, M_c, cols_to_views, row_to_clusters, seed=0):
	state = State.p_State(M_c, T, SEED=seed)
	X_L = state.get_X_L()

	# insert assigment into X_L (this is not a valid X_L because the counts and 
	# suffstats will be wrong)
	X_L['column_partition']['assignments'] = cols_to_views
	state = State.p_State(M_c, T, X_L=X_L, X_D=row_to_clusters, SEED=seed)

	X_L = state.get_X_L()
	X_D = state.get_X_D()

	return X_L, X_D


########NEW FILE########
__FILENAME__ = plot_utils
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import os
#
import numpy
import pylab
pylab.ion()
import hcluster
#
import crosscat.utils.general_utils as gu
import crosscat.utils.file_utils as fu


def save_current_figure(filename, dir='./', close=True, format=None):
    if filename is not None:
        fu.ensure_dir(dir)
        full_filename = os.path.join(dir, filename)
        pylab.savefig(full_filename, format=format)
        if close:
            pylab.close()

def get_aspect_ratio(T_array):
    num_rows = len(T_array)
    num_cols = len(T_array[0])
    aspect_ratio = float(num_cols)/num_rows
    return aspect_ratio

def plot_T(T_array, M_c, filename=None, dir='./', close=True):
    num_cols = len(T_array[0])
    column_names = [M_c['idx_to_name'][str(idx)] for idx in range(num_cols)]
    column_names = numpy.array(column_names)

    aspect_ratio = get_aspect_ratio(T_array)
    pylab.figure()
    pylab.imshow(T_array, aspect=aspect_ratio, interpolation='none',
                 cmap=pylab.matplotlib.cm.Greens)
    pylab.gca().set_xticks(range(num_cols))
    pylab.gca().set_xticklabels(column_names, rotation=90, size='x-small')

    pylab.show()
    
    save_current_figure(filename, dir, close)

def plot_views(T_array, X_D, X_L, M_c, filename=None, dir='./', close=True,
        format=None, do_colorbar=False):
    view_assignments = X_L['column_partition']['assignments']
    view_assignments = numpy.array(view_assignments)
    num_features = len(view_assignments)
    column_names = [M_c['idx_to_name'][str(idx)] for idx in range(num_features)]
    column_names = numpy.array(column_names)
    num_views = len(set(view_assignments)) + do_colorbar
    
    disLeft = 0.1
    disRight = 0.1
    viewSpacing = 0.1 / (max(2, num_views) - 1)
    nxtAxDisLeft = disLeft
    axpos2 = 0.2
    axpos4 = 0.75
    view_spacing_2 = (1-viewSpacing*(num_views-1.)-disLeft-disRight) / num_features
    
    fig = pylab.figure()
    for view_idx, X_D_i in enumerate(X_D):
        # figure out some sizing
        is_this_view = view_assignments==view_idx
        num_cols_i = sum(is_this_view)
        nxtAxWidth = float(num_cols_i) * view_spacing_2
        axes_pos = nxtAxDisLeft, axpos2, nxtAxWidth, axpos4
        nxtAxDisLeft = nxtAxDisLeft+nxtAxWidth+viewSpacing
        # define some helpers
        def norm_T(T_array):
            mincols = T_array_sub.min(axis=0)
            maxcols = T_array_sub.max(axis=0)
            T_range = maxcols[numpy.newaxis,:] - mincols[numpy.newaxis,:]
            return (T_array_sub-mincols[numpy.newaxis,:]) / T_range
        def plot_cluster_lines(X_D_i, num_cols_i):
            old_tmp = 0
            for cluster_i in range(max(X_D_i)):
                cluster_num_rows = numpy.sum(numpy.array(X_D_i) == cluster_i)
                if cluster_num_rows > 5:
                    xs = numpy.arange(num_cols_i + 1) - 0.5
                    ys = [old_tmp + cluster_num_rows] * (num_cols_i + 1)
                    pylab.plot(xs, ys, color='red', linewidth=2, hold='true')
                    pass
                old_tmp = old_tmp + cluster_num_rows
                pass
            return
        # plot
        argsorted = numpy.argsort(X_D_i)
        T_array_sub = T_array[:,is_this_view][argsorted]
        normed_T = norm_T(T_array_sub)
        currax = fig.add_axes(axes_pos)
        pylab.imshow(normed_T, aspect = 'auto',
                     interpolation='none', cmap=pylab.matplotlib.cm.Greens)
        plot_cluster_lines(X_D_i, num_cols_i)
        # munge plots
        pylab.gca().set_xticks(range(num_cols_i))
        pylab.gca().set_xticklabels(column_names[is_this_view], rotation=90, size='x-small')
        pylab.gca().set_yticklabels([])
        pylab.xlim([-0.5, num_cols_i-0.5])
        pylab.ylim([0, len(T_array_sub)])
        if view_idx!=0: pylab.gca().set_yticklabels([])
    if do_colorbar:
        nxtAxWidth = float(1.) * view_spacing_2
        axes_pos = nxtAxDisLeft, axpos2, nxtAxWidth, axpos4
        cax = fig.add_axes(axes_pos)
        cb = pylab.colorbar(cax=cax, ax=currax)
    save_current_figure(filename, dir, close, format=format)

def plot_predicted_value(value, samples, modelType, filename='imputed_value_hist.png', plotcolor='red', truth=None, x_axis_lim=None):

    fig = pylab.figure()
    # Find 50% bounds
    curr_std = numpy.std(samples)
    curr_delta = 2*curr_std/100;
    ndraws = len(samples)
    
    for thresh in numpy.arange(curr_delta, 2*curr_std, curr_delta):
        withinbounds = len([i for i in range(len(samples)) if samples[i] < (value+thresh) and samples[i] > (value-thresh)])
        if float(withinbounds)/ndraws > 0.5:
            break

    bounds = [value-thresh, value+thresh]
    
    # Plot histogram
    # 'normal_inverse_gamma': continuous_imputation,
    # 'symmetric_dirichlet_discrete': multinomial_imputation,
    
    if modelType == 'normal_inverse_gamma':
        nx, xbins, rectangles = pylab.hist(samples,bins=40,normed=0,color=plotcolor)
    elif modelType == 'symmetric_dirichlet_discrete':
        bin_edges = numpy.arange(numpy.min(samples)-0.5, numpy.max(samples)-0.5, 1)  
        nx, xbins, rectangles = pylab.hist(samples,bin_edges,normed=0,color=plotcolor)
    else:
        print 'Unsupported model type'

    pylab.clf()

    nx_frac = nx/float(sum(nx))
    x_width = [(xbins[i+1]-xbins[i]) for i in range(len(xbins)-1)]
    pylab.bar(xbins[0:len(xbins)-1],nx_frac,x_width,color=plotcolor)
    pylab.plot([value, value],[0,1], color=plotcolor, hold=True,linewidth=2)                      
    pylab.plot([bounds[0], bounds[0]],[0,1], color=plotcolor, hold=True, linestyle='--',linewidth=2)
    pylab.plot([bounds[1], bounds[1]],[0,1], color=plotcolor, hold=True, linestyle='--',linewidth=2)
    if truth != None:
        pylab.plot([truth, truth],[0,1], color='green', hold=True, linestyle='--',linewidth=2)
    pylab.show()

    if x_axis_lim != None:
        pylab.xlim(x_axis_lim)
    save_current_figure(filename, './', False)
    return pylab.gca().get_xlim()

def do_gen_feature_z(X_L_list, X_D_list, M_c, filename, tablename=''):
    num_cols = len(X_L_list[0]['column_partition']['assignments'])
    column_names = [M_c['idx_to_name'][str(idx)] for idx in range(num_cols)]
    column_names = numpy.array(column_names)
    # extract unordered z_matrix
    num_latent_states = len(X_L_list)
    z_matrix = numpy.zeros((num_cols, num_cols))
    for X_L in X_L_list:
      assignments = X_L['column_partition']['assignments']
      for i in range(num_cols):
        for j in range(num_cols):
          if assignments[i] == assignments[j]:
            z_matrix[i, j] += 1
    z_matrix /= float(num_latent_states)
    # hierachically cluster z_matrix
    Y = hcluster.pdist(z_matrix)
    Z = hcluster.linkage(Y)
    pylab.figure()
    hcluster.dendrogram(Z)
    intify = lambda x: int(x.get_text())
    reorder_indices = map(intify, pylab.gca().get_xticklabels())
    pylab.close()
    # REORDER! 
    z_matrix_reordered = z_matrix[:, reorder_indices][reorder_indices, :]
    column_names_reordered = column_names[reorder_indices]
    # actually create figure
    fig = pylab.figure()
    fig.set_size_inches(16, 12)
    pylab.imshow(z_matrix_reordered, interpolation='none',
                 cmap=pylab.matplotlib.cm.Greens)
    pylab.colorbar()
    if num_cols < 14:
      pylab.gca().set_yticks(range(num_cols))
      pylab.gca().set_yticklabels(column_names_reordered, size='x-small')
      pylab.gca().set_xticks(range(num_cols))
      pylab.gca().set_xticklabels(column_names_reordered, rotation=90, size='x-small')
    else:
      pylab.gca().set_yticks(range(num_cols)[::2])
      pylab.gca().set_yticklabels(column_names_reordered[::2], size='x-small')
      pylab.gca().set_xticks(range(num_cols)[1::2])
      pylab.gca().set_xticklabels(column_names_reordered[1::2],
                                  rotation=90, size='small')
    pylab.title('column dependencies for: %s' % tablename)
    pylab.savefig(filename)

def legend_outside(ax=None, bbox_to_anchor=(0.5, -.25), loc='upper center',
                   ncol=None, label_cmp=None):
    # labels must be set in original plot call: plot(..., label=label)
    if ax is None:
        ax = pylab.gca()
    handles, labels = ax.get_legend_handles_labels()
    label_to_handle = dict(zip(labels, handles))
    labels = label_to_handle.keys()
    if label_cmp is not None:
        labels = sorted(labels, cmp=label_cmp)
    handles = [label_to_handle[label] for label in labels]
    if ncol is None:
        ncol = min(len(labels), 3)
    lgd = ax.legend(handles, labels, loc=loc, ncol=ncol,
                    bbox_to_anchor=bbox_to_anchor, prop={"size":14})
    return

int_cmp = lambda x, y: cmp(int(x), int(y))
def legend_outside_from_dicts(marker_dict, color_dict,
                              marker_label_prepend='', color_label_prepend='',
                              ax=None, bbox_to_anchor=(0.5, -.07), loc='upper center',
                              ncol=None, label_cmp=None,
                              marker_color='k'):
    marker_handles = []
    marker_labels = []
    for label in sorted(marker_dict.keys(), cmp=int_cmp):
        marker = marker_dict[label]
        handle = pylab.Line2D([],[], color=marker_color, marker=marker, linewidth=0)
        marker_handles.append(handle)
        marker_labels.append(marker_label_prepend+label)
    color_handles = []
    color_labels = []
    for label in sorted(color_dict.keys(), cmp=int_cmp):
        color = color_dict[label]
        handle = pylab.Line2D([],[], color=color, linewidth=3)
        color_handles.append(handle)
        color_labels.append(color_label_prepend+label)
    num_marker_handles = len(marker_handles)
    num_color_handles = len(color_handles)
    num_to_add = abs(num_marker_handles - num_color_handles)
    if num_marker_handles < num_color_handles:
        add_to_handles = marker_handles
        add_to_labels = marker_labels
    else:
        add_to_handles = color_handles
        add_to_labels = color_labels
    for add_idx in range(num_to_add):
        add_to_handles.append(pylab.Line2D([],[], color=None, linewidth=0))
        add_to_labels.append('')
    handles = gu.roundrobin(marker_handles, color_handles)
    labels = gu.roundrobin(marker_labels, color_labels)
    if ax is None:
        ax = pylab.gca()
    if ncol is None:
        ncol = max(num_marker_handles, num_color_handles)
    lgd = ax.legend(handles, labels, loc=loc, ncol=ncol,
                    bbox_to_anchor=bbox_to_anchor, prop={"size":14})
    return

def savefig_legend_outside(filename, ax=None, bbox_inches='tight', dir='./'):
    if ax is None:
        ax = pylab.gca()
    lgd = ax.get_legend()
    fu.ensure_dir(dir)
    full_filename = os.path.join(dir, filename)
    pylab.savefig(full_filename,
                  bbox_extra_artists=(lgd,),
                  bbox_inches=bbox_inches,
                  )
    return

def _plot_diagnostic_with_mean(data_arr, hline=None):
    data_mean = data_arr.mean(axis=1)
    #
    fh = pylab.figure()
    pylab.plot(data_arr, color='k')
    pylab.plot(data_mean, linewidth=3, color='r')
    if hline is not None:
        pylab.axhline(hline)
    return fh

def plot_diagnostics(diagnostics_dict, hline_lookup=None, which_diagnostics=None):
    if which_diagnostics is None:
        which_diagnostics = diagnostics_dict.keys()
    if hline_lookup is None:
        hline_lookup = dict()
    for which_diagnostic in which_diagnostics:
        data_arr = diagnostics_dict[which_diagnostic]
        hline = hline_lookup.get(which_diagnostic)
        fh = _plot_diagnostic_with_mean(data_arr, hline=hline)
        pylab.xlabel('iter')
        pylab.ylabel(which_diagnostic)
    return fh

def show_parameters(parameters):
    if len(parameters) == 0: return
    ax = pylab.gca()
    text = gu.get_dict_as_text(parameters)
    pylab.text(0, 1, text, transform=ax.transAxes,
            va='top', size='small', linespacing=1.0)
    return

########NEW FILE########
__FILENAME__ = sample_utils
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import sys
import copy
import math

from collections import Counter
#
from scipy.misc import logsumexp
import numpy
#
import crosscat.cython_code.ContinuousComponentModel as CCM
import crosscat.cython_code.MultinomialComponentModel as MCM
import crosscat.utils.general_utils as gu

class Bunch(dict):
    def __getattr__(self, key):
        if self.has_key(key):
            return self.get(key, None)
        else:
            raise AttributeError(key)
    def __setattr__(self, key, value):
        self[key] = value

Constraints = Bunch

# Q is a list of three element tuples where each typle, (r,c,x) contains a
# row, r; a column, c; and a value x. The contraints, Y follow an identical format.
# Returns a numpy array where each entry, A[i] is the probability for query i given
# the contraints in Y.
def simple_predictive_probability(M_c, X_L, X_D, Y, Q):
    num_rows = len(X_D[0])
    num_cols = len(M_c['column_metadata'])
    query_row = Q[0][0]
    query_columns = [query[1] for query in Q]
    elements = [query[2] for query in Q]
    # enforce query rows all same row
    assert(all([query[0]==query_row for query in Q]))
    # enforce query columns observed column
    assert(all([query_column<num_cols for query_column in query_columns]))
    is_observed_row = query_row < num_rows

    x = []

    if not is_observed_row:
        x = simple_predictive_probability_unobserved(
            M_c, X_L, X_D, Y, query_row, query_columns, elements)
    else:
        x = simple_predictive_probability_observed(
            M_c, X_L, X_D, Y, query_row, query_columns, elements)    

    return x


def simple_predictive_probability_observed(M_c, X_L, X_D, Y, query_row,
                                      query_columns, elements):
    n_queries = len(query_columns)

    answer = numpy.zeros(n_queries)

    for n in range(n_queries):
        query_column = query_columns[n]
        x = elements[n]
        
        # get the view to which this column is assigned
        view_idx = X_L['column_partition']['assignments'][query_column]
        # get cluster
        cluster_idx = X_D[view_idx][query_row]
        # get the cluster model for this cluster
        cluster_model = create_cluster_model_from_X_L(M_c, X_L, view_idx, cluster_idx)
        # get the specific cluster model for this column
        component_model = cluster_model[query_column]
        # construct draw conataints
        draw_constraints = get_draw_constraints(X_L, X_D, Y, query_row, query_column)

        # return the PDF value (exp)
        p_x = component_model.calc_element_predictive_logp_constrained(x, draw_constraints)
        
        answer[n] = p_x
        
    return answer

def simple_predictive_probability_unobserved(M_c, X_L, X_D, Y, query_row, query_columns, elements):

    n_queries = len(query_columns)

    answer = numpy.zeros(n_queries)
    # answers = numpy.array([])

    for n in range(n_queries):
        query_column = query_columns[n]
        x = elements[n]
        
        # get the view to which this column is assigned
        view_idx = X_L['column_partition']['assignments'][query_column]
        # get the logps for all the clusters (plus a new one) in this view
        cluster_logps = determine_cluster_logps(M_c, X_L, X_D, Y, query_row, view_idx)
    
        answers_n = numpy.zeros(len(cluster_logps))

        # cluster_logps should logsumexp to log(1)
        assert(numpy.abs(logsumexp(cluster_logps)) < .0000001)

        # enumerate over the clusters
        for cluster_idx in range(len(cluster_logps)):

            # get the cluster model for this cluster
            cluster_model = create_cluster_model_from_X_L(M_c, X_L, view_idx, cluster_idx)
            # get the specific cluster model for this column
            component_model = cluster_model[query_column]
            # construct draw conataints
            draw_constraints = get_draw_constraints(X_L, X_D, Y, query_row, query_column)

            # return the PDF value (exp)
            p_x = component_model.calc_element_predictive_logp_constrained(x, draw_constraints)
        

            answers_n[cluster_idx] = p_x+cluster_logps[cluster_idx]

        answer[n] = logsumexp(answers_n)
        
    return answer

##############################################################################

def row_structural_typicality(X_L_list, X_D_list, row_id):
    """
    Returns how typical the row is (opposite of how anomalous the row is).
    """
    count = 0
    assert len(X_L_list) == len(X_D_list)
    for X_L, X_D in zip(X_L_list, X_D_list):
        for r in range(len(X_D[0])):
            for c in range(len(X_L['column_partition']['assignments'])):
                if X_D[X_L['column_partition']['assignments'][c]][r] == X_D[X_L['column_partition']['assignments'][c]][row_id]:
                    count += 1
    return float(count) / (len(X_D_list) * len(X_D[0]) * len(X_L_list[0]['column_partition']['assignments']))
                

def column_structural_typicality(X_L_list, col_id):
    """
    Returns how typical the column is (opposite of how anomalous the column is).
    """
    count = 0
    for X_L in X_L_list:
        for c in range(len(X_L['column_partition']['assignments'])):
            if X_L['column_partition']['assignments'][col_id] == X_L['column_partition']['assignments'][c]:
                count += 1
    return float(count) / (len(X_L_list) * len(X_L_list[0]['column_partition']['assignments']))

def simple_predictive_probability_multistate(M_c, X_L_list, X_D_list, Y, Q):
    """
    Returns the simple predictive probability, averaged over each sample.
    """
    avg_prob = 0
    for X_L, X_D in zip(X_L_list, X_D_list):
        avg_prob += simple_predictive_probability(M_c, X_L, X_D, Y, Q)
    return float(avg_prob)/len(X_L_list)


#############################################################################

def similarity(M_c, X_L_list, X_D_list, given_row_id, target_row_id, target_column=None):
    """
    Returns the similarity of the given row to the target row, averaged over
    all the column indexes given by col_idxs.
    Similarity is defined as the proportion of times that two cells are in the same
    view and category.
    """
    score = 0.0

    ## Set col_idxs: defaults to all columns.
    if target_column:
        if type(target_column) == str:
            col_idxs = [M_c['name_to_idx'][target_column]]
        elif type(target_column) == list:
            col_idxs = target_column
        else:
            col_idxs = [target_column]
    else:
        col_idxs = M_c['idx_to_name'].keys()
    col_idxs = [int(col_idx) for col_idx in col_idxs]
    
    ## Iterate over all latent states.
    for X_L, X_D in zip(X_L_list, X_D_list):
        for col_idx in col_idxs:
            view_idx = X_L['column_partition']['assignments'][col_idx]
            if X_D[view_idx][given_row_id] == X_D[view_idx][target_row_id]:
                score += 1.0
    return score / (len(X_L_list)*len(col_idxs))

################################################################################
################################################################################

def simple_predictive_sample(M_c, X_L, X_D, Y, Q, get_next_seed, n=1):
    num_rows = len(X_D[0])
    num_cols = len(M_c['column_metadata'])
    query_row = Q[0][0]
    query_columns = [query[1] for query in Q]
    # enforce query rows all same row
    assert(all([query[0]==query_row for query in Q]))
    # enforce query columns observed column
    assert(all([query_column<num_cols for query_column in query_columns]))
    is_observed_row = query_row < num_rows
    x = []
    if not is_observed_row:
        x = simple_predictive_sample_unobserved(
            M_c, X_L, X_D, Y, query_row, query_columns, get_next_seed, n)
    else:
        x = simple_predictive_sample_observed(
            M_c, X_L, X_D, Y, query_row, query_columns, get_next_seed, n)    
    # # more modular logic
    # observed_view_cluster_tuples = ()
    # if is_observed_row:
    #     observed_view_cluster_tuples = get_view_cluster_tuple(
    #         M_c, X_L, X_D, query_row)
    #     observed_view_cluster_tuples = [observed_view_cluster_tuples] * n
    # else:
    #     view_cluster_logps = determine_view_cluster_logps(
    #         M_c, X_L, X_D, Y, query_row)
    #     observed_view_cluster_tuples = \
    #         sample_view_cluster_tuples_from_logp(view_cluster_logps, n)
    # x = draw_from_view_cluster_tuples(M_c, X_L, X_D, Y,
    #                                   observed_view_cluster_tuples)
    return x

def simple_predictive_sample_multistate(M_c, X_L_list, X_D_list, Y, Q,
                                        get_next_seed, n=1):
    num_states = len(X_L_list)
    assert(num_states==len(X_D_list))
    n_from_each = n / num_states
    n_sampled = n % num_states
    random_state = numpy.random.RandomState(get_next_seed())
    which_sampled = random_state.permutation(xrange(num_states))[:n_sampled]
    which_sampled = set(which_sampled)
    x = []
    for state_idx, (X_L, X_D) in enumerate(zip(X_L_list, X_D_list)):
        this_n = n_from_each
        if state_idx in which_sampled:
            this_n += 1
        this_x = simple_predictive_sample(M_c, X_L, X_D, Y, Q,
                                          get_next_seed, this_n)
        x.extend(this_x)
    return x

def simple_predictive_sample_observed(M_c, X_L, X_D, Y, which_row,
                                      which_columns, get_next_seed, n=1):
    get_which_view = lambda which_column: \
        X_L['column_partition']['assignments'][which_column]
    column_to_view = dict()
    # get the views to which each column is assigned
    for which_column in which_columns:
        column_to_view[which_column] = get_which_view(which_column)
    #
    view_to_cluster_model = dict()
    for which_view in list(set(column_to_view.values())):
        # which calegory in this view
        which_cluster = X_D[which_view][which_row]
        # pull the suffstats, hypers, and marignal logP's for clusters
        cluster_model = create_cluster_model_from_X_L(M_c, X_L, which_view,
                                                      which_cluster)
        # store
        view_to_cluster_model[which_view] = cluster_model
    #
    samples_list = []
    for sample_idx in range(n):
        this_sample_draws = []
        for which_column in which_columns:
            # get the view to which this column is assigned
            which_view = column_to_view[which_column]
            # get the cluster model (suffstats, hypers, etc)
            cluster_model = view_to_cluster_model[which_view]
            # get the component model for this column
            component_model = cluster_model[which_column]
            # 
            draw_constraints = get_draw_constraints(X_L, X_D, Y,
                                                    which_row, which_column)
            # get a random int for seeding the rng
            SEED = get_next_seed()
            # draw
            draw = component_model.get_draw_constrained(SEED,draw_constraints)
            this_sample_draws.append(draw)
        samples_list.append(this_sample_draws)
    return samples_list

def names_to_global_indices(column_names, M_c):
    name_to_idx = M_c['name_to_idx']
    first_key = name_to_idx.keys()[0]
    # FIXME: str(column_name) is hack
    if isinstance(first_key, (unicode, str)):
        column_names = map(str, column_names)
    return [name_to_idx[column_name] for column_name in column_names]

def extract_view_column_info(M_c, X_L, view_idx):
    view_state_i = X_L['view_state'][view_idx]
    column_names = view_state_i['column_names']
    # view_state_i ordering should match global ordering
    column_component_suffstats = view_state_i['column_component_suffstats']
    global_column_indices = names_to_global_indices(column_names, M_c)
    column_metadata = numpy.array([
        M_c['column_metadata'][col_idx]
        for col_idx in global_column_indices
        ])
    column_hypers = numpy.array([
            X_L['column_hypers'][col_idx]
            for col_idx in global_column_indices
            ])
    zipped_column_info = zip(column_metadata, column_hypers,
                             column_component_suffstats)
    zipped_column_info = dict(zip(global_column_indices, zipped_column_info))
    row_partition_model = view_state_i['row_partition_model']
    return zipped_column_info, row_partition_model

def get_column_info_subset(zipped_column_info, column_indices):
    column_info_subset = dict()
    for column_index in column_indices:
        if column_index in zipped_column_info:
            column_info_subset[column_index] = \
                zipped_column_info[column_index]
    return column_info_subset

def get_component_model_constructor(modeltype):
    if modeltype == 'normal_inverse_gamma':
        component_model_constructor = CCM.p_ContinuousComponentModel
    elif modeltype == 'symmetric_dirichlet_discrete':
        component_model_constructor = MCM.p_MultinomialComponentModel
    else:
        assert False, \
            "get_model_constructor: unknown modeltype: %s" % modeltype
    return component_model_constructor
    
def create_component_model(column_metadata, column_hypers, suffstats):
    suffstats = copy.deepcopy(suffstats)
    count = suffstats.pop('N', 0)
    modeltype = column_metadata['modeltype']
    component_model_constructor = get_component_model_constructor(modeltype)
    # FIXME: this is a hack
    if modeltype == 'symmetric_dirichlet_discrete' and suffstats is not None:
        suffstats = dict(counts=suffstats)
    component_model = component_model_constructor(column_hypers, count,
                                                  **suffstats)
    return component_model

def create_cluster_model(zipped_column_info, row_partition_model,
                         cluster_idx):
    cluster_component_models = dict()
    for global_column_idx in zipped_column_info:
        column_metadata, column_hypers, column_component_suffstats = \
            zipped_column_info[global_column_idx]
        cluster_component_suffstats = column_component_suffstats[cluster_idx]
        component_model = create_component_model(
            column_metadata, column_hypers, cluster_component_suffstats)
        cluster_component_models[global_column_idx] = component_model
    return cluster_component_models

def create_empty_cluster_model(zipped_column_info):
    cluster_component_models = dict()
    for global_column_idx in zipped_column_info:
        column_metadata, column_hypers, column_component_suffstats = \
            zipped_column_info[global_column_idx]
        component_model = create_component_model(column_metadata,
                                                 column_hypers, dict(N=None))
        cluster_component_models[global_column_idx] = component_model
    return cluster_component_models

def create_cluster_models(M_c, X_L, view_idx, which_columns=None):
    zipped_column_info, row_partition_model = extract_view_column_info(
        M_c, X_L, view_idx)
    if which_columns is not None:
        zipped_column_info = get_column_info_subset(
            zipped_column_info, which_columns)
    num_clusters = len(row_partition_model['counts'])
    cluster_models = []
    for cluster_idx in range(num_clusters):
        cluster_model = create_cluster_model(
            zipped_column_info, row_partition_model, cluster_idx
            )
        cluster_models.append(cluster_model)
    empty_cluster_model = create_empty_cluster_model(zipped_column_info)
    cluster_models.append(empty_cluster_model)
    return cluster_models

def determine_cluster_data_logp(cluster_model, cluster_sampling_constraints,
                                X_D_i, cluster_idx):
    logp = 0
    for column_idx, column_constraint_dict \
            in cluster_sampling_constraints.iteritems():
        if column_idx in cluster_model:
            other_constraint_values = []
            for other_row, other_value in column_constraint_dict['others']:
                if X_D_i[other_row]==cluster_idx:
                    other_constraint_values.append(other_value)
            this_constraint_value = column_constraint_dict['this']
            component_model = cluster_model[column_idx]
            logp += component_model.calc_element_predictive_logp_constrained(
                this_constraint_value, other_constraint_values)
    return logp

def get_cluster_sampling_constraints(Y, query_row):
    constraint_dict = dict()
    if Y is not None:
        for constraint in Y:
            constraint_row, constraint_col, constraint_value = constraint
            is_same_row = constraint_row == query_row
            if is_same_row:
                constraint_dict[constraint_col] = dict(this=constraint_value)
                constraint_dict[constraint_col]['others'] = []
        for constraint in Y:
            constraint_row, constraint_col, constraint_value = constraint
            is_same_row = constraint_row == query_row
            is_same_col = constraint_col in constraint_dict
            if is_same_col and not is_same_row:
                other = (constraint_row, constraint_value)
                constraint_dict[constraint_col]['others'].append(other)
    return constraint_dict

def get_draw_constraints(X_L, X_D, Y, draw_row, draw_column):
    constraint_values = []
    if Y is not None:
        column_partition_assignments = X_L['column_partition']['assignments']
        view_idx = column_partition_assignments[draw_column]
        X_D_i = X_D[view_idx]
        try:
            draw_cluster = X_D_i[draw_row]
        except IndexError, e:
            draw_cluster = None
        for constraint in Y:
            constraint_row, constraint_col, constraint_value = constraint
            try:
                constraint_cluster = X_D_i[constraint_row]
            except IndexError, e:
                constraint_cluster = None
            if (constraint_col == draw_column) \
                    and (constraint_cluster == draw_cluster):
                constraint_values.append(constraint_value)
    return constraint_values

def determine_cluster_data_logps(M_c, X_L, X_D, Y, query_row, view_idx):
    logps = []
    cluster_sampling_constraints = \
        get_cluster_sampling_constraints(Y, query_row)
    relevant_constraint_columns = cluster_sampling_constraints.keys()
    cluster_models = create_cluster_models(M_c, X_L, view_idx,
                                           relevant_constraint_columns)
    X_D_i = X_D[view_idx]
    for cluster_idx, cluster_model in enumerate(cluster_models):
        logp = determine_cluster_data_logp(
            cluster_model, cluster_sampling_constraints, X_D_i, cluster_idx)
        logps.append(logp)
    return logps

def determine_cluster_crp_logps(view_state_i):
    counts = view_state_i['row_partition_model']['counts']
    # FIXME: remove branch after Avinash is done with old saved states 
    alpha = view_state_i['row_partition_model']['hypers'].get('alpha')
    if alpha is None:
        alpha = numpy.exp(view_state_i['row_partition_model']['hypers']['log_alpha'])
    counts_appended = numpy.append(counts, alpha)
    sum_counts_appended = sum(counts_appended)
    logps = numpy.log(counts_appended / float(sum_counts_appended))
    return logps

def determine_cluster_logps(M_c, X_L, X_D, Y, query_row, view_idx):
    view_state_i = X_L['view_state'][view_idx]
    cluster_crp_logps = determine_cluster_crp_logps(view_state_i)
    cluster_crp_logps = numpy.array(cluster_crp_logps)
    cluster_data_logps = determine_cluster_data_logps(M_c, X_L, X_D, Y,
                                                      query_row, view_idx)
    cluster_data_logps = numpy.array(cluster_data_logps)
    # 
    cluster_logps = cluster_crp_logps + cluster_data_logps
    
    return cluster_logps

def sample_from_cluster(cluster_model, random_state):
    sample = []
    for column_index in sorted(cluster_model.keys()):
        component_model = cluster_model[column_index]
        seed_i = random_state.randint(32767) # sys.maxint)
        sample_i = component_model.get_draw(seed_i)
        sample.append(sample_i)
    return sample

def create_cluster_model_from_X_L(M_c, X_L, view_idx, cluster_idx):
    zipped_column_info, row_partition_model = extract_view_column_info(
        M_c, X_L, view_idx)
    num_clusters = len(row_partition_model['counts'])
    if(cluster_idx==num_clusters):
        # drew a new cluster
        cluster_model = create_empty_cluster_model(zipped_column_info)
    else:
        cluster_model = create_cluster_model(
            zipped_column_info, row_partition_model, cluster_idx
            )
    return cluster_model

def simple_predictive_sample_unobserved(M_c, X_L, X_D, Y, query_row,
                                        query_columns, get_next_seed, n=1):
    num_views = len(X_D)
    #
    cluster_logps_list = []
    # for each view
    for view_idx in range(num_views):
        # get the logp of the cluster of query_row in this view
        cluster_logps = determine_cluster_logps(M_c, X_L, X_D, Y, query_row,
                                                view_idx)
        cluster_logps_list.append(cluster_logps)
    #
    samples_list = []
    for sample_idx in range(n):
        view_cluster_draws = dict()
        for view_idx, cluster_logps in enumerate(cluster_logps_list):
            probs = numpy.exp(cluster_logps)
            probs /= sum(probs)
            draw = numpy.nonzero(numpy.random.multinomial(1, probs))[0][0]
            view_cluster_draws[view_idx] = draw
        #
        get_which_view = lambda which_column: \
            X_L['column_partition']['assignments'][which_column]
        column_to_view = dict()
        for query_column in query_columns:
            column_to_view[query_column] = get_which_view(query_column)
        view_to_cluster_model = dict()
        for which_view in list(set(column_to_view.values())):
            which_cluster = view_cluster_draws[which_view]
            cluster_model = create_cluster_model_from_X_L(M_c, X_L,
                                                          which_view,
                                                          which_cluster)
            view_to_cluster_model[which_view] = cluster_model
        #
        this_sample_draws = []
        for query_column in query_columns:
            which_view = get_which_view(query_column)
            cluster_model = view_to_cluster_model[which_view]
            component_model = cluster_model[query_column]
            draw_constraints = get_draw_constraints(X_L, X_D, Y,
                                                    query_row, query_column)
            SEED = get_next_seed()
            draw = component_model.get_draw_constrained(SEED,
                                                        draw_constraints)
            this_sample_draws.append(draw)
        samples_list.append(this_sample_draws)
    return samples_list


def multinomial_imputation_confidence(samples, imputed, column_hypers_i):
    max_count = sum(numpy.array(samples) == imputed)
    confidence = float(max_count) / len(samples)
    return confidence

def get_continuous_mass_within_delta(samples, center, delta):
    num_samples = len(samples)
    num_within_delta = sum(numpy.abs(samples - center) < delta)
    mass_fraction = float(num_within_delta) / num_samples
    return mass_fraction

def continuous_imputation_confidence(samples, imputed,
                                     column_component_suffstats_i):
    col_std = get_column_std(column_component_suffstats_i)
    delta = .1 * col_std
    confidence = get_continuous_mass_within_delta(samples, imputed, delta)
    return confidence

def continuous_imputation(samples, get_next_seed):
    imputed = numpy.median(samples)
    return imputed

def multinomial_imputation(samples, get_next_seed):
    counter = Counter(samples)
    max_tuple = counter.most_common(1)[0]
    max_count = max_tuple[1]
    counter_counter = Counter(counter.values())
    num_max_count = counter_counter[max_count]
    imputed = max_tuple[0]
    if num_max_count >= 1:
        # if there is a tie, draw randomly
        max_tuples = counter.most_common(num_max_count)
        values = [max_tuple[0] for max_tuple in max_tuples]
        random_state = numpy.random.RandomState(get_next_seed())
        draw = random_state.randint(len(values))
        imputed = values[draw]
    return imputed

# FIXME: ensure callers aren't passing continuous, multinomial
modeltype_to_imputation_function = {
    'normal_inverse_gamma': continuous_imputation,
    'symmetric_dirichlet_discrete': multinomial_imputation,
    }

modeltype_to_imputation_confidence_function = {
    'normal_inverse_gamma': continuous_imputation_confidence,
    'symmetric_dirichlet_discrete': multinomial_imputation_confidence,
    }

def impute(M_c, X_L, X_D, Y, Q, n, get_next_seed, return_samples=False):
    # FIXME: allow more than one cell to be imputed
    assert(len(Q)==1)
    #
    col_idx = Q[0][1]
    modeltype = M_c['column_metadata'][col_idx]['modeltype']
    assert(modeltype in modeltype_to_imputation_function)
    if get_is_multistate(X_L, X_D):
        samples = simple_predictive_sample_multistate(M_c, X_L, X_D, Y, Q,
                                           get_next_seed, n)
    else:
        samples = simple_predictive_sample(M_c, X_L, X_D, Y, Q,
                                           get_next_seed, n)
    samples = numpy.array(samples).T[0]
    imputation_function = modeltype_to_imputation_function[modeltype]
    e = imputation_function(samples, get_next_seed)
    if return_samples:
        return e, samples
    else:
        return e

def get_confidence_interval(imputed, samples, confidence=.5):
    deltas = numpy.array(samples) - imputed
    sorted_abs_delta = numpy.sort(numpy.abs(deltas))
    n_samples = len(samples)
    lower_index = int(numpy.floor(confidence * n_samples))
    lower_value = sorted_abs_delta[lower_index]
    upper_value = sorted_abs_delta[lower_index + 1]
    interval = numpy.mean([lower_value, upper_value])
    return interval

def get_column_std(column_component_suffstats_i):
    N = sum(map(gu.get_getname('N'), column_component_suffstats_i))
    sum_x = sum(map(gu.get_getname('sum_x'), column_component_suffstats_i))
    sum_x_squared = sum(map(gu.get_getname('sum_x_squared'), column_component_suffstats_i))
    #
    exp_x = sum_x / float(N)
    exp_x_squared = sum_x_squared / float(N)
    col_var = exp_x_squared - (exp_x ** 2)
    col_std = col_var ** .5
    return col_std

def get_column_component_suffstats_i(M_c, X_L, col_idx):
    column_name = M_c['idx_to_name'][str(col_idx)]
    view_idx = X_L['column_partition']['assignments'][col_idx]
    view_state_i = X_L['view_state'][view_idx]
    local_col_idx = view_state_i['column_names'].index(column_name)
    column_component_suffstats_i = \
        view_state_i['column_component_suffstats'][local_col_idx]
    return column_component_suffstats_i

def impute_and_confidence(M_c, X_L, X_D, Y, Q, n, get_next_seed):
    # FIXME: allow more than one cell to be imputed
    assert(len(Q)==1)
    col_idx = Q[0][1]
    modeltype = M_c['column_metadata'][col_idx]['modeltype']
    imputation_confidence_function = \
        modeltype_to_imputation_confidence_function[modeltype]
    #
    imputed, samples = impute(M_c, X_L, X_D, Y, Q, n, get_next_seed,
                        return_samples=True)
    if get_is_multistate(X_L, X_D):
        X_L = X_L[0]
        X_D = X_D[0]
    column_component_suffstats_i = \
        get_column_component_suffstats_i(M_c, X_L, col_idx)
    imputation_confidence = \
        imputation_confidence_function(samples, imputed,
                                       column_component_suffstats_i)
    return imputed, imputation_confidence

def determine_replicating_samples_params(X_L, X_D):
    view_assignments_array = X_L['column_partition']['assignments']
    view_assignments_array = numpy.array(view_assignments_array)
    views_replicating_samples = []
    for view_idx, view_zs in enumerate(X_D):
        is_this_view = view_assignments_array == view_idx
        this_view_columns = numpy.nonzero(is_this_view)[0]
        this_view_replicating_samples = []
        for cluster_idx, cluster_count in Counter(view_zs).iteritems():
            view_zs_array = numpy.array(view_zs)
            first_row_idx = numpy.nonzero(view_zs_array==cluster_idx)[0][0]
            Y = None
            Q = [
                (int(first_row_idx), int(this_view_column))
                for this_view_column in this_view_columns
                ]
            n = cluster_count
            replicating_sample = dict(
                Y=Y,
                Q=Q,
                n=n,
                )
            this_view_replicating_samples.append(replicating_sample)
        views_replicating_samples.append(this_view_replicating_samples)
    return views_replicating_samples

def get_is_multistate(X_L, X_D):
    if isinstance(X_L, (list, tuple)):
        assert isinstance(X_D, (list, tuple))
        assert len(X_L) == len(X_D)
        return True
    else:
        return False

def ensure_multistate(X_L_list, X_D_list):
    was_multistate = get_is_multistate(X_L_list, X_D_list)
    if not was_multistate:
        X_L_list, X_D_list = [X_L_list], [X_D_list]
    return X_L_list, X_D_list, was_multistate

# def determine_cluster_view_logps(M_c, X_L, X_D, Y):
#     get_which_view = lambda which_column: \
#         X_L['column_partition']['assignments'][which_column]
#     column_to_view = dict()
#     for which_column in which_columns:
#         column_to_view[which_column] = get_which_view(which_column)
#     num_views = len(X_D)
#     cluster_logps_list = []
#     for view_idx in range(num_views):
#         cluster_logps = determine_cluster_logps(M_c, X_L, X_D, Y, view_idx)
#         cluster_logps_list.append(cluster_logp)
#     return cluster_view_logps

########NEW FILE########
__FILENAME__ = timing_test_utils
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import os
import functools
from collections import namedtuple, defaultdict
#
import pylab
#
import crosscat.utils.data_utils as du
import crosscat.utils.xnet_utils as xu
from crosscat.LocalEngine import LocalEngine
import crosscat.cython_code.State as State
import crosscat.utils.plot_utils as pu
import experiment_runner.experiment_utils as eu


def generate_hadoop_dicts(which_kernels, X_L, X_D, args_dict):
    for which_kernel in which_kernels:
        kernel_list = (which_kernel, )
        dict_to_write = dict(X_L=X_L, X_D=X_D)
        dict_to_write.update(args_dict)
        # must write kernel_list after update
        dict_to_write['kernel_list'] = kernel_list
        yield dict_to_write

def write_hadoop_input(input_filename, X_L, X_D, n_steps, SEED):
    # prep settings dictionary
    time_analyze_args_dict = xu.default_analyze_args_dict
    time_analyze_args_dict['command'] = 'time_analyze'
    time_analyze_args_dict['SEED'] = SEED
    time_analyze_args_dict['n_steps'] = n_steps
    # one kernel per line
    all_kernels = State.transition_name_to_method_name_and_args.keys()
    n_tasks = 0
    with open(input_filename, 'w') as out_fh:
        dict_generator = generate_hadoop_dicts(all_kernels, X_L, X_D, time_analyze_args_dict)
        for dict_to_write in dict_generator:
            xu.write_hadoop_line(out_fh, key=dict_to_write['SEED'], dict_to_write=dict_to_write)
            n_tasks += 1
    return n_tasks


dirname_prefix ='timing_analysis'
all_kernels = State.transition_name_to_method_name_and_args.keys()
_kernel_list = [[kernel] for kernel in all_kernels]
base_config = dict(
        gen_seed=0, inf_seed=0,
        num_rows=10, num_cols=10, num_clusters=1, num_views=1,
        kernel_list=(), n_steps=10,
        )
gen_config = functools.partial(eu.gen_config, base_config)
gen_configs = functools.partial(eu.gen_configs, base_config)


def _munge_config(config):
    generate_args = config.copy()
    generate_args['num_splits'] = generate_args.pop('num_views')
    #
    analyze_args = dict()
    analyze_args['n_steps'] = generate_args.pop('n_steps')
    analyze_args['kernel_list'] = generate_args.pop('kernel_list')
    #
    inf_seed = generate_args.pop('inf_seed')
    return generate_args, analyze_args, inf_seed

def runner(config):
    generate_args, analyze_args, inf_seed = _munge_config(config)
    # generate synthetic data
    T, M_c, M_r, X_L, X_D = du.generate_clean_state(max_mean=10, max_std=1,
            **generate_args)
    table_shape = map(len, (T, T[0]))
    start_dims = du.get_state_shape(X_L)
    # run engine with do_timing = True
    engine = LocalEngine(inf_seed)
    X_L, X_D, (elapsed_secs,) = engine.analyze(M_c, T, X_L, X_D,
            do_timing=True,
            **analyze_args
            )
    #
    end_dims = du.get_state_shape(X_L)
    same_shape = start_dims == end_dims
    summary = dict(
        elapsed_secs=elapsed_secs,
        same_shape=same_shape,
        )
    ret_dict = dict(
        config=config,
        summary=summary,
        table_shape=table_shape,
        start_dims=start_dims,
        end_dims=end_dims,
        )
    return ret_dict


#############
# begin nasty plotting support section
get_time_per_step = lambda timing_row: float(timing_row.time_per_step)
get_num_rows = lambda timing_row: timing_row.num_rows
get_num_cols = lambda timing_row: timing_row.num_cols
get_num_views = lambda timing_row: timing_row.num_views
get_num_clusters = lambda timing_row: timing_row.num_clusters
do_strip = lambda string: string.strip()

def group_results(timing_rows, get_fixed_parameters, get_variable_parameter):
    dict_of_dicts = defaultdict(dict)
    for timing_row in timing_rows:
        fixed_parameters = get_fixed_parameters(timing_row)
        variable_parameter = get_variable_parameter(timing_row)
        dict_of_dicts[fixed_parameters][variable_parameter] = timing_row
        pass
    return dict_of_dicts

num_cols_to_color = {'2':'k', '4':'b', '8':'c', '16':'r', '32':'m', '64':'g', '128':'c', '256':'k'}
num_cols_to_marker = {'2':'s', '4':'x', '8':'*', '16':'o', '32':'v', '64':'1', '128':'*',
    '256':'s'}
num_rows_to_color = {'100':'b', '200':'g', '400':'r', '1000':'m', '4000':'y', '10000':'g'}
num_rows_to_marker = {'100':'x', '200':'*', '400':'o', '1000':'v', '4000':'1', '10000':'*'}
num_clusters_to_marker = {'1':'s', '2':'v', '4':'x', '10':'x', '20':'o', '40':'s', '50':'v'}
num_views_to_marker = {'1':'x', '2':'o', '4':'v', '8':'*'}
#
plot_parameter_lookup = dict(
    rows=dict(
        vary_what='rows',
        which_kernel='row_partition_assignments',
        get_fixed_parameters=lambda timing_row: 'Co=%s;Cl=%s;V=%s' % \
            (timing_row.num_cols, timing_row.num_clusters,
             timing_row.num_views),
        get_variable_parameter=get_num_rows,
        get_color_parameter=get_num_cols,
        color_dict=num_cols_to_color,
        color_label_prepend='#Col=',
        get_marker_parameter=get_num_clusters,
        marker_dict=num_clusters_to_marker,
        marker_label_prepend='#Clust=',
        ),
    cols=dict(
        vary_what='cols',
        which_kernel='column_partition_assignments',
        get_fixed_parameters=lambda timing_row: 'R=%s;Cl=%s;V=%s' % \
            (timing_row.num_rows, timing_row.num_clusters,
             timing_row.num_views),
        get_variable_parameter=get_num_cols,
        get_color_parameter=get_num_rows,
        color_dict=num_rows_to_color,
        color_label_prepend='#Row=',
        get_marker_parameter=get_num_clusters,
        marker_dict=num_clusters_to_marker,
        marker_label_prepend='#Clust=',
        ),
    clusters=dict(
        vary_what='clusters',
        which_kernel='row_partition_assignments',
        get_fixed_parameters=lambda timing_row: 'R=%s;Co=%s;V=%s' % \
            (timing_row.num_rows, timing_row.num_cols,
             timing_row.num_views),
        get_variable_parameter=get_num_clusters,
        get_color_parameter=get_num_rows,
        color_dict=num_rows_to_color,
        color_label_prepend='#Row=',
        get_marker_parameter=get_num_views,
        marker_dict=num_views_to_marker,
        marker_label_prepend='#View=',
        ),
    views=dict(
        vary_what='views',
        which_kernel='column_partition_assignments',
        get_fixed_parameters=lambda timing_row: 'R=%s;Co=%s;Cl=%s' % \
            (timing_row.num_rows, timing_row.num_cols,
             timing_row.num_clusters),
        get_variable_parameter=get_num_views,
        get_color_parameter=get_num_rows,
        color_dict=num_rows_to_color,
        color_label_prepend='#Row=',
        get_marker_parameter=get_num_cols,
        marker_dict=num_cols_to_marker,
        marker_label_prepend='#Col=',
        ),
    )

get_first_label_value = lambda label: label[1+label.index('='):label.index(';')]
label_cmp = lambda x, y: cmp(int(get_first_label_value(x)), int(get_first_label_value(y)))
def plot_grouped_data(dict_of_dicts, plot_parameters):
    get_color_parameter = plot_parameters['get_color_parameter']
    color_dict = plot_parameters['color_dict']
    color_label_prepend = plot_parameters['color_label_prepend']
    timing_row_to_color = lambda timing_row: \
        color_dict[get_color_parameter(timing_row)]
    get_marker_parameter = plot_parameters['get_marker_parameter']
    marker_dict = plot_parameters['marker_dict']
    marker_label_prepend = plot_parameters['marker_label_prepend']
    timing_row_to_marker = lambda timing_row: \
        marker_dict[get_marker_parameter(timing_row)]
    vary_what = plot_parameters['vary_what']
    which_kernel = plot_parameters['which_kernel']
    def plot_run_data(configuration, run_data):
        x = sorted(run_data.keys())
        _y = [run_data[el] for el in x]
        y = map(get_time_per_step, _y)
        #
        first_timing_row = run_data.values()[0]
        color = timing_row_to_color(first_timing_row)
        marker = timing_row_to_marker(first_timing_row)
        label = str(configuration)
        pylab.plot(x, y, color=color, marker=marker, label=label)
        return
    #
    fh = pylab.figure()
    for configuration, run_data in dict_of_dicts.iteritems():
        plot_run_data(configuration, run_data)
    #
    pylab.xlabel('# %s' % vary_what)
    pylab.ylabel('time per step (seconds)')
    pylab.title('Timing analysis for kernel: %s' % which_kernel)

    # pu.legend_outside(bbox_to_anchor=(0.5, -.1), ncol=4, label_cmp=label_cmp)
    pu.legend_outside_from_dicts(marker_dict, color_dict,
            marker_label_prepend=marker_label_prepend,
            color_label_prepend=color_label_prepend, bbox_to_anchor=(0.5, -.1),
            label_cmp=label_cmp)
    return fh

def _munge_frame(frame):
    get_first_el = lambda row: row[0]
    # modifies frame in place
    frame['which_kernel'] = frame.pop('kernel_list').map(get_first_el)
    frame['time_per_step'] = frame.pop('elapsed_secs') / frame.pop('n_steps')
    return frame

def series_to_namedtuple(series):
    # for back-converting frame to previous plotting tool format
    index = list(series.index)
    _timing_row = namedtuple('timing_row', ' '.join(index))
    return _timing_row(*[str(series[name]) for name in index])
# end nasty plotting support section
#############

def _plot_results(_results_frame, vary_what='views', plot_filename=None):
    import experiment_runner.experiment_utils as experiment_utils
    # configure parsing/plotting
    plot_parameters = plot_parameter_lookup[vary_what]
    which_kernel = plot_parameters['which_kernel']
    get_fixed_parameters = plot_parameters['get_fixed_parameters']
    get_variable_parameter = plot_parameters['get_variable_parameter']
    get_is_this_kernel = lambda timing_row: \
        timing_row.which_kernel == which_kernel

    # munge data for plotting tools
    results_frame = _results_frame[_results_frame.same_shape]
    results_frame = _munge_frame(results_frame)
    timing_series_list = [el[1] for el in results_frame.iterrows()]
    all_timing_rows = map(series_to_namedtuple, timing_series_list)

    # filter rows
    these_timing_rows = filter(get_is_this_kernel, all_timing_rows)

    # plot
    dict_of_dicts = group_results(these_timing_rows, get_fixed_parameters,
                                  get_variable_parameter)
    plot_grouped_data(dict_of_dicts, plot_parameters)
    return

def plot_results(frame, save=True, plot_prefix=None, dirname='./'):
    # generate each type of plot
    filter_join = lambda join_with, list: join_with.join(filter(None, list))
    for vary_what in ['rows', 'cols', 'clusters', 'views']:
        plot_filename = filter_join('_', [plot_prefix, 'vary', vary_what])
        _plot_results(frame, vary_what, plot_filename)
        if save:
            pu.savefig_legend_outside(plot_filename, dir=dirname)
            pass
        pass
    return

if __name__ == '__main__':
    from experiment_runner.ExperimentRunner import ExperimentRunner


    config_list = gen_configs(
            kernel_list = _kernel_list,
            num_rows=[10, 100],
            )


    dirname = 'timing_analysis'
    er = ExperimentRunner(runner, dirname_prefix=dirname)
    er.do_experiments(config_list, dirname)
    print er.frame

    results_dict = er.get_results(er.frame[er.frame.same_shape])

########NEW FILE########
__FILENAME__ = useCase_utils
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import numpy, pylab, os, csv
import crosscat.utils.sample_utils as su
from copy import copy

def isnan_mixedtype(input_list):
    # Checks to see which elements are nans in a list of characters and numbers (the characters cannot be nans)
    outlist = numpy.zeros(len(input_list))

    num_indices = [x for x in range(len(input_list)) if numpy.isreal(input_list[x]) and numpy.isnan(input_list[x])]
    outlist[num_indices] = 1
    return outlist

def impute_table(T, M_c, X_L_list, X_D_list, numDraws, get_next_seed):
    T_imputed = copy(T)
    num_rows = len(T)
    num_cols = len(T[0])
    # Identify column types
    col_names = numpy.array([M_c['idx_to_name'][str(col_idx)] for col_idx in range(num_cols)])
    coltype = []
    for colindx in range(len(col_names)):
        if M_c['column_metadata'][colindx]['modeltype'] == 'normal_inverse_gamma':
            coltype.append('continuous')
        else:
            coltype.append('multinomial')

    rowsWithNans = [i for i in range(len(T)) if any(isnan_mixedtype(T[i]))]
    print rowsWithNans
    Q = []
    for x in rowsWithNans:
        y = [y for y in range(len(T[0])) if isnan_mixedtype([T[x][y]])]
        Q.extend(zip([x]*len(y), y)) 

    numImputations = len(Q)
    # Impute missing values in table
    values_list = []
    for queryindx in range(len(Q)):
        values = su.impute(M_c, X_L_list, X_D_list, [], [Q[queryindx]], numDraws, get_next_seed)
        values_list.append(values)

    
    # Put the samples back into the data table
    for imputeindx in range(numImputations):
        imputed_value = values_list[imputeindx]
        if coltype[Q[imputeindx][1]] == 'multinomial':
            imputed_value = M_c['column_metadata'][Q[imputeindx][1]]['value_to_code'][imputed_value]
        T_imputed[Q[imputeindx][0]][Q[imputeindx][1]] = imputed_value

    return T_imputed

def predict(M_c, X_L, X_D, Y, Q, n, get_next_seed, return_samples=False):
    # Predict is currently the same as impute except that the row Id in the query must lie outside the 
    # length of the table used to generate the model
    # For now, we will just call "impute" and leave it to the user to generate the query correctly 
    
    # FIXME: allow more than one cell to be predicted
    assert(len(Q)==1)
    if return_samples:
        e, samples = su.impute(M_c, X_L, X_D, Y, Q, n, get_next_seed, return_samples=True)
    else:
        e = su.impute(M_c, X_L, X_D, Y, Q, n, get_next_seed)
    return e

def predict_and_confidence(M_c, X_L, X_D, Y, Q, n, get_next_seed):
    # FIXME: allow more than one cell to be predicted
    assert(len(Q)==1)
    e, confidence = su.impute_and_confidence(M_c, X_L, X_D, Y, Q, n, get_next_seed)
    return e, confidence
    
def predict_in_table(T_test, T, M_c, X_L, X_D, numDraws, get_next_seed):
    # Predict all missing values in a table
    num_rows = len(T)
    num_cols = len(T[0])
    num_rows_test= len(T)
    num_cols_test = len(T[0])

    assert(num_cols == num_cols_test)
    
    # Identify column types
    col_names = numpy.array([M_c['idx_to_name'][str(col_idx)] for col_idx in range(num_cols)])
    coltype = []
    for colindx in range(len(col_names)):
        if M_c['column_metadata'][colindx]['modeltype'] == 'normal_inverse_gamma':
            coltype.append('continuous')
        else:
            coltype.append('multinomial')

    # Find missing values            
    rowsWithNans = [rowsWithNans for rowsWithNans in range(len(T_test)) if any(isnan_mixedtype(T_test[rowsWithNans]))]
    Q = []
    for x in rowsWithNans:
        y = [y for y in range(len(T_test[0])) if isnan_mixedtype([T_test[x][y]])]
        Q.extend(zip([x]*len(y), y)) 

    # Build queries for imputation
    numPredictions = len(Q)
 
    # Impute missing values in table
    values_list = []
    for queryindx in range(len(Q)):
        # Build conditions - we have to loop over conditions because "Impute" can only handles one query at a time
        # We already know the row Id, so just build conditions based on the rest of the row if data is available
        # Find attributes in the row that are available
        indx_row = Q[queryindx][0]
        condition_fields = numpy.where(~numpy.isnan(T_test[indx_row]))
        Y = []
        for indx_col in range(len(condition_fields[0])):
            Y.append([num_rows+indx_row, condition_fields[0][indx_col], T_test[indx_row][condition_fields[0][indx_col]]])
        #print [Q[queryindx]], Y
       
        values = predict(M_c, X_L, X_D, Y, [Q[queryindx]], numDraws, get_next_seed)
        values_list.append(values)

    # Put the samples back into the data table
    T_predicted = copy(T_test)

    for predictindx in range(numPredictions):
        predicted_value = values_list[predictindx]
        if coltype[Q[predictindx][1]] == 'multinomial':
            predicted_value = M_c['column_metadata'][Q[predictindx][1]]['value_to_code'][predicted_value]
        T_predicted[Q[predictindx][0]][Q[predictindx][1]] = predicted_value

    return T_predicted

def row_similarity(row_index, column_indices, X_D_list, X_L_list, num_returns = 10):

    # Finds rows most similar to row_index (index into the table) conditioned on
    # attributes represented by the column_indices based on the mappings into
    # categories, X_D_list, generated in each chain.

    # Create a list of scores for each row in the table
    score = numpy.zeros(len(X_D_list[0][0]))

    # For one chain
    for chain_indx in range(len(X_D_list)):
        X_D = X_D_list[chain_indx]
        X_L = X_L_list[chain_indx]

        # Find the number of views and view assignments from X_L
        view_assignments = X_L['column_partition']['assignments']
        view_assignments = numpy.array(view_assignments)
        num_features = len(view_assignments) # i.e, number of attributes
        num_views = len(set(view_assignments))

        # Find which view each conditional attribute (column_indices) belongs to 
        views_for_cols = view_assignments[column_indices]
        print views_for_cols
        for viewindx in views_for_cols:
            # Find which cluster the target row is in 
            tgt_cluster = X_D[viewindx][row_index]
    
            # Find every row in this cluster and give them all a point
            match_rows = [i for i in range(len(X_D[viewindx])) if X_D[viewindx][i] == tgt_cluster]
            score[match_rows] = score[match_rows] + 1
            
    
    # Normalize between 0 and 1
    normfactor = len(column_indices)*len(X_D_list)
    normscore = numpy.asarray([float(a)/normfactor for a in score])

    # Sort in descending order
    argsorted = numpy.argsort(normscore)[::-1]     
    sortedscore = normscore[argsorted]

    return argsorted[0:num_returns], sortedscore[0:num_returns]

########NEW FILE########
__FILENAME__ = validate_utils
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
from collections import Counter
#
import crosscat.utils.file_utils as fu


modeltypes = set(["asymmetric_beta_bernoulli", "normal_inverse_gamma", "pitmanyor_atom", "symmetric_dirichlet_discrete", "poisson_gamma"])

strify_dict = lambda in_dict: dict([
        (str(key), str(value))
        for key, value in in_dict.iteritems()
        ])

##################
# helpers for cython saved states
def strify_M_r(M_r):
    M_r['name_to_idx'] = strify_dict(M_r['name_to_idx'])
    M_r['idx_to_name'] = strify_dict(M_r['idx_to_name'])
    return M_r

def strify_M_c(M_c):
    M_c['name_to_idx'] = strify_dict(M_c['name_to_idx'])
    M_c['idx_to_name'] = strify_dict(M_c['idx_to_name'])
    for column_metadata_i in M_c['column_metadata']:
        column_metadata_i['value_to_code'] = \
            strify_dict(column_metadata_i['value_to_code'])
        column_metadata_i['code_to_value'] = \
            strify_dict(column_metadata_i['code_to_value'])
    return M_c

def dirichelt_alpha_to_alpha(in_dict):
    in_dict['alpha'] = in_dict.pop('dirichlet_alpha')
    return in_dict

def convert_column_hypers(in_dict):
    if 'r' in in_dict:
        in_dict['kappa'] = in_dict.pop('r')
        in_dict['alpha'] = in_dict.pop('nu')
        in_dict['beta'] = in_dict.pop('s')
    else:
        in_dict = dirichelt_alpha_to_alpha(in_dict)
    return in_dict

def convert_suffstats(view_state_i):
    column_component_suffstats = view_state_i['column_component_suffstats']
    for col_idx, col_suffstats in enumerate(column_component_suffstats):
        for cluster_idx, suffstats in enumerate(col_suffstats):
            if 'sum_x' not in suffstats:
                N = suffstats.pop('N')
                col_suffstats[cluster_idx] = dict(counts=suffstats, N=N)
    return view_state_i

def convert_X_L(X_L):
    for column_hypers in X_L['column_hypers']:
        column_hypers = convert_column_hypers(column_hypers)
    for view_state_i in X_L['view_state']:
        convert_suffstats(view_state_i)
    return X_L

def convert_T(T):
    num_rows = len(T)
    num_cols = len(T[0])
    dims = [num_rows, num_cols]
    T = dict(data=T, orientation="row_major", dimensions=dims)
    return T
# helpers for cython saved states
##################

def assert_map_consistency(map_1, map_2):
    assert(len(map_1)==len(map_2))
    for key in map_1:
        assert(key == map_2[map_1[key]])

def verify_keys(keys, in_dict):
    for key in keys:
        assert key in in_dict, "%s not in %s" % (key, in_dict)

def asymmetric_beta_bernoulli_hyper_validator(in_dict):
    required_keys = ["strength", "balance"]
    verify_keys(required_keys, in_dict)
    assert 0 <= in_dict["strength"]
    assert 0 <= in_dict["balance"]
    assert in_dict["balance"] <= 1

def normal_inverse_gamma_hyper_validator(in_dict):
    required_keys = ["mu", "kappa", "alpha", "beta"]
    verify_keys(required_keys, in_dict)
    #
    # mu ranges from negative infinity to positive infinity
    # kappa, alpha, beta range from 0 to infinity
    assert 0 < in_dict["kappa"]
    assert 0 <= in_dict["alpha"]
    assert 0 <= in_dict["beta"]

def pitmanyor_atom_hyper_validator(in_dict):
    required_keys = ["gamma", "alpha"]
    verify_keys(required_keys, in_dict)
    #
    assert 0 < in_dict["gamma"]
    assert in_dict["gamma"] < 1
    assert -gamma < in_dict["alpha"]

def symmetric_dirichlet_discrete_hyper_validator(in_dict):
    required_keys = ["alpha", "K"]
    verify_keys(required_keys, in_dict)
    # range of alpha is negative infinity to positive infinity
    assert 0 < in_dict["alpha"]
    assert 1 < in_dict["K"]

def poisson_gamma_hyper_validator(in_dict):
    nrequired_keys = ["kappa", "beta"]
    verify_keys(required_keys, in_dict)
    # kappa and beta range from (0, infinity)
    assert 0 < in_dict["kappa"]
    assert 0 < in_dict["beta"]

modeltype_hyper_validators = {
    "asymmetric_beta_bernoulli": asymmetric_beta_bernoulli_hyper_validator,
    "normal_inverse_gamma": normal_inverse_gamma_hyper_validator,
    "pitmanyor_atom": pitmanyor_atom_hyper_validator,
    "symmetric_dirichlet_discrete": symmetric_dirichlet_discrete_hyper_validator,
    "poisson_gamma": poisson_gamma_hyper_validator
}

def asymmetric_beta_bernoulli_suffstats_validator(in_dict):
    required_keys = ["0_count", "1_count", "N"]
    verify_keys(required_keys, in_dict)
    #
    assert in_dict["0_count"] + in_dict["1_count"] == in_dict["N"]
    assert 0 <= in_dict["0_count"]
    assert 0 <= in_dict["1_count"]

def normal_inverse_gamma_suffstats_validator(in_dict):
    required_keys = ["sum_x", "sum_x_squared", "N"]
    verify_keys(required_keys, in_dict)
    assert 0 <= in_dict["sum_x_squared"]
    assert 0 <= in_dict["N"]

def pitmanyor_atom_suffstats_validator(in_dict):
    required_keys = ["counts", "N"]
    verify_keys(required_keys, in_dict)
    #
    assert sum(in_dict["counts"]) == in_dict["N"]

def symmetric_dirichlet_discrete_suffstats_validator(in_dict):
    required_keys = ["counts", "N"]
    verify_keys(required_keys, in_dict)
    #
    assert sum(in_dict["counts"].values()) == in_dict["N"]

def poisson_gamma_suffstats_validator(in_dict):
    required_keys = ["summed_values", "N"]
    verify_keys(required_keys, in_dict)
    #
    assert 0 <= in_dict["summed_values"]
    assert 0 <= in_dict["N"]

modeltype_suffstats_validators = {
    "asymmetric_beta_bernoulli": asymmetric_beta_bernoulli_suffstats_validator,
    "normal_inverse_gamma": normal_inverse_gamma_suffstats_validator,
    "pitmanyor_atom": pitmanyor_atom_suffstats_validator,
    "symmetric_dirichlet_discrete": symmetric_dirichlet_discrete_suffstats_validator,
    "poisson_gamma": poisson_gamma_suffstats_validator
}

def assert_mc_consistency(mc):
    # check the name to index maps
    assert_map_consistency(mc["name_to_idx"], mc["idx_to_name"])
    # check that there is metadata for each column
    assert(len(mc["name_to_idx"])==len(mc["column_metadata"]))
    # check that each metadata includes a model type and code-value map
    for column_metadata_i in mc["column_metadata"]:
        assert(column_metadata_i["modeltype"] in modeltypes)
        assert_map_consistency(column_metadata_i["value_to_code"],
                               column_metadata_i["code_to_value"])

def assert_mr_consistency(mr):
    assert_map_consistency(mr["name_to_idx"], mr["idx_to_name"])

def assert_xl_view_state_consistency(view_state_i, mc):
    column_names = view_state_i["column_names"]
    column_component_suffstats = view_state_i["column_component_suffstats"]
    for column_name_i, column_component_suffstats_i in \
            zip(column_names, column_component_suffstats):
        # keys must be strings
        global_column_idx = mc["name_to_idx"][str(column_name_i)]
        modeltype = mc["column_metadata"][int(global_column_idx)]["modeltype"]
        suffstats_validator = modeltype_suffstats_validators[modeltype]
        for component_suffstats in column_component_suffstats_i:
            suffstats_validator(component_suffstats)

def assert_xl_consistency(xl, mc):
    assignment_counts = Counter(xl["column_partition"]["assignments"])
    # sum(xl["counts"]) == len(assignments) is a byproduct of above
    for idx, count in enumerate(xl["column_partition"]["counts"]):
        assert(count==assignment_counts[idx])
    for column_metadata_i, column_hypers_i in \
            zip(mc["column_metadata"], xl["column_hypers"]):
        modeltype = column_metadata_i["modeltype"]
        validator = modeltype_hyper_validators[modeltype]
        validator(column_hypers_i)
        if modeltype == "symmetric_dirichlet_discrete":
            num_codes_metadata = len(column_metadata_i["value_to_code"])
            num_codes_hypers = column_hypers_i["K"]
            assert num_codes_metadata == num_codes_hypers
            # FIXME: should assert len(suffstats['counts']) <= num_codes_hypers
    for view_state_i in xl["view_state"]:
        assert_xl_view_state_consistency(view_state_i, mc)
    assert sum(xl["column_partition"]["counts"]) == len(mc["name_to_idx"])

    
def assert_xd_consistency(xd, mr, mc):
    # is number of row labels in xd's first view equal to number of row names?
    assert len(xd[0]) == len(mr["name_to_idx"])
    # do all views have the same number of row labels?
    assert len(set(map(len, xd))) == 1

def assert_t_consistency(T, mr, mc):
    # is it rectangular?
    assert len(set(map(len, T["data"]))) == 1
    if T["orientation"] == "row_major":
        assert T["dimensions"][0] == len(T["data"])
        assert T["dimensions"][1] == len(T["data"][0])
        assert T["dimensions"][0] == len(mr["name_to_idx"])
        assert T["dimensions"][1] == len(mc["name_to_idx"])
    else: # "column_major"
        assert T["dimensions"][1] == len(T["data"])
        assert T["dimensions"][0] == len(T["data"][0])
        assert T["dimensions"][1] == len(mr["name_to_idx"])
        assert T["dimensions"][0] == len(mc["name_to_idx"])

def assert_other(mr, mc, xl, xd, T):
    # is the number of views in xd equal to their cached counts in xl?
    assert len(xl["column_partition"]["counts"]) == len(xd)

if __name__ == '__main__':
    import argparse
    import json
    parser = argparse.ArgumentParser('A script to validate a json file\'s compliance with the predictive-DB spec')
    parser.add_argument('filename', type=str)
    args = parser.parse_args()
    filename = args.filename
    #
    if filename.endswith('.pkl.gz'):
        parsed_sample = fu.unpickle(filename)
        parsed_sample['M_r'] = strify_M_r(parsed_sample['M_r'])
        parsed_sample['M_c'] = strify_M_c(parsed_sample['M_c'])
        parsed_sample['X_L'] = convert_X_L(parsed_sample['X_L'])
        parsed_sample['T'] = convert_T(parsed_sample['T'])
    else:
        with open(filename) as fh:
            one_line = "".join(fh.readlines()).translate(None,"\n\t ")
            parsed_sample = json.loads(one_line)

    M_c = parsed_sample["M_c"]
    M_r = parsed_sample["M_r"]
    X_L = parsed_sample["X_L"]
    X_D = parsed_sample["X_D"]
    T = parsed_sample["T"]

    assert_mc_consistency(M_c)
    assert_mr_consistency(M_r)
#assert_xl_view_state_consistency(view_state_i, mc)
    assert_xl_consistency(X_L, M_c)
    assert_xd_consistency(X_D, M_r, M_c)
    assert_t_consistency(T, M_r, M_c)
    assert_other(M_r, M_c, X_L, X_D, T)

########NEW FILE########
__FILENAME__ = xnet_utils
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import os
import re
import argparse
import cPickle
import zlib
import base64
#
import crosscat.settings as S
from crosscat.settings import Hadoop as hs
import crosscat.utils.file_utils as fu
import crosscat.utils.data_utils as du


default_table_data_filename = hs.default_table_data_filename
default_table_filename = hs.default_table_filename
default_analyze_args_dict = hs.default_analyze_args_dict.copy()
default_initialize_args_dict = hs.default_initialize_args_dict.copy()


# read the data, create metadata
def read_and_pickle_table_data(table_data_filename, pkl_filename):
    T, M_r, M_c = du.read_model_data_from_csv(table_data_filename,
                                              gen_seed=0)
    table_data = dict(T=T, M_r=M_r, M_c=M_c)
    fu.pickle(table_data, pkl_filename)
    return table_data

# cat the data into the script, as hadoop would
def run_script_local(infile, script_name, outfile, table_data_filename=None):
    infix_str = ''
    if table_data_filename is not None:
        infix_str = '--table_data_filename %s' % table_data_filename
    cmd_str = 'cat %s | python %s %s > %s'
    cmd_str %= (infile, script_name, infix_str, outfile)
    print cmd_str
    os.system(cmd_str)
    return

def my_dumps(in_object):
    ret_str = cPickle.dumps(in_object)
    ret_str = zlib.compress(ret_str)
    ret_str = base64.b64encode(ret_str) 
    return ret_str

def my_loads(in_str):
    in_str = base64.b64decode(in_str)
    in_str = zlib.decompress(in_str)
    out_object = cPickle.loads(in_str)
    return out_object

def write_hadoop_line(fh, key, dict_to_write):
    escaped_str = my_dumps(dict_to_write)
    fh.write(str(key) + ' ')
    fh.write(escaped_str)
    fh.write('\n')
    return

line_re = '(\d+)\s+(.*)'
pattern = re.compile(line_re)
def parse_hadoop_line(line):
    line = line.strip()
    match = pattern.match(line)
    key, dict_in = None, None
    if match:
        key, dict_in_str = match.groups()
        try:
          dict_in = my_loads(dict_in_str)
        except Exception, e:
          # for parsing new NLineInputFormat
          match = pattern.match(dict_in_str)
          if match is None:
            print 'OMG: ' + dict_in_str[:50]
            import pdb; pdb.set_trace()
          key, dict_in_str = match.groups()
          dict_in = my_loads(dict_in_str)
    return key, dict_in

def write_support_files(table_data, table_data_filename,
                        command_dict, command_dict_filename):
    fu.pickle(table_data, table_data_filename)
    fu.pickle(command_dict, command_dict_filename)
    return

def write_initialization_files(initialize_input_filename,
                               table_data, table_data_filename,
                               initialize_args_dict, intialize_args_dict_filename,
                               n_chains=10):
    write_support_files(table_data, table_data_filename,
                        initialize_args_dict, intialize_args_dict_filename)
    with open(initialize_input_filename, 'w') as out_fh:
        for SEED in range(n_chains):
            out_dict = dict(SEED=SEED)
            write_hadoop_line(out_fh, SEED, out_dict)
    return

def write_analyze_files(analyze_input_filename, X_L_list, X_D_list,
                        table_data, table_data_filename,
                        analyze_args_dict, analyze_args_dict_filename,
                        SEEDS=None):
    assert len(X_L_list) == len(X_D_list)
    write_support_files(table_data, table_data_filename,
                        analyze_args_dict, analyze_args_dict_filename)
    if SEEDS is None:
        SEEDS = xrange(len(X_L_list))
    with open(analyze_input_filename, 'w') as out_fh:
        for SEED, X_L, X_D in zip(SEEDS, X_L_list, X_D_list):
            out_dict = dict(SEED=SEED, X_L=X_L, X_D=X_D)
            write_hadoop_line(out_fh, SEED, out_dict)
    return

# read initialization output, write analyze input
def link_initialize_to_analyze(initialize_output_filename,
                               analyze_input_filename,
                               analyze_args_dict=None):
    if analyze_args_dict is None:
        analyze_args_dict = default_analyze_args_dict.copy()
    num_lines = 0
    with open(initialize_output_filename) as in_fh:
        with open(analyze_input_filename, 'w') as out_fh:
            for line in in_fh:
                num_lines += 1
                key, dict_in = parse_hadoop_line(line)
                dict_in.update(analyze_args_dict)
                dict_in['SEED'] = int(key)
                write_hadoop_line(out_fh, key, dict_in)
    return num_lines

def get_is_vpn_connected():
    # cmd_str = 'ifconfig | grep tun'
    cmd_str = 'ping -W 2 -c 1 10.1.90.10'
    lines = [line for line in os.popen(cmd_str)]
    is_vpn_connected = False
    if len(lines) != 0:
        is_vpn_connected = True
    return is_vpn_connected

def assert_vpn_is_connected():
    is_vpn_connected = get_is_vpn_connected()
    assert is_vpn_connected
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('do_what', type=str)
    parser.add_argument('--hadoop_filename', type=str, default=None)
    parser.add_argument('--table_filename',
        default=default_table_filename, type=str)
    parser.add_argument('--pkl_filename',
                        default=default_table_data_filename, type=str)
    parser.add_argument('--initialize_input_filename',
                        default='initialize_input', type=str)
    parser.add_argument('--initialize_output_filename',
                        default='initialize_output', type=str)
    parser.add_argument('--analyze_input_filename',
                        default='analyze_input', type=str)
    parser.add_argument('--n_steps', default=1, type=int)
    parser.add_argument('--n_chains', default=1, type=int)
    args = parser.parse_args()
    #
    do_what = args.do_what
    hadoop_filename = args.hadoop_filename
    table_filename = args.table_filename
    pkl_filename = args.pkl_filename
    initialize_input_filename = args.initialize_input_filename
    initialize_output_filename = args.initialize_output_filename
    analyze_input_filename = args.analyze_input_filename
    n_steps = args.n_steps
    n_chains = args.n_chains


    if do_what == 'read_and_pickle_table_data':
        read_and_pickle_table_data(table_filename, pkl_filename)
    elif do_what == 'write_initialization_files':
        write_initialization_files(initialize_input_filename,
                                   n_chains=n_chains)
    elif do_what == 'link_initialize_to_analyze':
        analyze_args_dict = default_analyze_args_dict.copy()
        analyze_args_dict['n_steps'] = n_steps
        link_initialize_to_analyze(initialize_output_filename,
                                   analyze_input_filename,
                                   analyze_args_dict)
    elif do_what == 'assert_vpn_is_connected':
        assert_vpn_is_connected()
    elif do_what == 'parse_hadoop_lines':
        assert hadoop_filename is not None
        parsed_lines = []
        with open(hadoop_filename) as fh:
            for line in fh:
                parsed_lines.append(parse_hadoop_line(line))
                print len(parsed_lines)
        if pkl_filename != default_table_data_filename:
            fu.pickle(parsed_lines, pkl_filename)
    else:
        print 'uknown do_what: %s' % do_what

########NEW FILE########
__FILENAME__ = conf
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# -*- coding: utf-8 -*-
#
# CrossCat documentation build configuration file, created by
# sphinx-quickstart on Thu Aug  1 12:56:23 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'CrossCat'
copyright = u'2013, MIT Probabilistic Computing Project + Univ. of Louisville'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1'
# The full version, including alpha/beta/rc tags.
release = '0.1'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'rtd'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['themes']

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'CrossCatdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
    'classoptions': ',openany,oneside',
    'babel' : '\\usepackage[english]{babel}'
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'CrossCat.tex', u'CrossCat Documentation',
   u'MIT Probabilistic Computing Project + Univ. of Louisville', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'bayesdb', u'CrossCat Documentation',
     [u'MIT Probabilistic Computing Project + Univ. of Louisville'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'CrossCat', u'CrossCat Documentation',
   u'MIT Probabilistic Computing Project + Univ. of Louisville', 'CrossCat', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

########NEW FILE########
__FILENAME__ = simple_engine_example
from crosscat.LocalEngine import LocalEngine
import crosscat.utils.data_utils as data_utils


data_filename = 'T.csv'
inference_seed = 0
num_full_transitions = 10

# read the data table into internal json representation
data_table, row_metadata, column_metadata, header = \
        data_utils.read_data_objects(data_filename)

# create an engine to run analysis, inference
engine = LocalEngine(seed=inference_seed)

# initialize markov chain samples
initial_latent_state, initial_latent_state_clustering = \
        engine.initialize(column_metadata, row_metadata, data_table)

# run markov chain transition kernels on samples
latent_state, latent_state_clustering = engine.analyze(column_metadata,
        data_table, initial_latent_state, initial_latent_state_clustering,
        n_steps=num_full_transitions)


########NEW FILE########
__FILENAME__ = dha_example
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import argparse
import os
#
import numpy
#
import crosscat.settings as S
import crosscat.utils.data_utils as du
import crosscat.utils.file_utils as fu
import crosscat.LocalEngine as LE


# parse input
parser = argparse.ArgumentParser()
parser.add_argument('filename', type=str)
parser.add_argument('--inf_seed', default=0, type=int)
parser.add_argument('--gen_seed', default=0, type=int)
parser.add_argument('--num_chains', default=25, type=int)
parser.add_argument('--num_transitions', default=200, type=int)
args = parser.parse_args()
#
filename = args.filename
inf_seed = args.inf_seed
gen_seed = args.gen_seed
num_chains = args.num_chains
num_transitions = args.num_transitions
#
pkl_filename = 'dha_example_num_transitions_%s.pkl.gz' % num_transitions


def determine_Q(M_c, query_names, num_rows, impute_row=None):
    name_to_idx = M_c['name_to_idx']
    query_col_indices = [name_to_idx[colname] for colname in query_names]
    row_idx = num_rows + 1 if impute_row is None else impute_row
    Q = [(row_idx, col_idx) for col_idx in query_col_indices]
    return Q

def determine_unobserved_Y(num_rows, M_c, condition_tuples):
    name_to_idx = M_c['name_to_idx']
    row_idx = num_rows + 1
    Y = []
    for col_name, col_value in condition_tuples:
        col_idx = name_to_idx[col_name]
        col_code = du.convert_value_to_code(M_c, col_idx, col_value)
        y = (row_idx, col_idx, col_code)
        Y.append(y)
    return Y

# set everything up
T, M_r, M_c = du.read_model_data_from_csv(filename, gen_seed=gen_seed)
num_rows = len(T)
num_cols = len(T[0])
col_names = numpy.array([M_c['idx_to_name'][str(col_idx)] for col_idx in range(num_cols)])

# initialze and transition chains
seeds = range(num_chains)
engine = LE.LocalEngine(inf_seed)
X_L_list, X_D_list = engine.initialize(M_c, M_r, T, 'from_the_prior', n_chains=num_chains)
X_L_list, X_D_list = engine.analyze(M_c, T, X_L_list, X_D_list, n_steps=num_transitions)

# save the progress
to_pickle = dict(X_L_list=X_L_list, X_D_list=X_D_list)
fu.pickle(to_pickle, pkl_filename)

# to_pickle = fu.unpickle(pkl_filename)
# X_L_list = to_pickle['X_L_list']
# X_D_list = to_pickle['X_D_list']

engine = LE.LocalEngine(inf_seed)
# can we recreate a row given some of its values?
query_cols = [2, 6, 9]
query_names = col_names[query_cols]
Q = determine_Q(M_c, query_names, num_rows)
#
condition_cols = [3, 4, 10]
condition_names = col_names[condition_cols]
samples_list = []
for actual_row_idx in [1, 10, 100]:
    actual_row_values = T[actual_row_idx]
    condition_values = [actual_row_values[condition_col] for condition_col in condition_cols]
    condition_tuples = zip(condition_names, condition_values)
    Y = determine_unobserved_Y(num_rows, M_c, condition_tuples)
    samples = engine.simple_predictive_sample(M_c, X_L_list, X_D_list, Y, Q, 10)
    samples_list.append(samples)

round_1 = lambda value: round(value, 2)
# impute some values (as if they were missing)
for impute_row in [10, 20, 30, 40, 50, 60, 70, 80]:
    impute_cols = [31, 32, 52, 60, 62]
    #
    actual_values = [T[impute_row][impute_col] for impute_col in impute_cols]
    # conditions are immaterial
    Y = []
    imputed_list = []
    for impute_col in impute_cols:
        impute_names = [col_names[impute_col]]
        Q = determine_Q(M_c, impute_names, num_rows, impute_row=impute_row)
        #
        imputed = engine.impute(M_c, X_L_list, X_D_list, Y, Q, 1000)
        imputed_list.append(imputed)
    print
    print actual_values
    print map(round_1, imputed_list)

########NEW FILE########
__FILENAME__ = dha_example_ipython_parallel
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import argparse
import os
#
import numpy
#
import crosscat.settings as S
import crosscat.utils.data_utils as du
import crosscat.utils.file_utils as fu
import crosscat.LocalEngine as LE


# parse input
parser = argparse.ArgumentParser()
parser.add_argument('ipython_parallel_config', default=None, type=str)
parser.add_argument('filename', type=str)
parser.add_argument('--path_append', default=None, type=str)
parser.add_argument('--inf_seed', default=0, type=int)
parser.add_argument('--gen_seed', default=0, type=int)
parser.add_argument('--num_chains', default=25, type=int)
parser.add_argument('--num_transitions', default=200, type=int)
args = parser.parse_args()
#
ipython_parallel_config = args.ipython_parallel_config
path_append = args.path_append
filename = args.filename
inf_seed = args.inf_seed
gen_seed = args.gen_seed
num_chains = args.num_chains
num_transitions = args.num_transitions
#
pkl_filename = 'dha_example_num_transitions_%s.pkl.gz' % num_transitions


def determine_Q(M_c, query_names, num_rows, impute_row=None):
    name_to_idx = M_c['name_to_idx']
    query_col_indices = [name_to_idx[colname] for colname in query_names]
    row_idx = num_rows + 1 if impute_row is None else impute_row
    Q = [(row_idx, col_idx) for col_idx in query_col_indices]
    return Q

def determine_unobserved_Y(num_rows, M_c, condition_tuples):
    name_to_idx = M_c['name_to_idx']
    row_idx = num_rows + 1
    Y = []
    for col_name, col_value in condition_tuples:
        col_idx = name_to_idx[col_name]
        col_code = du.convert_value_to_code(M_c, col_idx, col_value)
        y = (row_idx, col_idx, col_code)
        Y.append(y)
    return Y

def do_intialize(SEED):
    _do_initialize = crosscat.LocalEngine._do_initialize
    return _do_initialize(M_c, M_r, T, 'from_the_prior', SEED)

def do_analyze((SEED, state_tuple)):
    X_L, X_D = state_tuple
    _do_analyze = crosscat.LocalEngine._do_analyze
    return _do_analyze(M_c, T, X_L, X_D, (), num_transitions, (), (), -1, -1, SEED)

# set everything up
T, M_r, M_c = du.read_model_data_from_csv(filename, gen_seed=gen_seed)
num_rows = len(T)
num_cols = len(T[0])
col_names = numpy.array([M_c['idx_to_name'][str(col_idx)] for col_idx in range(num_cols)])


## set up parallel
from IPython.parallel import Client
c = Client(ipython_parallel_config)
dview = c[:]
with dview.sync_imports():
    import crosscat
    import crosscat.LocalEngine
    import sys
if path_append is not None:
    dview.apply_sync(lambda: sys.path.append(path_append))
#
dview.push(dict(
        M_c=M_c,
        M_r=M_r,
        T=T,
        num_transitions=num_transitions
        ))
seeds = range(num_chains)
async_result = dview.map_async(do_intialize, seeds)
initialized_states = async_result.get()
#
async_result = dview.map_async(do_analyze, zip(seeds, initialized_states))
chain_tuples = async_result.get()


# visualize the column cooccurence matrix    
X_L_list, X_D_list = map(list, zip(*chain_tuples))

# save the progress
to_pickle = dict(X_L_list=X_L_list, X_D_list=X_D_list)
fu.pickle(to_pickle, pkl_filename)

# to_pickle = fu.unpickle(pkl_filename)
# X_L_list = to_pickle['X_L_list']
# X_D_list = to_pickle['X_D_list']

# can we recreate a row given some of its values?
query_cols = [2, 6, 9]
query_names = col_names[query_cols]
Q = determine_Q(M_c, query_names, num_rows)
#
condition_cols = [3, 4, 10]
condition_names = col_names[condition_cols]
samples_list = []
engine = LE.LocalEngine(inf_seed)
for actual_row_idx in [1, 10, 100]:
    actual_row_values = T[actual_row_idx]
    condition_values = [actual_row_values[condition_col] for condition_col in condition_cols]
    condition_tuples = zip(condition_names, condition_values)
    Y = determine_unobserved_Y(num_rows, M_c, condition_tuples)
    samples = engine.simple_predictive_sample(M_c, X_L_list, X_D_list, Y, Q, 10)
    samples_list.append(samples)

round_1 = lambda value: round(value, 2)
# impute some values (as if they were missing)
for impute_row in [10, 20, 30, 40, 50, 60, 70, 80]:
    impute_cols = [31, 32, 52, 60, 62]
    #
    actual_values = [T[impute_row][impute_col] for impute_col in impute_cols]
    # conditions are immaterial
    Y = []
    imputed_list = []
    for impute_col in impute_cols:
        impute_names = [col_names[impute_col]]
        Q = determine_Q(M_c, impute_names, num_rows, impute_row=impute_row)
        #
        imputed = engine.impute(M_c, X_L_list, X_D_list, Y, Q, 1000)
        imputed_list.append(imputed)
    print
    print actual_values
    print map(round_1, imputed_list)

########NEW FILE########
__FILENAME__ = dha_example_multiprocessing
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Dan Lovell and Jay Baxter
#   Authors: Dan Lovell, Baxter Eaves, Jay Baxter, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
import argparse
from multiprocessing import Pool
import os
#
import numpy
#
import crosscat.settings as S
import crosscat.utils.data_utils as du
import crosscat.utils.file_utils as fu
import crosscat.LocalEngine as LE
import crosscat.MultiprocessingEngine as MultiprocessingEngine


# parse input
parser = argparse.ArgumentParser()
parser.add_argument('filename', type=str)
parser.add_argument('--inf_seed', default=0, type=int)
parser.add_argument('--gen_seed', default=0, type=int)
parser.add_argument('--num_chains', default=14, type=int)
parser.add_argument('--num_transitions', default=2, type=int)
args = parser.parse_args()
#
filename = args.filename
inf_seed = args.inf_seed
gen_seed = args.gen_seed
num_chains = args.num_chains
num_transitions = args.num_transitions
#
pkl_filename = 'dha_example_num_transitions_%s.pkl.gz' % num_transitions


def determine_Q(M_c, query_names, num_rows, impute_row=None):
    name_to_idx = M_c['name_to_idx']
    query_col_indices = [name_to_idx[colname] for colname in query_names]
    row_idx = num_rows + 1 if impute_row is None else impute_row
    Q = [(row_idx, col_idx) for col_idx in query_col_indices]
    return Q

def determine_unobserved_Y(num_rows, M_c, condition_tuples):
    name_to_idx = M_c['name_to_idx']
    row_idx = num_rows + 1
    Y = []
    for col_name, col_value in condition_tuples:
        col_idx = name_to_idx[col_name]
        col_code = du.convert_value_to_code(M_c, col_idx, col_value)
        y = (row_idx, col_idx, col_code)
        Y.append(y)
    return Y


# set everything up
T, M_r, M_c = du.read_model_data_from_csv(filename, gen_seed=gen_seed)
num_rows = len(T)
num_cols = len(T[0])
col_names = numpy.array([M_c['idx_to_name'][str(col_idx)] for col_idx in range(num_cols)])
engine = LE.LocalEngine(inf_seed)

# run the chains
engine = MultiprocessingEngine.MultiprocessingEngine()
X_L_list, X_D_list = engine.initialize(M_c, M_r, T, n_chains=num_chains)
X_L_list, X_D_list = engine.analyze(M_c, T, X_L_list, X_D_list)

# save the progress
to_pickle = dict(X_L_list=X_L_list, X_D_list=X_D_list)
fu.pickle(to_pickle, pkl_filename)

# to_pickle = fu.unpickle(pkl_filename)
# X_L_list = to_pickle['X_L_list']
# X_D_list = to_pickle['X_D_list']

# can we recreate a row given some of its values?
query_cols = [2, 6, 9]
query_names = col_names[query_cols]
Q = determine_Q(M_c, query_names, num_rows)
#
condition_cols = [3, 4, 10]
condition_names = col_names[condition_cols]
samples_list = []
for actual_row_idx in [1, 10, 100]:
    actual_row_values = T[actual_row_idx]
    condition_values = [actual_row_values[condition_col] for condition_col in condition_cols]
    condition_tuples = zip(condition_names, condition_values)
    Y = determine_unobserved_Y(num_rows, M_c, condition_tuples)
    samples = engine.simple_predictive_sample(M_c, X_L_list, X_D_list, Y, Q, 10)
    samples_list.append(samples)

round_1 = lambda value: round(value, 2)
# impute some values (as if they were missing)
for impute_row in [10, 20, 30, 40, 50, 60, 70, 80]:
    impute_cols = [31, 32, 52, 60, 62]
    #
    actual_values = [T[impute_row][impute_col] for impute_col in impute_cols]
    # conditions are immaterial
    Y = []
    imputed_list = []
    for impute_col in impute_cols:
        impute_names = [col_names[impute_col]]
        Q = determine_Q(M_c, impute_names, num_rows, impute_row=impute_row)
        #
        imputed = engine.impute(M_c, X_L_list, X_D_list, Y, Q, 1000)
        imputed_list.append(imputed)
    print
    print actual_values
    print map(round_1, imputed_list)

########NEW FILE########
__FILENAME__ = diagnostics_example
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <codecell>

import os
#
import numpy
import pylab
pylab.ion()
pylab.show()
#
import crosscat.LocalEngine as LE
import crosscat.MultiprocessingEngine as ME
import crosscat.IPClusterEngine as IPE
import crosscat.utils.data_utils as du
import crosscat.utils.plot_utils as pu
import crosscat.utils.convergence_test_utils as ctu
import crosscat.utils.timing_test_utils as ttu
import crosscat.utils.diagnostic_utils as su

# <codecell>

# settings
gen_seed = 0
inf_seed = 0
num_clusters = 4
num_cols = 32
num_views = 4
n_steps = 64
diagnostics_every_N= 2
n_test = 40
data_max_mean = 1
data_max_std = 1.
#
#num_rows = 800
#n_chains = 16
#config_filename = os.path.expanduser('~/.config/ipython/profile_ssh/security/ipcontroller-client.json')
#
num_rows = 100
n_chains = 2
config_filename = None


# generate some data
T, M_r, M_c, data_inverse_permutation_indices = du.gen_factorial_data_objects(
        gen_seed, num_clusters, num_cols, num_rows, num_views,
        max_mean=data_max_mean, max_std=data_max_std,
        send_data_inverse_permutation_indices=True)
view_assignment_truth, X_D_truth = ctu.truth_from_permute_indices(
        data_inverse_permutation_indices, num_rows, num_cols, num_views, num_clusters)
X_L_gen, X_D_gen = ttu.get_generative_clustering(M_c, M_r, T,
        data_inverse_permutation_indices, num_clusters, num_views)
T_test = ctu.create_test_set(M_c, T, X_L_gen, X_D_gen, n_test, seed_seed=0)
#
generative_mean_test_log_likelihood = ctu.calc_mean_test_log_likelihood(M_c, T,
        X_L_gen, X_D_gen, T_test)
ground_truth_lookup = dict(
        ARI=1.0,
        mean_test_ll=generative_mean_test_log_likelihood,
        num_views=num_views,
        )

# <codecell>

# create the engine
# engine = ME.MultiprocessingEngine(seed=inf_seed)
engine = IPE.IPClusterEngine(config_filename=config_filename, seed=inf_seed)

# <codecell>

# run inference
do_diagnostics = True
X_L_list, X_D_list = engine.initialize(M_c, M_r, T, n_chains=n_chains)
X_L_list, X_D_list, diagnostics_dict = engine.analyze(M_c, T, X_L_list, X_D_list,
        n_steps=n_steps, do_diagnostics=do_diagnostics,
        diagnostics_every_N=diagnostics_every_N,
        )

# <codecell>

# plot results
pu.plot_diagnostics(diagnostics_dict, hline_lookup=ground_truth_lookup)

# <codecell>

# demonstrate custom diagnostic functions
# each custom function must take only p_State as its argument
diagnostic_func_dict = dict(LE.default_diagnostic_func_dict)
def get_ari(p_State):
    # requires environment: {view_assignment_truth}
    # requires import: {crosscat.utils.convergence_test_utils}
    X_L = p_State.get_X_L()
    ctu = crosscat.utils.convergence_test_utils
    return ctu.get_column_ARI(X_L, view_assignment_truth)
# push the function and any arguments needed from the surrounding environment
args_dict = dict(
        get_ari=get_ari,
        view_assignment_truth=view_assignment_truth,
        )
engine.dview.push(args_dict, block=True)
diagnostic_func_dict['ARI'] = get_ari

# <codecell>

# run inference
do_diagnostics = diagnostic_func_dict
X_L_list, X_D_list = engine.initialize(M_c, M_r, T, n_chains=n_chains)
X_L_list, X_D_list, diagnostics_dict = engine.analyze(M_c, T, X_L_list, X_D_list,
        n_steps=n_steps, do_diagnostics=do_diagnostics,
        diagnostics_every_N=diagnostics_every_N,
        )

# <codecell>

# plot results
which_diagnostics = ['num_views', 'column_crp_alpha', 'ARI', 'f_z[0, 1]', 'f_z[0, D]']
pu.plot_diagnostics(diagnostics_dict, hline_lookup=ground_truth_lookup,
        which_diagnostics=which_diagnostics)
# pu.plot_views(numpy.array(T), X_D_gen, X_L_gen, M_c)

# <codecell>



########NEW FILE########
