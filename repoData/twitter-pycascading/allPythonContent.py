__FILENAME__ = cache
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Example showing how to use caches.

A cache saves the result of an operation to a temporary folder, and running
the same script again will take the data from the cached files, instead of
executing the original pipe again. Try to run this job several times with
different separators: after the first run, the checkpointed state will be
used for subsequent runs.

This is useful if we want to repeatedly run the script with modifications
to parts that do not change the cached results.

For this script, the first run will have two MR jobs, but any subsequent runs
will only have one, as the
"""

import sys
from pycascading.helpers import *


@udf_map
def find_lines_with_beginning(tuple, first_char):
    try:
        if tuple.get(1)[0] == first_char:
            return [tuple.get(1)]
    except:
        pass


@udf_buffer
def concat_all(group, tuples, separator):
    out = ''
    for tuple in tuples:
        try:
            out = out + tuple.get(0) + separator
        except:
            pass
    return [out]


def main():
    if len(sys.argv) < 2:
        print 'A character must be given as a command line argument for the ' \
        'separator character.'
        return

    flow = Flow()
    input = flow.source(Hfs(TextLine(), 'pycascading_data/town.txt'))
    output = flow.tsv_sink('pycascading_data/out')

    # Select the lines beginning with 'A', and save this intermediate result
    # in the cache so that we can call the script several times with
    # different separator characters
    p = input | map_replace(find_lines_with_beginning('A'), 'line')
    # Checkpoint the results from 'p' into a cache folder named 'line_begins'
    # The caches are in the user's HDFS folder, under pycascading.cache/
    p = flow.cache('line_begins') | p
    # Everything goes to one reducer
    p | group_by(Fields.VALUES, concat_all(sys.argv[1]), 'result') | output

    flow.run(num_reducers=1)

########NEW FILE########
__FILENAME__ = callback
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
Contrived example showing that you can pass functions as args to a UDF.
Also shows how to use keyword args (just the way it's expected).

Thanks to ebernhardson.
"""

from pycascading.helpers import *


def word_count_callback(value):
    return len(value.split())


@udf_map
def word_count(tuple, inc, second_inc, callback=None):
    return [inc + second_inc + callback(tuple.get(1)), tuple.get(1)]


def main():
    flow = Flow()
    input = flow.source(Hfs(TextLine(), 'pycascading_data/town.txt'))
    output = flow.tsv_sink('pycascading_data/out')

    p = input | map_replace(
        word_count(100, second_inc=200, callback=word_count_callback),
        ['word_count', 'line']) | output

    flow.run(num_reducers=1)

########NEW FILE########
__FILENAME__ = joins
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Example showing the joining and splitting of tuple streams."""


from pycascading.helpers import *


@udf_map(produces=['ucase_lhs2', 'rhs2'])
def upper_case(tuple):
    """Return the upper case of the 'lhs2' column, and the 'rhs2' column"""
    return [tuple.get('lhs2').upper(), tuple.get('rhs2')]


def main():
    flow = Flow()
    lhs = flow.source(Hfs(TextDelimited(Fields(['col1', 'col2']), ' ',
                                        [Integer, String]),
                          'pycascading_data/lhs.txt'))
    rhs = flow.source(Hfs(TextDelimited(Fields(['col1', 'col2']), ' ',
                                        [Integer, String]),
                          'pycascading_data/rhs.txt'))
    output1 = flow.tsv_sink('pycascading_data/out1')
    output2 = flow.tsv_sink('pycascading_data/out2')

    # Join on the first columns ('col1' for both) of lhs and rhs inputs
    # We need to use declared_fields if the field names since the field names
    # of the two pipes overlap
    p = (lhs & rhs) | inner_join(['col1', 'col1'],
                                 declared_fields=['lhs1', 'lhs2', 'rhs1', 'rhs2'])

    # Save the 2nd and 4th columns of p to output1
    p | retain('lhs2', 'rhs2') | output1

    # Join on the upper-cased first column of p and the 2nd column of rhs,
    # and save the output to output2
    ((p | upper_case) & (rhs | retain('col2'))) | \
    inner_join(['ucase_lhs2', 'col2']) | output2

    flow.run(num_reducers=2)

########NEW FILE########
__FILENAME__ = map_types
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Example illustrating the different types of map operations.

In the output folders check the .pycascading_types and .pycascading_header
files to see what the names of the fields were when the pipes were sinked.
"""


from pycascading.helpers import *


def main():
    flow = Flow()
    input = flow.source(Hfs(TextLine(), 'pycascading_data/town.txt'))

    out_folder = 'pycascading_data/maps/'

    @udf(produces='word')
    def decorated_udf(tuple):
        for word in tuple.get('line').split():
            yield [word]

    def undecorated_udf(tuple):
        for word in tuple.get('line').split():
            yield [word]

    # This will create an output with one field called 'word', as the UDF
    # was declared with a 'produces'
    # In this case the swap swaps out the whole input tuple with the output
    input | map_replace(decorated_udf) | \
    flow.tsv_sink(out_folder + 'decorated_udf')

    # This will create an output with one unnamed field, but otherwise the
    # same as the previous one
    input | map_replace(undecorated_udf) | \
    flow.tsv_sink(out_folder + 'undecorated_udf')

    # This will only replace the first ('line') field with the output of
    # the map, but 'offset' will be retained
    # Note that once we add an unnamed field, all field names will be lost
    input | map_replace(1, undecorated_udf) | \
    flow.tsv_sink(out_folder + 'undecorated_udf_with_input_args')

    # This will create one field only, 'word', just like the first example
    input | map_replace(undecorated_udf, 'word') | \
    flow.tsv_sink(out_folder + 'undecorated_udf_with_output_fields')

    # This one will add the new column, 'word', to all lines
    input | map_add(decorated_udf) | \
    flow.tsv_sink(out_folder + 'decorated_udf_all')

    # This produces the same output as the previous example
    input | map_add(1, undecorated_udf, 'word') | \
    flow.tsv_sink(out_folder + 'undecorated_udf_all')

    flow.run(num_reducers=1)

########NEW FILE########
__FILENAME__ = merge_streams
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Merge two streams together.

We are using Cascading GroupBy with multiple input streams to join them into
one. The streams have to have the same field names and types.

If the column names are different, Cascading won't even build the flow,
however if the column types differ, the flow is run but most likely will fail
due to different types not being comparable when grouping.
"""

from pycascading.helpers import *


def main():
    flow = Flow()
    stream1 = flow.source(Hfs(TextDelimited(Fields(['col1', 'col2']), ' ',
                                        [Integer, String]),
                          'pycascading_data/lhs.txt'))
    stream2 = flow.source(Hfs(TextDelimited(Fields(['col1', 'col2']), ' ',
                                        [Integer, String]),
                          'pycascading_data/rhs.txt'))
    output = flow.tsv_sink('pycascading_data/out')

    (stream1 & stream2) | group_by() | output

    flow.run(num_reducers=1)

########NEW FILE########
__FILENAME__ = pagerank
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Calculates PageRank for a given graph.

We assume that there are no dangling pages with no outgoing links.
"""

import os
from pycascading.helpers import *


def test(graph_file, d, iterations):
    """This is the Python implementation of PageRank."""
    in_links = {}
    out_degree = {}
    pagerank = {}
    file = open(graph_file)
    for line in file:
        (source, dest) = line.rstrip().split()
        try:
            in_links[dest].add(source)
        except KeyError:
            in_links[dest] = set(source)
        try:
            out_degree[source] += 1
        except KeyError:
            out_degree[source] = 1
        pagerank[source] = 1.0
        pagerank[dest] = 1.0
    file.close()
    old_pr = pagerank
    new_pr = {}
    for iteration in xrange(0, iterations):
        for node in old_pr:
            new_pr[node] = (1 - d)
            try:
                new_pr[node] += \
                d * sum([old_pr[n] / out_degree[n] for n in in_links[node]])
            except KeyError:
                pass
        tmp = old_pr
        old_pr = new_pr
        new_pr = tmp
    return old_pr


def main():
    """The PyCascading job."""
    # The damping factor
    d = 0.85
    # The number of iterations
    iterations = 5

    # The directed, unweighted graph in a space-separated file, in
    # <source_node> <destination_node> format
    graph_file = 'pycascading_data/graph.txt'

    graph_source = Hfs(TextDelimited(Fields(['from', 'to']), ' ',
                                     [String, String]), graph_file)

    out_links_file = 'pycascading_data/out/pagerank/out_links'
    pr_values_1 = 'pycascading_data/out/pagerank/iter1'
    pr_values_2 = 'pycascading_data/out/pagerank/iter2'

    # Some setup here: we'll need the ougoing degree of nodes, and we will
    # initialize the pageranks of nodes to 1.0
    flow = Flow()
    graph = flow.source(graph_source)

    # Count the number of outgoing links for every node that is a source,
    # and store it in a field called 'out_degree'
    graph | group_by('from') | native.count('out_degree') | \
    flow.binary_sink(out_links_file)

    # Initialize the pageranks of all nodes to 1.0
    # This file has fields 'node' and 'pagerank', and is stored to pr_values_1
    @udf
    def constant(tuple, c):
        """Just a field with a constant value c."""
        yield [c]
    @udf
    def both_nodes(tuple):
        """For each link returns both endpoints."""
        yield [tuple.get(0)]
        yield [tuple.get(1)]
    graph | map_replace(both_nodes, 'node') | \
    native.unique(Fields.ALL) | map_add(constant(1.0), 'pagerank') | \
    flow.binary_sink(pr_values_1)

    flow.run(num_reducers=1)

    pr_input = pr_values_1
    pr_output = pr_values_2
    for iteration in xrange(0, iterations):
        flow = Flow()

        graph = flow.source(graph_source)
        pageranks = flow.meta_source(pr_input)
        out_links = flow.meta_source(out_links_file)

        # Decorate the graph's source nodes with their pageranks and the
        # number of their outgoing links
        # We could have joined graph & out_links outside of the loop, but
        # in order to demonstrate joins with multiple streams, we do it here
        p = (graph & pageranks & (out_links | rename('from', 'from_out'))) | \
        inner_join(['from', 'node', 'from_out']) | \
        rename(['pagerank', 'out_degree'], ['from_pagerank', 'from_out_degree']) | \
        retain('from', 'from_pagerank', 'from_out_degree', 'to')

        # Distribute the sources' pageranks to their out-neighbors equally
        @udf
        def incremental_pagerank(tuple, d):
            yield [d * tuple.get('from_pagerank') / tuple.get('from_out_degree')]
        p = p | map_replace(['from', 'from_pagerank', 'from_out_degree'],
                            incremental_pagerank(d), 'incr_pagerank') | \
        rename('to', 'node') | retain('node', 'incr_pagerank')

        # Add the constant jump probability to all the pageranks that come
        # from the in-links
        p = (p & (pageranks | map_replace('pagerank', constant(1.0 - d), 'incr_pagerank'))) | group_by()
        p = p | group_by('node', 'incr_pagerank', native.sum('pagerank'))

        if iteration == iterations - 1:
            # Only store the final result in a TSV file
            p | flow.tsv_sink(pr_output)
        else:
            # Store intermediate results in a binary format for faster IO
            p | flow.binary_sink(pr_output)

        # Swap the input and output folders for the next iteration
        tmp = pr_input
        pr_input = pr_output
        pr_output = tmp

        flow.run(num_reducers=1)

    print 'Results from PyCascading:', pr_input
    os.system('cat %s/.pycascading_header %s/part*' % (pr_input, pr_input))

    print 'The test values:'
    test_pr = test(graph_file, d, iterations)
    print 'node\tpagerank'
    for n in sorted(test_pr.iterkeys()):
        print '%s\t%g' % (n, test_pr[n])

########NEW FILE########
__FILENAME__ = python_fields
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Example demonstrating the use of arbitrary Python (or Java) data in tuples.

The fields have to implement Serializable.

Currently these fields cannot be joined on, since we do not want to
deserialize them for each comparison. We are also doing a join here to test
the serializers.

Note that the serialization is currently done using the standard Java
serialization framework, and thus is slow and produces large blobs. There are
plans to use more efficient serializers in the future.
"""


from pycascading.helpers import *


@udf_map(produces=['col1', 'col2', 'info'])
def add_python_data(tuple):
    """This function returns a Python data structure as well."""
    return [ tuple.get(0), tuple.get(1), [ 'first', { 'key' : 'value' } ]]


def main():
    flow = Flow()
    lhs = flow.source(Hfs(TextDelimited(Fields(['col1', 'col2']), ' ',
                                        [Integer, String]),
                          'pycascading_data/lhs.txt'))
    rhs = flow.source(Hfs(TextDelimited(Fields(['col1', 'col2']), ' ',
                                        [Integer, String]),
                          'pycascading_data/rhs.txt'))

    ((lhs | add_python_data()) & rhs) | inner_join(['col1', 'col1'],
        declared_fields=['lhs1', 'lhs2', 'info', 'rhs1', 'rhs2']) | \
        flow.tsv_sink('pycascading_data/out')

    flow.run(num_reducers=2)

########NEW FILE########
__FILENAME__ = reduce
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Example showing how to use filters and buffers.

A buffer UDF is similar to the built-in Python reduce function. It takes a
group of tuples that have been previously grouped by group_by, and yields an
arbitrary number of new tuples for the group (it is most useful though to do
some aggregation on the group). The tuples are fetched using an iterator.
"""

from pycascading.helpers import *


@udf_filter
def starts_with_letter(tuple, letter):
    try:
        return tuple.get(1)[0].upper() == letter
    except:
        return False


@udf_map
def word_count(tuple):
    return [len(tuple.get(1).split()), tuple.get(1)]


def main():
    flow = Flow()
    input = flow.source(Hfs(TextLine(), 'pycascading_data/town.txt'))
    output = flow.tsv_sink('pycascading_data/out')

    p = input | filter_by(starts_with_letter('A')) | \
    map_replace(word_count(), ['word_count', 'line'])

    @udf_buffer(produces=['word_count', 'count', 'first_chars'])
    def count(group, tuples):
        """Counts the number of tuples in the group, and also emits a string
        that is the first character of the 'line' column repeated this many
        times."""
        c = 0
        first_char = ''
        for tuple in tuples:
            c += 1
            first_char += tuple.get('line')[0]
        yield [group.get(0), c, first_char]

    p | group_by('word_count', count()) | output

    flow.run(num_reducers=2)

########NEW FILE########
__FILENAME__ = subassembly
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Example demonstrating the use of predefined subassemblies.

Useful aggregators, subassemblies, pipes available in Cascading are imported
into PyCascading by native.py
"""

from pycascading.helpers import *


def main():
    flow = Flow()
    repeats = flow.source(Hfs(TextDelimited(Fields(['col1', 'col2']), ' ',
                                            [String, Integer]),
                              'pycascading_data/repeats.txt'))
    output = flow.tsv_sink('pycascading_data/out')

    # This selects the distinct records considering all fields
    repeats | native.unique(Fields.ALL) | output

    flow.run()

########NEW FILE########
__FILENAME__ = total_sort
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Simple word count example with reverse sorting of the words by frequency."""

from pycascading.helpers import *


def main():
    flow = Flow()
    input = flow.source(Hfs(TextLine(), 'pycascading_data/town.txt'))
    output = flow.tsv_sink('pycascading_data/out')

    @udf_map
    def split_words(tuple):
        for word in tuple.get(1).split():
            yield [word]

    input | \
    map_replace(split_words, 'word') | \
    group_by('word') | \
    native.count() | \
    group_by(Fields.VALUES, sort_fields=['count'], reverse_order=True) | \
    output

    flow.run(num_reducers=5)

########NEW FILE########
__FILENAME__ = udf_contexts
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Example showing how to pass in parameters to UDFs.

The context is serialized and shipped to where the UDFs are executed. A use
case for example is to perform replicated joins on constant data.
"""

from pycascading.helpers import *


def main():
    flow = Flow()
    input = flow.source(Hfs(TextLine(), 'pycascading_data/town.txt'))
    output = flow.tsv_sink('pycascading_data/out')

    @udf_filter
    def starts_with_letters(tuple, field, letters):
        """Only let tuples through whose second field starts with a given letter.

        The set of acceptable initial letters is passed in the letters parameter,
        and is defined at the time when we build the flow.
        """
        try:
            return tuple.get(field)[0].upper() in letters
        except:
            return False

    # Retain only lines that start with an 'A' or 'T'
    input | retain('line') | starts_with_letters(0, set(['A', 'T'])) | output

    flow.run(num_reducers=2)

########NEW FILE########
__FILENAME__ = word_count
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Simple word count example."""

from pycascading.helpers import *


@udf_map(produces=['word'])
def split_words(tuple):
    """The function to split the line and return several new tuples.

    The tuple to operate on is passed in as the first parameter. We are
    yielding the results in a for loop back. Each word becomes the only field
    in a new tuple stream, and the string to be split is the 2nd field of the
    input tuple.
    """
    for word in tuple.get(1).split():
        yield [word]


def main():
    flow = Flow()
    # The TextLine() scheme produces tuples where the first field is the 
    # offset of the line in the file, and the second is the line as a string.
    input = flow.source(Hfs(TextLine(), 'pycascading_data/town.txt'))
    output = flow.tsv_sink('pycascading_data/out')

    input | split_words | group_by('word', native.count()) | output

    flow.run(num_reducers=2)

########NEW FILE########
__FILENAME__ = bootstrap
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Bootstrap the PyCascading script.

This is the main Python module that gets executed by Hadoop or in local mode.
The first command line argument is either 'local' or 'hadoop'. This determines
whether we're running the script in local mode or with Hadoop. For Hadoop we
need to pack the sources into a jar, which are extracted later to a temporary
directory, so we need to set up the search paths differently in this case.
"""

__author__ = 'Gabor Szabo'


import sys, imp


if __name__ == "__main__":
    # The first command line parameter must be 'hadoop' or 'local'
    # to indicate the running mode
    running_mode = sys.argv[1]

    # The second is the location of the PyCascading Python sources in local
    # mode, and the PyCascading tarball in Hadoop mode
    python_dir = sys.argv[2]

    # Remove the first two arguments so that sys.argv will look like as
    # if it was coming from a simple command line execution
    # The further parameters are the command line parameters to the script
    sys.argv = sys.argv[3:]

    from com.twitter.pycascading import Util

    cascading_jar = Util.getCascadingJar()
    # This is the folder where Hadoop extracted the jar file for execution
    tmp_dir = Util.getJarFolder()

    Util.setPycascadingRoot(python_dir)

    # The initial value of sys.path is JYTHONPATH plus whatever Jython appends
    # to it (normally the Python standard libraries the come with Jython)
    sys.path.extend((cascading_jar, '.', tmp_dir, python_dir + '/python',
                     python_dir + '/python/Lib'))

    # Allow the importing of user-installed Jython packages
    import site
    site.addsitedir(python_dir + 'python/Lib/site-packages')

    import os
    import encodings
    import pycascading.pipe, getopt

    # This holds some global configuration parameters
    pycascading.pipe.config = dict()

    opts, args = getopt.getopt(sys.argv, 'a:')
    pycascading.pipe.config['pycascading.distributed_cache.archives'] = []
    for opt in opts:
        if opt[0] == '-a':
            pycascading.pipe.config['pycascading.distributed_cache.archives'] \
            .append(opt[1])

    # This is going to be seen by main()
    sys.argv = args

    # It's necessary to put this import here, otherwise simplejson won't work.
    # Maybe it's automatically imported in the beginning of a Jython program,
    # but since at that point the sys.path is not set yet to Lib, it will fail?
    # Instead, we can use Java's JSON decoder...
#    import encodings

    # pycascading.pipe.config is a dict with configuration parameters
    pycascading.pipe.config['pycascading.running_mode'] = running_mode
    pycascading.pipe.config['pycascading.main_file'] = args[0]

    # Import and run the user's script
    _main_module_ = imp.load_source('__main__', \
        pycascading.pipe.config['pycascading.main_file'])
    _main_module_.main()

########NEW FILE########
__FILENAME__ = cogroup
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Operations related to a CoGroup pipe."""

__author__ = 'Gabor Szabo'


import cascading.pipe
import cascading.pipe.cogroup
import cascading.operation

from pycascading.pipe import Operation, coerce_to_fields, _Stackable


class CoGroup(Operation):

    """CoGroup two or more streams on common fields.

    This is a PyCascading wrapper around a Cascading CoGroup.
    """

    def __init__(self, *args, **kwargs):
        """Create a Cascading CoGroup pipe.

        Arguments:
        args[0] -- the fields on which to join

        Keyword arguments:
        group_name -- the groupName parameter for Cascading
        group_fields -- the fields on which to group
        declared_fields -- the declaredFields parameter for Cascading
        result_group_fields -- the resultGroupFields parameter for Cascading
        joiner -- the joiner parameter for Cascading
        num_self_joins -- the numSelfJoins parameter for Cascading
        lhs -- the lhs parameter for Cascading
        lhs_group_fields -- the lhsGroupFields parameter for Cascading
        rhs -- the rhs parameter for Cascading
        rhs_group_fields -- the rhsGroupFields parameter for Cascading
        """
        Operation.__init__(self)
        self.__args = args
        self.__kwargs = kwargs

    def __create_args(self,
                      group_name=None,
                      pipes=None, group_fields=None, declared_fields=None,
                      result_group_fields=None, joiner=None,
                      pipe=None, num_self_joins=None,
                      lhs=None, lhs_group_fields=None,
                      rhs=None, rhs_group_fields=None):
        # We can use an unnamed parameter only for group_fields
        if self.__args:
            group_fields = [coerce_to_fields(f) for f in self.__args[0]]
        args = []
        if group_name:
            args.append(str(group_name))
        if lhs:
            args.append(lhs.get_assembly())
            args.append(coerce_to_fields(lhs_group_fields))
            args.append(rhs.get_assembly())
            args.append(coerce_to_fields(rhs_group_fields))
            if declared_fields:
                args.append(coerce_to_fields(declared_fields))
                if result_group_fields:
                    args.append(coerce_to_fields(result_group_fields))
            if joiner:
                args.append(joiner)
        elif pipes:
            args.append([p.get_assembly() for p in pipes])
            if group_fields:
                args.append([coerce_to_fields(f) for f in group_fields])
                if declared_fields:
                    args.append(coerce_to_fields(declared_fields))
                    if result_group_fields:
                        args.append(coerce_to_fields(result_group_fields))
                else:
                    args.append(None)
                if joiner is None:
                    joiner = cascading.pipe.cogroup.InnerJoin()
                args.append(joiner)
        elif pipe:
            args.append(pipe.get_assembly())
            args.append(coerce_to_fields(group_fields))
            args.append(int(num_self_joins))
            if declared_fields:
                args.append(coerce_to_fields(declared_fields))
                if result_group_fields:
                    args.append(coerce_to_fields(result_group_fields))
            if joiner:
                args.append(joiner)
        return args

    def _create_with_parent(self, parent):
        if isinstance(parent, _Stackable):
            args = self.__create_args(pipes=parent.stack, **self.__kwargs)
        else:
            args = self.__create_args(pipe=parent, **self.__kwargs)
        return cascading.pipe.CoGroup(*args)


def inner_join(*args, **kwargs):
    """Shortcut for an inner join."""
    kwargs['joiner'] = cascading.pipe.cogroup.InnerJoin()
    if not 'declared_fields' in kwargs:
        kwargs['declared_fields'] = None
    return CoGroup(*args, **kwargs)


def outer_join(*args, **kwargs):
    """Shortcut for an outer join."""
    kwargs['joiner'] = cascading.pipe.cogroup.OuterJoin()
    if not 'declared_fields' in kwargs:
        kwargs['declared_fields'] = None
    return CoGroup(*args, **kwargs)


def left_outer_join(*args, **kwargs):
    """Shortcut for a left outer join."""
    # The documentation says a Cascading RightJoin is a right inner join, but
    # that's not true, it's really an outer join as it should be.
    kwargs['joiner'] = cascading.pipe.cogroup.LeftJoin()
    if not 'declared_fields' in kwargs:
        kwargs['declared_fields'] = None
    return CoGroup(*args, **kwargs)


def right_outer_join(*args, **kwargs):
    """Shortcut for a right outer join."""
    kwargs['joiner'] = cascading.pipe.cogroup.RightJoin()
    if not 'declared_fields' in kwargs:
        kwargs['declared_fields'] = None
    return CoGroup(*args, **kwargs)

########NEW FILE########
__FILENAME__ = decorators
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
PyCascading function decorators to be used with user-defined functions.

A user-defined function is a function that gets applied as a filter or an
Each function for each tuple, or the reduce-side function for tuples in a
grouping in an Every Cascading operation.

UDFs can emit a new set of tuples (as in a Function after an Each operation),
keep or filter out tuples (a Filter after an Each), or emit aggregate values
(an Aggregator or Buffer for a group after an Every).

We use globally or locally scoped Python functions to perform these
user-defined operations. When building the data processing pipeline, we can
simply stream data through a Python function with PyCascading if it was
decorated by one of the decorators.

* A udf_'map' function is executed for each input tuple, and returns no, one, or
several new output tuples.

* A 'udf_filter' is a boolean-valued function, which should return true if the
input tuple should be kept for the output, and false if not.

* A 'udf_buffer' is a function that is applied to groups of tuples, and is the
equivalent of a Cascading Buffer. It returns an aggregate after iterating
through the tuples in the group.

Exports the following:
udf
yields
numargs_expected
python_list_expected
python_dict_expected
collects_output
produces_python_list
produces_tuples
udf_filter
udf_map
udf_buffer
"""

__author__ = 'Gabor Szabo'

import inspect

from pycascading.pipe import DecoratedFunction
from com.twitter.pycascading import CascadingBaseOperationWrapper
from com.twitter.pycascading import CascadingRecordProducerWrapper


def _function_decorator(args, kwargs, defaults={}):
    """
    A decorator to recursively decorate a function with arbitrary attributes.
    """

    def fun_decorator(function_or_callabledict):
        if isinstance(function_or_callabledict, DecoratedFunction):
            # Another decorator is next
            dff = function_or_callabledict
        else:
            # The original function comes next
            dff = DecoratedFunction.decorate_function(function_or_callabledict)
        # Add the attributes to the decorated function
        dff.decorators.update(additional_parameters)
        return dff

    additional_parameters = dict(defaults)
    additional_parameters.update(kwargs)
    if len(args) == 1 and not kwargs and (inspect.isroutine(args[0]) or isinstance(args[0], DecoratedFunction)):
        # We used the decorator without ()s, the first argument is the
        # function. We cannot use additional parameters in this case.
        return fun_decorator(args[0])
    else:
        return fun_decorator


def udf(*args, **kwargs):
    """The function can receive tuples or groups of tuples from Cascading.

    This is the decorator to use when we have a function that we want to use
    in a Cascading job after an Each or Every.
    """
    return _function_decorator(args, kwargs)


def yields(*args, **kwargs):
    """The function is a generator that yields output tuples.

    PyCascading considers this function a generator that yields one or more
    output tuples before returning. If this decorator is not used, the way the
    function emits tuples is determined automatically at runtime the first time
    the funtion is called. The alternative to yielding values is to return
    one tuple with return.

    We can safely yield Nones or not yield anything at all; no output tuples
    will be emitted in this case.  
    """
    return _function_decorator(args, kwargs, \
    { 'output_method' : CascadingRecordProducerWrapper.OutputMethod.YIELDS })


def numargs_expected(num, *args, **kwargs):
    """The function expects a num number of fields in the input tuples.

    Arguments:
    num -- the exact number of fields that the input tuples must have
    """
    return _function_decorator(args, kwargs, { 'numargs_expected' : num })


def python_list_expected(*args, **kwargs):
    """PyCascading will pass in the input tuples as Python lists.

    There is some performance penalty as all the incoming tuples need to be
    converted to Python lists.
    """
    params = dict(kwargs)
    params.update()
    return _function_decorator(args, kwargs, { 'input_conversion' : \
    CascadingBaseOperationWrapper.ConvertInputTuples.PYTHON_LIST })


def python_dict_expected(*args, **kwargs):
    """The input tuples are converted to Python dicts for this function.

    PyCascading will convert all input tuples to a Python dict for this
    function. The keys of the dict are the Cascading field names and the values
    are the values read from the tuple.

    There is some performance penalty as all the incoming tuples need to be
    converted to Python dicts.
    """
    return _function_decorator(args, kwargs, { 'input_conversion' : \
    CascadingBaseOperationWrapper.ConvertInputTuples.PYTHON_DICT })


def collects_output(*args, **kwargs):
    """The function expects an output collector where output tuples are added.

    PyCascading will pass in a Cascading TupleEntryCollector to which the
    function can add output tuples by calling its 'add' method.

    Use this if performance is important, as no conversion takes place between
    Python objects and Cascading tuples.
    """
    return _function_decorator(args, kwargs, { 'output_method' : \
    CascadingRecordProducerWrapper.OutputMethod.COLLECTS })


def produces_python_list(*args, **kwargs):
    """The function emits Python lists as tuples.

    These will be converted by PyCascading to Cascading Tuples, so this impacts
    performance somewhat.
    """
    return _function_decorator(args, kwargs, { 'output_type' : \
    CascadingRecordProducerWrapper.OutputType.PYTHON_LIST })


def produces_tuples(*args, **kwargs):
    """The function emits native Cascading Tuples or TupleEntrys.

    No conversion takes place so this is a fast way to add tuples to the
    output.
    """
    return _function_decorator(args, kwargs, { 'output_type' : \
    CascadingRecordProducerWrapper.OutputType.TUPLE })


def udf_filter(*args, **kwargs):
    """This makes the function a filter.

    The function should return 'true' for each input tuple that should stay
    in the output stream, and 'false' if it is to be removed.

    IMPORTANT: this behavior is the opposite of what Cascading expects, but
    similar to how the Python filter works!

    Note that the same effect can be attained by a map that returns the tuple
    itself or None if it should be filtered out.
    """
    return _function_decorator(args, kwargs, { 'type' : 'filter' })


def udf_map(*args, **kwargs):
    """The function decorated with this emits output tuples for each input one.

    The function is called for all the tuples in the input stream as happens
    in a Cascading Each. The function input tuple is passed in to the function
    as the first parameter and is a native Cascading TupleEntry unless the
    python_list_expected or python_dict_expected decorators are also used.

    If collects_output is used, the 2nd parameter is a Cascading
    TupleEntryCollector to which Tuples or TupleEntrys can be added. Otherwise,
    the function may return an output tuple or yield any number of tuples if
    it is a generator.

    Whether the function yields or returns will be determined automatically if
    no decorators used that specify this, and so will be the output tuple type
    (it can be Python list or a Cascading Tuple).

    Note that the meaning of 'map' used here is closer to the Python map()
    builtin than the 'map' in MapReduce. It essentially means that each input
    tuple needs to be transformed (mapped) by a custom function.

    Arguments:
    produces -- a list of output field names
    """
    return _function_decorator(args, kwargs, { 'type' : 'map' })


def udf_buffer(*args, **kwargs):
    """The function decorated with this takes a group and emits aggregates.

    A udf_buffer function must follow a Cascading Every operation, which comes
    after a GroupBy. The function will be called for each grouping on a
    different reducer. The first parameter passed to the function is the
    value of the grouping field for this group, and the second is an iterator
    to the tuples belonging to this group.

    Note that the iterator always points to a static variable in Cascading
    that holds a copy of the current TupleEntry, thus we cannot cache this for
    subsequent operations in the function. Instead, take iterator.getTuple() or
    create a new TupleEntry by deep copying the item in the loop.

    Cascading also doesn't automatically add the group field to the output
    tuples, so we need to do it manually. In fact a Cascading Buffer is more
    powerful than an aggregator, although it can be used as one. It acts more
    like a function emitting arbitrary tuples for groups, rather than just a
    simple aggregator.

    By default the output tuples will be what the buffer returns or yields,
    and the grouping fields won't be included. This is different from the
    aggregators' behavior, which add the output fields to the grouping fields.

    Also, only one buffer may follow a GroupBy, in contrast to aggregators, of
    which many may be present.

    See http://groups.google.com/group/cascading-user/browse_thread/thread/f5e5f56f6500ed53/f55fdd6bba399dcf?lnk=gst&q=scope#f55fdd6bba399dcf
    """
    return _function_decorator(args, kwargs, { 'type' : 'buffer' })


def unwrap(*args, **kwargs):
    """Unwraps the tuple into function parameters before calling the function.

    This is not implemented on the Java side yet.
    """
    return _function_decorator(args, kwargs, { 'parameters' : 'unwrap' })

def tuplein(*args, **kwargs):
    return _function_decorator(args, kwargs, { 'parameters' : 'tuple' })

########NEW FILE########
__FILENAME__ = each
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Operations related to an Each pipe.

* Add fields to the stream: map_add
* Map fields to new fields: map_replace
* Map the whole tuple to the new tuple: map_to
* Filter tuples: filter_by
"""

__author__ = 'Gabor Szabo'


import inspect

import cascading.pipe
from cascading.tuple import Fields

from com.twitter.pycascading import CascadingFunctionWrapper, \
CascadingFilterWrapper

from pycascading.pipe import Operation, coerce_to_fields, wrap_function, \
random_pipe_name, DecoratedFunction
from pycascading.decorators import udf


class _Each(Operation):

    """The equivalent of Each in Cascading.

    We need to wrap @maps and @filters with different Java classes, but
    the constructors for Each are built similarly. This class provides this
    functionality.
    """

    def __init__(self, function_type, *args):
        """Build the Each constructor for the Python function.

        Arguments:
        function_type -- CascadingFunctionWrapper or CascadingFilterWrapper,
            whether we are calling Each with a function or filter
        *args -- the arguments passed on to Cascading Each
        """
        Operation.__init__(self)

        self.__function = None
        # The default argument selector is Fields.ALL (per Cascading sources
        # for Operator.java)
        self.__argument_selector = None
        # The default output selector is Fields.RESULTS (per Cascading sources
        # for Operator.java)
        self.__output_selector = None

        if len(args) == 1:
            self.__function = args[0]
        elif len(args) == 2:
            (self.__argument_selector, self.__function) = args
        elif len(args) == 3:
            (self.__argument_selector, self.__function,
             self.__output_selector) = args
        else:
            raise Exception('The number of parameters to Apply/Filter ' \
                            'should be between 1 and 3')
        # This is the Cascading Function type
        self.__function = wrap_function(self.__function, function_type)

    def _create_with_parent(self, parent):
        args = []
        if self.__argument_selector:
            args.append(coerce_to_fields(self.__argument_selector))
        args.append(self.__function)
        if self.__output_selector:
            args.append(coerce_to_fields(self.__output_selector))
        # We need to put another Pipe after the Each since otherwise
        # joins may not work as the names of pipes apparently have to be
        # different for Cascading.
        each = cascading.pipe.Each(parent.get_assembly(), *args)
        return cascading.pipe.Pipe(random_pipe_name('each'), each)


class Apply(_Each):
    """Apply the given user-defined function to each tuple in the stream.

    The corresponding class in Cascading is Each called with a Function.
    """
    def __init__(self, *args):
        _Each.__init__(self, CascadingFunctionWrapper, *args)


class Filter(_Each):
    """Filter the tuple stream through the user-defined function.

    The corresponding class in Cascading is Each called with a Filter.
    """
    def __init__(self, *args):
        _Each.__init__(self, CascadingFilterWrapper, *args)


def _any_instance(var, classes):
    """Check if var is an instance of any class in classes."""
    for cl in classes:
        if isinstance(var, cl):
            return True
    return False


def _map(output_selector, *args):
    """Maps the given input fields to output fields."""
    if len(args) == 1:
        (input_selector, function, output_field) = \
        (Fields.ALL, args[0], Fields.UNKNOWN)
    elif len(args) == 2:
        if inspect.isfunction(args[0]) or _any_instance(args[0], \
        (DecoratedFunction, cascading.operation.Function, cascading.operation.Filter)):
            # The first argument is a function, the second is the output fields
            (input_selector, function, output_field) = \
            (Fields.ALL, args[0], args[1])
        else:
            # The first argument is the input tuple argument selector,
            # the second one is the function
            (input_selector, function, output_field) = \
            (args[0], args[1], Fields.UNKNOWN)
    elif len(args) == 3:
        (input_selector, function, output_field) = args
    else:
        raise Exception('map_{add,replace} needs to be called with 1 to 3 parameters')
    if isinstance(function, DecoratedFunction):
        # By default we take everything from the UDF's decorators
        df = function
        if output_field != Fields.UNKNOWN:
            # But if we specified the output fields for the map, use that
            df = DecoratedFunction.decorate_function(function.decorators['function'])
            df.decorators = dict(function.decorators)
            df.decorators['produces'] = output_field
    elif inspect.isfunction(function):
        df = udf(produces=output_field)(function)
    else:
        df = function
    return Apply(input_selector, df, output_selector)


def map_add(*args):
    """Map the defined fields (or all fields), and add the results to the tuple.

    Note that the new field names we are adding to the tuple cannot overlap
    with existing field names, or Cascading will complain.
    """
    return _map(Fields.ALL, *args)


def map_replace(*args):
    """Map the tuple, remove the mapped fields, and add the new fields.

    This mapping replaces the fields mapped with the new fields that the
    mapping operation adds.

    The number of arguments to this function is between 1 and 3:
    * One argument: it's the map function. The output fields will be named
      after the 'produces' parameter if the map function is decorated, or
      will be Fields.UNKNOWN if it's not defined. Note that after UNKNOW field
      names are introduced to the tuple, all the other field names are also
      lost.
    * Two arguments: it's either the input field selector and the map function,
      or the map function and the output fields' names.
    * Three arguments: they are interpreted as the input field selector, the
      map function, and finally the output fields' names.
    """
    return _map(Fields.SWAP, *args)


def map_to(*args):
    """Map the tuple, and keep only the results returned by the function."""
    return _map(Fields.RESULTS, *args)


def filter_by(function):
    if isinstance(function, DecoratedFunction):
        # We make sure we will treat the function as a filter
        # Here we make a copy of the decorators so that we don't overwrite
        # the original parameters
        if function.decorators['type'] not in ('filter', 'auto'):
            raise Exception('Function is not a filter')
        df = DecoratedFunction.decorate_function(function.decorators['function'])
        df.decorators = dict(function.decorators)
        df.decorators['type'] = 'filter'
    else:
        df = udf(type='filter')(function)
    return Filter(df)

########NEW FILE########
__FILENAME__ = every
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Operations related to an Every pipe."""

__author__ = 'Gabor Szabo'


import inspect

import cascading.pipe
import cascading.operation
from cascading.tuple import Fields

from com.twitter.pycascading import CascadingAggregatorWrapper, \
CascadingBufferWrapper

from pycascading.pipe import Operation, coerce_to_fields, wrap_function, \
random_pipe_name, DecoratedFunction, _Stackable


class Every(Operation):

    """Apply an operation to a group of tuples.

    This operation is similar to Apply, but can only follow a GroupBy or
    CoGroup. It runs a Cascading Aggregator or Buffer on every grouping.
    Native Java aggregators or buffers may be used, and also PyCascading
    @reduces.

    By default the tuples contain only the values in a group, but not the
    grouping field. This can be had from the group first parameter.
    """

    def __init__(self, *args, **kwargs):
        """Create a Cascading Every pipe.

        Keyword arguments:
        aggregator -- a Cascading aggregator (only either aggregator or buffer
            should be used)
        buffer -- a Cascading Buffer or a PyCascading @reduce function
        output_selector -- the outputSelector parameter for Cascading
        argument_selector -- the argumentSelector parameter for Cascading
        assertion_level -- the assertionLevel parameter for Cascading
        assertion -- the assertion parameter for Cascading
        """
        Operation.__init__(self)
        self.__args = args
        self.__kwargs = kwargs

    def __create_args(self,
                      pipe=None,
                      aggregator=None, output_selector=None,
                      assertion_level=None, assertion=None,
                      buffer=None,
                      argument_selector=None):
        if self.__args:
            # If we pass in an unnamed argument, try to determine its type
            if isinstance(self.__args[0], cascading.operation.Aggregator):
                aggregator = self.__args[0]
            else:
                buffer = self.__args[0]
        # Set up some defaults
        if argument_selector is None:
            argument_selector = cascading.tuple.Fields.ALL
        if output_selector is None:
            if aggregator is not None:
                # In the case of aggregators, we want to return both the
                # groupings and the results
                output_selector = cascading.tuple.Fields.ALL
            else:
                output_selector = cascading.tuple.Fields.RESULTS

        args = []
        args.append(pipe.get_assembly())
        if argument_selector is not None:
            args.append(coerce_to_fields(argument_selector))
        if aggregator is not None:
            # for now we assume it's a Cascading aggregator straight
            args.append(wrap_function(aggregator, CascadingAggregatorWrapper))
            if output_selector:
                args.append(coerce_to_fields(output_selector))
        if assertion_level is not None:
            args.append(assertion_level)
            args.append(assertion)
        if buffer is not None:
            args.append(wrap_function(buffer, CascadingBufferWrapper))
            if output_selector:
                args.append(coerce_to_fields(output_selector))
        return args

    def _create_with_parent(self, parent):
        args = self.__create_args(pipe=parent, **self.__kwargs)
        return cascading.pipe.Every(*args)


class GroupBy(Operation):

    """GroupBy first merges the given pipes, then groups by the fields given.

    This class does the same as the corresponding Cascading GroupBy.
    """

    def __init__(self, *args, **kwargs):
        """Create a Cascading Every pipe.

        Arguments:
        args[0] -- the fields on which to group

        Keyword arguments:
        group_name -- the groupName parameter for Cascading
        group_fields -- the fields on which to group
        sort_fields -- the sortFields parameter for Cascading
        reverse_order -- the reverseOrder parameter for Cascading
        lhs_pipe -- the lhsPipe parameter for Cascading
        rhs_pipe -- the rhsPipe parameter for Cascading
        """
        Operation.__init__(self)
        self.__args = args
        self.__kwargs = kwargs

    def __create_args(self,
                      group_name=None,
                      pipes=None, group_fields=None, sort_fields=None,
                      reverse_order=None,
                      pipe=None,
                      lhs_pipe=None, rhs_pipe=None):
        # We can use an unnamed parameter only for group_fields
        if self.__args:
            group_fields = coerce_to_fields(self.__args[0])
        args = []
        if group_name:
            args.append(group_name)
        if pipes:
            args.append([p.get_assembly() for p in pipes])
            if group_fields:
                args.append(coerce_to_fields(group_fields))
                if sort_fields:
                    args.append(coerce_to_fields(sort_fields))
                    if reverse_order:
                        args.append(reverse_order)
        elif pipe:
            args.append(pipe.get_assembly())
            if group_fields:
                args.append(coerce_to_fields(group_fields))
                if sort_fields:
                    args.append(coerce_to_fields(sort_fields))
                if reverse_order:
                    args.append(reverse_order)
        elif lhs_pipe:
            args.append(lhs_pipe.get_assembly())
            args.append(rhs_pipe.get_assembly())
            args.append(coerce_to_fields(group_fields))
        return args

    def _create_with_parent(self, parent):
        if isinstance(parent, _Stackable):
            # We're chaining with a _Stackable object
            args = self.__create_args(pipes=parent.stack, **self.__kwargs)
        else:
            # We're chaining with a Chainable object
            args = self.__create_args(pipe=parent, **self.__kwargs)
        return cascading.pipe.GroupBy(*args)


class _DelayedInitialization(Operation):
    def __init__(self, callback):
        Operation.__init__(self)
        self.__callback = callback

    def _create_with_parent(self, parent):
        return self.__callback(parent).get_assembly()


def group_by(*args, **kwargs):
    if len(args) == 0:
        grouping_fields = None
        parameters = ()
    elif len(args) == 1:
        grouping_fields = args[0]
        parameters = ()
    elif len(args) == 2:
        grouping_fields = args[0]
        parameters = (Fields.ALL, args[1], Fields.UNKNOWN)
    elif len(args) == 3:
        grouping_fields = args[0]
        if inspect.isfunction(args[1]) or isinstance(args[1], \
        (DecoratedFunction, cascading.operation.Aggregator, cascading.operation.Buffer)):
            # The first argument is an aggregator/buffer,
            # the second is the output fields
            parameters = (Fields.ALL, args[1], args[2])
        else:
            parameters = (args[1], args[2], Fields.UNKNOWN)
    elif len(args) == 4:
        grouping_fields = args[0]
        parameters = (args[1], args[2], args[3])
    else:
        raise Exception('group_by needs to be called with 1 to 4 parameters')

    if parameters:
        (input_selector, function, output_field) = parameters
        if isinstance(function, DecoratedFunction):
            # By default we take everything from the UDF's decorators
            df = function
            if output_field != Fields.UNKNOWN:
                # But if we specified the output fields for the map, use that
                df = DecoratedFunction.decorate_function(function.decorators['function'])
                df.decorators = dict(function.decorators)
                df.decorators['produces'] = output_field
        elif inspect.isfunction(function):
            df = udf(produces=output_field)(function)
        else:
            df = function
        def pipe(parent):
            if grouping_fields:
                return parent | GroupBy(grouping_fields, **kwargs) | \
                    Every(df, argument_selector=input_selector)
            else:
                return parent | GroupBy(**kwargs) | \
                    Every(df, argument_selector=input_selector)
        return _DelayedInitialization(pipe)
    else:
        def pipe(parent):
            if grouping_fields:
                return parent | GroupBy(grouping_fields, **kwargs)
            else:
                return parent | GroupBy(**kwargs)
        return _DelayedInitialization(pipe)

########NEW FILE########
__FILENAME__ = helpers
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Helper functions for a PyCascading script.

This module imports the PyCascading modules so that we don't have to import
them manually all the time. It also imports the Java classes wrapping the
primitive types (Integer, Long, Float, Double, String), so that casts are made
easy. Furthermore frequently used Cascading classes are also imported, such as
Fields, Tuple, and TupleEntry, and the pre-defined aggregators, filters,
assemblies, and schemes.
"""

__author__ = 'Gabor Szabo'


import time, struct, subprocess

# Import frequently used Cascading classes
# We import these first so that we can override some global names (like Rename)
from cascading.tuple import Fields, Tuple, TupleEntry
from cascading.operation.aggregator import *
from cascading.operation.filter import *
from cascading.pipe.assembly import *
from cascading.scheme import *
from cascading.tap import *

# Import all important PyCascading modules so we don't have to in the scripts
from pycascading.decorators import *
from pycascading.tap import *
from pycascading.operators import *
from pycascading.each import *
from pycascading.every import *
from pycascading.cogroup import *
# We don't import * as the name of some functions (sum) collides with Python
import pycascading.native as native

# Import Java basic types for conversions
from java.lang import Integer, Long, Float, Double, String

import com.twitter.pycascading.SelectFields
from pycascading.pipe import coerce_to_fields


class Getter():

    """A wrapper for an object with 'get' and 'set' methods.

    If the object has a .get(key) method and a .set(key, value) method,
    these can be replaced by referencing the key with []s.
    """

    def __init__(self, object):
        self.object = object

    def __getitem__(self, key):
        return self.object.get(key)

    def __setitem__(self, key, value):
        return self.object.set(key, value)


def time2epoch(t):
    """Converts times in UTC to seconds since the UNIX epoch, 1/1/1970 00:00.

    Arguments:
    t -- the time string in 'YYYY-MM-DD hh:mm:ss' format

    Exceptions:
    Throws an exception if t is not in the right format.
    """
    t = time.strptime(t + ' UTC', '%Y-%m-%d %H:%M:%S.0 %Z')
    return int(time.mktime(t)) - time.timezone


def bigendian2long(b):
    """Converts a series of 4 bytes in big-endian format to a Java Long.

    Arguments:
    b -- a string of 4 bytes that represent a word
    """
    return Long(struct.unpack('>I', b)[0])


def bigendian2int(b):
    """Converts a series of 4 bytes in big-endian format to a Python int.

    Arguments:
    b -- a string of 4 bytes that represent a word
    """
    return struct.unpack('>i', b)[0]


def SelectFields(fields):
    """Keeps only some fields in the tuple stream.

    Arguments:
    fields -- a list of fields to keep, or a Cascading Fields wildcard
    """
    return com.twitter.pycascading.SelectFields(coerce_to_fields(fields))


def read_hdfs_tsv_file(path):
    """Read a tab-separated HDFS folder and yield the records.

    The first line of the file should contain the name of the fields. Each
    record contains columns separated by tabs.

    Arguments:
    path -- path to a tab-separated folder containing the data files
    """
    pipe = subprocess.Popen('hdfs -cat "%s/.pycascading_header" "%s/part-*"' \
    % (path, path), shell=True, stdout=subprocess.PIPE).stdout
    first_line = True
    for line in pipe:
        line = line[0 : (len(line) - 1)]
        fields = line.split('\t')
        if first_line:
            field_names = fields
            first_line = False
        else:
            yield dict(zip(field_names, fields))

########NEW FILE########
__FILENAME__ = init_module
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Used internally. PyCascading module to set up the paths for the sources.

The module that gets loaded first when a Cascading pipeline is deserialized.
PyCascading needs to start a Jython interpreter whenever a mapper or reducer
executes Python code, so we need to start an interpreter, set up the
environment, and load the job's source code.
"""

__author__ = 'Gabor Szabo'


import sys


def setup_paths(module_paths):
    """Set up sys.path on the mappers and reducers.

    module_paths is an array of path names where the sources or other
    supporting files are found. In particular, module_paths[0] is the location
    of the PyCascading Python sources, and modules_paths[1] is the location of
    the source file defining the function.

    In Hadoop mode (with remote_deploy.sh), the first two -a options must
    specify the archives of the PyCascading sources and the job sources,
    respectively.

    Arguments:
    module_paths -- the locations of the Python sources 
    """
    from com.twitter.pycascading import Util

    cascading_jar = Util.getCascadingJar()
    jython_dir = module_paths[0]

    sys.path.extend((cascading_jar, jython_dir + '/python',
                     jython_dir + '/python/Lib'))
    sys.path.extend(module_paths[1 : ])

    # Allow importing of user-installed Jython packages
    # Thanks to Simon Radford
    import site
    site.addsitedir(jython_dir + 'python/Lib/site-packages')

    # Haha... it's necessary to put this here, otherwise simplejson won't work.
    # Maybe it's automatically imported in the beginning of a Jython program,
    # but since at that point the sys.path is not set yet to Lib, it will fail?
    #import encodings

########NEW FILE########
__FILENAME__ = native
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Aggregators, filters, functions, and assemblies adapted to PyCascading.

These useful operations are provided by Cascading.
"""

__author__ = 'Gabor Szabo'


import cascading.operation.aggregator as aggregator
import cascading.operation.filter as filter
import cascading.operation.function as function
import cascading.pipe.assembly as assembly

from pycascading.pipe import coerce_to_fields, SubAssembly


def average(*args):
    args = list(args)
    if args:
        args[0] = coerce_to_fields(args[0])
    return aggregator.Average(*args)


def count(*args):
    args = list(args)
    if args:
        args[0] = coerce_to_fields(args[0])
    return aggregator.Count(*args)


def first(*args):
    args = list(args)
    if args:
        args[0] = coerce_to_fields(args[0])
    return aggregator.First(*args)


def last(*args):
    args = list(args)
    if args:
        args[0] = coerce_to_fields(args[0])
    return aggregator.Last(*args)


def max(*args):
    args = list(args)
    if args:
        args[0] = coerce_to_fields(args[0])
    return aggregator.Max(*args)


def min(*args):
    args = list(args)
    if args:
        args[0] = coerce_to_fields(args[0])
    return aggregator.Min(*args)


def sum(*args):
    args = list(args)
    if args:
        args[0] = coerce_to_fields(args[0])
    return aggregator.Sum(*args)


def limit(lim):
    return filter.Limit(lim)


def sample(*args):
    return filter.Sample(lim)


def un_group(*args):
    args = list(args)
    if args:
        args[0] = coerce_to_fields(args[0])
    if len(args) > 1:
        if isinstance(args[1], (list, tuple)):
            new_arg = []
            for f in args[1]:
                new_arg.append(coerce_to_fields(f))
            args[1] = new_arg
        else:
            args[1] = coerce_to_fields(args[1])
    if len(args) > 2:
        if isinstance(args[2], (list, tuple)):
            new_arg = []
            for f in args[2]:
                new_arg.append(coerce_to_fields(f))
            args[2] = new_arg
    return function.UnGroup(*args)


def average_by(*args):
    args = list(args)
    if len(args) > 0:
        args[0] = coerce_to_fields(args[0])
    if len(args) > 1:
        args[1] = coerce_to_fields(args[1])
    if len(args) > 2:
        args[2] = coerce_to_fields(args[2])
    return SubAssembly(assembly.AverageBy, *args)


def count_by(*args):
    args = list(args)
    if len(args) > 0:
        args[0] = coerce_to_fields(args[0])
    if len(args) > 1:
        args[1] = coerce_to_fields(args[1])
    return SubAssembly(assembly.CountBy, *args)


def sum_by(*args):
    # SumBy has at least 3 parameters
    args = list(args)
    for i in xrange(0, 3):
        args[i] = coerce_to_fields(args[i])
    return SubAssembly(assembly.SumBy, *args)


def unique(*args):
    args = list(args)
    args[0] = coerce_to_fields(args[0])
    return SubAssembly(assembly.Unique, *args)

########NEW FILE########
__FILENAME__ = operators
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Various operations acting on the tuples.

* Select fields from the stream: retain
* Remove fields from the stream: discard (not implemented in Cascading 1.2.*)
* Rename fields: rename
"""

__author__ = 'Gabor Szabo'


import itertools

from cascading.tuple import Fields
from cascading.operation import Identity
import cascading.pipe.assembly.Rename

from pycascading.pipe import SubAssembly, coerce_to_fields
from pycascading.each import Apply


def retain(*fields_to_keep):
    """Retain only the given fields.

    The fields can be given in array or by separate parameters.
    """
    if len(fields_to_keep) > 1:
        fields_to_keep = list(itertools.chain(fields_to_keep))
    else:
        fields_to_keep = fields_to_keep[0]
    return Apply(fields_to_keep, Identity(Fields.ARGS), Fields.RESULTS)


def _discard(fields_to_discard):
    # In 2.0 there's a builtin function this, Discard
    # In 1.2 there is nothing for this
    raise Exception('Discard only works with Cascading 2.0')


def rename(*args):
    """Rename the fields to new names.

    If only one argument (a list of names) is given, it is assumed that the
    user wants to rename all the fields. If there are two arguments, the first
    list is the set of fields to be renamed, and the second is a list of the
    new names.
    """
    if len(args) == 1:
        (fields_from, fields_to) = (Fields.ALL, args[0])
    else:
        (fields_from, fields_to) = (args[0], args[1])
    return SubAssembly(cascading.pipe.assembly.Rename, \
                       coerce_to_fields(fields_from), \
                       coerce_to_fields(fields_to))

########NEW FILE########
__FILENAME__ = pipe
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Build and execute Cascading flows in Python.

Flows are built from Cascading operations that reshape, join, and split
streams. Some operations make use of user-defined functions, for instance, the
Each operation applies an UDF to each tuple seen in the stream.

Exports the following:
Pipe
CoGroup
Join
OuterJoin
LeftOuterJoin
RightOuterJoin
SubAssembly
coerce_to_fields
random_pipe_name
"""

__author__ = 'Gabor Szabo'


import types, inspect, pickle

import cascading.pipe
import cascading.tuple
import cascading.operation
import cascading.pipe.cogroup
from com.twitter.pycascading import CascadingBaseOperationWrapper, \
CascadingRecordProducerWrapper

import serializers

from java.io import ObjectOutputStream


import java.lang.Integer


def coerce_to_fields(obj):
    """
    Utility function to convert a list or field name to cascading.tuple.Fields.

    Arguments:
    obj -- a cascading.tuple.Fields, an integer, or a string, or a list of
        integers and/or strings identifying fields

    Return:
    obj coerced to a cascading.tuple.Fields object
    """
    if isinstance(obj, list):
        # For some reason integers will not be cast to Comparables by Jython,
        # so we need to do it manually before calling the Fields constructor
        for i in xrange(len(obj)):
            if isinstance(obj[i], int):
                obj[i] = java.lang.Integer(obj[i])
        return cascading.tuple.Fields(obj)
    elif isinstance(obj, str) or isinstance(obj, int):
        if isinstance(obj, int):
            obj = java.lang.Integer(obj)
        return cascading.tuple.Fields([obj])
    else:
        # obj is assumed to be Fields already
        return obj


def random_pipe_name(prefix):
    """Generate a random string that can be used to name pipes.

    Otherwise Cascading always gets confused.
    """
    import random, re, traceback
    stack = traceback.extract_stack()
    stack.reverse()
    file = None
    for s in stack:
        if not re.match(r'.*/pycascading/[^/]+\.py$', s[0]) and \
        not re.match(r'.*/bootstrap.py$', s[0]):
            file = s[0]
            line = s[1]
            i = file.rfind('/')
            if i >= 0:
                file = file[i + 1 :]
            break
    name = prefix
    if file:
        name = name + '/' + str(line) + ':' + file
    name += ' '
    id = ''
    for i in xrange(0, 4):
        name += chr(random.randint(ord('a'), ord('z')))
    return name


def wrap_function(function, casc_function_type):
    """Wrap a Python function into a Serializable and callable Java object.
    This wrapping is necessary as Cascading serializes the job pipeline before
    it sends the job to the workers. We need to in essence reconstruct the
    Python function from source on the receiving end when we deserialize the
    function, as Python is an interpreted language.

    Arguments:
    function -- either a Cascading Operation, a PyCascading-decorated Python
        function, or a native Python function
    casc_function_type -- the Cascading Operation that this Python function
        will be called by in its operate method
    """
    if isinstance(function, cascading.operation.Operation):
        return function
    if isinstance(function, DecoratedFunction):
        # Build the arguments for the constructor
        args = []
        decorators = function.decorators
        if 'numargs_expected' in decorators:
            args.append(decorators['numargs_expected'])
        if 'produces' in decorators and decorators['produces']:
            args.append(coerce_to_fields(decorators['produces']))
        # Create the appropriate type (function or filter)
        fw = casc_function_type(*args)
        function = decorators['function']
        fw.setConvertInputTuples(decorators['input_conversion'])
        if decorators['type'] in set(['map', 'buffer', 'auto']):
            fw.setOutputMethod(decorators['output_method'])
            fw.setOutputType(decorators['output_type'])
        fw.setContextArgs(decorators['args'])
        fw.setContextKwArgs(decorators['kwargs'])
    else:
        # When function is a pure Python function, declared without decorators
        fw = casc_function_type()
    fw.setFunction(function)
    fw.setWriteObjectCallBack(serializers.replace_object)
    return fw


class _Stackable(object):

    """An object that can be chained with '&' operations."""

    def __init__(self):
        self.stack = [self]

    def __and__(self, other):
        result = _Stackable()
        result.stack = self.stack + other.stack
        return result

    def __or__(self, other):
        result = Chainable()
        result._assembly = other._create_with_parent(self)
        for s in self.stack:
            result.add_context(s.context)
        return result


class Chainable(_Stackable):

    """An object that can be chained with '|' operations."""

    def __init__(self):
        _Stackable.__init__(self)
        self._assembly = None
        self.context = set()
        self.hash = 0

    def add_context(self, ctx):
        # TODO: see if context is indeed needed
        """
        This is used to keep track of the sources connected to this pipeline
        so that a possible cache can remove them for Cascading.
        """
        # Cannot use extend because of the strings
        self.context.update(ctx)

    def get_assembly(self):
        """Return the Cascading Pipe instance that this object represents."""
        if self._assembly == None:
            self._assembly = self._create_without_parent()
        return self._assembly

    def __or__(self, other):
        result = Chainable()
        if isinstance(other, cascading.operation.Aggregator):
            import every
            other = every.Every(aggregator=other)
        elif isinstance(other, cascading.operation.Function):
            import each
            other = each.Apply(other)
        elif isinstance(other, cascading.operation.Filter):
            import each
            other = each.Apply(other)
        elif inspect.isroutine(other):
            other = DecoratedFunction.decorate_function(other)
        if isinstance(other, Chainable):
            result._assembly = other._create_with_parent(self)
            result.add_context(self.context)
            result.hash = self.hash ^ hash(result._assembly)
        return result

    def _create_without_parent(self):
        """Called when the Chainable is the first member of a chain.

        We want to initialize the chain with this operation as the first
        member.
        """
        raise Exception('Cannot create without parent')

    def _create_with_parent(self, parent):
        """Called when the Chainable is NOT the first member of a chain.

        Takes a PyCascading Pipe object, or a list thereof, and returns a
        corresponding Cascading Pipe instance.

        Arguments:
        parent -- the PyCascading pipe that we need to append this operation to
        """
        raise Exception('Cannot create with parent')


class Pipe(Chainable):

    """The basic PyCascading Pipe object.

    This represents an operation on the tuple stream. A Pipe object can has an
    upstream parent (unless it is a source), and a downstream child (unless it
    is a sink).
    """

    def __init__(self, name=None, *args):
        Chainable.__init__(self)
        if name:
            self.__name = name
        else:
            self.__name = 'unnamed'

    def _create_without_parent(self):
        """
        Create the Cascading operation when this is the first element of a
        chain.
        """
        return cascading.pipe.Pipe(self.__name)

    def _create_with_parent(self, parent):
        """
        Create the Cascading operation when this is not the first element
        of a chain.
        """
        return cascading.pipe.Pipe(self.__name, parent.get_assembly())


class Operation(Chainable):

    """A common base class for all operations (Functions, Filters, etc.).

    It doesn't do anything just provides the class.
    """

    def __init__(self):
        Chainable.__init__(self)


class DecoratedFunction(Operation):

    """Decorates Python functions with arbitrary attributes.

    Additional attributes and the original functions are stored in a dict
    self.decorators.
    """

    def __init__(self):
        Operation.__init__(self)
        self.decorators = {}

    def __call__(self, *args, **kwargs):
        """
        When we call the function we don't actually want to execute it, just
        to store the parameters passed to it so that we can distribute them
        to workers as a shared context.
        """
        args, kwargs = self._wrap_argument_functions(args, kwargs)
        if args:
            self.decorators['args'] = args
        if kwargs:
            self.decorators['kwargs'] = kwargs
        return self

    def _create_with_parent(self, parent):
        """
        Use the appropriate operation when the function is used in the pipe.
        """
        my_type = self.decorators['type']
        if my_type == 'auto':
            # Determine the type of function automatically based on the parent
            if isinstance(parent, Chainable) and \
            isinstance(parent.get_assembly(), cascading.pipe.GroupBy):
                my_type = 'buffer'
            else:
                raise Exception('Function was not decorated with @udf_map or' \
                                ' @udf_filter, and I cannot decide if it is' \
                                ' a map or a filter')
        if my_type == 'map':
            import each
            return each.Apply(self)._create_with_parent(parent)
        elif my_type == 'filter':
            import pycascading.each
            return pycascading.each.Filter(self)._create_with_parent(parent)
        elif my_type == 'buffer':
            import every
            return every.Every(buffer=self)._create_with_parent(parent)
        else:
            raise Exception('Function was not annotated with ' \
                            '@udf_map(), @udf_filter(), or @udf_buffer()')

    def _wrap_argument_functions(self, args, kwargs):
        """
        Just like the nested function, any arguments that are functions
        have to be wrapped.
        """
        args_out = []
        for arg in args:
            if type(arg) == types.FunctionType:
#                args_out.append(_python_function_to_java(arg))
                args_out.append(arg)
            else:
                args_out.append(arg)
        for key in kwargs:
            if type(kwargs[key]) == types.FunctionType:
#                kwargs[key] = _python_function_to_java(kwargs[key])
                pass
        return (tuple(args_out), kwargs)

    @classmethod
    def decorate_function(cls, function):
        """Return a DecoratedFunction with the default parameters set."""
        dff = DecoratedFunction()
        # This is the user-defined Python function
        dff.decorators['function'] = function
        # If it's used as an Each, Every, or Filter function
        dff.decorators['type'] = 'auto'
        dff.decorators['input_conversion'] = \
        CascadingBaseOperationWrapper.ConvertInputTuples.NONE
        dff.decorators['output_method'] = \
        CascadingRecordProducerWrapper.OutputMethod.YIELDS_OR_RETURNS
        dff.decorators['output_type'] = \
        CascadingRecordProducerWrapper.OutputType.AUTO
        dff.decorators['args'] = None
        dff.decorators['kwargs'] = None
        return dff


class SubAssembly(Operation):

    """Pipe for a Cascading SubAssembly.

    We can use it in PyCascading to make use of existing subassemblies,
    such as Unique.
    """

    def __init__(self, sub_assembly_class, *args):
        """Create a pipe for a Cascading SubAssembly.

        This makes use of a cascading.pipe.SubAssembly class.

        Arguments:
        sub_assembly_class -- the Cascading SubAssembly class
        *args -- parameters passed on to the subassembly's constructor when
            it's initialized
        """
        self.__sub_assembly_class = sub_assembly_class
        self.__args = args

    def _create_with_parent(self, parent):
        pipe = self.__sub_assembly_class(parent.get_assembly(), *self.__args)
        tails = pipe.getTails()
        if len(tails) == 1:
            result = tails[0]
        else:
            result = _Stackable()
            result.stack = tails
        return result

########NEW FILE########
__FILENAME__ = serializers
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Serialize a Python function.

This module will serialize a Python function in one of two ways:
* if the function is globally scoped, or a method of a class, it will
  serialize it by its name, the module, and class it was defined in. Note that
  methods of nested classes cannot be serialized, as nested classes don't hold
  references to their nesting class, so they cannot be reloaded from sources.
* if the function is scoped locally (nested), we grab its source so that it
  can be reloaded on deserialization.

Exports the following:
replace_object
"""


import inspect, re, types

import pipe


def _remove_indents_from_function(code):
    """Remove leading indents from the function's source code.

    Otherwise an exec later when running the function would complain about
    the indents.
    """

    def swap_tabs_to_spaces(line):
        new_line = ''
        for i in xrange(0, len(line)):
            if line[i] == ' ':
                new_line += line[i]
            elif line[i] == '\t':
                new_line += ' ' * 8
            else:
                new_line += line[i : len(line)]
                break
        return new_line

    lines = code.split('\n')
    indent = -1
    for line in lines:
        m = re.match('^([ \t]*)def\s.*$', line)
        if m:
            #print line, 'x', m.group(1), 'x'
            indent = len(swap_tabs_to_spaces(m.group(1)))
            break
    if indent < 0:
        raise Exception('No def found for function source')
    #print 'indent', indent
    result = ''
    for line in lines:
        line = swap_tabs_to_spaces(line)
        i = 0
        while i < len(line):
            if i < indent and line[i] == ' ':
                i += 1
            else:
                break
        result += line[i : len(line)] + '\n'
    return result


def _get_source(func):
    """Return the source code for func."""
    return _remove_indents_from_function(inspect.getsource(func))


def function_scope(func):
    if (not inspect.isfunction(func)) and (not inspect.ismethod(func)):
        raise Exception('Expecting a (non-built-in) function or method')
    name = func.func_name
    module = inspect.getmodule(func)
    module_name = module.__name__
    if module_name == '__main__':
        module_name = ''
    enclosing_object = None
    if inspect.ismethod(func):
        if func.im_class == types.ClassType:
            # Function is a classmethod
            class_name = func.im_self.__name__
            if class_name in dir(module):
                # Class is a top-level class in the module
                type = 'classmethod'
                source = None
            else:
                raise Exception('Class for @classmethod is nested, and Python '
                                'cannot determine the nesting class, '
                                'thus it\'s not allowed')
        else:
            # Function is a normal method
            class_name = func.im_class.__name__
            enclosing_object = func.im_self
            if class_name in dir(module):
                # Class is a top-level class in the module
                type = 'method'
                source = None
            else:
                raise Exception('The method\'s class is not top-level')
    else:
        # The function is a global or nested function, but not a method in a class
        class_name = None
        if name in dir(module):
            # Function is a global function
            type = 'global'
            source = None
        else:
            # Function is a closure
            type = 'closure'
            source = _get_source(func)
    return (type, module_name, class_name, name, source)


def replace_object(obj):
    if inspect.isfunction(obj):
        return function_scope(obj)
    else:
        return None

########NEW FILE########
__FILENAME__ = tap
#
# Copyright 2011 Twitter, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Taps (sources and sinks) in PyCascading.

All taps need to be registered using this module because Cascading expects
them to be named by strings when running the flow.

Exports the following:
Flow
read_hdfs_tsv_file
"""

__author__ = 'Gabor Szabo'


from pycascading.pipe import random_pipe_name, Chainable, Pipe
from com.twitter.pycascading import Util, MetaScheme

import cascading.tap
import cascading.scheme
from cascading.tuple import Fields

from org.apache.hadoop.fs import Path
from org.apache.hadoop.conf import Configuration

from pipe import random_pipe_name, Operation


def expand_path_with_home(output_folder):
    """Prepend the home folder to a relative location on HDFS if necessary.

    Only if we specified a relative path and no scheme, prepend it with the
    home folder of the user on HDFS. This behavior is similar to how
    "hadoop fs" works. If we are running in local mode, don't do anything.

    Arguments:
    output_folder -- the absolute or relative path of the output HDFS folder
    """
    import pycascading.pipe
    if pycascading.pipe.config['pycascading.running_mode'] == 'hadoop':
        if not any(map(lambda scheme: output_folder.startswith(scheme), \
                       ['hdfs:', 'file:', 's3:', 's3n:', '/'])):
            fs = Path('/').getFileSystem(Configuration())
            home_folder = fs.getHomeDirectory().toString()
            return home_folder + '/' + output_folder
    return output_folder


class Flow(object):

    """Define sources and sinks for the flow.

    This associates all sources and sinks with their head pipe mappings.
    The default number of reducers is 100. Set this in the num_reducers
    parameter when starting the flow with run().
    """

    def __init__(self):
        self.source_map = {}
        self.sink_map = {}
        self.tails = []

    def _connect_source(self, pipe_name, cascading_tap):
        """Add a source to the flow.

        Cascading needs to map taps to a pipeline with string names. This is
        inconvenient, but we need to keep track of these strings. We also need
        to count references to taps, as sometimes we need to remove pipelines
        due to replacement with a cache, and in this case we may also need to
        remove a tap. Otherwise Cascading complains about not all
        taps/pipelines being connected up to the flow.
        """
        self.source_map[pipe_name] = cascading_tap

    def source(self, cascading_tap):
        """A generic source using Cascading taps.

        Arguments:
        cascading_tap -- the Cascading Scheme object to store data into
        """
        # We can create the source tap right away and also use a Pipe to name
        # the head of this pipeline
        p = Pipe(name=random_pipe_name('source'))
        p.hash = hash(cascading_tap)
        p.add_context([p.get_assembly().getName()])
        self._connect_source(p.get_assembly().getName(), cascading_tap)
        return p

    def meta_source(self, input_path):
        """Use data files in a folder and read the scheme from the meta file.

        Defines a source tap using files in input_path, which should be a
        (HDFS) folder. Takes care of using the appropriate scheme that was
        used to store the data, using meta data in the data folder.

        Arguments:
        input_path -- the HDFS folder to store data into
        """
        input_path = expand_path_with_home(input_path)
        source_scheme = MetaScheme.getSourceScheme(input_path)
        return self.source(cascading.tap.Hfs(source_scheme, input_path))

    def sink(self, cascading_scheme):
        """A Cascading sink using a Cascading Scheme.

        Arguments:
        cascading_scheme -- the Cascading Scheme used to store the data
        """
        return _Sink(self, cascading_scheme)

    def meta_sink(self, cascading_scheme, output_path):
        """Store data together with meta information about the scheme used.

        A sink that also stores in a file information about the scheme used to
        store data, and human-readable descriptions in the .pycascading_header
        and .pycascading_types files with the field names and their types,
        respectively.

        Arguments:
        cascading_scheme -- the Cascading Scheme used to store data
        output_path -- the folder where the output tuples should be stored.
            If it exists, it will be erased and replaced!
        """
        output_path = expand_path_with_home(output_path)
        sink_scheme = MetaScheme.getSinkScheme(cascading_scheme, output_path)
        return self.sink(cascading.tap.Hfs(sink_scheme, output_path,
                                           cascading.tap.SinkMode.REPLACE))

    def tsv_sink(self, output_path, fields=Fields.ALL):
        # TODO: in local mode, do not prepend the home folder to the path
        """A sink to store the tuples as tab-separated values in text files.

        Arguments:
        output_path -- the folder for the output
        fields -- the fields to store. Defaults to all fields.
        """
        output_path = expand_path_with_home(output_path)
        return self.meta_sink(cascading.scheme.TextDelimited(fields, '\t'),
                              output_path)

    def binary_sink(self, output_path, fields=Fields.ALL):
        """A sink to store binary sequence files to store the output.

        This is a sink that uses the efficient Cascading SequenceFile scheme to
        store data. This is a serialized version of all tuples and is
        recommended when we want to store intermediate results for fast access
        later.

        Arguments:
        output_path -- the (HDFS) folder to store data into
        fields -- the Cascading Fields field selector of which tuple fields to
            store. Defaults to Fields.ALL.
        """
        output_path = expand_path_with_home(output_path)
        return self.meta_sink(cascading.scheme.SequenceFile(fields),
                              output_path)

    def cache(self, identifier, refresh=False):
        """A sink for temporary results.

        This caches results into a temporary folder if the folder does not
        exist yet. If we need to run slightly modified versions of the
        PyCascading script several times during testing for instance, this is
        very useful to store some results that can be reused without having to
        go through the part of the flow that generated them again.

        Arguments:
        identifier -- the unique identifier for this cache. This is used as
            part of the path where the temporary files are stored.
        refresh -- if True, we will regenerate the cache data as if it was
            the first time creating it
        """
        return _Cache(self, identifier, refresh)

    def run(self, num_reducers=50, config=None):
        """Start the Cascading job.

        We call this when we are done building the pipeline and explicitly want
        to start the flow process.
        """
        sources_used = set([])
        for tail in self.tails:
            sources_used.update(tail.context)
        # Remove unused sources from the source map
        source_map = {}
        for source in self.source_map.iterkeys():
            if source in sources_used:
                source_map[source] = self.source_map[source]
        tails = [t.get_assembly() for t in self.tails]
        import pycascading.pipe
        Util.run(num_reducers, pycascading.pipe.config, source_map, \
                 self.sink_map, tails)


class _Sink(Chainable):

    """A PyCascading sink that can be used as the tail in a pipeline.

    Used internally.
    """

    def __init__(self, taps, cascading_tap):
        Chainable.__init__(self)
        self.__cascading_tap = cascading_tap
        self.__taps = taps

    def _create_with_parent(self, parent):
        # We need to name every tail differently so that Cascading can assign
        # a tail map to all sinks.
        # TODO: revise this after I name every pipe part separately
        parent = parent | Pipe(name=random_pipe_name('sink'))
        self.__taps.sink_map[parent.get_assembly().getName()] = \
        self.__cascading_tap
        self.__taps.tails.append(parent)
        return None


class _Cache:

    """Act as a source or sink to store and retrieve temporary data."""

    def __init__(self, taps, hdfs_folder, refresh=False):
        tmp_folder = 'pycascading.cache/' + hdfs_folder
        self.__cache_folder = expand_path_with_home(tmp_folder)
        self.__hdfs_folder_exists = \
        self.hdfs_folder_exists(self.__cache_folder)
        self.__taps = taps
        self.__refresh = refresh

    def hdfs_folder_exists(self, folder):
        path = Path(folder)
        fs = path.getFileSystem(Configuration())
        try:
            status = fs.getFileStatus(path)
            # TODO: there could be problems if it exists but is a simple file
            return status.isDir()
        except:
            return False

    def __or__(self, pipe):
        if not self.__refresh and self.__hdfs_folder_exists:
            # We remove all sources that are replaced by this cache, otherwise
            # Cascading complains about unused source taps
            return self.__taps.meta_source(self.__cache_folder)
        else:
            # We split the data into storing and processing pipelines
            pipe | Pipe(random_pipe_name('cache')) | \
            self.__taps.binary_sink(self.__cache_folder)
            return pipe | Pipe(random_pipe_name('no_cache'))

########NEW FILE########
