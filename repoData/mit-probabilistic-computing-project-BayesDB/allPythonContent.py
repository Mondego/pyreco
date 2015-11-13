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
__FILENAME__ = bql
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

from bayesdb.client import Client
from cmd2 import Cmd
import sys

class BayesDBApp(Cmd):
  """Provides "interactive mode" features."""
  Cmd.redirector = '>>>'

  def __init__(self, client):
    self.client = client
    self.prompt = 'bql> '
    Cmd.__init__(self, 'tab')


  def do_show(self, line):
    self.client('show ' + str(line))

  def do_list(self, line):
    self.client('list ' + str(line))

  def do_analyze(self, line):
    self.client('analyze ' + str(line))

  def do_execute(self, line):
    self.client('execute ' + str(line))

  def do_drop(self, line):
    self.client('drop ' + str(line))

  def do_initialize(self, line):
    self.client('initialize ' + str(line))

  def do_create(self, line):
    self.client('create ' + str(line))

  def do_infer(self, line):
    self.client('infer ' + str(line))

  def do_select(self, line):
    self.client('select ' + str(line))

  def do_simulate(self, line):
    self.client('simulate ' + str(line))

  def do_save(self, line):
    self.client('save ' + str(line))
    
  def do_load(self, line):
    self.client('load ' + str(line))

  def do_estimate(self, line):
    self.client('estimate ' + str(line))

  def do_update(self, line):
    self.client('update ' + str(line))

  def do_help(self, line):
    self.client('help ' + str(line))
    
  def default(self, line):
    self.client(str(line))

def run_command_line():
  # Get command line arguments to specify hostname and port
  hostname = None
  port = None
  if len(sys.argv) > 1:
    # Treat the first argument as hostname[:port]
    input = sys.argv[1].split(':')
    hostname = input[0]
    if len(input) == 1:
      client = Client(hostname)
      print "Using hostname %s." % hostname
    if len(input) == 2:
      port = int(input[1])
      client = Client(hostname, port)
      print "Using hostname %s, port %d" % (hostname, port)
    elif len(input) > 2:
      print "Run with 'python bql [hostname[:port]]'"
  else:
    client = Client()

  print """Welcome to BayesDB. You may enter BQL commands directly into this prompt. Type 'help' for help, and 'quit' to quit."""
  app = BayesDBApp(client)
  app.cmdloop()

if __name__ == "__main__":
  run_command_line()

########NEW FILE########
__FILENAME__ = bql_grammar
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

from pyparsing import *
## uses the module pyparsing. This document provides a very good explanation of pyparsing: 
## http://www.nmt.edu/tcc/help/pubs/pyparsing/pyparsing.pdf

## Matches any white space and stores it as a single space
single_white = White().setParseAction(replaceWith(' '))

## basic keywords
and_keyword = CaselessKeyword("and")
from_keyword = CaselessKeyword("from")
for_keyword = CaselessKeyword("for")
into_keyword = CaselessKeyword("into")
of_keyword = CaselessKeyword("of")
with_keyword = CaselessKeyword("with")
help_keyword = CaselessKeyword("help").setResultsName("statement_id")
quit_keyword = CaselessKeyword("quit").setResultsName("statement_id")
to_keyword = CaselessKeyword('to')
## Many basic keywords will never be used alone
## creating them separately like this allows for simpler whitespace and case flexibility
create_keyword = CaselessKeyword("create")
execute_keyword = CaselessKeyword("execute")
file_keyword = CaselessKeyword("file")
update_keyword = CaselessKeyword("update")
schema_keyword = CaselessKeyword("schema")
set_keyword = CaselessKeyword("set")
categorical_keyword = CaselessKeyword("categorical")
numerical_keyword = CaselessKeyword("numerical")
ignore_keyword = CaselessKeyword("ignore")
key_keyword = CaselessKeyword("key")
initialize_keyword = CaselessKeyword("initialize").setResultsName("statement_id")
analyze_keyword = CaselessKeyword("analyze").setResultsName("statement_id")
index_keyword = CaselessKeyword("index")
save_keyword = CaselessKeyword("save")
load_keyword = CaselessKeyword("load")
drop_keyword = CaselessKeyword("drop")
show_keyword = CaselessKeyword("show")
select_keyword = CaselessKeyword("select")
infer_keyword = CaselessKeyword("infer")
simulate_keyword = CaselessKeyword("simulate")
estimate_keyword = CaselessKeyword("estimate")
pairwise_keyword = CaselessKeyword("pairwise")
where_keyword = CaselessKeyword("where")
order_keyword = CaselessKeyword("order")
by_keyword = CaselessKeyword("by")
limit_keyword = CaselessKeyword("limit")
confidence_keyword = CaselessKeyword("confidence")
times_keyword = CaselessKeyword("times")
dependence_keyword = CaselessKeyword("dependence")
probability_keyword = CaselessKeyword("probability")
correlation_keyword = CaselessKeyword("correlation")
mutual_keyword = CaselessKeyword("mutual")
information_keyword = CaselessKeyword("information")
typicality_keyword = CaselessKeyword("typicality")
as_keyword = CaselessKeyword("as")
show_keyword = CaselessKeyword("show")
similarity_keyword = CaselessKeyword("similarity")
respect_keyword = CaselessKeyword("respect")
predictive_keyword = CaselessKeyword("predictive")
group_keyword = CaselessKeyword("group")
diagnostics_keyword = CaselessKeyword("diagnostics")
hist_keyword = CaselessKeyword("hist").setResultsName("hist")
connected_keyword = CaselessKeyword("connected")
components_keyword = CaselessKeyword("components")
threshold_keyword = CaselessKeyword("threshold")
row_keyword = CaselessKeyword("row")
key_keyword = CaselessKeyword("key")
in_keyword = CaselessKeyword("in")
## Single and plural keywords
single_model_keyword = CaselessKeyword("model")
multiple_models_keyword = CaselessKeyword("models")
single_iteration_keyword = CaselessKeyword("iteration")
multiple_iterations_keyword = CaselessKeyword("iterations")
single_sample_keyword = CaselessKeyword("sample")
multiple_samples_keyword = CaselessKeyword("samples")
single_column_keyword = CaselessKeyword("column")
multiple_columns_keyword = CaselessKeyword("columns")
single_list_keyword = CaselessKeyword("list")
multiple_lists_keyword = CaselessKeyword("lists")
single_btable_keyword = CaselessKeyword("btable")
multiple_btable_keyword = CaselessKeyword("btables")
single_second_keyword = CaselessKeyword("second")
multiple_seconds_keyword = CaselessKeyword("seconds")
## Plural agnostic syntax, setParseAction makes it all display the singular
model_keyword = single_model_keyword | multiple_models_keyword
model_keyword.setParseAction(replaceWith("model"))
iteration_keyword = single_iteration_keyword | multiple_iterations_keyword
iteration_keyword.setParseAction(replaceWith("iteration"))
sample_keyword = single_sample_keyword | multiple_samples_keyword
sample_keyword.setParseAction(replaceWith("sample"))
column_keyword = single_column_keyword | multiple_columns_keyword
column_keyword.setParseAction(replaceWith("column"))
list_keyword = single_list_keyword | multiple_lists_keyword
list_keyword.setParseAction(replaceWith("list"))
btable_keyword = single_btable_keyword | multiple_btable_keyword
btable_keyword.setParseAction(replaceWith("btable"))
second_keyword = single_second_keyword | multiple_seconds_keyword
second_keyword.setParseAction(replaceWith("second"))

## Composite keywords: Inseparable elements that can have whitespace
## Using single_white and Combine to make them one string
execute_file_keyword = Combine(execute_keyword + single_white + file_keyword).setResultsName("statement_id")
create_btable_keyword = Combine(create_keyword + single_white + btable_keyword).setResultsName("statement_id")
update_schema_for_keyword = Combine(update_keyword + single_white + 
                                    schema_keyword + single_white + for_keyword).setResultsName("statement_id")
models_for_keyword = Combine(model_keyword + single_white + for_keyword)
model_index_keyword = Combine(model_keyword + single_white + index_keyword)
load_model_keyword = Combine(load_keyword + single_white + model_keyword).setResultsName("statement_id")
save_model_keyword = Combine(save_keyword + single_white + model_keyword).setResultsName("statement_id")
save_to_keyword = Combine(save_keyword + single_white + to_keyword).setResultsName("statement_id")
list_btables_keyword = Combine(list_keyword + single_white + btable_keyword).setResultsName("statement_id")
drop_btable_keyword = Combine(drop_keyword + single_white + btable_keyword).setResultsName("statement_id")
drop_model_keyword = Combine(drop_keyword + single_white + model_keyword).setResultsName("statement_id")
show_schema_for_keyword = Combine(show_keyword + single_white + schema_keyword + 
                                  single_white + for_keyword).setResultsName("statement_id")
show_models_for_keyword = Combine(show_keyword + single_white + model_keyword + 
                                  single_white + for_keyword).setResultsName("statement_id")
show_diagnostics_for_keyword = Combine(show_keyword + single_white + diagnostics_keyword + 
                                       single_white + for_keyword).setResultsName("statement_id")
show_column_lists_for_keyword = Combine(show_keyword + single_white + column_keyword + 
                                        single_white + list_keyword + 
                                        single_white + for_keyword).setResultsName("statement_id")
show_columns_for_keyword = Combine(show_keyword + single_white + column_keyword + 
                                   single_white + for_keyword).setResultsName("statement_id")
show_row_lists_for_keyword = Combine(show_keyword + single_white + row_keyword + 
                                 single_white + list_keyword + 
                                 single_white + for_keyword).setResultsName("statement_id")
estimate_pairwise_keyword = Combine(estimate_keyword + single_white + 
                                    pairwise_keyword).setResultsName("statement_id")
estimate_pairwise_row_keyword = Combine(estimate_keyword + single_white + pairwise_keyword + 
                                        single_white + row_keyword).setResultsName("statement_id")
row_similarity_keyword = Combine(row_keyword + single_white + similarity_keyword)
with_confidence_keyword = Combine(with_keyword + single_white + confidence_keyword)
order_by_keyword = Combine(order_keyword + single_white + by_keyword)
dependence_probability_keyword = Combine(dependence_keyword + single_white + probability_keyword)
mutual_information_keyword = Combine(mutual_keyword + single_white + information_keyword)
estimate_columns_from_keyword = Combine(estimate_keyword + single_white + column_keyword + 
                                        single_white + from_keyword).setResultsName("statement_id")
estimate_columns_keyword = Combine(estimate_keyword + single_white + column_keyword).setResultsName("statement_id")
column_lists_keyword = Combine(column_keyword + single_white + list_keyword)
similarity_to_keyword = Combine(similarity_keyword + single_white + to_keyword).setResultsName("statement_id")
with_respect_to_keyword = Combine(with_keyword + single_white + respect_keyword + single_white + to_keyword)
probability_of_keyword = Combine(probability_keyword + single_white + of_keyword)
typicality_of_keyword = Combine(typicality_keyword + single_white + of_keyword)
predictive_probability_of_keyword = Combine(predictive_keyword + single_white + probability_keyword + single_white + of_keyword)
save_connected_components_with_threshold_keyword = Combine(save_keyword + single_white + 
                                                           connected_keyword + single_white + 
                                                           components_keyword + single_white + 
                                                           with_keyword + single_white + 
                                                           threshold_keyword)
save_connected_components_keyword = save_connected_components_with_threshold_keyword
key_in_keyword = Combine(key_keyword + single_white + in_keyword)

## Values/Literals
sub_query = QuotedString("(",endQuoteChar=")").setResultsName('sub_query')
float_number = Regex(r'[-+]?[0-9]*\.?[0-9]+') | sub_query#TODO setParseAction to float/int
int_number = Word(nums) | sub_query
operation_literal = oneOf("<= >= = < >")
equal_literal = Literal("=")
semicolon_literal = Literal(";")
comma_literal = Literal(",")
hyphen_literal = Literal("-")
all_column_literal = Literal('*')
identifier = (Word(alphas + '/', alphanums + "_./").setParseAction(downcaseTokens)) | sub_query
btable = identifier.setResultsName("btable") | sub_query
# single and double quotes inside value must be escaped. 
value = (QuotedString('"', escChar='\\') | 
         QuotedString("'", escChar='\\') | 
         Word(printables)| 
         float_number | 
         sub_query)
filename = (QuotedString('"', escChar='\\') | 
            QuotedString("'", escChar='\\') | 
            Word(alphanums + "!\"/#$%&'()*+,-.:;<=>?@[\]^_`{|}~")).setResultsName("filename")
data_type_literal = categorical_keyword | numerical_keyword | ignore_keyword | key_keyword

###################################################################################
# ------------------------------------ Functions -------------------------------- #
###################################################################################

# ------------------------------- Management statements ------------------------- #

# CREATE BTABLE <btable> FROM <filename.csv>
create_btable_function = create_btable_keyword + btable + Suppress(from_keyword) + filename

# UPDATE SCHEMA FOR <btable> SET <col1>=<type1>[,<col2>=<type2>...]
type_clause = Group(ZeroOrMore(Group(identifier + Suppress(equal_literal) + data_type_literal) + 
                               Suppress(comma_literal)) + 
                    Group(identifier + Suppress(equal_literal) + data_type_literal)).setResultsName("type_clause")
update_schema_for_function = (update_schema_for_keyword + 
                              btable + 
                              Suppress(set_keyword) + 
                              type_clause)
# EXECUTE FILE <filename.bql>
execute_file_function = execute_file_keyword + filename

# INITIALIZE <num_models> MODELS FOR <btable>
initialize_function = (initialize_keyword + int_number.setResultsName("num_models") + 
                       Suppress(models_for_keyword) + btable)

# ANALYZE <btable> [MODEL[S] <model_index>-<model_index>] FOR (<num_iterations> ITERATIONS | <seconds> SECONDS)
def list_from_index_clause(toks):
    print toks
    ## takes index tokens separated by '-' for range and ',' for individual and returns a list of unique indexes
    index_list = []
    for token in toks[0]:
        if type(token)== str:
            index_list.append(int(token))
        elif len(token) == 2:
            index_list += range(int(token[0]), int(token[1])+1)
        #TODO else throw exception
        index_list.sort()
    return [list(set(index_list))]

# TODO separate out model_keyword for generic use
model_index_clause = (model_keyword + 
                      Group((Group(int_number + Suppress(hyphen_literal) + int_number) | int_number) + 
                            ZeroOrMore(Suppress(comma_literal) + 
                                       (Group(int_number + Suppress(hyphen_literal) + int_number) |
                                        int_number)))
                      .setParseAction(list_from_index_clause)
                      .setResultsName('index_list')).setResultsName('index_clause')
analyze_function = (analyze_keyword + btable + 
                    Optional(model_index_clause) + 
                    Suppress(for_keyword) + 
                    ((int_number.setResultsName('num_iterations') + iteration_keyword) | 
                     (int_number.setResultsName('num_seconds') + second_keyword)))
                    
# LIST BTABLES
list_btables_function = list_btables_keyword

show_for_btable_statement = ((show_schema_for_keyword | 
                              show_models_for_keyword | 
                              show_diagnostics_for_keyword | 
                              show_column_lists_for_keyword |  
                              show_columns_for_keyword | 
                              show_row_lists_for_keyword) + 
                             btable)

# LOAD MODELS <filename.pkl.gz> INTO <btable>
load_model_function = load_model_keyword + filename + Suppress(into_keyword) + btable

# SAVE MODELS FROM <btable> TO <filename.pkl.gz>
save_model_from_function = save_model_keyword + Suppress(from_keyword) + btable + Suppress(to_keyword) + filename

# DROP BTABLE <btable>
drop_btable_function = drop_btable_keyword + btable

# DROP MODEL[S] [<model_index>-<model_index>] FROM <btable>
drop_model_function = drop_keyword.setParseAction(replaceWith("drop model")).setResultsName("statement_id") + model_index_clause + Suppress(from_keyword) + btable

help_function = help_keyword
quit_function = quit_keyword

# ------------------------------ Helper Clauses --------------------------- #

# Rows can be identified either by an integer or <column> = <value> where value is unique for the given column
row_clause = (int_number.setResultsName("row_id") | 
              (identifier.setResultsName("column") + 
               Suppress(equal_literal) + 
               value.setResultsName("column_value")))

column_list_clause = Group((identifier | all_column_literal) + 
                           ZeroOrMore(Suppress(comma_literal) + 
                                      (identifier | all_column_literal))).setResultsName("column_list")

# SAVE TO <file>
save_to_clause = save_to_keyword + filename#todo names

# WITH CONFIDENCE <confidence>
with_confidence_clause = with_confidence_keyword + float_number.setResultsName("confidence")#todo names

management_queries = (create_btable_function | 
                      update_schema_for_function | 
                      execute_file_function | 
                      initialize_function | 
                      analyze_function | 
                      list_btables_function | 
                      show_for_btable_statement | 
                      load_model_function | 
                      save_model_from_function | 
                      drop_btable_function | 
                      drop_model_function | 
                      help_function | 
                      quit_function)

# -------------------------------- Functions ------------------------------ #

# SIMILARITY TO <row> [WITH RESPECT TO <column>]
similarity_to_function = (Group(similarity_to_keyword.setResultsName('function_id') + 
                                row_clause + 
                                Optional(with_respect_to_keyword + column_list_clause)
                                .setResultsName('with_respect_to'))
                          .setResultsName("function")) # todo more names less indexes

# TYPICALITY
typicality_function = Group(typicality_keyword.setResultsName('function_id')).setResultsName('function')

typicality_of_function = Group(typicality_of_keyword.setResultsName("function_id") + 
                                           identifier.setResultsName("column")).setResultsName("function")

# Functions of two columns for use in dependence probability, mutual information, correlation
functions_of_two_columns_subclause = ((Suppress(with_keyword) + 
                                       identifier.setResultsName("with_column")) | 
                                      (Suppress(of_keyword) + 
                                       identifier.setResultsName("of_column") + 
                                       Suppress(with_keyword) + 
                                       identifier.setResultsName("with_column")))

# DEPENDENCE PROBABILITY (WITH <column> | OF <column1> WITH <column2>)
dependence_probability_function = Group(dependence_probability_keyword.setResultsName('function_id') + 
                                        functions_of_two_columns_subclause).setResultsName("function")

# MUTUAL INFORMATION [OF <column1> WITH <column2>]
mutual_information_function = Group(mutual_information_keyword.setResultsName('function_id') + 
                                    functions_of_two_columns_subclause).setResultsName("function")

# CORRELATION [OF <column1> WITH <column2>]
correlation_function = Group(correlation_keyword.setResultsName('function_id') + 
                             functions_of_two_columns_subclause).setResultsName("function")


# PROBABILITY OF <column>=<value>
probability_of_function = Group((probability_of_keyword.setResultsName("function_id") + 
                                 identifier.setResultsName("column") + 
                                 Suppress(equal_literal) + 
                                 value.setResultsName("value"))).setResultsName('function')

# PREDICTIVE PROBABILITY OF <column>
predictive_probability_of_function = Group(predictive_probability_of_keyword.setResultsName("function_id") + 
                                           identifier.setResultsName("column")).setResultsName("function")

# KEY IN <row_list>
key_in_rowlist_clause = Group(key_in_keyword.setResultsName("function_id") + identifier.setResultsName("row_list")).setResultsName('function')

non_aggregate_function = similarity_to_function | typicality_function | predictive_probability_of_function | Group(identifier.setResultsName('column'))

# -------------------------------- other clauses --------------------------- #

# ORDER BY <column|non-aggregate-function>[<column|function>...]
order_by_clause = Group(order_by_keyword + Group((non_aggregate_function) + ZeroOrMore(Suppress(comma_literal) + (non_aggregate_function))).setResultsName("order_by_set")).setResultsName('order_by')

# WHERE <whereclause>
single_where_condition = Group(((non_aggregate_function.setResultsName('function') + 
                                 operation_literal.setResultsName('operation') + 
                                 value.setResultsName('value')) | key_in_rowlist_clause) + 
                               Optional(with_confidence_clause))

where_clause = (where_keyword.setResultsName('where_keyword') + 
                Group(single_where_condition + 
                      ZeroOrMore(Suppress(and_keyword) + single_where_condition))
                .setResultsName("where_conditions"))

save_connected_components_clause = Group(save_connected_components_keyword
                                         .setResultsName("save_connected_components") + 
                                         float_number.setResultsName("threshold") + 
                                         ((as_keyword + 
                                           identifier.setResultsName('as_label')) | 
                                          (into_keyword + 
                                           identifier.setResultsName('into_label')))).setResultsName('connected_components_clause')

row_list_clause = Group(int_number + 
                           ZeroOrMore(Suppress(comma_literal) + 
                                      int_number)).setResultsName("row_list")

# ----------------------------- Master Query Syntax ---------------------------------------- #

query_id = (select_keyword | 
            infer_keyword | 
            simulate_keyword | 
            estimate_pairwise_keyword |
            estimate_keyword).setResultsName('query_id')

function_in_query = (predictive_probability_of_function | 
                     probability_of_function | 
                     typicality_of_function | 
                     typicality_function | 
                     similarity_to_function |
                     dependence_probability_function | 
                     mutual_information_function | 
                     correlation_function | 
                     row_similarity_keyword |
                     similarity_keyword |
                     column_keyword |
                     Group(column_list_clause.setResultsName("columns"))).setResultsName("function")

functions_clause = Group(function_in_query + 
                         ZeroOrMore(Suppress(comma_literal) + 
                                    function_in_query)).setResultsName('functions')

query = (query_id + 
         Optional(hist_keyword).setResultsName("hist") +
         functions_clause + 
         Suppress(from_keyword) + 
         btable + 
         Optional(where_clause) + 
         Each(Optional(order_by_clause) + 
              Optional(with_confidence_clause) + 
              Optional(Suppress(with_keyword) + int_number.setResultsName('samples') + Suppress(sample_keyword)) + 
              Optional(Suppress(limit_keyword) + int_number.setResultsName("limit")) + 
              Optional(for_keyword + column_list_clause.setResultsName('columns')) +
              Optional(for_keyword + row_list_clause.setResultsName('rows')) + 
              Optional(Suppress(save_to_keyword) + filename) + 
              Optional(save_connected_components_clause) + 
              Optional(Suppress(times_keyword) + int_number.setResultsName("times")) + 
              Optional(Suppress(as_keyword) + identifier.setResultsName("as_column_list"))))

########NEW FILE########
__FILENAME__ = client
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import inspect
import pickle
import gzip
import prettytable
import re
import os
import time
import ast

import utils
import data_utils
import plotting_utils
import api_utils
from parser import Parser
from engine import Engine

class Client(object):
    def __init__(self, crosscat_host=None, crosscat_port=8007, crosscat_engine_type='multiprocessing',
                 bayesdb_host=None, bayesdb_port=8008, seed=None):
        """
        Create a client object. The client creates a parser, that is uses to parse all commands,
        and an engine, which is uses to execute all commands. The engine can be remote or local.
        If local, the engine will be created.
        """
        self.parser = Parser()
        if bayesdb_host is None or bayesdb_host=='localhost':
            self.online = False
            self.engine = Engine(crosscat_host, crosscat_port, crosscat_engine_type, seed)
        else:
            self.online = True
            self.hostname = bayesdb_host
            self.port = bayesdb_port
            self.URI = 'http://' + self.hostname + ':%d' % self.port

    def call_bayesdb_engine(self, method_name, args_dict, debug=False):
        """
        Helper function used to call the BayesDB engine, whether it is remote or local.
        Accepts method name and arguments for that method as input.
        """
        if self.online:
            out, id = aqupi_utils.call(method_name, args_dict, self.URI)
        else:
            method = getattr(self.engine, method_name)
            if debug:
                out = method(**args_dict)
            else:
                # when not in debug mode, catch all BayesDBErrors
                try:
                    out = method(**args_dict)
                except utils.BayesDBError as e:
                    out = dict(message=str(e), error=True)
        return out

    def __call__(self, call_input, pretty=True, timing=False, wait=False, plots=None, yes=False, debug=False, pandas_df=None, pandas_output=True):
        """Wrapper around execute."""
        return self.execute(call_input, pretty, timing, wait, plots, yes, debug, pandas_df, pandas_output)

    def execute(self, call_input, pretty=True, timing=False, wait=False, plots=None, yes=False, debug=False, pandas_df=None, pandas_output=True):
        """
        Execute a chunk of BQL. This method breaks a large chunk of BQL (like a file)
        consisting of possibly many BQL statements, breaks them up into individual statements,
        then passes each individual line to self.execute_statement() as a string.
        
        param call_input: may be either a file object, or a string.
        If the input is a file, then we load the inputs of the file, and use those as a string.

        See self.execute_statement() for an explanation of arguments.
        """
        if type(call_input) == file:
            bql_string = call_input.read()
            path = os.path.abspath(call_input.name)
            self.parser.set_root_dir(os.path.dirname(path))
        elif type(call_input) == str:
            bql_string = call_input
        else:
            print "Invalid input type: expected file or string."

        return_list = []
            
        lines = self.parser.split_lines(bql_string)
        # Iterate through lines with while loop so we can append within loop.
        while len(lines) > 0:
            line = lines.pop(0)
            if type(call_input) == file:
                print '> %s' % line
            if wait:
                user_input = raw_input()
                if len(user_input) > 0 and (user_input[0] == 'q' or user_input[0] == 's'):
                    continue
            result = self.execute_statement(line, pretty=pretty, timing=timing, plots=plots, yes=yes, debug=debug, pandas_df=pandas_df, pandas_output=pandas_output)

            if type(result) == dict and 'message' in result and result['message'] == 'execute_file':
                ## special case for one command: execute_file
                new_lines = self.parser.split_lines(result['bql_string'])
                lines += new_lines
            if type(call_input) == file:
                print

            return_list.append(result)

        self.parser.reset_root_dir()

        if not pretty:
            return return_list

    def execute_statement(self, bql_statement_string, pretty=True, timing=False, plots=None, yes=False, debug=False, pandas_df=None, pandas_output=True):
        """
        Accepts a SINGLE BQL STATEMENT as input, parses it, and executes it if it was parsed
        successfully.

        If pretty=True, then the command output will be pretty-printed as a string.
        If pretty=False, then the command output will be returned as a python object.

        timing=True prints out how long the command took to execute.

        For commands that have visual results, plots=True will cause those to be displayed
        by matplotlib as graphics rather than being pretty-printed as text.
        (Note that the graphics will also be saved if the user added SAVE TO <filename> to the BQL.)
        """
        if timing:
            start_time = time.time()

        parser_out = None
        if debug:
            parser_out = self.parser.parse_statement(bql_statement_string)
        else:
            try:
                parser_out = self.parser.parse_statement(bql_statement_string)
            except Exception as e:            
                raise utils.BayesDBParseError(str(e))
        if parser_out is None:
            print "Could not parse command. Try typing 'help' for a list of all commands."
            return
        elif not parser_out:
            return

        method_name, args_dict, client_dict = parser_out
        if client_dict is None:
            client_dict = {}
            
        ## Do stuff now that you know the user's command, but before passing it to engine.
        if method_name == 'execute_file':
            return dict(message='execute_file', bql_string=open(args_dict['filename'], 'r').read())
        elif (method_name == 'drop_btable') and (not yes):
            ## If dropping something, ask for confirmation.
            print "Are you sure you want to permanently delete this btable, and all associated models, without any way to get them back? Enter 'y' if yes."
            user_confirmation = raw_input()
            if 'y' != user_confirmation.strip():
                return dict(message="Operation canceled by user.")
        elif (method_name == 'drop_models') and (not yes):
            ## If dropping something, ask for confirmation.
            print "Are you sure you want to permanently delete model(s), without any way to get them back? Enter 'y' if yes."
            user_confirmation = raw_input()
            if 'y' != user_confirmation.strip():
                return dict(message="Operation canceled by user.")
        elif method_name == 'load_models':
            pklpath = client_dict['pkl_path']
            try:
                models = pickle.load(gzip.open(self.parser.get_absolute_path(pklpath), 'rb'))
            except IOError as e:
                if pklpath[-7:] != '.pkl.gz':
                    if pklpath[-4:] == '.pkl':
                        models = pickle.load(open(self.parser.get_absolute_path(pklpath), 'rb'))
                    else:
                        pklpath = pklpath + ".pkl.gz"
                        models = pickle.load(gzip.open(self.parser.get_absolute_path(pklpath), 'rb'))
                else:
                    raise utils.BayesDBError('Models file %s could not be found.' % pklpath)
            args_dict['models'] = models
        elif method_name == 'create_btable':
            if pandas_df is None:
                header, rows = data_utils.read_csv(client_dict['csv_path'])
            else:
                header, rows = data_utils.read_pandas_df(pandas_df)
            args_dict['header'] = header
            args_dict['raw_T_full'] = rows
        elif method_name in ['label_columns', 'update_metadata']:
            if client_dict['source'] == 'file':
                header, rows = data_utils.read_csv(client_dict['csv_path'])
                args_dict['mappings'] = {key: value for key, value in rows}

        ## Call engine.
        result = self.call_bayesdb_engine(method_name, args_dict, debug)

        ## If error occurred, exit now.
        if 'error' in result and result['error']:
            if pretty:
                print result['message']
                return result['message']
            else:
                return result

        ## Do stuff now that engine has given you output, but before printing the result.
        result = self.callback(method_name, args_dict, client_dict, result)
        
        assert type(result) != int
        
        if timing:
            end_time = time.time()
            print 'Elapsed time: %.2f seconds.' % (end_time - start_time)

        if plots is None:
            plots = 'DISPLAY' in os.environ.keys()

        if 'matrix' in result and (plots or client_dict['filename']):
            # Plot matrices
            plotting_utils.plot_matrix(result['matrix'], result['column_names'], result['title'], client_dict['filename'])
            if pretty:
                if 'column_lists' in result:
                    print self.pretty_print(dict(column_lists=result['column_lists']))
                return self.pretty_print(result)
            else:
                return result
        if ('plot' in client_dict and client_dict['plot']):
            if (plots or client_dict['filename']):
                # Plot generalized histograms or scatterplots
                plotting_utils.plot_general_histogram(result['columns'], result['data'], result['M_c'], client_dict['filename'], client_dict['scatter'], True) # pairwise always true
                return self.pretty_print(result)
            else:
                if 'message' not in result:
                    result['message'] = ""
                result['message'] = "Your query indicates that you would like to make a plot, but in order to do so, you must either enable plotting in a window or specify a filename to save to by appending 'SAVE TO <filename>' to this command.\n" + result['message']

        if pretty:
            pp = self.pretty_print(result)
            print pp
        
        if pandas_output and 'data' in result and 'columns' in result:
            result_pandas_df = data_utils.construct_pandas_df(result)
            return result_pandas_df
        else:
            if type(result) == dict and 'message' in result.keys():
                print result['message']
            return result

    def callback(self, method_name, args_dict, client_dict, result):
        """
        This method is meant to be called after receiving the result of a
        call to the BayesDB engine, and modifies the output before it is displayed
        to the user.
        """
        if method_name == 'save_models':
            samples_dict = result
            ## Here is where the models get saved.
            pkl_path = client_dict['pkl_path']
            if pkl_path[-7:] != '.pkl.gz':
                if pkl_path[-4:] == '.pkl':
                    pkl_path = pkl_path + ".gz"
                else:
                    pkl_path = pkl_path + ".pkl.gz"
            samples_file = gzip.GzipFile(pkl_path, 'w')
            pickle.dump(samples_dict, samples_file)
            return dict(message="Successfully saved the samples to %s" % client_dict['pkl_path'])

        else:
            return result
        
    def pretty_print(self, query_obj):
        """
        Return a pretty string representing the output object.
        """
        assert type(query_obj) == dict
        result = ""
        if type(query_obj) == dict and 'message' in query_obj:
            result += query_obj["message"] + "\n"
        if 'data' in query_obj and 'columns' in query_obj:
            """ Pretty-print data table """
            pt = prettytable.PrettyTable()
            pt.field_names = query_obj['columns']
            for row in query_obj['data']:
                pt.add_row(row)
            result += str(pt)
        elif 'list' in query_obj:
            """ Pretty-print lists """
            result += str(query_obj['list'])
        elif 'column_names' in query_obj:
            """ Pretty-print cctypes """
            colnames = query_obj['column_names']
            zmatrix = query_obj['matrix']
            pt = prettytable.PrettyTable(hrules=prettytable.ALL, vrules=prettytable.ALL, header=False)
            pt.add_row([''] + list(colnames))
            for row, colname in zip(zmatrix, list(colnames)):
                pt.add_row([colname] + list(row))
            result += str(pt)
        elif 'columns' in query_obj:
            """ Pretty-print column list."""
            pt = prettytable.PrettyTable()
            pt.field_names = ['column']
            for column in query_obj['columns']:
                pt.add_row([column])
            result += str(pt)
        elif 'row_lists' in query_obj:
            """ Pretty-print multiple row lists, which are just names and row sizes. """
            pt = prettytable.PrettyTable()
            pt.field_names = ('Row List Name', 'Row Count')
            
            def get_row_list_sorting_key(x):
                """ To be used as the key function in a sort. Puts cc_2 ahead of cc_10, e.g. """
                name, count = x
                if '_' not in name:
                    return name
                s = name.split('_')
                end = s[-1]
                start = '_'.join(s[:-1])
                if utils.is_int(end):
                    return (start, int(end))
                return name
                    
            for name, count in sorted(query_obj['row_lists'], key=get_row_list_sorting_key):
                pt.add_row((name, count))
            result += str(pt)
        elif 'column_lists' in query_obj:
            """ Pretty-print multiple column lists. """
            print
            clists = query_obj['column_lists']
            for name, clist in clists:
                print "%s:" % name
                pt = prettytable.PrettyTable()
                pt.field_names = clist
                print pt
        elif 'models' in query_obj:
            """ Pretty-print model info. """
            pt = prettytable.PrettyTable()
            pt.field_names = ('model_id', 'iterations')
            for (id, iterations) in query_obj['models']:
                pt.add_row((id, iterations))
            result += str(pt)

        if len(result) >= 1 and result[-1] == '\n':
            result = result[:-1]
        return result




########NEW FILE########
__FILENAME__ = data_utils
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
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
import pandas
import re
import numpy

import utils

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

def gen_ignore_metadata(column_data):
    return dict(
        modeltype="ignore",
        value_to_code=dict(),
        code_to_value=dict(),
        )

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
    ignore=gen_ignore_metadata,
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

def construct_pandas_df(query_obj):
    """
    Take a result from a BQL statement (dict with 'data' and 'columns')
    and constructs a pandas data frame.

    Currently this is only called if the user specifies pandas_output = True
    """
    if len(query_obj['data']) == 0:
        data = None
    else:
        data = query_obj['data']

    pandas_df = pandas.DataFrame(data = data, columns = query_obj['columns'])
    return pandas_df

def read_pandas_df(pandas_df):
    """
    Takes pandas data frame object and converts data
    into list-of-lists format
    """
    header = list(pandas_df.columns)
    rows = [map(str, row) for index, row in pandas_df.iterrows()]
    return header, rows

def read_csv(filename, has_header=True):
    with open(filename, 'rU') as fh:
        csv_reader = csv.reader(fh)
        header = None
        if has_header:
            header = csv_reader.next()
        rows = [[r.strip() for r in row] for row in csv_reader]
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
        try:
            return M_c['column_metadata'][cidx]['code_to_value'][str(value)]
        except KeyError:
            raise utils.BayesDBError("Error: value '%s' not in btable." % str(value))

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
            if (cctype == 'ignore' or cctype == 'key')
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

    if cctypes is None:
        cctypes = ['continuous'] * len(header)
        pass

    T_uncast_arr, cctypes, header = remove_ignore_cols(raw_T, cctypes, header) # remove ignore columns
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
    return gen_T_and_metadata(colnames, raw_T, max_rows, gen_seed, cctypes)

def gen_T_and_metadata(colnames, raw_T, max_rows=None, gen_seed=0,
                       cctypes=None):
    T = at_most_N_rows(raw_T, max_rows, gen_seed)
    T = convert_nans(T)
    if cctypes is None:
        cctypes = guess_column_types(T)
    M_c = gen_M_c_from_T(T, cctypes, colnames)
    T = map_to_T_with_M_c(numpy.array(T), M_c)
    M_r = gen_M_r_from_T(T)
    return T, M_r, M_c, cctypes

extract_view_count = lambda X_L: len(X_L['view_state'])
extract_cluster_count = lambda view_state_i: view_state_i['row_partition_model']['counts']
extract_cluster_counts = lambda X_L: map(extract_cluster_count, X_L['view_state'])
get_state_shape = lambda X_L: (extract_view_count(X_L), extract_cluster_counts(X_L))

########NEW FILE########
__FILENAME__ = engine
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import time
import inspect
import os
import json
import datetime
import re
import operator
import copy
import math
import ast
import sys
import random

import pylab
import numpy
import matplotlib.cm
from collections import defaultdict

import bayesdb.settings as S
from persistence_layer import PersistenceLayer
import api_utils
import data_utils
import utils
import pairwise
import functions
import select_utils
import estimate_columns_utils
import plotting_utils

class Engine(object):
  def __init__(self, crosscat_host=None, crosscat_port=8007, crosscat_engine_type='multiprocessing', seed=None, **kwargs):
    """ One optional argument that you may find yourself using frequently is seed.
    It defaults to random seed, but for testing/reproduceability purposes you may
    want a deterministic one. """
    
    self.persistence_layer = PersistenceLayer()

    if crosscat_host is None or crosscat_host == 'localhost':
      self.online = False
      
      # Only dependent on CrossCat when you actually instantiate Engine
      # (i.e., allow engine to be imported in order to examine the API, without CrossCat)
      from crosscat.CrossCatClient import get_CrossCatClient
      self.backend = get_CrossCatClient(crosscat_engine_type, seed=seed, **kwargs)
    else:
      self.online = True
      self.hostname = crosscat_host
      self.port = crosscat_port
      self.URI = 'http://' + self.hostname + ':%d' % self.port

  def call_backend(self, method_name, args_dict):
    """
    Helper function used to call the CrossCat backend, whether it is remote or local.
    Accept method name and arguments for that method as input.
    """
    if self.online:
      out, id = api_utils.call(method_name, args_dict, self.URI)
    else:
      method = getattr(self.backend, method_name)
      out = method(**args_dict)
    return out

  def drop_btable(self, tablename):
    """Delete table by tablename."""
    self.persistence_layer.drop_btable(tablename)
    return dict()

  def list_btables(self):
    """Return names of all btables."""
    return dict(columns=['btable'], data=[[name] for name in self.persistence_layer.list_btables()])

  def label_columns(self, tablename, mappings):
    """
    Add column labels to table in persistence layer, replacing
    labels without warning. Mappings is a dict of column names
    and their labels as given by the user.
    No length is enforced on labels - should we?
    """
    if not self.persistence_layer.check_if_table_exists(tablename):
      raise utils.BayesDBInvalidBtableError(tablename)

    # Get column names for table so labels don't get written for nonexistent columns.
    M_c_full = self.persistence_layer.get_metadata_full(tablename)['M_c_full']
    colnames_full = utils.get_all_column_names_in_original_order(M_c_full)

    labels_edited = {}
    # Only add labels or overwrite one-by-one.
    for colname, label in mappings.items():
      if colname in colnames_full:
        self.persistence_layer.add_column_label(tablename, colname, label)
        labels_edited[colname] = label
      else:
        raise utils.BayesDBColumnDoesNotExistError(colname, tablename)

    labels = self.persistence_layer.get_column_labels(tablename)
    ret = {'data': [[c, l] for c, l in labels_edited.items()], 'columns': ['column', 'label']}
    ret['message'] = "Updated column labels for %s." % (tablename)
    return ret

  def show_labels(self, tablename, columnstring):
    """
    Show column labels for the columns in columnstring
    """
    if not self.persistence_layer.check_if_table_exists(tablename):
      raise utils.BayesDBInvalidBtableError(tablename)

    labels = self.persistence_layer.get_column_labels(tablename)

    # Get colnames from columnstring
    if columnstring.strip() == '':
      colnames = labels.keys()
    else:
      column_lists = self.persistence_layer.get_column_lists(tablename)
      M_c = self.persistence_layer.get_metadata(tablename)['M_c']
      colnames = utils.column_string_splitter(columnstring, M_c, column_lists)
      colnames = [c.lower() for c in colnames]
      utils.check_for_duplicate_columns(colnames)

    ret = {'data': [[c, l] for c, l in labels.items() if c in colnames], 'columns': ['column', 'label']}
    ret['message'] = "Showing labels for %s." % (tablename)
    return ret

  def update_metadata(self, tablename, mappings):
    """
    Add user metadata to table in persistence layer, replacing
    values without warning. Mappings is a dict of key names
    and their values as given by the user.
    """
    if not self.persistence_layer.check_if_table_exists(tablename):
      raise utils.BayesDBInvalidBtableError(tablename)

    for key, value in mappings.items():
        self.persistence_layer.add_user_metadata(tablename, key, value)

    metadata = self.persistence_layer.get_user_metadata(tablename)
    ret = {'data': [[k, v] for k, v in metadata.items() if k in mappings.keys()], 'columns': ['key', 'value']}
    ret['message'] = "Updated user metadata for %s." % (tablename)
    return ret

  def show_metadata(self, tablename, keystring):
    """
    Get user metadata from persistence layer and show the values for the keys specified
    by the user. If no keystring is given, show all metadata key-value pairs.
    """
    if not self.persistence_layer.check_if_table_exists(tablename):
      raise utils.BayesDBInvalidBtableError(tablename)

    metadata = self.persistence_layer.get_user_metadata(tablename)
    if keystring.strip() == '':
      metadata_keys = metadata.keys()
    else:
      metadata_keys = [key.strip() for key in keystring.split(',')]

    ret = {'data': [[k, metadata[k]] for k in metadata_keys if k in metadata], 'columns': ['key', 'value']}
    ret['message'] = "Showing user metadata for %s." % (tablename)
    return ret

  def update_schema(self, tablename, mappings):
    """
    mappings is a dict of column name to 'continuous', 'multinomial',
    or 'ignore', or 'key'.
    Requires that models are already initialized.
    """
    if not self.persistence_layer.check_if_table_exists(tablename):
      raise utils.BayesDBInvalidBtableError(tablename)
    if self.persistence_layer.has_models(tablename):
      raise utils.BayesDBError("Error: btable %s already has models. The schema may not be updated after models have been initialized; please either create a new btable or drop the models from this one." % tablename)
    
    msg = self.persistence_layer.update_schema(tablename, mappings)
    ret = self.show_schema(tablename)
    ret['message'] = 'Updated schema.'
    return ret
    
  def create_btable(self, tablename, header, raw_T_full, cctypes_full=None):
    """Uplooad a csv table to the predictive db.
    cctypes must be a dictionary mapping column names
    to either 'ignore', 'continuous', or 'multinomial'. Not every
    column name must be present in the dictionary: default is continuous."""
    
    ## First, test if table with this name already exists, and fail if it does
    if self.persistence_layer.check_if_table_exists(tablename):
      raise utils.BayesDBError('Btable with name %s already exists.' % tablename)
      
    # variables with "_full" include ignored columns.
    colnames_full = [h.lower().strip() for h in header]
    raw_T_full = data_utils.convert_nans(raw_T_full)
    if cctypes_full is None:
      cctypes_full = data_utils.guess_column_types(raw_T_full)
    T_full, M_r_full, M_c_full, _ = data_utils.gen_T_and_metadata(colnames_full, raw_T_full, cctypes=cctypes_full)

    # variables without "_full" don't include ignored columns.
    raw_T, cctypes, colnames = data_utils.remove_ignore_cols(raw_T_full, cctypes_full, colnames_full)
    T, M_r, M_c, _ = data_utils.gen_T_and_metadata(colnames, raw_T, cctypes=cctypes)
      
    self.persistence_layer.create_btable(tablename, cctypes_full, T, M_r, M_c, T_full, M_r_full, M_c_full, raw_T_full)

    return dict(columns=colnames_full, data=[cctypes_full], message='Created btable %s. Inferred schema:' % tablename)

  def show_schema(self, tablename):
    if not self.persistence_layer.check_if_table_exists(tablename):
      raise utils.BayesDBInvalidBtableError(tablename)
    
    metadata = self.persistence_layer.get_metadata(tablename)
    colnames = utils.get_all_column_names_in_original_order(metadata['M_c'])
    cctypes = metadata['cctypes']
    return dict(columns=['column','datatype'], data=zip(colnames, cctypes))

  def save_models(self, tablename):    
    """Opposite of load models! Returns the models, including the contents, which
    the client then saves to disk (in a pickle file)."""
    if not self.persistence_layer.check_if_table_exists(tablename):
      raise utils.BayesDBInvalidBtableError(tablename)
    
    return self.persistence_layer.get_models(tablename)

  def load_models(self, tablename, models):
    """Load these models as if they are new models"""
    # Models are stored in the format: dict[model_id] = dict[X_L, X_D, iterations].
    # We just want to pass the values.

    # For backwards compatibility with v0.1, where models are stored in the format:
    # dict[X_L_list, X_D_list, M_c, T]
    if not self.persistence_layer.check_if_table_exists(tablename):
      raise utils.BayesDBInvalidBtableError(tablename)
    
    if 'X_L_list' in models:
      print """WARNING! The models you are currently importing are stored in an old format
         (from version 0.1); it is deprecated and may not be supported in future releases.
         Please use "SAVE MODELS" to create an updated copy of your models."""
      
      old_models = models
      models = dict()
      for id, (X_L, X_D) in enumerate(zip(old_models['X_L_list'], old_models['X_D_list'])):
        models[id] = dict(X_L=X_L, X_D=X_D, iterations=500)
      
    result = self.persistence_layer.add_models(tablename, models.values())
    return self.show_models(tablename)

  def drop_models(self, tablename, model_indices=None):
    """Drop the specified models. If model_ids is None or all, drop all models."""
    if not self.persistence_layer.check_if_table_exists(tablename):
      raise utils.BayesDBInvalidBtableError(tablename)
    
    self.persistence_layer.drop_models(tablename, model_indices)
    return self.show_models(tablename)
    
  def initialize_models(self, tablename, n_models, model_config=None):
    """
    Initialize n_models models.

    By default, model_config specifies to use the CrossCat model. You may pass 'naive bayes'
    or 'crp mixture' to use those specific models instead. Alternatively, you can pass a custom
    dictionary for model_config, as long as it contains a kernel_list, initializaiton, and
    row_initialization.
    """
    if not self.persistence_layer.check_if_table_exists(tablename):
      raise utils.BayesDBInvalidBtableError(tablename)

    # Get t, m_c, and m_r, and tableid
    M_c, M_r, T = self.persistence_layer.get_metadata_and_table(tablename)

    # Set model configuration parameters.
    if type(model_config) == str and model_config.lower() == 'naive bayes':
      model_config = dict(kernel_list=['column_hyperparameters'],
                          initialization='together',
                          row_initialization='together')
    elif type(model_config) == str and model_config.lower() == 'crp mixture':
      model_config = dict(kernel_list=['column_hyperparameters',
                                       'row_partition_hyperparameters',
                                       'row_partition_assignments'],
                          initialization='together',
                          row_initialization='from_the_prior')
    elif type(model_config) != dict or ('kernel_list' not in model_config) or ('initialization' not in model_config) or ('row_initialization' not in model_config):
      # default model_config: crosscat
      model_config = dict(kernel_list=(), # uses default
                          initialization='from_the_prior',
                          row_initialization='from_the_prior')
    else:
      raise utils.BayesDBError("Invalid model config")

    # Make sure the model config matches existing model config, if there are other models.
    existing_model_config = self.persistence_layer.get_model_config(tablename)
    if existing_model_config is not None and existing_model_config != model_config:
      raise utils.BayesDBError("Error: model config must match existing model config: %s" % str(existing_model_config))
      
    # Call initialize on backend
    X_L_list, X_D_list = self.call_backend('initialize',
                                           dict(M_c=M_c, M_r=M_r, T=T, n_chains=n_models,
                                                initialization=model_config['initialization'],
                                                row_initialization=model_config['row_initialization']))

    # If n_models is 1, initialize returns X_L and X_D instead of X_L_list and X_D_list
    if n_models == 1:
      X_L_list = [X_L_list]
      X_D_list = [X_D_list]
    
    model_list = list()    
    for X_L, X_D in zip(X_L_list, X_D_list):
      model_list.append(dict(X_L=X_L, X_D=X_D, iterations=0,
                             column_crp_alpha=[], logscore=[], num_views=[],
                             model_config=model_config))

    # Insert results into persistence layer
    self.persistence_layer.add_models(tablename, model_list)
    return self.show_models(tablename)

  def show_models(self, tablename):
    """Return the current models and their iteration counts."""
    if not self.persistence_layer.check_if_table_exists(tablename):
      raise utils.BayesDBInvalidBtableError(tablename)
    
    models = self.persistence_layer.get_models(tablename)
    modelid_iteration_info = list()
    for modelid, model in sorted(models.items(), key=lambda t:t[0]):
      modelid_iteration_info.append((modelid, model['iterations']))
    if len(models) == 0:
      return dict(message="No models for btable %s. Create some with the INITIALIZE MODELS command." % tablename)
    else:
      return dict(models=modelid_iteration_info)

  def show_diagnostics(self, tablename):
    """
    Display diagnostic information for all your models.
    TODO: generate plots of num_views, column_crp_alpha, logscore, and f_z stuff
    """
    if not self.persistence_layer.check_if_table_exists(tablename):
      raise utils.BayesDBInvalidBtableError(tablename)
    
    models = self.persistence_layer.get_models(tablename)    
    data = list()
    for modelid, model in sorted(models.items(), key=lambda t:t[0]):
      data.append((modelid, model['iterations'], str(model['model_config'])))
    if len(models) == 0:
      return dict(message="No models for btable %s. Create some with the INITIALIZE MODELS command." % tablename)
    else:
      return dict(columns=['model_id', 'iterations', 'model_config'], data=data)
    

  def analyze(self, tablename, model_indices=None, iterations=None, seconds=None, ct_kernel=0):
    """
    Run analyze for the selected table. model_indices may be 'all' or None to indicate all models.

    Runs for a maximum of iterations 
    
    Previously: this command ran in the same thread as this engine.
    Now: runs each model in its own thread, and does 10 seconds of inference at a time,
    by default. Each thread also has its own crosscat engine instance!
    """
    if not self.persistence_layer.check_if_table_exists(tablename):
      raise utils.BayesDBInvalidBtableError(tablename)
    if not self.persistence_layer.has_models(tablename):
      raise utils.BayesDBNoModelsError(tablename)
    
    if iterations is None:
      iterations = 1000
    
    M_c, M_r, T = self.persistence_layer.get_metadata_and_table(tablename)
    
    max_model_id = self.persistence_layer.get_max_model_id(tablename)
    if max_model_id == -1:
      return dict(message="You must INITIALIZE MODELS before using ANALYZE.")
    models = self.persistence_layer.get_models(tablename)

    if model_indices is None or (str(model_indices).upper() == 'ALL'):
      modelids = sorted(models.keys())
    else:
      assert type(model_indices) == list
      modelids = model_indices

    X_L_list = [models[i]['X_L'] for i in modelids]
    X_D_list = [models[i]['X_D'] for i in modelids]

    first_model = models[modelids[0]]
    if 'model_config' in first_model and 'kernel_list' in first_model['model_config']:
      kernel_list = first_model['model_config']['kernel_list']
    else:
      kernel_list = () # default kernel list

    analyze_args = dict(M_c=M_c, T=T, X_L=X_L_list, X_D=X_D_list, do_diagnostics=True,
                        kernel_list=kernel_list)
    if ct_kernel != 0:
      analyze_args['CT_KERNEL'] = ct_kernel
    
    analyze_args['n_steps'] = iterations
    if seconds is not None:
      analyze_args['max_time'] = seconds

    X_L_list_prime, X_D_list_prime, diagnostics_dict = self.call_backend('analyze', analyze_args)
    iterations = len(diagnostics_dict['logscore'])
    self.persistence_layer.update_models(tablename, modelids, X_L_list_prime, X_D_list_prime, diagnostics_dict)
    
    ret = self.show_models(tablename)
    ret['message'] = 'Analyze complete.'
    return ret

  def infer(self, tablename, columnstring, newtablename, confidence, whereclause, limit, numsamples, order_by=False, plot=False, modelids=None, summarize=False):
    """
    Impute missing values.
    Sample INFER: INFER columnstring FROM tablename WHERE whereclause WITH confidence LIMIT limit;
    Sample INFER INTO: INFER columnstring FROM tablename WHERE whereclause WITH confidence INTO newtablename LIMIT limit;
    Argument newtablename == null/emptystring if we don't want to do INTO
    """
    if not self.persistence_layer.check_if_table_exists(tablename):
      raise utils.BayesDBInvalidBtableError(tablename)
    if not self.persistence_layer.has_models(tablename):
      raise utils.BayesDBNoModelsError(tablename)      
    
    if numsamples is None:
      numsamples=50
      
    return self.select(tablename, columnstring, whereclause, limit, order_by,
                       impute_confidence=confidence, num_impute_samples=numsamples, plot=plot, modelids=modelids, summarize=summarize)
    
  def select(self, tablename, columnstring, whereclause, limit, order_by, impute_confidence=None, num_impute_samples=None, plot=False, modelids=None, summarize=False):
    """
    BQL's version of the SQL SELECT query.
    
    First, reads codes from T and converts them to values.
    Then, filters the values based on the where clause.
    Then, fills in all imputed values, if applicable.
    Then, orders by the given order_by functions.
    Then, computes the queried values requested by the column string.

    One refactoring option: you could try generating a list of all functions that will be needed, either
    for selecting or for ordering. Then compute those and add them to the data tuples. Then just do the
    order by as if you're doing it exclusively on columns. The only downside is that now if there isn't an
    order by, but there is a limit, then we computed a large number of extra functions.
    """
    if not self.persistence_layer.check_if_table_exists(tablename):
      raise utils.BayesDBInvalidBtableError(tablename)
    
    M_c, M_r, T = self.persistence_layer.get_metadata_and_table(tablename)
    X_L_list, X_D_list, M_c = self.persistence_layer.get_latent_states(tablename, modelids)
    column_lists = self.persistence_layer.get_column_lists(tablename)

    # query_colnames is the list of the raw columns/functions from the columnstring, with row_id prepended
    # queries is a list of (query_function, query_args, aggregate) tuples, where 'query_function' is
    #   a function like row_id, column, similarity, or typicality, and 'query_args' are the function-specific
    #   arguments that that function takes (in addition to the normal arguments, like M_c, X_L_list, etc).
    #   aggregate specifies whether that individual function is aggregate or not
    queries, query_colnames = select_utils.get_queries_from_columnstring(columnstring, M_c, T, column_lists)
    utils.check_for_duplicate_columns(query_colnames)

    # where_conditions is a list of (c_idx, op, val) tuples, e.g. name > 6 -> (0,>,6)
    # TODO: support functions in where_conditions. right now we only support actual column values.
    where_conditions = select_utils.get_conditions_from_whereclause(whereclause, M_c, T, column_lists)

    # If there are no models, make sure that we aren't using functions that require models.
    # TODO: make this less hardcoded
    if len(X_L_list) == 0:
      blacklisted_functions = [functions._similarity, functions._row_typicality, functions._col_typicality, functions._probability]
      used_functions = [q[0] for q in queries]
      for bf in blacklisted_functions:
        if bf in queries:
          raise utils.BayesDBNoModelsError(tablename)
      if order_by:
        order_by_functions = [x[0] for x in order_by]
        blacklisted_function_names = ['similarity', 'typicality', 'probability', 'predictive probability']        
        for fname in blacklisted_function_names:
          for order_by_f in order_by_functions:
            if fname in order_by_f:
              raise utils.BayesDBNoModelsError(tablename)              

    # List of rows; contains actual data values (not categorical codes, or functions),
    # missing values imputed already, and rows that didn't satsify where clause filtered out.
    filtered_rows = select_utils.filter_and_impute_rows(where_conditions, whereclause, T, M_c, X_L_list, X_D_list, self,
                                                        query_colnames, impute_confidence, num_impute_samples, tablename)

    ## TODO: In order to avoid double-calling functions when we both select them and order by them,
    ## we should augment filtered_rows here with all functions that are going to be selected
    ## (and maybe temporarily augmented with all functions that will be ordered only)
    ## If only being selected: then want to compute after ordering...

    # Simply rearranges the order of the rows in filtered_rows according to the order_by query.
    filtered_rows = select_utils.order_rows(filtered_rows, order_by, M_c, X_L_list, X_D_list, T, self, column_lists)

    # Iterate through each row, compute the queried functions for each row, and limit the number of returned rows.
    data = select_utils.compute_result_and_limit(filtered_rows, limit, queries, M_c, X_L_list, X_D_list, T, self)

    ret = dict(data=data, columns=query_colnames)
    if plot:
      ret['M_c'] = M_c
    elif summarize:
      data, columns = utils.summarize_table(ret['data'], ret['columns'], M_c)
      ret['data'] = data
      ret['columns'] = columns
    return ret

  def simulate(self, tablename, columnstring, newtablename, givens, whereclause, numpredictions, order_by, plot=False, modelids=None, summarize=False):
    """Simple predictive samples. Returns one row per prediction, with all the given and predicted variables."""
    # TODO: whereclause not implemented.
    if not self.persistence_layer.check_if_table_exists(tablename):
      raise utils.BayesDBInvalidBtableError(tablename)
    if not self.persistence_layer.has_models(tablename):
      raise utils.BayesDBNoModelsError(tablename)            

    X_L_list, X_D_list, M_c = self.persistence_layer.get_latent_states(tablename, modelids)
    if len(X_L_list) == 0:
      return {'message': 'You must INITIALIZE MODELS (and highly preferably ANALYZE) before using predictive queries.'}
    M_c, M_r, T = self.persistence_layer.get_metadata_and_table(tablename)

    numrows = len(M_r['idx_to_name'])
    name_to_idx = M_c['name_to_idx']

    # parse givens
    ## TODO throw exception for <,> without dissallowing them in the values. 
    given_col_idxs_to_vals = dict()
    if givens=="" or '=' not in givens:
      Y = None
    else:
      varlist = [[c.strip() for c in b.split('=')] for b in re.split(r'and|,', givens, flags=re.IGNORECASE)]
      Y = []
      for colname, colval in varlist:
        if type(colval) == str or type(colval) == unicode:
          try:
            colval = ast.literal_eval(colval)
          except ValueError: 
            raise utils.BayesDBParseError("Could not parse value %s. Try '%s' instead." % (colval, colval))
        given_col_idxs_to_vals[name_to_idx[colname]] = colval
        Y.append((numrows+1, name_to_idx[colname], colval))

      # map values to codes
      Y = [(r, c, data_utils.convert_value_to_code(M_c, c, colval)) for r,c,colval in Y]

    ## Parse queried columns.
    column_lists = self.persistence_layer.get_column_lists(tablename)
    colnames = utils.column_string_splitter(columnstring, M_c, column_lists)
    colnames = [c.lower() for c in colnames]
    utils.check_for_duplicate_columns(colnames)
    col_indices = [name_to_idx[colname] for colname in colnames]
    query_col_indices = [idx for idx in col_indices if idx not in given_col_idxs_to_vals.keys()]
    Q = [(numrows+1, col_idx) for col_idx in query_col_indices]

    if len(Q) > 0:
      out = self.call_backend('simple_predictive_sample', dict(M_c=M_c, X_L=X_L_list, X_D=X_D_list, Y=Y, Q=Q, n=numpredictions))
    else:
      out = [[] for x in range(numpredictions)]
    assert type(out) == list and len(out) >= 1 and type(out[0]) == list and len(out) == numpredictions
    
    # convert to data, columns dict output format
    # map codes to original values
    data = []
    for out_row in out:
      row = []
      i = 0
      for idx in col_indices:
        if idx in given_col_idxs_to_vals:
          row.append(given_col_idxs_to_vals[idx])
        else:
          row.append(data_utils.convert_code_to_value(M_c, idx, out_row[i]))
          i += 1
      data.append(row)
      
    ret = {'columns': colnames, 'data': data}
    if plot:
      ret['M_c'] = M_c
    elif summarize:
      data, columns = utils.summarize_table(ret['data'], ret['columns'], M_c)
      ret['data'] = data
      ret['columns'] = columns      
    return ret

  def show_column_lists(self, tablename):
    """
    Return a list of all column list names.
    """
    if not self.persistence_layer.check_if_table_exists(tablename):
      raise utils.BayesDBInvalidBtableError(tablename)
      
    column_lists = self.persistence_layer.get_column_lists(tablename)
    return dict(columns=['column list'], data=[[k] for k in column_lists.keys()])

  def show_row_lists(self, tablename):
    """
    Return a list of all row lists, and their row counts.
    """
    if not self.persistence_layer.check_if_table_exists(tablename):
      raise utils.BayesDBInvalidBtableError(tablename)
      
    row_lists = self.persistence_layer.get_row_lists(tablename)
    return dict(row_lists=[(name, len(rows)) for (name, rows) in row_lists.items()])

    
  def show_columns(self, tablename, column_list=None):
    """
    Return the specified columnlist. If None, return all columns in original order.
    """
    if not self.persistence_layer.check_if_table_exists(tablename):
      raise utils.BayesDBInvalidBtableError(tablename)
      
    if column_list:
      column_names = self.persistence_layer.get_column_list(tablename, column_list)
    else:
      M_c, M_r, T = self.persistence_layer.get_metadata_and_table(tablename)      
      column_names = list(M_c['name_to_idx'].keys())
    return dict(columns=column_names)

  def show_model(self, tablename, modelid, filename):
    X_L_list, X_D_list, M_c = self.persistence_layer.get_latent_states(tablename)
    M_c, M_r, T = self.persistence_layer.get_metadata_and_table(tablename)
    import crosscat.utils.plot_utils
    crosscat.utils.plot_utils.plot_views(numpy.array(T), X_D_list[modelid], X_L_list[modelid], M_c, filename)

  def estimate_columns(self, tablename, columnstring, whereclause, limit, order_by, name=None, modelids=None):
    """
    Return all the column names from the specified table as a list.
    First, columns are filtered based on whether they match the whereclause.
    The whereclause must consist of functions of a single column only.
    Next, the columns are ordered by other functions of a single column.
    Finally, the columns are limited to the specified number.

    ## allowed functions:
    # typicality(centrality)
    # dependence probability to <col>
    # mutual information with <col>
    # correlation with <col>
    """
    if not self.persistence_layer.check_if_table_exists(tablename):
      raise utils.BayesDBInvalidBtableError(tablename)
    
    X_L_list, X_D_list, M_c = self.persistence_layer.get_latent_states(tablename, modelids)
    M_c, M_r, T = self.persistence_layer.get_metadata_and_table(tablename)
    
    if columnstring and len(columnstring) > 0:
      # User has entered the columns to be in the column list.
      column_indices = [M_c['name_to_idx'][colname.lower()] for colname in utils.column_string_splitter(columnstring, M_c, [])]
    else:
      # Start with all columns.
      column_indices = list(M_c['name_to_idx'].values())
    
    ## filter based on where clause
    where_conditions = estimate_columns_utils.get_conditions_from_column_whereclause(whereclause, M_c, T)
    if len(where_conditions) > 0 and len(X_L_list) == 0:
      raise utils.BayesDBNoModelsError(tablename)      
    column_indices = estimate_columns_utils.filter_column_indices(column_indices, where_conditions, M_c, T, X_L_list, X_D_list, self)
    
    ## order
    if order_by and len(X_L_list) == 0:
      raise utils.BayesDBNoModelsError(tablename)      
    column_indices = estimate_columns_utils.order_columns(column_indices, order_by, M_c, X_L_list, X_D_list, T, self)
    
    # limit
    if limit != float('inf'):
      column_indices = column_indices[:limit]

    # convert indices to names
    column_names = [M_c['idx_to_name'][str(idx)] for idx in column_indices]

    # save column list, if given a name to save as
    if name:
      self.persistence_layer.add_column_list(tablename, name, column_names)
    
    return {'columns': column_names}

  def estimate_pairwise_row(self, tablename, function_name, row_list, components_name=None, threshold=None, modelids=None):
    if not self.persistence_layer.check_if_table_exists(tablename):
      raise utils.BayesDBInvalidBtableError(tablename)
    X_L_list, X_D_list, M_c = self.persistence_layer.get_latent_states(tablename, modelids)
    M_c, M_r, T = self.persistence_layer.get_metadata_and_table(tablename)
    if len(X_L_list) == 0:
      raise utils.BayesDBNoModelsError(tablename)

    # TODO: deal with row_list
    if row_list:
      row_indices = self.persistence_layer.get_row_list(tablename, row_list)
      if len(row_indices) == 0:
        raise utils.BayesDBError("Error: Row list %s has no rows." % row_list)
    else:
      row_indices = None

    column_lists = self.persistence_layer.get_column_lists(tablename)
    
    # Do the heavy lifting: generate the matrix itself
    matrix, row_indices_reordered, components = pairwise.generate_pairwise_row_matrix(function_name, X_L_list, X_D_list, M_c, T, tablename, engine=self, row_indices=row_indices, component_threshold=threshold, column_lists=column_lists)
    
    title = 'Pairwise row %s for %s' % (function_name, tablename)      
    ret = dict(
      matrix=matrix,
      column_names=row_indices_reordered, # this is called column_names so that the plotting code displays them
      title=title,
      message = "Created " + title
      )

    # Create new btables from connected components (like into), if desired. Overwrites old ones with same name.
    if components is not None:
      component_name_tuples = []
      for i, component in enumerate(components):
        name = "%s_%d" % (components_name, i)
        num_rows = len(component)
        self.persistence_layer.add_row_list(tablename, name, component)
        component_name_tuples.append((name, num_rows))
      ret['components'] = components
      ret['row_lists'] = component_name_tuples

    return ret
    
  
  def estimate_pairwise(self, tablename, function_name, column_list=None, components_name=None, threshold=None, modelids=None):
    if not self.persistence_layer.check_if_table_exists(tablename):
      raise utils.BayesDBInvalidBtableError(tablename)
    X_L_list, X_D_list, M_c = self.persistence_layer.get_latent_states(tablename, modelids)
    M_c, M_r, T = self.persistence_layer.get_metadata_and_table(tablename)
    if len(X_L_list) == 0:
      raise utils.BayesDBNoModelsError(tablename)

    if column_list:
      column_names = self.persistence_layer.get_column_list(tablename, column_list)
      if len(column_names) == 0:
        raise utils.BayesDBError("Error: Column list %s has no columns." % column_list)

      utils.check_for_duplicate_columns(column_names)
    else:
      column_names = None

    # Do the heavy lifting: generate the matrix itself
    matrix, column_names_reordered, components = pairwise.generate_pairwise_column_matrix(   \
        function_name, X_L_list, X_D_list, M_c, T, tablename,
        engine=self, column_names=column_names, component_threshold=threshold)
    
    title = 'Pairwise column %s for %s' % (function_name, tablename)      
    ret = dict(
      matrix=matrix,
      column_names=column_names_reordered,
      title=title,
      message = "Created " + title
      )

    # Add the column lists for connected components, if desired. Overwrites old ones with same name.
    if components is not None:
      component_name_tuples = []
      for i, component in enumerate(components):
        name = "%s_%d" % (components_name, i)
        column_names = [M_c['idx_to_name'][str(idx)] for idx in component]
        self.persistence_layer.add_column_list(tablename, name, column_names)
        component_name_tuples.append((name, column_names))
      ret['components'] = components
      ret['column_lists'] = component_name_tuples

    return ret

# helper functions
get_name = lambda x: getattr(x, '__name__')
get_Engine_attr = lambda x: getattr(Engine, x)
is_Engine_method_name = lambda x: inspect.ismethod(get_Engine_attr(x))
#
def get_method_names():
    return filter(is_Engine_method_name, dir(Engine))
#
def get_method_name_to_args():
    method_names = get_method_names()
    method_name_to_args = dict()
    for method_name in method_names:
        method = Engine.__dict__[method_name]
        arg_str_list = inspect.getargspec(method).args[1:]
        method_name_to_args[method_name] = arg_str_list
    return method_name_to_args

########NEW FILE########
__FILENAME__ = estimate_columns_utils
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import re
import utils
import numpy
import os
import pylab
import matplotlib.cm
import inspect
import operator
import ast

import utils
import functions
import data_utils as du


def filter_column_indices(column_indices, where_conditions, M_c, T, X_L_list, X_D_list, engine):
  return [c_idx for c_idx in column_indices if _is_column_valid(c_idx, where_conditions, M_c, X_L_list, X_D_list, T, engine)]

def _is_column_valid(c_idx, where_conditions, M_c, X_L_list, X_D_list, T, engine):
    for ((func, f_args), op, val) in where_conditions:
        # mutual_info, correlation, and dep_prob all take args=(i,j)
        # col_typicality takes just args=i
        # incoming f_args will be None for col_typicality, j for the three others
        if f_args is not None:
            f_args = (f_args, c_idx)
        else:
            f_args = c_idx
      
        where_value = func(f_args, None, None, M_c, X_L_list, X_D_list, T, engine)
        return op(where_value, val)
    return True

def get_conditions_from_column_whereclause(whereclause, M_c, T):
  ## Create conds: the list of conditions in the whereclause.
  ## List of (c_idx, op, val) tuples.
  conds = list() 
  if len(whereclause) > 0:
    conditions = re.split(r'and', whereclause, flags=re.IGNORECASE)
    ## Order matters: need <= and >= before < and > and =.
    operator_list = ['<=', '>=', '=', '>', '<']
    operator_map = {'<=': operator.le, '<': operator.lt, '=': operator.eq, '>': operator.gt, '>=': operator.ge}

    # TODO: parse this properly with pyparsing
    # note that there can be more than one operator!
    # if 1 total: we want that one. if 2 total: we want 2nd (assuming probably query on left). if 3 total: we want 2nd.
    
    for condition in conditions:
      for operator_str in operator_list:
        if operator_str in condition:
          op_str = operator_str
          op = operator_map[op_str]
          break
      vals = condition.split(op_str)
      raw_string = vals[0].strip()

      ## Determine what type the value is
      raw_val = vals[1].strip()
      if utils.is_int(raw_val):
        val = int(raw_val)
      elif utils.is_float(raw_val):
        val = float(raw_val)
      else:
        ## val could have matching single or double quotes, which we can safely eliminate
        ## with the following safe (string literal only) implementation of eval
        val = ast.literal_eval(raw_val).lower()


      t = functions.parse_cfun_column_typicality(raw_string, M_c)
      if t is not None:
        conds.append(((functions._col_typicality, None), op, val))
        continue

      d = functions.parse_cfun_dependence_probability(raw_string, M_c)
      if d is not None:
        conds.append(((functions._dependence_probability, d), op, val))
        continue

      m = functions.parse_cfun_mutual_information(raw_string, M_c)
      if m is not None:
        conds.append(((functions._mutual_information, m), op, val))
        continue

      c= functions.parse_cfun_correlation(raw_string, M_c)
      if c is not None:
        conds.append(((functions._correlation, c), op, val))
        continue

      raise utils.BayesDBParseError("Invalid query argument: could not parse '%s'" % raw_string)
  return conds
    

def order_columns(column_indices, order_by, M_c, X_L_list, X_D_list, T, engine):
  if not order_by:
    return column_indices
  # Step 1: get appropriate functions.
  function_list = list()
  for orderable in order_by:
    assert type(orderable) == tuple and type(orderable[0]) == str and type(orderable[1]) == bool
    raw_orderable_string = orderable[0]
    desc = orderable[1]

    ## function_list is a list of
    ##   (f(args, row_id, data_values, M_c, X_L_list, X_D_list, engine), args, desc)

    t = functions.parse_cfun_column_typicality(raw_orderable_string, M_c)
    if t:
      function_list.append((functions._col_typicality, None, desc))
      continue

    d = functions.parse_cfun_dependence_probability(raw_orderable_string, M_c)
    if d:
      function_list.append((functions._dependence_probability, d, desc))
      continue

    m = functions.parse_cfun_mutual_information(raw_orderable_string, M_c)
    if m is not None:
      function_list.append((functions._mutual_information, m, desc))
      continue

    c= functions.parse_cfun_correlation(raw_orderable_string, M_c)
    if c is not None:
      function_list.append((functions._correlation, c, desc))
      continue

    raise utils.BayesDBParseError("Invalid query argument: could not parse '%s'" % raw_orderable_string)

  ## Step 2: call order by.
  sorted_column_indices = _column_order_by(column_indices, function_list, M_c, X_L_list, X_D_list, T, engine)
  return sorted_column_indices

def _column_order_by(column_indices, function_list, M_c, X_L_list, X_D_list, T, engine):
  """
  Return the original column indices, but sorted by the individual functions.
  """
  if len(column_indices) == 0 or not function_list:
    return column_indices

  scored_column_indices = list() ## Entries are (score, cidx)
  for c_idx in column_indices:
    ## Apply each function to each cidx to get a #functions-length tuple of scores.
    scores = []
    for (f, f_args, desc) in function_list:

      # mutual_info, correlation, and dep_prob all take args=(i,j)
      # col_typicality takes just args=i
      # incoming f_args will be None for col_typicality, j for the three others
      if f_args:
        f_args = (f_args, c_idx)
      else:
        f_args = c_idx
        
      score = f(f_args, None, None, M_c, X_L_list, X_D_list, T, engine)
      if desc:
        score *= -1
      scores.append(score)
    scored_column_indices.append((tuple(scores), c_idx))
  scored_column_indices.sort(key=lambda tup: tup[0], reverse=False)

  return [tup[1] for tup in scored_column_indices]

########NEW FILE########
__FILENAME__ = functions
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import re
import utils
import numpy
import os
import pylab
import matplotlib.cm
import inspect
import operator
import ast
import math
from scipy.stats import pearsonr

import utils
import select_utils
import data_utils as du

###
# Three types of function signatures, for each purpose.
#
# SELECT/ORDER BY/WHERE:
# f(args, row_id, data_values, M_c, X_L_list, X_D_list, T, engine)
#
# ESTIMATE COLUMNS
#
#
# First argument of each of these functions is the function-specific argument list,
# which is parsed from parse_<function_name>(), also in this file.
#
##

###################################################################
# NORMAL FUNCTIONS (have a separate output value for each row: can ORDER BY, SELECT, etc.)
###################################################################


def _column(column_args, row_id, data_values, M_c, X_L_list, X_D_list, T, engine):
    col_idx = column_args
    return data_values[col_idx]

def _row_id(args, row_id, data_values, M_c, X_L_list, X_D_list, T, engine):
    return row_id

def _similarity(similarity_args, row_id, data_values, M_c, X_L_list, X_D_list, T, engine):
    target_row_id, target_columns = similarity_args
    return engine.call_backend('similarity', dict(M_c=M_c, X_L_list=X_L_list, X_D_list=X_D_list, given_row_id=row_id, target_row_id=target_row_id, target_columns=target_columns))

def _row_typicality(row_typicality_args, row_id, data_values, M_c, X_L_list, X_D_list, T, engine):
    return engine.call_backend('row_structural_typicality', dict(X_L_list=X_L_list, X_D_list=X_D_list, row_id=row_id))

def _predictive_probability(predictive_probability_args, row_id, data_values, M_c, X_L_list, X_D_list, T, engine):
    c_idx = predictive_probability_args
    assert type(c_idx) == int    
    Q = [(row_id, c_idx, T[row_id][c_idx])]
    Y = []
    p = math.exp(engine.call_backend('simple_predictive_probability_multistate', dict(M_c=M_c, X_L_list=X_L_list, X_D_list=X_D_list, Y=Y, Q=Q)))
    return p

#####################################################################
# AGGREGATE FUNCTIONS (have only one output value)
#####################################################################
    
def _col_typicality(col_typicality_args, row_id, data_values, M_c, X_L_list, X_D_list, T, engine):
    c_idx = col_typicality_args
    assert type(c_idx) == int
    return engine.call_backend('column_structural_typicality', dict(X_L_list=X_L_list, col_id=c_idx))

def _probability(probability_args, row_id, data_values, M_c, X_L_list, X_D_list, T, engine):
    c_idx, value = probability_args
    assert type(c_idx) == int
    try:
        observed = du.convert_value_to_code(M_c, c_idx, value)
    except KeyError:
        # value doesn't exist
        return 0
    row_id = len(X_D_list[0][0]) + 1 ## row is set to 1 + max row, instead of this row.
    Q = [(row_id, c_idx, observed)]
    Y = []
    p = math.exp(engine.call_backend('simple_predictive_probability_multistate', dict(M_c=M_c, X_L_list=X_L_list, X_D_list=X_D_list, Y=Y, Q=Q)))
    return p
    

#########################################################################
## TWO COLUMN AGGREGATE FUNCTIONS (have only one output value, and take two columns as input)
#########################################################################

def _dependence_probability(dependence_probability_args, row_id, data_values, M_c, X_L_list, X_D_list, T, engine):
    """
    TODO: THIS NEEDS TO BE A FUNCTION ON CROSSCAT ENGINE! MOVE IT THERE!
    """
    col1, col2 = dependence_probability_args
    prob_dep = 0
    for X_L, X_D in zip(X_L_list, X_D_list):
        assignments = X_L['column_partition']['assignments']
        ## Columns dependent if in same view, and the view has greater than 1 category
        ## Future work can investigate whether more advanced probability of dependence measures
        ## that attempt to take into account the number of outliers do better.
        if (assignments[col1] == assignments[col2]):
            if len(numpy.unique(X_D[assignments[col1]])) > 1 or col1 == col2:
                prob_dep += 1
    prob_dep /= float(len(X_L_list))
    return prob_dep

def _old_dependence_probability(dependence_probability_args, row_id, data_values, M_c, X_L_list, X_D_list, T, engine):
    col1, col2 = dependence_probability_args
    prob_dep = 0
    for X_L, X_D in zip(X_L_list, X_D_list):
        assignments = X_L['column_partition']['assignments']
        ## Columns dependent if in same view, and the view has greater than 1 category
        ## Future work can investigate whether more advanced probability of dependence measures
        ## that attempt to take into account the number of outliers do better.
        if (assignments[col1] == assignments[col2]):
            prob_dep += 1
    prob_dep /= float(len(X_L_list))
    return prob_dep

    
def _mutual_information(mutual_information_args, row_id, data_values, M_c, X_L_list, X_D_list, T, engine, n_samples=None):
    col1, col2 = mutual_information_args
    Q = [(col1, col2)]
    ## Returns list of lists.
    ## First list: same length as Q, so we just take first.
    ## Second list: MI, linfoot. we take MI.
    if n_samples is None:
        results_by_model = engine.call_backend('mutual_information', dict(M_c=M_c, X_L_list=X_L_list, X_D_list=X_D_list, Q=Q))[0][0]
    else:
        results_by_model = engine.call_backend('mutual_information', dict(M_c=M_c, X_L_list=X_L_list, X_D_list=X_D_list, Q=Q, n_samples=n_samples))[0][0]                                               
    ## Report the average mutual information over each model.
    mi = float(sum(results_by_model)) / len(results_by_model)
    return mi
    
def _correlation(correlation_args, row_id, data_values, M_c, X_L_list, X_D_list, T, engine):
    col1, col2 = correlation_args
    t_array = numpy.array(T, dtype=float)
    nan_index = numpy.logical_or(numpy.isnan(t_array[:,col1]), numpy.isnan(t_array[:,col2]))
    t_array = t_array[numpy.logical_not(nan_index),:]
    correlation, p_value = pearsonr(t_array[:,col1], t_array[:,col2])
    return correlation


##############################################
# function parsing
##############################################

def parse_predictive_probability(colname, M_c):
  prob_match = re.search(r"""
      PREDICTIVE\s+PROBABILITY\s+OF\s+
      (?P<column>[^\s]+)
  """, colname, re.VERBOSE | re.IGNORECASE)
  if prob_match:
    column = prob_match.group('column')
    c_idx = M_c['name_to_idx'][column.lower()]
    return c_idx
  else:
    return None

def parse_probability(colname, M_c):
  prob_match = re.search(r"""
      ^PROBABILITY\s+OF\s+
      (?P<column>[^\s]+)\s*=\s*(\'|\")?\s*(?P<value>[^\'\"]*)\s*(\'|\")?$
    """, colname, re.VERBOSE | re.IGNORECASE)
  if prob_match:
    column = prob_match.group('column')
    c_idx = M_c['name_to_idx'][column.lower()]
    value = prob_match.group('value')
    if utils.is_int(value):
      value = int(value)
    elif utils.is_float(value):
      value = float(value)
    ## TODO: need to escape strings here with ast.eval... call?
    return c_idx, value
  else:
    return None

def parse_similarity(colname, M_c, T, column_lists):
  """
  colname: this is the thing that we want to try to parse as a similarity.
  It is an entry in a query's columnstring. eg: SELECT colname1, colname2 FROM...
  We are checking if colname matches "SIMILARITY TO <rowid> [WITH RESPECT TO <col>]"
  it is NOT just the column name
  """
  similarity_match = re.search(r"""
      similarity\s+to\s+
      (\()?
      (?P<rowid>[^,\)\(]+)
      (\))?
      \s+with\s+respect\s+to\s+
      (?P<columnstring>.*$)
  """, colname, re.VERBOSE | re.IGNORECASE)
  if not similarity_match:
    similarity_match = re.search(r"""
      similarity\s+to\s+
      (\()?
      (?P<rowid>[^,\)\(]+)
      (\))?
      \s*$
    """, colname, re.VERBOSE | re.IGNORECASE)
  if similarity_match:
      rowid = similarity_match.group('rowid').strip()
      if utils.is_int(rowid):
        target_row_id = int(rowid)
      else:
        ## Instead of specifying an integer for rowid, you can specify a simple where clause.
        where_vals = rowid.split('=')
        where_colname = where_vals[0]
        where_val = where_vals[1]
        if type(where_val) == str or type(where_val) == unicode:
          where_val = ast.literal_eval(where_val)
        ## Look up the row_id where this column has this value!
        c_idx = M_c['name_to_idx'][where_colname.lower()]
        for row_id, T_row in enumerate(T):
          row_values = select_utils.convert_row_from_codes_to_values(T_row, M_c)
          if row_values[c_idx] == where_val:
            target_row_id = row_id
            break

      if 'columnstring' in similarity_match.groupdict() and similarity_match.group('columnstring'):
          columnstring = similarity_match.group('columnstring').strip()

          target_colnames = [colname.strip() for colname in utils.column_string_splitter(columnstring, M_c, column_lists)]
          utils.check_for_duplicate_columns(target_colnames)
          target_columns = [M_c['name_to_idx'][colname] for colname in target_colnames]
      else:
          target_columns = None

      return target_row_id, target_columns
  else:
      return None

def parse_similarity_pairwise(colname, M_c, _, column_lists):
  """
  TODO: this is horribly hacky.
  Note that this function returns False if it doesn't parse; different from normal.
  
  colname: this is the thing that we want to try to parse as a similarity.
  It is an entry in a query's columnstring. eg: SELECT colname1, colname2 FROM...
  We are checking if colname matches "SIMILARITY TO <rowid> [WITH RESPECT TO <col>]"
  it is NOT just the column name
  """
  similarity_match = re.search(r"""
      similarity\s+with\s+respect\s+to\s+
      (?P<columnstring>.*$)
  """, colname, re.VERBOSE | re.IGNORECASE)
  if not similarity_match:
    similarity_match = re.search(r"""
      similarity
    """, colname, re.VERBOSE | re.IGNORECASE)
  if similarity_match:
      if 'columnstring' in similarity_match.groupdict() and similarity_match.group('columnstring'):
          columnstring = similarity_match.group('columnstring').strip()

          target_colnames = [colname.strip() for colname in utils.column_string_splitter(columnstring, M_c, column_lists)]
          utils.check_for_duplicate_columns(target_colnames)
          target_columns = [M_c['name_to_idx'][colname] for colname in target_colnames]
      else:
          target_columns = None

      return target_columns
  else:
      return False
      

def parse_row_typicality(colname):
    row_typicality_match = re.search(r"""
        ^\s*    
        ((row_typicality)|
        (^\s*TYPICALITY\s*$))
        \s*$
    """, colname, re.VERBOSE | re.IGNORECASE)
    if row_typicality_match:
        return True
    else:
        return None

def parse_column_typicality(colname, M_c):
  col_typicality_match = re.search(r"""
      col_typicality
      \s*
      \(\s*
      (?P<column>[^\s]+)
      \s*\)
  """, colname, re.VERBOSE | re.IGNORECASE)
  if not col_typicality_match:
      col_typicality_match = re.search(r"""
      ^\s*
      TYPICALITY\s+OF\s+
      (?P<column>[^\s]+)
      \s*$
      """, colname, flags=re.VERBOSE | re.IGNORECASE)
  if col_typicality_match:
      colname = col_typicality_match.group('column').strip()
      return M_c['name_to_idx'][colname.lower()]
  else:
      return None

def parse_mutual_information(colname, M_c):
  mutual_information_match = re.search(r"""
      mutual_information
      \s*\(\s*
      (?P<col1>[^\s]+)
      \s*,\s*
      (?P<col2>[^\s]+)
      \s*\)
  """, colname, re.VERBOSE | re.IGNORECASE)
  if not mutual_information_match:
    mutual_information_match = re.search(r"""
      MUTUAL\s+INFORMATION\s+OF\s+
      (?P<col1>[^\s]+)
      \s+(WITH|TO)\s+
      (?P<col2>[^\s]+)
    """, colname, re.VERBOSE | re.IGNORECASE)    
  if mutual_information_match:
      col1 = mutual_information_match.group('col1')
      col2 = mutual_information_match.group('col2')
      col1, col2 = M_c['name_to_idx'][col1.lower()], M_c['name_to_idx'][col2.lower()]
      return col1, col2
  else:
      return None

def parse_dependence_probability(colname, M_c):
  dependence_probability_match = re.search(r"""
    DEPENDENCE\s+PROBABILITY\s+OF\s+
    (?P<col1>[^\s]+)
    \s+(WITH|TO)\s+
    (?P<col2>[^\s]+)
  """, colname, re.VERBOSE | re.IGNORECASE)    
  if dependence_probability_match:
      col1 = dependence_probability_match.group('col1')
      col2 = dependence_probability_match.group('col2')
      col1, col2 = M_c['name_to_idx'][col1.lower()], M_c['name_to_idx'][col2.lower()]
      return col1, col2
  else:
      return None

        
def parse_correlation(colname, M_c):
  correlation_match = re.search(r"""
    CORRELATION\s+OF\s+
    (?P<col1>[^\s]+)
    \s+(WITH|TO)\s+
    (?P<col2>[^\s]+)
  """, colname, re.VERBOSE | re.IGNORECASE)    
  if correlation_match:
      col1 = correlation_match.group('col1')
      col2 = correlation_match.group('col2')
      col1, col2 = M_c['name_to_idx'][col1.lower()], M_c['name_to_idx'][col2.lower()]
      return col1, col2
  else:
      return None

        
#########################
# single-column versions
#########################

def parse_cfun_column_typicality(colname, M_c):
  col_typicality_match = re.search(r"""
      ^\s*
      TYPICALITY
      \s*$
  """, colname, flags=re.VERBOSE | re.IGNORECASE)
  if col_typicality_match:
      return True
  else:
      return None

def parse_cfun_mutual_information(colname, M_c):
  mutual_information_match = re.search(r"""
      MUTUAL\s+INFORMATION\s+
      (WITH|TO)\s+
      ['"]?
      (?P<col1>[^\s'"]+)
      ['"]?
  """, colname, re.VERBOSE | re.IGNORECASE)    
  if mutual_information_match:
      col1 = mutual_information_match.group('col1')
      return M_c['name_to_idx'][col1.lower()]
  else:
      return None

def parse_cfun_dependence_probability(colname, M_c):
  dependence_probability_match = re.search(r"""
    DEPENDENCE\s+PROBABILITY\s+
    (WITH|TO)\s+
    ['"]?
    (?P<col1>[^\s'"]+)
    ['"]?
  """, colname, re.VERBOSE | re.IGNORECASE)
  if dependence_probability_match:
      col1 = dependence_probability_match.group('col1')
      return M_c['name_to_idx'][col1.lower()]
  else:
      return None

def parse_cfun_correlation(colname, M_c):
  correlation_match = re.search(r"""
    CORRELATION\s+
    (WITH|TO)\s+
    ['"]?
    (?P<col1>[^\s'"]+)
    ['"]?
  """, colname, re.VERBOSE | re.IGNORECASE)    
  if correlation_match:
      col1 = correlation_match.group('col1')
      return M_c['name_to_idx'][col1.lower()]
  else:
      return None

########NEW FILE########
__FILENAME__ = jsonrpc_server
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
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

from twisted.internet import ssl
import traceback

from twisted.internet import reactor
from twisted.web import server, iweb
from twisted.web.resource import EncodingResourceWrapper

from jsonrpc.server import ServerEvents, JSON_RPC

import bayesdb.engine as engine_module
engine_methods = engine_module.get_method_names()
from bayesdb.engine import Engine
engine = Engine()

class ExampleServer(ServerEvents):
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
                  return getattr(engine, method)
            else:
                  return None
            
      # helper methods
      methods = set(engine_methods)
      def _get_msg(self, response):
            ret_str = 'No id response: %s' % str(response)
            if hasattr(response, 'id'):
                  ret_str = str(response.id)
                  if response.result:
                        ret_str += '; result: %s' % str(response.result)
                  else:
                        ret_str += '; error: %s' % str(response.error)
                        for at in dir(response):
                              if not at.startswith('__'):
                                    print(at + ": " + str(getattr(response, at)))
                        print("response:\n" + str(dir(response)))
            return ret_str
      
      
class CorsEncoderFactory(object):
      def encoderForRequest(self, request):
            request.setHeader("Access-Control-Allow-Origin", '*')
            request.setHeader("Access-Control-Allow-Methods", 'PUT, GET')
            return _CorsEncoder(request)

class _CorsEncoder(object):
      """
      @ivar _request: A reference to the originating request.
      
      @since: 12.3
      """
      
      def __init__(self, request):
            self._request = request
            
      def encode(self, data):
            return data
      
      def finish(self):
            return ""


root = JSON_RPC().customize(ExampleServer)
wrapped = EncodingResourceWrapper(root, [CorsEncoderFactory()])
site = server.Site(wrapped)

# 8008 is the port you want to run under. Choose something >1024
PORT = 8008
print('Listening on port %d...' % PORT)
reactor.listenTCP(PORT, site)
reactor.run()

########NEW FILE########
__FILENAME__ = pairwise
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import numpy
import os
import re
import inspect
import ast
import pylab
import matplotlib.cm
import time

import data_utils as du
import select_utils
import functions
import utils

def parse_pairwise_function(function_name, column=True, M_c=None, column_lists={}):
    if column:
        if function_name == 'mutual information':
            return functions._mutual_information
        elif function_name == 'dependence probability':
            return functions._dependence_probability
        elif function_name == 'correlation':
            return functions._correlation
        else:
            raise utils.BayesDBParseError('Invalid column function: %s' % function_name)
    else:
        # TODO: need to refactor to support similarity with respect to column, because then we need to parse
        # and return the column id here.
        target_columns = functions.parse_similarity_pairwise(function_name, M_c, None, column_lists)
        if target_columns is None:
            return (functions._similarity, None)
        elif type(target_columns) == list:
            return (functions._similarity, target_columns)
        else:
            raise utils.BayesDBParseError('Invalid row function: %s' % function_name)

def get_columns(column_names, M_c):
    # If using a subset of the columns, get the appropriate names, and figure out their indices.
    if column_names is not None:
        column_indices = [M_c['name_to_idx'][name] for name in column_names]
    else:
        num_cols = len(M_c['name_to_idx'].keys())
        column_names = [M_c['idx_to_name'][str(idx)] for idx in range(num_cols)]
        column_indices = range(num_cols)
    column_names = numpy.array(column_names)
    return column_names, column_indices

def compute_raw_column_pairwise_matrix(function, X_L_list, X_D_list, M_c, T, engine, column_indices=None):
    # Compute unordered matrix: evaluate the function for every pair of columns
    # Shortcut: assume all functions are symmetric between columns, only compute half.
    num_cols = len(column_indices)
    matrix = numpy.zeros((num_cols, num_cols))
    for i, orig_i in enumerate(column_indices):
        for j in range(i, num_cols):
            orig_j = column_indices[j]
            func_val = function((orig_i, orig_j), None, None, M_c, X_L_list, X_D_list, T, engine)
            matrix[i][j] = func_val
            matrix[j][i] = func_val
    return matrix

def compute_raw_row_pairwise_matrix(function, arg, X_L_list, X_D_list, M_c, T, engine, row_indices=None):
    # TODO: currently assume that the only function possible is similarity
    if row_indices is None:
        row_indices = range(len(T))
    num_rows = len(row_indices)
    matrix = numpy.zeros((num_rows, num_rows))
    for i, orig_i in enumerate(row_indices):
        for j in range(i, num_rows):
            orig_j = row_indices[j]
            func_val = function((orig_i, arg), orig_j, None, M_c, X_L_list, X_D_list, T, engine)
            matrix[i][j] = func_val
            matrix[j][i] = func_val
    return matrix

def reorder_indices_by_cluster(matrix):
    # Hierarchically cluster columns.
    from scipy.spatial.distance import pdist
    from scipy.cluster.hierarchy import linkage, dendrogram
    Y = pdist(matrix)
    Z = linkage(Y)
    pylab.figure()
    dendrogram(Z)
    intify = lambda x: int(x.get_text())
    reorder_indices = map(intify, pylab.gca().get_xticklabels())
    pylab.clf() ## use instead of close to avoid error spam
    matrix_reordered = matrix[:, reorder_indices][reorder_indices, :]    
    return matrix_reordered, reorder_indices

def get_connected_components(matrix, component_threshold):
    # If component_threshold isn't none, then we want to return all the connected components
    # of columns: columns are connected if their edge weight is above the threshold.
    # Just do a search, starting at each column id.

    from collections import defaultdict
    components = [] # list of lists (conceptually a set of sets, but faster here)

    # Construct graph, in the form of a neighbor dictionary
    neighbors_dict = defaultdict(list)
    for i in range(matrix.shape[0]):
        for j in range(i+1, matrix.shape[0]):
            if matrix[i][j] > component_threshold:
                neighbors_dict[i].append(j)
                neighbors_dict[j].append(i)

    # Outer while loop: make sure every column has been visited
    unvisited = set(range(matrix.shape[0]))
    while(len(unvisited) > 0):
        component = []
        stack = [unvisited.pop()]
        while(len(stack) > 0):
            cur = stack.pop()
            component.append(cur)                
            neighbors = neighbors_dict[cur]
            for n in neighbors:
                if n in unvisited:
                    stack.append(n)
                    unvisited.remove(n)                        
        if len(component) > 1:
            components.append(component)
    return components

def generate_pairwise_column_matrix(function_name, X_L_list, X_D_list, M_c, T, tablename='', limit=None, engine=None, column_names=None, component_threshold=None):
    """
    Compute a matrix. In using a function that requires engine (currently only
    mutual information), engine must not be None.
    """

    # Get appropriate function
    function = parse_pairwise_function(function_name, column=True, M_c=M_c)

    # Get appropriate column information from column_names
    column_names, column_indices = get_columns(column_names, M_c)

    # Actually compute each function between each pair of columns
    matrix = compute_raw_column_pairwise_matrix(function, X_L_list, X_D_list, M_c, T, engine, column_indices)

    if component_threshold is not None:
        # Components is a list of lists, where the inner list contains the ids (into the matrix)
        # of the columns in each component.
        components = get_connected_components(matrix, component_threshold)
        
        # Now, convert the components from their matrix indices to their btable indices
        new_comps = []
        for comp in components:
            new_comps.append([column_indices[c] for c in comp])
        components = new_comps
    else:
        components = None

    # reorder the matrix
    matrix, reorder_indices = reorder_indices_by_cluster(matrix)
    column_names_reordered = column_names[reorder_indices]
            
    return matrix, column_names_reordered, components

def generate_pairwise_row_matrix(function_name, X_L_list, X_D_list, M_c, T, tablename='', engine=None, row_indices=None, component_threshold=None, column_lists={}):
    """
    Compute a matrix. In using a function that requires engine (currently only
    mutual information), engine must not be None.
    """

    # Get appropriate function
    function, arg = parse_pairwise_function(function_name, column=False, M_c=M_c, column_lists=column_lists)

    # Get appropriate row list
    if row_indices is None:
        row_indices = numpy.array(range(len(T)))
    else:
        row_indices = numpy.array(row_indices)

    # Actually compute each function between each pair of columns
    matrix = compute_raw_row_pairwise_matrix(function, arg, X_L_list, X_D_list, M_c, T, engine, row_indices)

    if component_threshold is not None:
        # Components is a list of lists, where the inner list contains the ids (into the matrix)
        # of the columns in each component.
        components = get_connected_components(matrix, component_threshold)
        
        # Now, convert the components from their matrix indices to their btable indices
        new_comps = []
        for comp in components:
            new_comps.append([row_indices[c] for c in comp])
        components = new_comps
    else:
        components = None

    # reorder the matrix
    matrix, reorder_indices = reorder_indices_by_cluster(matrix)
    row_indices_reordered = row_indices[reorder_indices]
            
    return matrix, row_indices_reordered, components
    

########NEW FILE########
__FILENAME__ = parser
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import engine as be
import re
import pickle
import gzip
import utils
import os

class Parser(object):
    def __init__(self):
        self.method_names = [method_name[6:] for method_name in dir(Parser) if method_name[:6] == 'parse_']
        self.method_names.remove('statement')
        self.method_name_to_args = be.get_method_name_to_args()
        self.reset_root_dir()
    
    def split_lines(self, bql_string):
        """
        Accepts a large chunk of BQL (such as a file containing many BQL statements)
        as a string, and returns individual BQL statements as a list of strings.

        Uses semicolons to split statements.
        """
        ret_statements = []
        if len(bql_string) == 0:
            return
        bql_string = re.sub(r'--.*?\n', '', bql_string)
        lines = bql_string.split(';')
        for line in lines:
            if '--' in line:
                line = line[:line.index('--')]
            line = line.strip()
            if line is not None and len(line) > 0:
                ret_statements.append(line)
        return ret_statements
    
    def parse_statement(self, bql_statement_string):
        """
        Accepts an individual BQL statement as a string, and parses it.

        If the input can be parsed into a valid BQL statement, then the tuple
        (method_name, arguments_dict) is returned, which corresponds to the
        Engine method name and arguments that should be called to execute this statement.

        If the input is not a valid BQL statement, False or None is returned.
        
        False indicates that the user was close to a valid command, but has slightly
        incorrect syntax for the arguments. In this case, a helpful message will be printed.
        
        None indicates that no good match for the command was found.
        """
        if len(bql_statement_string) == 0:
            return
        if bql_statement_string[-1] == ';':
            bql_statement_string = bql_statement_string[:-1]
        
        words = bql_statement_string.lower().split()
        if len(words) >= 1 and words[0] == 'help':
            print "Welcome to BQL help. Here is a list of BQL commands and their syntax:\n"
            for method_name in sorted(self.method_names):
                help_method = getattr(self, 'help_' +  method_name)
                print help_method()
            return False

        help_strings_to_print = list()
        for method_name in self.method_names:
            parse_method = getattr(self, 'parse_' + method_name)
            result = parse_method(words, bql_statement_string)
            if result is not None:
                if result[0] == 'help':
                    help_strings_to_print.append(result[1])
                else:
                    return result

        for help_string in help_strings_to_print:
            print help_string

    def set_root_dir(self, root_dir):
        """Set the root_directory, used as the base for all relative paths."""
        self.root_directory = root_dir

    def reset_root_dir(self):
        """Set the root_directory, used as the base for all relative paths, to
        the current working directory."""        
        self.root_directory = os.getcwd()

    def get_absolute_path(self, relative_path):
        """
        If a relative file path is given by the user in a command,
        this method is used to convert the path to an absolute path
        by assuming that the correct base directory is self.root_directory.
        """
        if os.path.isabs(relative_path):
            return relative_path
        else:
            return os.path.join(self.root_directory, relative_path)

##################################################################################
# Methods to parse individual commands (and the associated help method with each)
##################################################################################

    def help_list_btables(self):
        return "LIST BTABLES: view the list of all btable names."

    def parse_list_btables(self, words, orig):
        if len(words) >= 2:
            if words[0] == 'list' and words[1] == 'btables':
                return 'list_btables', dict(), None


    def help_execute_file(self):
        return "EXECUTE FILE <filename>: execute a BQL script from file."

    def parse_execute_file(self, words, orig):
        if len(words) >= 1 and words[0] == 'execute':
            if len(words) >= 3 and words[1] == 'file':
                filename = words[2]
                return 'execute_file', dict(filename=self.get_absolute_path(filename)), None
            else:
                return 'help', self.help_execute_file()

                
    def help_show_schema(self):
        return "SHOW SCHEMA FOR <btable>: show the datatype schema for the btable."

    def parse_show_schema(self, words, orig):
        if len(words) >= 4 and words[0] == 'show' and words[1] == 'schema':
            if words[2] == 'for':
                return 'show_schema', dict(tablename=words[3]), None
            else:
                return 'help', self.help_show_schema()

                
    def help_show_models(self):
        return "SHOW MODELS FOR <btable>: show the models and iterations stored for btable."

    def parse_show_models(self, words, orig):
        if len(words) >= 4 and words[0] == 'show' and words[1] == 'models':
            if words[2] == 'for':
                return 'show_models', dict(tablename=words[3]), None
            else:
                return 'help', self.help_show_models()

                
    def help_show_diagnostics(self):
        return "SHOW DIAGNOSTICS FOR <btable>: show diagnostics for this btable's models."

    def parse_show_diagnostics(self, words, orig):
        if len(words) >= 4 and words[0] == 'show' and words[1] == 'diagnostics':
            if words[2] == 'for':
                return 'show_diagnostics', dict(tablename=words[3]), None
            else:
                return 'help', self.help_show_diagnostics()


    def help_drop_models(self):
        return "DROP MODEL[S] [<id>-<id>] FROM <btable>: drop the models specified by the given ids."

    def parse_drop_models(self, words, orig):
        match = re.search(r"""
            drop\s+model(s)?\s+
            ( ((?P<start>\d+)\s*-\s*(?P<end>\d+)) | (?P<id>\d+) )?
            \s*(from|for)\s+
            (?P<btable>[^\s]+)
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if words[0] == 'drop':
                return 'help', self.help_drop_models()
        else:
            tablename = match.group('btable')
            
            model_indices = None            
            start = match.group('start')
            end = match.group('end')
            if start is not None and end is not None:
                model_indices = range(int(start), int(end)+1)
            id = match.group('id')
            if id is not None:
                model_indices = [int(id)]
            
            return 'drop_models', dict(tablename=tablename, model_indices=model_indices), None
                
                
    def help_initialize_models(self):
        return "INITIALIZE <num_models> MODELS FOR <btable> [WITH CONFIG <model_config>]: the step to perform before analyze."

    def parse_initialize_models(self, words, orig):
        match = re.search(r"""
            initialize\s+
            (?P<num_models>[^\s]+)
            \s+model(s)?\s+for\s+
            (?P<btable>[^\s]+)
            (\s+with\s+config\s+(?P<model_config>.*))?
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if words[0] == 'initialize' or (words[0] == 'create' and len(words) >= 2 and words[1] != 'models'):
                return 'help', self.help_initialize_models()
        else:
            n_models = int(match.group('num_models'))
            tablename = match.group('btable')
            model_config = match.group('model_config')

            if model_config is not None:
                model_config = model_config.strip()
            return 'initialize_models', dict(tablename=tablename, n_models=n_models,
                                             model_config=model_config), None
                    
    def help_create_btable(self):
        return "CREATE BTABLE <tablename> FROM <filename>: create a table from a csv file"

    def parse_create_btable(self, words, orig):
        crosscat_column_types = None
        if len(words) >= 2:
            if (words[0] == 'upload' or words[0] == 'create') and (words[1] == 'ptable' or words[1] == 'btable'):
                if len(words) >= 5:
                    tablename = words[2]
                    if words[3] == 'from':
                        csv_path = self.get_absolute_path(orig.split()[4])
                        return 'create_btable', \
                            dict(tablename=tablename, cctypes_full=crosscat_column_types), \
                            dict(csv_path=csv_path)
                    else:
                        return 'help', self.help_create_btable()
                else:
                    return 'help', self.help_create_btable()

                    
    def help_drop_btable(self):
        return "DROP BTABLE <tablename>: drop table."

    def parse_drop_btable(self, words, orig):
        if len(words) >= 3:
            if words[0] == 'drop' and (words[1] == 'tablename' or words[1] == 'ptable' or words[1] == 'btable'):
                return 'drop_btable', dict(tablename=words[2]), None


    def help_analyze(self):
        return "ANALYZE <btable> [MODEL[S] <id>-<id>] [FOR <iterations> ITERATIONS | FOR <seconds> SECONDS]: perform inference."

    def parse_analyze(self, words, orig):
        match = re.search(r"""
            analyze\s+
            (?P<btable>[^\s]+)\s+
            (model(s)?\s+
              (((?P<start>\d+)\s*-\s*(?P<end>\d+)) | (?P<id>\d+)) )?
            \s*for\s+
            ((?P<iterations>\d+)\s+iteration(s)?)?
            ((?P<seconds>\d+)\s+second(s)?)?
            (\s*with\s+(?P<kernel>[^\s]+)\s+kernel)?
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None or (match.group('iterations') is None and match.group('seconds') is None):
            if words[0] == 'analyze':
                return 'help', self.help_analyze()
        else:
            model_indices = None
            tablename = match.group('btable')

            start = match.group('start')
            end = match.group('end')
            if start is not None and end is not None:
                model_indices = range(int(start), int(end)+1)
            id = match.group('id')
            if id is not None:
                model_indices = [int(id)]
            
            iterations = match.group('iterations')
            if iterations is not None:
                iterations = int(iterations)
            
            seconds = match.group('seconds')
            if seconds is not None:
                seconds = int(seconds)

            kernel = match.group('kernel')
            if kernel is not None and kernel.strip().lower()=='mh':
                ct_kernel = 1
            else:
                ct_kernel = 0
                
            return 'analyze', dict(tablename=tablename, model_indices=model_indices,
                                   iterations=iterations, seconds=seconds, ct_kernel=ct_kernel), None

            
    def help_infer(self):
        return "[SUMMARIZE | PLOT] INFER <columns|functions> FROM <btable> [WHERE <whereclause>] [WITH CONFIDENCE <confidence>] [WITH <numsamples> SAMPLES] [ORDER BY <columns|functions>] [LIMIT <limit>] [USING MODEL[S] <id>-<id>] [SAVE TO <file>]: like select, but imputes (fills in) missing values."
        
    def parse_infer(self, words, orig):
        match = re.search(r"""
            ((?P<summarize>summarize)?)?\s*
            ((?P<plot>(plot|scatter)))?\s*
            infer\s+
            (?P<columnstring>[^\s,]+(?:,\s*[^\s,]+)*)\s+
            from\s+(?P<btable>[^\s]+)\s+
            (where\s+(?P<whereclause>.*(?=with)))?
            \s*with\s+confidence\s+(?P<confidence>[^\s]+)
            (\s+limit\s+(?P<limit>\d+))?
            (\s+with\s+(?P<numsamples>[^\s]+)\s+samples)?
            (\s*save\s+to\s+(?P<filename>[^\s]+))?
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if words[0] == 'infer':
                return 'help', self.help_infer()
        else:
            summarize = match.group('summarize') is not None
            columnstring = match.group('columnstring').strip()
            tablename = match.group('btable')
            whereclause = match.group('whereclause')
            if whereclause is None:
                whereclause = ''
            else:
                whereclause = whereclause.strip()
            confidence = float(match.group('confidence'))
            limit = match.group('limit')
            if limit is None:
                limit = float("inf")
            else:
                limit = int(limit)
            numsamples = match.group('numsamples')
            if numsamples is None:
                numsamples = None
            else:
                numsamples = int(numsamples)
            newtablename = '' # For INTO
            orig, order_by = self.extract_order_by(orig)
            modelids = self.extract_using_models(orig)

            plot = match.group('plot') is not None
            if plot:
                scatter = 'scatter' in match.group('plot')
            else:
                scatter = False
                
            if match.group('filename'):
                filename = match.group('filename')
            else:
                filename = None
            return 'infer', \
                   dict(tablename=tablename, columnstring=columnstring, newtablename=newtablename,
                        confidence=confidence, whereclause=whereclause, limit=limit,
                        numsamples=numsamples, order_by=order_by, plot=plot, modelids=modelids, summarize=summarize), \
                   dict(plot=plot, scatter=scatter, filename=filename)

            
            
    def help_save_models(self):
        return "SAVE MODELS FROM <btable> TO <pklpath>: save your models to a pickle file."

    def parse_save_models(self, words, orig):
        match = re.search(r"""
            save\s+
            (models\s+)?
            ((from\s+)|(for\s+))
            (?P<btable>[^\s]+)
            \s+to\s+
            (?P<pklpath>[^\s]+)
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if words[0] == 'save':
                return 'help', self.help_save_models()
        else:
            tablename = match.group('btable')
            pkl_path = match.group('pklpath')
            return 'save_models', dict(tablename=tablename), dict(pkl_path=pkl_path)


            
    def help_load_models(self):
        return "LOAD MODELS <pklpath> INTO <btable>: load models from a pickle file."
        
    def parse_load_models(self, words, orig):
        match = re.search(r"""
            load\s+
            models\s+
            (?P<pklpath>[^\s]+)\s+
            ((into\s+)|(for\s+))
            (?P<btable>[^\s]+)\s*$
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if words[0] == 'load':
                return 'help', self.help_load_models()
        else:
            tablename = match.group('btable')
            pkl_path = match.group('pklpath')
            return 'load_models', dict(tablename=tablename), dict(pkl_path=pkl_path)

            
    def help_show_model(self):
        return "SHOW MODEL <model_id> FROM <btable>"

    def parse_show_model(self, words, orig):
        match = re.search(r"""
            show\s+model\s+
            (?P<modelid>\d+)
            \s+from\s+
            (?P<btable>[^\s]+)
            (\s*save\s+to\s+(?P<filename>))?
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if words[0] == 'show' and words[1] == 'model':
                return 'help', self.help_show_model()
        else:
            if match.group('filename'):
                filename = match.group('filename')
            else:
                filename = None            
            return 'show_model', dict(tablename=match.group('btable'),
                                      modelid=int(match.group('modelid')),
                                      filename=filename), None

            
    def help_select(self):
        return '[SUMMARIZE | PLOT] SELECT <columns|functions> FROM <btable> [WHERE <whereclause>] [ORDER BY <columns|functions>] [LIMIT <limit>] [USING MODEL[S] <id>-<id>] [SAVE TO <filename>]'
        
    def parse_select(self, words, orig):
        match = re.search(r"""
            ((?P<summarize>summarize)?)?\s*
            ((?P<plot>(plot|scatter)))?\s*        
            select\s+
            (?P<columnstring>.*?((?=from)))
            \s*from\s+(?P<btable>[^\s]+)\s*
            (where\s+(?P<whereclause>.*?((?=limit)|(?=order)|$)))?
            (\s*limit\s+(?P<limit>\d+))?
            (\s*save\s+to\s+(?P<filename>[^\s]+))?
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if words[0] == 'select':
                return 'help', self.help_select()
        else:
            summarize = match.group('summarize') is not None
            columnstring = match.group('columnstring').strip()
            tablename = match.group('btable')
            whereclause = match.group('whereclause')
            if whereclause is None:
                whereclause = ''
            else:
                whereclause = whereclause.strip()
            limit = self.extract_limit(orig)
            orig, order_by = self.extract_order_by(orig)
            modelids = self.extract_using_models(orig)

            plot = match.group('plot') is not None
            if plot:
                scatter = 'scatter' in match.group('plot')
            else:
                scatter = False

            if match.group('filename'):
                filename = match.group('filename')
            else:
                filename = None

            return 'select', dict(tablename=tablename, columnstring=columnstring, whereclause=whereclause,
                                  limit=limit, order_by=order_by, plot=plot, modelids=modelids, summarize=summarize), \
              dict(scatter=scatter, filename=filename, plot=plot)


    def help_simulate(self):
        return "[SUMMARIZE | PLOT] SIMULATE <columns> FROM <btable> [GIVEN <givens>] [WHERE <whereclause>] TIMES <times> [USING MODEL[S] <id>-<id>] [SAVE TO <filename>]: simulate new datapoints based on the underlying model."

    def parse_simulate(self, words, orig):
        match = re.search(r"""
            ((?P<summarize>summarize)?)?\s*
            ((?P<plot>(plot|scatter)))?\s*        
            simulate\s+
            (?P<columnstring>[^\s,]+(?:,\s*[^\s,]+)*)\s+
            from\s+(?P<btable>[^\s]+)\s+
            (given\s+(?P<givens>.*((?=times)|(?=where))))?
            (where\s+(?P<whereclause>.*?((?=limit)|(?=times)|$)))?
            times\s+(?P<times>\d+)
            (\s*save\s+to\s+(?P<filename>[^\s]+))?
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if words[0] == 'simulate':
                return 'help', self.help_simulate()
        else:
            summarize = match.group('summarize') is not None
            columnstring = match.group('columnstring').strip()
            tablename = match.group('btable')
            givens = match.group('givens')
            if givens is None:
                givens = ''
            else:
                givens = givens.strip()
            whereclause = match.group('whereclause')
            if whereclause is None:
                whereclause = ''
            else:
                whereclause = whereclause.strip()
                
            numpredictions = int(match.group('times'))
            newtablename = '' # For INTO
            orig, order_by = self.extract_order_by(orig)
            modelids = self.extract_using_models(orig)
            
            plot = match.group('plot') is not None
            if plot:
                scatter = 'scatter' in match.group('plot')
            else:
                scatter = False
            
            if match.group('filename'):
                filename = match.group('filename')
            else:
                filename = None            
            return 'simulate', \
                    dict(tablename=tablename, columnstring=columnstring, newtablename=newtablename,
                         givens=givens, whereclause=whereclause, numpredictions=numpredictions,
                         order_by=order_by, plot=plot, modelids=modelids, summarize=summarize), \
                    dict(filename=filename, plot=plot, scatter=scatter)

    def help_show_row_lists(self):
        return "SHOW ROW LISTS FOR <btable>"

    def parse_show_row_lists(self, words, orig):
        match = re.search(r"""
          SHOW\s+ROW\s+LISTS\s+FOR\s+
          (?P<btable>[^\s]+)\s*$
        """, orig, flags=re.VERBOSE|re.IGNORECASE)
        if not match:
            if words[0] == 'show' and words[1] == 'row':
                return 'help', self.help_show_row_lists()
        else:
            tablename = match.group('btable')
            return 'show_row_lists', dict(tablename=tablename), None

    def help_show_column_lists(self):
        return "SHOW COLUMN LISTS FOR <btable>"

    def parse_show_column_lists(self, words, orig):
        match = re.search(r"""
          SHOW\s+COLUMN\s+LISTS\s+FOR\s+
          (?P<btable>[^\s]+)\s*$
        """, orig, flags=re.VERBOSE|re.IGNORECASE)
        if not match:
            if words[0] == 'show' and words[1] == 'column':
                return 'help', self.help_show_column_lists()
        else:
            tablename = match.group('btable')
            return 'show_column_lists', dict(tablename=tablename), None

    def help_show_columns(self):
        return "SHOW COLUMNS <column_list> FROM <btable>"

    def parse_show_columns(self, words, orig):
        match = re.search(r"""
          SHOW\s+COLUMNS\s+
          ((?P<columnlist>[^\s]+)\s+)?
          FROM\s+
          (?P<btable>[^\s]+)\s*$
        """, orig, flags= re.VERBOSE | re.IGNORECASE)
        if not match:
            if words[0] == 'show' and words[1] == 'columns':
                return 'help', self.help_show_columns()
        else:
            tablename = match.group('btable')
            column_list = match.group('columnlist')
            return 'show_columns', dict(tablename=tablename, column_list=column_list), None

            
    def help_estimate_columns(self):
        return "(ESTIMATE COLUMNS | CREATE COLUMN LIST) [<column_names>] FROM <btable> [WHERE <whereclause>] [ORDER BY <orderable>] [LIMIT <limit>] [USING MODEL[S] <id>-<id>] [AS <column_list>]"

    def parse_estimate_columns(self, words, orig):
        match = re.search(r"""
            ((estimate\s+columns\s+)|(create\s+column\s+list\s+))
            (?P<columnstring>.*?((?=from)))
            \s*from\s+
            (?P<btable>[^\s]+)\s*
            (where\s+(?P<whereclause>.*?((?=limit)|(?=order)|(?=as)|$)))?
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if (words[0] == 'estimate' and words[2] == 'columns') or (words[0] == 'create' and words[1] == 'column'):
                return 'help', self.help_estimate_columns()
        else:
            tablename = match.group('btable').strip()
            
            columnstring = match.group('columnstring')
            if columnstring is None:
                columnstring = ''
            else:
                columnstring = columnstring.strip()
                
            whereclause = match.group('whereclause')
            if whereclause is None:
                whereclause = ''
            else:
                whereclause = whereclause.strip()
                
            limit = self.extract_limit(orig)                
            orig, order_by = self.extract_order_by(orig)
            modelids = self.extract_using_models(orig)            
            
            name_match = re.search(r"""
              as\s+
              (?P<name>[^\s]+)
              \s*$
            """, orig, flags=re.VERBOSE|re.IGNORECASE)
            if name_match:
                name = name_match.group('name')
            else:
                name = None

            return 'estimate_columns', dict(tablename=tablename, columnstring=columnstring, whereclause=whereclause,
                                            limit=limit, order_by=order_by, name=name, modelids=modelids), None

    def help_estimate_pairwise_row(self):
        return "ESTIMATE PAIRWISE ROW SIMILARITY FROM <btable> [FOR <rows>] [USING MODEL[S] <id>-<id>] [SAVE TO <file>] [SAVE CONNECTED COMPONENTS WITH THRESHOLD <threshold> [INTO|AS] <btable>]: estimate a pairwise function of columns."

    def parse_estimate_pairwise_row(self, words, orig):
        match = re.search(r"""
            estimate\s+pairwise\s+row\s+
            (?P<functionname>.*?((?=\sfrom)))
            \s*from\s+
            (?P<btable>[^\s]+)
            (\s+for\s+rows\s+(?P<rows>[^\s]+))?
            (\s+save\s+to\s+(?P<filename>[^\s]+))?
            (\s+save\s+connected\s+components\s+with\s+threshold\s+(?P<threshold>[^\s]+)\s+(as|into)\s+(?P<components_name>[^\s]+))?
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if words[0] == 'estimate' and words[1] == 'pairwise':
                return 'help', self.help_estimate_pairwise()
        else:
            tablename = match.group('btable').strip()
            function_name = match.group('functionname')
            if function_name.strip().lower().split()[0] not in ["similarity"]:
                return 'help', self.help_estimate_pairwise()
            filename = match.group('filename') # Could be None
            row_list = match.group('rows') # Could be None
            if match.group('components_name') and match.group('threshold'):
                components_name = match.group('components_name')
                threshold = float(match.group('threshold'))
            else:
                components_name = None
                threshold = None
            modelids = self.extract_using_models(orig)                            
            return 'estimate_pairwise_row', \
              dict(tablename=tablename, function_name=function_name,
                   row_list=row_list, components_name=components_name, threshold=threshold, modelids=modelids), \
              dict(filename=filename)

        
    def help_estimate_pairwise(self):
        return "ESTIMATE PAIRWISE [DEPENDENCE PROBABILITY | CORRELATION | MUTUAL INFORMATION] FROM <btable> [FOR <columns>] [USING MODEL[S] <id>-<id>] [SAVE TO <file>] [SAVE CONNECTED COMPONENTS WITH THRESHOLD <threshold> AS <columnlist>]: estimate a pairwise function of columns."
        
    def parse_estimate_pairwise(self, words, orig):
        match = re.search(r"""
            estimate\s+pairwise\s+
            (?P<functionname>.*?((?=\sfrom)))
            \s*from\s+
            (?P<btable>[^\s]+)
            (\s+for\s+columns\s+(?P<columns>[^\s]+))?
            (\s+save\s+to\s+(?P<filename>[^\s]+))?
            (\s+save\s+connected\s+components\s+with\s+threshold\s+(?P<threshold>[^\s]+)\s+as\s+(?P<components_name>[^\s]+))?
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if words[0] == 'estimate' and words[1] == 'pairwise':
                return 'help', self.help_estimate_pairwise()
        else:
            tablename = match.group('btable').strip()
            function_name = match.group('functionname').strip().lower()
            if function_name not in ["mutual information", "correlation", "dependence probability"]:
                return 'help', self.help_estimate_pairwise()
            filename = match.group('filename') # Could be None
            column_list = match.group('columns') # Could be None
            if match.group('components_name') and match.group('threshold'):
                components_name = match.group('components_name')
                threshold = float(match.group('threshold'))
            else:
                components_name = None
                threshold = None
            modelids = self.extract_using_models(orig)                            
            return 'estimate_pairwise', \
              dict(tablename=tablename, function_name=function_name,
                   column_list=column_list, components_name=components_name, threshold=threshold, modelids=modelids), \
              dict(filename=filename)

    def help_label_columns(self):
        return "LABEL COLUMNS FOR <btable> [SET <column1>=value1[,...] | FROM <filename.csv>]: "

    def parse_label_columns(self, words, orig):
        match = re.search(r"""
            label\s+columns\s+for\s+
            (?P<btable>[^\s]+)\s+
            (set|from)\s+
            (?P<mappings>[^;]*);?
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if words[0] == 'label':
                return 'help', self.help_label_columns()
        else:
            tablename = match.group('btable').strip()
            mapping_string = match.group('mappings').strip()

            csv_path, mappings = None, None
            if words[4] == 'from':
                source = 'file'
                csv_path = mapping_string
            elif words[4] == 'set':
                source = 'inline'
                mappings = dict()
                for mapping in mapping_string.split(','):
                    vals = mapping.split('=')
                    column, label = vals[0].strip(), vals[1].strip()
                    mappings[column.strip()] = label
            return 'label_columns', dict(tablename=tablename, mappings=mappings), dict(source=source, csv_path=csv_path)

    def help_show_labels(self):
        return "SHOW LABELS FOR <btable> [<column1>[, <column2>..]]: "

    def parse_show_labels(self, words, orig):
        match = re.search(r"""
            show\s+labels\s+for\s+
            (?P<btable>[^\s]+)
            \s*(?P<columns>[^;]*);?
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if words[0] == 'show' and words[1] == 'labels':
                return 'help', self.help_show_columns()
        else:
            tablename = match.group('btable').strip()
            columnstring = match.group('columns').strip()
            return 'show_labels', dict(tablename=tablename, columnstring=columnstring), None

    def help_update_metadata(self):
        return "UPDATE METADATA FOR <btable> [SET <metadata-key1>=value1[,...] | FROM <filename.csv>]: "

    def parse_update_metadata(self, words, orig):
        match = re.search(r"""
            update\s+metadata\s+for\s+
            (?P<btable>[^\s]+)\s+
            (set|from)\s+
            (?P<mappings>[^;]*);?
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if words[0] == 'update' and words[1] == 'metadata':
                return 'help', self.help_update_metadata()
        else:
            tablename = match.group('btable').strip()
            mapping_string = match.group('mappings').strip()

            csv_path, mappings = None, None
            if words[4] == 'from':
                source = 'file'
                csv_path = mapping_string
            elif words[4] == 'set':
                source = 'inline'
                mappings = dict()
                for mapping in mapping_string.split(','):
                    vals = mapping.split('=')
                    column, label = vals[0].strip(), vals[1].strip()
                    mappings[column.strip()] = label
            return 'update_metadata', dict(tablename=tablename, mappings=mappings), dict(source=source, csv_path=csv_path)

    def help_show_metadata(self):
        return "SHOW METADATA FOR <btable> [<metadata-key1> [, <metadata-key2>...]]"

    def parse_show_metadata(self, words, orig):
        match = re.search(r"""
            show\s+metadata\s+for\s+
            (?P<btable>[^\s]+)
            \s*(?P<keystring>[^;]*);?
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if words[0] == 'show' and words[1] == 'metadata':
                return 'help', self.help_show_metadata()
        else:
            tablename = match.group('btable').strip()
            keystring = match.group('keystring').strip()
            return 'show_metadata', dict(tablename=tablename, keystring=keystring), None

    def help_update_schema(self):
        return "UPDATE SCHEMA FOR <btable> SET [<column_name>=(numerical|categorical|key|ignore)[,...]]: must be done before creating models or analyzing."
        
    def parse_update_schema(self, words, orig):
        match = re.search(r"""
            update\s+schema\s+for\s+
            (?P<btable>[^\s]+)\s+
            set\s+(?P<mappings>[^;]*);?
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if words[0] == 'update' and words[1] == 'schema':
                return 'help', self.help_update_schema()
        else:
            tablename = match.group('btable').strip()
            mapping_string = match.group('mappings').strip()
            mappings = dict()
            for mapping in mapping_string.split(','):
                vals = mapping.split('=')
                if 'continuous' in vals[1] or 'numerical' in vals[1]:
                    datatype = 'continuous'
                elif 'multinomial' in vals[1] or 'categorical' in vals[1]:
                    m = re.search(r'\((?P<num>[^\)]+)\)', vals[1])
                    if m:
                        datatype = int(m.group('num'))
                    else:
                        datatype = 'multinomial'
                elif 'key' in vals[1]:
                    datatype = 'key'
                elif 'ignore' in vals[1]:
                    datatype = 'ignore'
                else:
                    return 'help', self.help_update_datatypes()
                mappings[vals[0].strip()] = datatype
            return 'update_schema', dict(tablename=tablename, mappings=mappings), None

############################################################
# Parsing helper functions: "extract" functions
############################################################

    def extract_columns(self, orig):
        """TODO"""
        pattern = r"""
            \(\s*
            (estimate\s+)?
            columns\s+where\s+
            (?P<columnstring>\d+
            \)
        """
        match = re.search(pattern, orig.lower(), re.VERBOSE | re.IGNORECASE)
        if match:
            limit = int(match.group('limit').strip())
            return limit
        else:
            return float('inf')

    def extract_using_models(self, orig):
        """
        """
        match = re.search(r"""
            using\s+model(s)?\s+
              (((?P<start>\d+)\s*-\s*(?P<end>\d+)) | (?P<id>\d+))
        """, orig, flags = re.VERBOSE | re.IGNORECASE)
        if match:
            modelids = None
            start = match.group('start')
            end = match.group('end')
            if start is not None and end is not None:
                modelids = range(int(start), int(end)+1)
            id = match.group('id')
            if id is not None:
                modelids = [int(id)]
            return modelids


    def extract_order_by(self, orig):
        pattern = r"""
            (order\s+by\s+(?P<orderbyclause>.*?((?=limit)|$)))
        """ 
        match = re.search(pattern, orig, re.VERBOSE | re.IGNORECASE)
        if match:
            order_by_clause = match.group('orderbyclause')
            ret = list()
            orderables = list()
            
            for orderable in utils.column_string_splitter(order_by_clause):
                ## Check for DESC/ASC
                desc = re.search(r'\s+(desc|asc)($|\s|,|(?=limit))', orderable, re.IGNORECASE)
                if desc is not None and desc.group().strip().lower() == 'asc':
                    desc = False
                else:
                    desc = True
                orderable = re.sub(r'\s+(desc|asc)($|\s|,|(?=limit))', '', orderable, flags=re.IGNORECASE)
                orderables.append((orderable.strip(), desc))
                
            orig = re.sub(pattern, '', orig, flags=re.VERBOSE | re.IGNORECASE)
            return (orig, orderables)
        else:
            return (orig, False)

            
    def extract_limit(self, orig):
        pattern = r'limit\s+(?P<limit>\d+)'
        match = re.search(pattern, orig.lower())
        if match:
            limit = int(match.group('limit').strip())
            return limit
        else:
            return float('inf')



########NEW FILE########
__FILENAME__ = persistence_layer
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import os
import sys
import datetime
import json
import pickle
import shutil
import contextlib

import data_utils
import utils

import bayesdb.settings as S


class PersistenceLayer():
    """
    Stores btables in the following format in the "data" directory:
    bayesdb/data/
    ..btable_index.pkl
    ..<tablename>/
    ....metadata_full.pkl
    ....metadata.pkl
    ....column_labels.pkl
    ....column_lists.pkl
    ....row_lists.pkl
    ....models/
    ......model_<id>.pkl

    table_index.pkl: list of btable names.
    
    metadata.pkl: dict. keys: M_r, M_c, T, cctypes
    metadata_full.pkl: dict. keys: M_r_full, M_c_full, T_full, cctypes_full
    column_lists.pkl: dict. keys: column list names, values: list of column names.
    row_lists.pkl: dict. keys: row list names, values: list of row keys (need to update all these if table key is changed!).
    models.pkl: dict[model_idx] -> dict[X_L, X_D, iterations, column_crp_alpha, logscore, num_views, model_config]. Idx starting at 1.
    data.csv: the raw csv file that the data was loaded from.
    """
    
    def __init__(self):
        """
        Create data directory if doesn't exist: every other function requires data_dir.
        """
        self.cur_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.cur_dir, 'data')
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        self.load_btable_index() # sets self.btable_index

    def load_btable_index(self):
        """
        Create btable_index.pkl with an empty list if it doesn't exist; otherwise, read its contents.
        Set it to self.btable_index
        """
        btable_index_path = os.path.join(self.data_dir, 'btable_index.pkl')
        if not os.path.exists(btable_index_path):
            self.btable_index = []
            self.write_btable_index()
        else:
            f = open(btable_index_path, 'r')
            self.btable_index = pickle.load(f)
            f.close()

    def write_btable_index(self):
        btable_index_path = os.path.join(self.data_dir, 'btable_index.pkl')        
        f = open(btable_index_path, 'w')
        pickle.dump(self.btable_index, f, pickle.HIGHEST_PROTOCOL)
        f.close()

    def add_btable_to_index(self, tablename):
        self.btable_index.append(tablename)
        self.write_btable_index()

    def remove_btable_from_index(self, tablename):
        self.btable_index.remove(tablename)
        self.write_btable_index()

    def get_metadata(self, tablename):
        try:
            f = open(os.path.join(self.data_dir, tablename, 'metadata.pkl'), 'r')
        except Exception as e:
            raise utils.BayesDBError("Error: metadata does not exist. Has %s been corrupted?" % self.data_dir)
        metadata = pickle.load(f)
        f.close()
        return metadata

    def get_metadata_full(self, tablename):
        try:
            f = open(os.path.join(self.data_dir, tablename, 'metadata_full.pkl'), 'r')
        except Exception as e:
            raise utils.BayesDBError("Error: metadata_full file doesn't exist. This is most likely a result of this btable being created with an old version of BayesDB. Please try recreating the table from the original csv, and loading any models you might have.")
        metadata = pickle.load(f)
        f.close()
        return metadata

    def write_metadata(self, tablename, metadata):
        metadata_f = open(os.path.join(self.data_dir, tablename, 'metadata.pkl'), 'w')
        pickle.dump(metadata, metadata_f, pickle.HIGHEST_PROTOCOL)
        metadata_f.close()

    def write_metadata_full(self, tablename, metadata):
        metadata_f = open(os.path.join(self.data_dir, tablename, 'metadata_full.pkl'), 'w')
        pickle.dump(metadata, metadata_f, pickle.HIGHEST_PROTOCOL)
        metadata_f.close()

    def get_model_config(self, tablename):
        """
        Just loads one model, and gets the model_config from it.
        """
        model = self.get_models(tablename, modelid=self.get_max_model_id(tablename))
        if model is None:
            return None
        if 'model_config' in model:
            return model['model_config']
        else:
            return None

    def get_models(self, tablename, modelid=None):
        """
        Return the models dict for the table if modelid is None.
        If modelid is an int, then return the model specified by that id.
        If modelid is a list, then get each individual model specified by each int in that list.
        """
        models_dir = os.path.join(self.data_dir, tablename, 'models')
        if os.path.exists(models_dir):
            if modelid is not None:
                def get_single_model(modelid):
                    # Only return one of the models
                    full_fname = os.path.join(models_dir, 'model_%d.pkl' % modelid)
                    if not os.path.exists(full_fname):
                        return None
                    f = open(full_fname, 'r')
                    m = pickle.load(f)
                    f.close()
                    return m
                if type(modelid) == list:
                    models = {}
                    for i in modelid:
                        if not utils.is_int(i):
                            raise utils.BayesDBError('Invalid modelid: %s' % str(modelid))
                        models[i] = get_single_model(int(i))
                    return models
                elif utils.is_int(modelid):
                    return get_single_model(int(modelid))
                else:
                    raise utils.BayesDBError('Invalid modelid: %s' % str(modelid))
            else:
                # Return all the models
                models = {}
                fnames = os.listdir(models_dir)
                for fname in fnames:
                    model_id = fname[6:] # remove preceding 'model_'
                    model_id = int(model_id[:-4]) # remove trailing '.pkl' and cast to int
                    full_fname = os.path.join(models_dir, fname)
                    f = open(full_fname, 'r')
                    m = pickle.load(f)
                    f.close()
                    models[model_id] = m
                return models
        else:
            # Backwards compatibility with old model style.
            try:
                f = open(os.path.join(self.data_dir, tablename, 'models.pkl'), 'r')
                models = pickle.load(f)
                f.close()
                if modelid is not None:
                    return models[modelid]
                else:
                    return models
            except IOError:
                return {}

    def get_column_labels(self, tablename):
        try:
            f = open(os.path.join(self.data_dir, tablename, 'column_labels.pkl'), 'r')
            column_labels = pickle.load(f)
            f.close()
            return column_labels
        except IOError:
            return dict()

    def get_column_lists(self, tablename):
        try:
            f = open(os.path.join(self.data_dir, tablename, 'column_lists.pkl'), 'r')
            column_lists = pickle.load(f)
            f.close()
            return column_lists
        except IOError:
            return dict()

    def get_row_lists(self, tablename):
        try:
            f = open(os.path.join(self.data_dir, tablename, 'row_lists.pkl'), 'r')
            row_lists = pickle.load(f)
            f.close()
            return row_lists
        except IOError:
            return dict()

    def get_user_metadata(self, tablename):
        try:
            f = open(os.path.join(self.data_dir, tablename, 'user_metadata.pkl'), 'r')
            column_labels = pickle.load(f)
            f.close()
            return column_labels
        except IOError:
            return dict()

    def add_user_metadata(self, tablename, metadata_key, metadata_value):
        user_metadata = self.get_user_metadata(tablename)
        user_metadata[metadata_key.lower()] = metadata_value
        self.write_user_metadata(tablename, user_metadata)

    def add_column_label(self, tablename, column_name, column_label):
        column_labels = self.get_column_labels(tablename)
        column_labels[column_name.lower()] = column_label
        self.write_column_labels(tablename, column_labels)
            
    def add_column_list(self, tablename, column_list_name, column_list):
        column_lists = self.get_column_lists(tablename)
        column_lists[column_list_name] = column_list
        self.write_column_lists(tablename, column_lists)

    def add_row_list(self, tablename, row_list_name, row_list):
        row_lists = self.get_row_lists(tablename)
        row_lists[row_list_name] = row_list
        self.write_row_lists(tablename, row_lists)

    def get_column_label(self, tablename, column_name):
        column_labels = self.get_column_labels(tablename)
        if column_name.lower() in column_labels:
            return column_labels[column_name.lower()]
        else:
            raise utils.BayesDBError('Column %s in btable %s has no label.' % (column_name, tablename))
        
    def get_column_list(self, tablename, column_list):
        column_lists = self.get_column_lists(tablename)
        if column_list in column_lists:
            return column_lists[column_list]
        else:
            raise utils.BayesDBColumnListDoesNotExistError(column_list, tablename)

    def get_row_list(self, tablename, row_list):
        row_lists = self.get_row_lists(tablename)
        if row_list in row_lists:
            return row_lists[row_list]
        else:
            raise utils.BayesDBRowListDoesNotExistError(row_list, tablename)
            
    def write_model(self, tablename, model, modelid):
        # Make models dir
        models_dir = os.path.join(self.data_dir, tablename, 'models')
        if not os.path.exists(models_dir):
            os.makedirs(models_dir)

        model_f = open(os.path.join(models_dir, 'model_%d.pkl' % modelid), 'w')
        pickle.dump(model, model_f, pickle.HIGHEST_PROTOCOL)
        model_f.close()

    def write_models(self, tablename, models):
        # Make models dir
        models_dir = os.path.join(self.data_dir, tablename, 'models')
        if not os.path.exists(models_dir):
            os.makedirs(models_dir)

        # Write each model individually
        for i, v in models.items():
            model_f = open(os.path.join(models_dir, 'model_%d.pkl' % i), 'w')
            pickle.dump(v, model_f, pickle.HIGHEST_PROTOCOL)
            model_f.close()

    def write_column_labels(self, tablename, column_labels):
        column_labels_f = open(os.path.join(self.data_dir, tablename, 'column_labels.pkl'), 'w')
        pickle.dump(column_labels, column_labels_f, pickle.HIGHEST_PROTOCOL)
        column_labels_f.close()

    def write_user_metadata(self, tablename, user_metadata):
        user_metadata_f = open(os.path.join(self.data_dir, tablename, 'user_metadata.pkl'), 'w')
        pickle.dump(user_metadata, user_metadata_f, pickle.HIGHEST_PROTOCOL)
        user_metadata_f.close()

    def write_column_lists(self, tablename, column_lists):
        column_lists_f = open(os.path.join(self.data_dir, tablename, 'column_lists.pkl'), 'w')
        pickle.dump(column_lists, column_lists_f, pickle.HIGHEST_PROTOCOL)
        column_lists_f.close()

    def write_row_lists(self, tablename, row_lists):
        row_lists_f = open(os.path.join(self.data_dir, tablename, 'row_lists.pkl'), 'w')
        pickle.dump(row_lists, row_lists_f, pickle.HIGHEST_PROTOCOL)
        row_lists_f.close()
        
    def drop_btable(self, tablename):
        """Delete a single btable."""
        if tablename in self.btable_index:
            shutil.rmtree(os.path.join(self.data_dir, tablename))
            self.remove_btable_from_index(tablename)
        return 0
        
    def list_btables(self):
        """Return a list of all btable names."""
        return self.btable_index

    def drop_models(self, tablename, model_ids='all'):
        """ Delete a single model, or all, if model_ids == 'all' or None. """
        models_dir = os.path.join(self.data_dir, tablename, 'models')
        if os.path.exists(models_dir):
            if model_ids is None or model_ids == 'all':
                fnames = os.listdir(models_dir)
                for fname in fnames:
                    if 'model_' in fname:
                        os.remove(os.path.join(models_dir, fname))
            else:
                for modelid in model_ids:
                    fname = os.path.join(models_dir, 'model_%d.pkl' % modelid)
                    if os.path.exists(fname):
                        os.remove(fname)
        else:
            # If models in old style, convert to new style, save, and retry.
            models = self.get_models(tablename)
            self.write_models(tablename, models)
            self.drop_models(tablename, model_ids)

            
    def get_latent_states(self, tablename, modelid=None):
        """Return X_L_list, X_D_list, and M_c"""
        metadata = self.get_metadata(tablename)
        models = self.get_models(tablename, modelid)
        if None in models.values():
            raise utils.BayesDBError('Invalid model id. Use "SHOW MODELS FOR <btable>" to see valid model ids.')
        M_c = metadata['M_c']
        X_L_list = [model['X_L'] for model in models.values()]
        X_D_list = [model['X_D'] for model in models.values()]
        return (X_L_list, X_D_list, M_c)
        
    def get_metadata_and_table(self, tablename):
        """Return M_c and M_r and T"""
        metadata = self.get_metadata(tablename)
        M_c = metadata['M_c']
        M_r = metadata['M_r']
        T = metadata['T']
        return M_c, M_r, T

    def has_models(self, tablename):
        return self.get_max_model_id(tablename) != -1

    def get_max_model_id(self, tablename, models=None):
        """Get the highest model id, and -1 if there are no models.
        Model indexing starts at 0 when models exist."""
        
        if models is not None:
            model_ids = models.keys()
        else:
            models_dir = os.path.join(self.data_dir, tablename, 'models')
            if not os.path.exists(models_dir):
                model_ids = []
            else:
                model_ids = []                
                fnames = os.listdir(models_dir)
                for fname in fnames:
                    model_id = fname[6:] # remove preceding 'model_'
                    model_id = int(model_id[:-4]) # remove trailing '.pkl' and cast to int
                    model_ids.append(model_id)
        if len(model_ids) == 0:
            return -1
        else:
            return max(model_ids)

    def get_cctypes(self, tablename):
        """Access the table's current cctypes."""
        metadata = self.get_metadata(tablename)
        return metadata['cctypes']


    def update_metadata(self, tablename, M_r=None, M_c=None, T=None, cctypes=None):
        """Overwrite M_r, M_c, and T (not cctypes) for the table."""
        metadata = self.get_metadata(tablename)
        if M_r:
            metadata['M_r'] = M_r
        if M_c:
            metadata['M_c'] = M_c
        if T:
            metadata['T'] = T
        if cctypes:
            metadata['cctypes'] = cctypes
        f = open(os.path.join(self.data_dir, tablename, 'metadata.pkl'), 'w')            
        pickle.dump(metadata, f, pickle.HIGHEST_PROTOCOL)
        f.close()

    def update_metadata_full(self, tablename, M_r_full=None, M_c_full=None, T_full=None, cctypes_full=None):
        """Overwrite M_r, M_c, and T (not cctypes) for the table."""
        metadata = self.get_metadata_full(tablename)
        if M_r_full:
            metadata['M_r_full'] = M_r_full
        if M_c_full:
            metadata['M_c_full'] = M_c_full
        if T_full:
            metadata['T_full'] = T_full
        if cctypes_full:
            metadata['cctypes_full'] = cctypes_full
        f = open(os.path.join(self.data_dir, tablename, 'metadata_full.pkl'), 'w')            
        pickle.dump(metadata, f, pickle.HIGHEST_PROTOCOL)
        f.close()
        

    def check_if_table_exists(self, tablename):
        """Return true iff this tablename exists in the persistence layer."""
        return tablename in self.btable_index

    def update_schema(self, tablename, mappings):
        """
        mappings is a dict of column name to 'continuous', 'multinomial', 'ignore', or 'key'.
        TODO: can we get rid of cctypes?
        """
        metadata_full = self.get_metadata_full(tablename)
        cctypes_full = metadata_full['cctypes_full']
        M_c_full = metadata_full['M_c_full']
        raw_T_full = metadata_full['raw_T_full']
        colnames_full = utils.get_all_column_names_in_original_order(M_c_full)

        # Now, update cctypes_full (cctypes updated later, after removing ignores).
        mapping_set = 'continuous', 'multinomial', 'ignore', 'key'
        for col, mapping in mappings.items():
            if col.lower() not in M_c_full['name_to_idx']:
                raise utils.BayesDBError('Error: column %s does not exist.' % col)
            if mapping not in mapping_set:
                raise utils.BayesDBError('Error: datatype %s is not one of the valid datatypes: %s.' % (mapping, str(mapping_set)))
                
            cidx = M_c_full['name_to_idx'][col.lower()]
            cctypes_full[cidx] = mapping

        assert len(filter(lambda x: x=='key', cctypes_full)) <= 1

        if cctypes_full is None:
            cctypes_full = data_utils.guess_column_types(raw_T_full)
        T_full, M_r_full, M_c_full, _ = data_utils.gen_T_and_metadata(colnames_full, raw_T_full, cctypes=cctypes_full)

        # variables without "_full" don't include ignored columns.
        raw_T, cctypes, colnames = data_utils.remove_ignore_cols(raw_T_full, cctypes_full, colnames_full)
        T, M_r, M_c, _ = data_utils.gen_T_and_metadata(colnames, raw_T, cctypes=cctypes)
          

        # Now, put cctypes, T, M_c, and M_r back into the DB
        self.update_metadata(tablename, M_r, M_c, T, cctypes)
        self.update_metadata_full(tablename, M_r_full, M_c_full, T_full, cctypes_full)
        
        return self.get_metadata_full(tablename)
        

    def create_btable(self, tablename, cctypes_full, T, M_r, M_c, T_full, M_r_full, M_c_full, raw_T_full):
        """
        This function is called to create a btable.
        It creates the table's persistence directory, saves data.csv and metadata.pkl.
        Creates models.pkl as empty dict.
        """
        # Make directory for table
        if not os.path.exists(os.path.join(self.data_dir, tablename)):
            os.mkdir(os.path.join(self.data_dir, tablename))        

        # Write metadata and metadata_full
        metadata_full = dict(M_c_full=M_c_full, M_r_full=M_r_full, T_full=T_full, cctypes_full=cctypes_full, raw_T_full=raw_T_full)
        self.write_metadata_full(tablename, metadata_full)
        metadata = dict(M_c=M_c, M_r= M_r, T=T, cctypes=cctypes_full)
        self.write_metadata(tablename, metadata)

        # Write models
        models = {}
        self.write_models(tablename, models)
        
        # Write column labels
        column_labels = dict()
        self.write_column_labels(tablename, column_labels)

        # Write column lists
        column_lists = dict()
        self.write_column_lists(tablename, column_lists)

        # Write row lists
        row_lists = dict()
        self.write_row_lists(tablename, row_lists)

        # Add to btable name index
        self.add_btable_to_index(tablename)


    def add_models(self, tablename, model_list):
        """
        Add a set of models (X_Ls and X_Ds) to a table (the table does not need to
        already have models).
        
        parameter model_list is a list of dicts, where each dict contains the keys
        X_L, X_D, and iterations.
        """
        ## Model indexing starts at 0 (and is -1 if none exist)
        max_model_id = self.get_max_model_id(tablename)
        for i,m in enumerate(model_list):
            modelid = max_model_id + 1 + i
            self.write_model(tablename, m, modelid)

    def update_models(self, tablename, modelids, X_L_list, X_D_list, diagnostics_dict):
        """
        Overwrite all models by id, and append diagnostic info.
        
        param diagnostics_dict: -> dict[f_z[0, D], num_views, logscore, f_z[0, 1], column_crp_alpha]
        Each of the 5 diagnostics is a 2d array, size #models x #iterations

        Ignores f_z[0, D] and f_z[0, 1], since these will need to be recalculated after all
        inference is done in order to properly incorporate all models.
        """
        models = self.get_models(tablename)
        new_iterations = len(diagnostics_dict['logscore'])

        # models: dict[model_idx] -> dict[X_L, X_D, iterations, column_crp_alpha, logscore, num_views]. Idx starting at 1.
        # each diagnostic entry is a list, over iterations.

        # Add all information indexed by model id: X_L, X_D, iterations, column_crp_alpha, logscore, num_views.
        for idx, modelid in enumerate(modelids):
            model_dict = models[modelid]
            model_dict['X_L'] = X_L_list[idx]
            model_dict['X_D'] = X_D_list[idx]
            model_dict['iterations'] = model_dict['iterations'] + new_iterations
            
            for diag_key in 'column_crp_alpha', 'logscore', 'num_views':
                diag_list = [l[idx] for l in diagnostics_dict[diag_key]]
                if diag_key in model_dict and type(model_dict[diag_key]) == list:
                    model_dict[diag_key] += diag_list
                else:
                    model_dict[diag_key] = diag_list

        # Save to disk
        self.write_models(tablename, models)

    def update_model(self, tablename, X_L, X_D, modelid, diagnostics_dict):
        """
        Overwrite a certain model by id.
        Assumes that diagnostics_dict was from an analyze run with only one model.

        param diagnostics_dict: -> dict[f_z[0, D], num_views, logscore, f_z[0, 1], column_crp_alpha]
        Each of the 5 diagnostics is a 2d array, size #models x #iterations

        Ignores f_z[0, D] and f_z[0, 1], since these will need to be recalculated after all
        inference is done in order to properly incorporate all models.

        models: dict[model_idx] -> dict[X_L, X_D, iterations, column_crp_alpha, logscore, num_views]. Idx starting at 1.
        each diagnostic entry is a list, over iterations.

        """
        model = self.get_models(tablename, modelid)

        model['X_L'] = X_L
        model['X_D'] = X_D
        model['iterations'] = model['iterations'] + len(diagnostics_dict['logscore'])

        # Add all information indexed by model id: X_L, X_D, iterations, column_crp_alpha, logscore, num_views.
        for diag_key in 'column_crp_alpha', 'logscore', 'num_views':
            diag_list = [l[idx] for l in diagnostics_dict[diag_key]]
            if diag_key in model_dict and type(model_dict[diag_key]) == list:
                model_dict[diag_key] += diag_list
            else:
                model_dict[diag_key] = diag_list
        
        self.write_model(tablename, model, modelid)

    def get_model_ids(self, tablename):
        """ Receive a list of all model ids for the table. """
        models = self.get_models(tablename)
        return models.keys()
            

########NEW FILE########
__FILENAME__ = plotting_utils
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import numpy as np
import pylab as p
import os
from matplotlib.colors import LogNorm, Normalize
from matplotlib.ticker import MaxNLocator
import matplotlib.gridspec as gs
import matplotlib.cm
import pandas as pd
import numpy
import utils
import functions
import data_utils as du
import math

def turn_off_labels(subplot):
    subplot.axes.get_xaxis().set_visible(False)
    subplot.axes.get_yaxis().set_visible(False)
         

def plot_general_histogram(colnames, data, M_c, filename=None, scatter=False, pairwise=False):
    '''
    colnames: list of column names
    data: list of tuples (first list is a list of rows, so each inner tuples is a row)
    colnames = ['name', 'age'], data = [('bob',37), ('joe', 39),...]
    scatter: False if histogram, True if scatterplot
    '''
    if pairwise:
        gsp = gs.GridSpec(1, 1)
        plots = create_pairwise_plot(colnames, data, M_c, gsp)
    else:
        f, ax = p.subplots()
        create_plot(parse_data_for_hist(colnames, data, M_c), ax, horizontal=True)
    if filename:
        p.savefig(filename)
        p.close()
    else:
        p.show()

def create_plot(parsed_data, subplot, label_x=True, label_y=True, text=None, compress=False, super_compress=False, **kwargs):
    """
    Takes parsed data and a subplot object, and creates a plot of the data on that subplot object.
    """
    if parsed_data['datatype'] == 'mult1D':
        if len(parsed_data['data']) == 0:
            return
        if 'horizontal' in kwargs and kwargs['horizontal']:
            subplot.tick_params(top='off', bottom='off', left='off', right='off')
            subplot.axes.get_yaxis().set_ticks([])
            labels = parsed_data['labels']
            datapoints = parsed_data['data']
            num_vals = len(labels)
            ind = np.arange(num_vals)
            width = .5
            subplot.barh(ind, datapoints, width, color=matplotlib.cm.Blues(0.5), align='center')

            # rotate major label if super compress
            subplot.set_ylabel(parsed_data['axis_label'])                            
            if super_compress:
                rot = 0
            else:
                rot = 90
                #subplot.set_ylabel(parsed_data['axis_label'], rotation=rot)                
            
            if (not compress and len(labels) < 15) or (compress and len(labels) < 5):
                subplot.axes.get_yaxis().set_ticks(range(len(labels)))
                subplot.axes.get_yaxis().set_ticklabels(labels)
            if compress:
                subplot.axes.get_xaxis().set_visible(False)
        else:
            subplot.tick_params(top='off', bottom='off', left='off', right='off')
            subplot.axes.get_xaxis().set_ticks([])
            labels = parsed_data['labels']
            datapoints = parsed_data['data']
            num_vals = len(labels)
            ind = np.arange(num_vals)
            width = .5
            subplot.bar(ind, datapoints, width, color=matplotlib.cm.Blues(0.5), align='center')

            # rotate major label if super compress
            subplot.set_xlabel(parsed_data['axis_label'])                            
            if super_compress:
                rot = 90
            else:
                rot = 0
                #subplot.set_xlabel(parsed_data['axis_label'], rotation=rot)                
            
            if (not compress and len(labels) < 15) or (compress and len(labels) < 5):
                subplot.axes.get_xaxis().set_ticks(range(len(labels)))
                subplot.axes.get_xaxis().set_ticklabels(labels, rotation=50)
            if compress:
                subplot.axes.get_yaxis().set_visible(False)
        
    elif parsed_data['datatype'] == 'cont1D':
        if len(parsed_data['data']) == 0:
            return
        datapoints = parsed_data['data']
        subplot.series = pd.Series(datapoints)
        if 'horizontal' in kwargs and kwargs['horizontal']:
            subplot.series.hist(normed=True, color=matplotlib.cm.Blues(0.5), orientation='horizontal')
            subplot.set_ylabel(parsed_data['axis_label'])
            if compress:
                subplot.axes.get_xaxis().set_visible(False)
                subplot.axes.get_yaxis().set_major_locator(MaxNLocator(nbins = 3))                
        else:
            subplot.series.hist(normed=True, color=matplotlib.cm.Blues(0.5))
            subplot.set_xlabel(parsed_data['axis_label'])
            if compress:
                subplot.axes.get_xaxis().set_major_locator(MaxNLocator(nbins = 3))
                subplot.axes.get_yaxis().set_visible(False)
            else:
                subplot.series.dropna().plot(kind='kde', style='r--')                 

    elif parsed_data['datatype'] == 'contcont':
        if len(parsed_data['data_y']) == 0 or len(parsed_data['data_x']) == 0:
            return
        subplot.hist2d(parsed_data['data_y'], parsed_data['data_x'], bins=max(len(parsed_data['data_x'])/200,40), norm=LogNorm(), cmap=matplotlib.cm.Blues)
        if not compress:
            subplot.set_xlabel(parsed_data['axis_label_x'])
            subplot.set_ylabel(parsed_data['axis_label_y'])
        else:
            turn_off_labels(subplot)
        
    elif parsed_data['datatype'] == 'multmult':
        if len(parsed_data['data']) == 0:
            return
        subplot.tick_params(labelcolor='b', top='off', bottom='off', left='off', right='off')
        subplot.axes.get_xaxis().set_ticks([])
        unique_xs = parsed_data['labels_x']
        unique_ys = parsed_data['labels_y']
        dat = parsed_data['data']
        norm_a = Normalize(vmin=dat.min(), vmax=dat.max()) 
        subplot.imshow(parsed_data['data'],norm=Normalize(), interpolation='nearest',  cmap=matplotlib.cm.Blues, aspect = float(len(unique_xs))/len(unique_ys))

        subplot.axes.get_xaxis().set_ticks(range(len(unique_xs)))
        subplot.axes.get_xaxis().set_ticklabels(unique_xs, rotation=90)
        subplot.axes.get_yaxis().set_ticks(range(len(unique_ys)))
        subplot.axes.get_yaxis().set_ticklabels(unique_ys)
        if not compress:
            subplot.set_xlabel(parsed_data['axis_label_x'])
            subplot.set_ylabel(parsed_data['axis_label_y'])
        else:
            turn_off_labels(subplot)


    elif parsed_data['datatype'] == 'multcont':
        # Multinomial is always first. parsed_data['transpose'] is true if multinomial should be on Y axis.
        values = parsed_data['values']
        groups = parsed_data['groups']
        vert = not parsed_data['transpose']
        subplot.boxplot(values, vert=vert)

        if compress:
            turn_off_labels(subplot)
        else:
            if vert:
                xtickNames = p.setp(subplot, xticklabels=groups)
                p.setp(xtickNames, fontsize=8, rotation=90)
            else:
                p.setp(subplot, yticklabels=groups)

    else:
        raise Exception('Unexpected data type, or too many arguments')

    x0,x1 = subplot.get_xlim()
    y0,y1 = subplot.get_ylim()
    aspect = (abs(float((x1-x0)))/abs(float((y1-y0))))
    subplot.set_aspect(aspect)
    return subplot

def parse_data_for_hist(colnames, data, M_c):
    data_c = []
    for i in data:
        no_nan = True
        for j in i:
            if isinstance(j, float) and math.isnan(j):
                no_nan = False
        if no_nan:
            data_c.append(i)
    output = {}
    columns = colnames[:]
    data_no_id = [] # This will be the data with the row_ids removed if present
    if colnames[0] == 'row_id':
        columns.pop(0)
    if len(data_c) == 0:
        raise utils.BayesDBError('There are no datapoints that contain values from every category specified. Try excluding columns with many NaN values.')
    if len(columns) == 1:
        if colnames[0] == 'row_id':
            data_no_id = [x[1] for x in data_c]
        else:
            data_no_id = [x[0] for x in data_c]
        output['axis_label'] = columns[0]
        output['title'] = columns[0]

        # Allow col_idx to be None, to allow for predictive functions to be plotted.
        if columns[0] in M_c['name_to_idx']:
            col_idx = M_c['name_to_idx'][columns[0]]
        else:
            col_idx = None

        # Treat not-column (e.g. function) the same as continuous, since no code to value conversion.            
        if col_idx is None or M_c['column_metadata'][col_idx]['modeltype'] == 'normal_inverse_gamma':
            output['datatype'] = 'cont1D'
            output['data'] = np.array(data_no_id)
            
        elif M_c['column_metadata'][col_idx]['modeltype'] == 'symmetric_dirichlet_discrete':
            unique_labels = sorted(M_c['column_metadata'][M_c['name_to_idx'][columns[0]]]['code_to_value'].keys())
            np_data = np.array(data_no_id)
            counts = []
            for label in unique_labels:
                counts.append(sum(np_data==str(label)))
            output['datatype'] = 'mult1D'
            output['labels'] = unique_labels
            output['data'] = counts

    elif len(columns) == 2:
        if colnames[0] == 'row_id':
            data_no_id = [(x[1], x[2]) for x in data_c]
        else:
            data_no_id = [(x[0], x[1]) for x in data_c]

        types = []

        # Treat not-column (e.g. function) the same as continuous, since no code to value conversion.
        if columns[0] in M_c['name_to_idx']:
            col_idx_1 = M_c['name_to_idx'][columns[0]]
            types.append(M_c['column_metadata'][col_idx_1]['modeltype'])
        else:
            col_idx_1 = None
            types.append('normal_inverse_gamma')
        if columns[1] in M_c['name_to_idx']:
            col_idx_2 = M_c['name_to_idx'][columns[1]]
            types.append(M_c['column_metadata'][col_idx_2]['modeltype'])            
        else:
            col_idx_2 = None
            types.append('normal_inverse_gamma')            
        types = tuple(types)
        
        output['axis_label_x'] = columns[1]
        output['axis_label_y'] = columns[0]
        output['title'] = columns[0] + ' -versus- ' + columns[1]
 
        if types[0] == 'normal_inverse_gamma' and types[1] == 'normal_inverse_gamma':
            output['datatype'] = 'contcont'
            output['data_x'] = [x[0] for x in data_no_id]
            output['data_y'] = [x[1] for x in data_no_id]

        elif types[0] == 'symmetric_dirichlet_discrete' and types[1] == 'symmetric_dirichlet_discrete':
            counts = {} # keys are (var 1 value, var 2 value)
            # data_no_id is a tuple for each datapoint: (value of var 1, value of var 2)
            for i in data_no_id:
                if i in counts:
                    counts[i]+=1
                else:
                    counts[i]=1

            # these are the values.
            unique_xs = sorted(M_c['column_metadata'][col_idx_2]['code_to_value'].keys())
            unique_ys = sorted(M_c['column_metadata'][col_idx_1]['code_to_value'].keys())
            unique_ys.reverse()#Hack to reverse the y's            
            x_ordered_codes = [du.convert_value_to_code(M_c, col_idx_2, xval) for xval in unique_xs]
            y_ordered_codes = [du.convert_value_to_code(M_c, col_idx_1, yval) for yval in unique_ys]

            # Make count array: indexed by y index, x index
            counts_array = numpy.zeros(shape=(len(unique_ys), len(unique_xs)))
            for i in counts:
                # this converts from value to code
                #import pdb; pdb.set_trace()
                y_index = y_ordered_codes.index(M_c['column_metadata'][col_idx_1]['code_to_value'][i[0]])
                x_index = x_ordered_codes.index(M_c['column_metadata'][col_idx_2]['code_to_value'][i[1]])
                counts_array[y_index][x_index] = float(counts[i])
            output['datatype'] = 'multmult'
            output['data'] = counts_array
            output['labels_x'] = unique_xs
            output['labels_y'] = unique_ys

        elif 'normal_inverse_gamma' in types and 'symmetric_dirichlet_discrete' in types:
            output['datatype'] = 'multcont'
            categories = {}

            col = 0
            type = 1
            if types[0] == 'normal_inverse_gamma':
                type = 0
                col = 1
            
            groups = sorted(M_c['column_metadata'][M_c['name_to_idx'][columns[col]]]['code_to_value'].keys())
            for i in groups:
                categories[i] = []
            for i in data_no_id:
                categories[i[col]].append(i[type])
                
            output['groups'] = groups
            output['values'] = [categories[x] for x in groups]
            output['transpose'] = (type == 1)

    else:
        output['datatype'] = None
    return output

def create_pairwise_plot(colnames, data, M_c, gsp):
    output = {}
    columns = colnames[:]
    data_no_id = [] #This will be the data with the row_ids removed if present
    if colnames[0] == 'row_id':
        columns.pop(0)
        data_no_id = [x[1:] for x in data]
    else:
        data_no_id = data[:]

    super_compress=len(columns) > 6 # rotate outer labels
    gsp = gs.GridSpec(len(columns), len(columns))
    for i in range(len(columns)):
        for j in range(len(columns)):
            if j == 0 and i < len(columns) - 1:
                #left hand marginals
                sub_colnames = [columns[i]]
                sub_data = [[x[i]] for x in data_no_id]
                data = parse_data_for_hist(sub_colnames, sub_data, M_c)
                create_plot(data, p.subplot(gsp[i, j], adjustable='box', aspect=1), False, False, columns[i], horizontal=True, compress=True, super_compress=super_compress)
                
            elif i == len(columns) - 1 and j > 0:
                #bottom marginals
                subdata = None
                if j == 1:
                    sub_colnames = [columns[len(columns)-1]]
                    sub_data = [[x[len(columns) - 1]] for x in data_no_id]
                else:
                    sub_colnames = [columns[j-2]]
                    sub_data = [[x[j-2]] for x in data_no_id]
                data = parse_data_for_hist(sub_colnames, sub_data, M_c)
                create_plot(data, p.subplot(gsp[i, j], adjustable='box', aspect=1), False, False, columns[j-2], horizontal=False, compress=True, super_compress=super_compress)

            elif (j != 0 and i != len(columns)-1) and j < i+2:
                #pairwise joints
                j_col = j-2
                if j == 1:
                    j_col = len(columns) - 1
                sub_colnames = [columns[i], columns[j_col]]
                sub_data = [[x[i], x[j_col]] for x in data_no_id]
                data = parse_data_for_hist(sub_colnames, sub_data, M_c)
                create_plot(data, p.subplot(gsp[i, j]), False, False, horizontal=True, compress=True, super_compress=super_compress)
            else:
                pass

def plot_matrix(matrix, column_names, title='', filename=None):
    # actually create figure
    fig = p.figure()
    fig.set_size_inches(16, 12)
    p.imshow(matrix, interpolation='none',
                 cmap=matplotlib.cm.Blues, vmin=0, vmax=1)
    p.colorbar()
    p.gca().set_yticks(range(len(column_names)))
    p.gca().set_yticklabels(column_names, size='small')
    p.gca().set_xticks(range(len(column_names)))
    p.gca().set_xticklabels(column_names, rotation=90, size='small')
    p.title(title)
    if filename:
        p.savefig(filename)
    else:
        fig.show()



def _create_histogram(M_c, data, columns, mc_col_indices, filename):
  dir=S.path.web_resources_data_dir
  full_filename = os.path.join(dir, filename)
  num_rows = data.shape[0]
  num_cols = data.shape[1]
  #
  p.figure()
  # col_i goes from 0 to number of predicted columns
  # mc_col_idx is the original column's index in M_c
  for col_i in range(num_cols):
    mc_col_idx = mc_col_indices[col_i]
    data_i = data[:, col_i]
    ax = p.subplot(1, num_cols, col_i, title=columns[col_i])
    if M_c['column_metadata'][mc_col_idx]['modeltype'] == 'normal_inverse_gamma':
      p.hist(data_i, orientation='horizontal')
    else:
      str_data = [du.convert_code_to_value(M_c, mc_col_idx, code) for code in data_i]
      unique_labels = list(set(str_data))
      np_str_data = np.array(str_data)
      counts = []
      for label in unique_labels:
        counts.append(sum(np_str_data==label))
      num_vals = len(M_c['column_metadata'][mc_col_idx]['code_to_value'])
      rects = p.barh(range(num_vals), counts)
      heights = np.array([rect.get_height() for rect in rects])
      ax.set_yticks(np.arange(num_vals) + heights/2)
      ax.set_yticklabels(unique_labels)
  p.tight_layout()
  p.savefig(full_filename)

########NEW FILE########
__FILENAME__ = pyparser
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

from pyparsing import Literal, CaselessLiteral, Word, Upcase, delimitedList, Optional,\
    Combine, Group, alphas, nums, alphanums, ParseException, Forward, oneOf, quotedString,\
    ZeroOrMore, OneOrMore, restOfLine, Keyword

selectStatement = Forward()

identifier = Word(alphas, alphanums + "_")


selectToken = Keyword("select", caseless=True)
fromToken = Keyword("from", caseless=True)
orderByToken = Keyword("order", caseless=True) + Keyword("by", caseless=True)
limitToken = Keyword("limit", caseless=True)

columnNameList = Group(delimitedList(identifier | '*'))

createBtableStatement = Keyword("create", caseless=True) + Keyword("btable", caseless=True) + \
                        identifier.setResultsName("tablename") + fromToken + identifier.setResultsName("filename")

#orderByClause = orderByToken + 

selectStatement << ( selectToken +
                     columnNameList.setResultsName("columns") +
                     fromToken +
                     identifier.setResultsName("tablename") +
                     Optional(whereClause) +
                     Optional(orderByClause) +
                     Optional(limitClause) )

BQLStatement = (selectStatement | createBtableStatement) + Optional(';')

BQL = ZeroOrMore(BQLStatement)

## allows comments
dashComment = "--" + restOfLine
BQL.ignore(dashComment)



def test( str ):
    print str,"->"
    try:
        tokens = BQL.parseString( str )
        print "tokens = ",        tokens
        print "tokens.tablename =", tokens.tablename
        print "tokens.filename =",  tokens.filename
        #print "tokens.where =", tokens.where
    except ParseException, err:
        print " "*err.loc + "^\n" + err.msg
        print err
    print


class PyParser(object):
    def __init__(self):
        pass

    def parse(self, bql_string):
        pass

    def parse_line(self, bql_string):
        pass

########NEW FILE########
__FILENAME__ = select_utils
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import re
import utils
import numpy
import os
import pylab
import matplotlib.cm
import inspect
import operator
import ast
import string

import utils
import functions
import data_utils as du
from pyparsing import *
import bayesdb.bql_grammar as bql_grammar

def get_conditions_from_whereclause(whereclause, M_c, T, column_lists):
  whereclause = "WHERE " + whereclause # Temporary while partially switched to pyparsing
  if whereclause == "WHERE ":
    return ""
  ## Create conds: the list of conditions in the whereclause.
  ## List of (c_idx, op, val) tuples.
  conds = list() 
  operator_map = {'<=': operator.le, '<': operator.lt, '=': operator.eq, '>': operator.gt, '>=': operator.ge, 'in': operator.contains}
  try:
    top_level_parse = bql_grammar.where_clause.parseString(whereclause,parseAll=True)
  except ParseException as x:
    
    raise utils.BayesDBParseError("Invalid where clause argument: could not parse '%s'" % whereclause)
  for inner_element in top_level_parse.where_conditions:
    if inner_element.confidence != '':
      confidence = inner_element.confidence
    else:
      confidence = None
    ## simple where column = value statement
    if inner_element.operation != '':
      op = operator_map[inner_element.operation]
    raw_val = inner_element.value
    if utils.is_int(raw_val):
      val = int(raw_val)
    elif utils.is_float(raw_val):
      val = float(raw_val)
    else:
      val = raw_val
    if inner_element.function.function_id == 'predictive probability of':
      if M_c['name_to_idx'].has_key(inner_element.function.column):
        column_index = M_c['name_to_idx'][inner_element.function.column]
        conds.append(((functions._predictive_probability,column_index), op, val))
        continue
    elif inner_element.function.function_id == 'typicality':
      conds.append(((functions._row_typicality, True), op, val))
      continue
    elif inner_element.function.function_id == 'similarity to':
      if inner_element.function.row_id == '':
        column_name = inner_element.function.column
        try:
          column_value = int(inner_element.function.column_value)
        except ValueError:
          try:
            column_value = float(inner_element.function.column_value)
          except ValueError:
            column_value = inner_element.function.column_value 
        column_index =  M_c['name_to_idx'][column_name]
        for row_id, T_row in enumerate(T):
          row_values = convert_row_from_codes_to_values(T_row, M_c)
          if row_values[column_index] == column_value:
            target_row_id = row_id
            break
      else: 
        target_row_id = int(inner_element.function.row_id)
      respect_to_clause = inner_element.function.with_respect_to
      target_column_ids = None
      if respect_to_clause != '':
        target_columns = respect_to_clause.column_list
        target_colnames = [colname.strip() for colname in utils.column_string_splitter(','.join(target_columns), M_c, column_lists)]
        utils.check_for_duplicate_columns(target_colnames)
        target_column_ids = [M_c['name_to_idx'][colname] for colname in target_colnames]
      conds.append(((functions._similarity, (target_row_id, target_column_ids)), op, val))
      continue
    elif inner_element.function.function_id == "key in":
      val = inner_element.function.row_list
      op = operator_map['in']
      conds.append(((functions._row_id, None), op, val))
      continue
    elif inner_element.function.column != '':
      colname = inner_element.function.column
      if M_c['name_to_idx'].has_key(colname.lower()):
        if utils.get_cctype_from_M_c(M_c, colname.lower()) != 'continuous':
          val = str(val)## TODO hack, fix with util
        conds.append(((functions._column, M_c['name_to_idx'][colname.lower()]), op, val))
        continue
      raise utils.BayesDBParseError("Invalid where clause argument: could not parse '%s'" % colname)
    raise utils.BayesDBParseError("Invalid where clause argument: could not parse '%s'" % whereclause)
  return conds

def is_row_valid(idx, row, where_conditions, M_c, X_L_list, X_D_list, T, backend, tablename):
  """Helper function that applies WHERE conditions to row, returning True if row satisfies where clause."""
  for ((func, f_args), op, val) in where_conditions:
    where_value = func(f_args, idx, row, M_c, X_L_list, X_D_list, T, backend)    
    if func != functions._row_id:
      if not op(where_value, val):
        return False
    else:
      ## val should be a row list name in this case. look up the row list, and set val to be the list of row indices
      ## in the row list. Throws BayesDBRowListDoesNotExistError if row list does not exist.
      val = backend.persistence_layer.get_row_list(tablename, val)
      if not op(val, where_value): # for operator.contains, op(a,b) means 'b in a': so need to switch args.
        return False
  return True

def get_queries_from_columnstring(columnstring, M_c, T, column_lists):
    """
    Iterate through the columnstring portion of the input, and generate the query list.
    queries is a list of (query_function, query_args, aggregate) tuples,
    where query_function is: row_id, column, probability, similarity.
    
    For row_id: query_args is ignored (so it is None).
    For column: query_args is a c_idx.
    For probability: query_args is a (c_idx, value) tuple.
    For similarity: query_args is a (target_row_id, target_column) tuple.
    """
    query_colnames = [colname.strip() for colname in utils.column_string_splitter(columnstring, M_c, column_lists)]
    queries = []
    for idx, colname in enumerate(query_colnames):
      #####################
      # Single column functions (aggregate)
      #####################
      c = functions.parse_column_typicality(colname, M_c)
      if c is not None:
        queries.append((functions._col_typicality, c, True))
        continue
        
      m = functions.parse_mutual_information(colname, M_c)
      if m is not None:
        queries.append((functions._mutual_information, m, True))
        continue

      d = functions.parse_dependence_probability(colname, M_c)
      if d is not None:
        queries.append((functions._dependence_probability, d, True))
        continue

      c = functions.parse_correlation(colname, M_c)
      if c is not None:
        queries.append((functions._correlation, c, True))
        continue

      p = functions.parse_probability(colname, M_c)
      if p is not None:
        queries.append((functions._probability, p, True))
        continue

      #####################
      ## Normal functions (of a cell)
      ######################
      s = functions.parse_similarity(colname, M_c, T, column_lists)
      if s is not None:
        queries.append((functions._similarity, s, False))
        continue

      t = functions.parse_row_typicality(colname)
      if t is not None:
        queries.append((functions._row_typicality, None, False))
        continue

      p = functions.parse_predictive_probability(colname, M_c)
      if p is not None:
        queries.append((functions._predictive_probability, p, False))
        continue

      ## If none of above query types matched, then this is a normal column query.
      if colname.lower() in M_c['name_to_idx']:
        queries.append((functions._column, M_c['name_to_idx'][colname], False))
        continue

      raise utils.BayesDBParseError("Invalid query argument: could not parse '%s'" % colname)        

    ## Always return row_id as the first column.
    query_colnames = ['row_id'] + query_colnames
    queries = [(functions._row_id, None, False)] + queries
    
    return queries, query_colnames

def convert_row_from_codes_to_values(row, M_c):
  """
  Helper function to convert a row from its 'code' (as it's stored in T) to its 'value'
  (the human-understandable value).
  """
  ret = []
  for cidx, code in enumerate(row): 
    if not numpy.isnan(code) and not code=='nan':
      ret.append(du.convert_code_to_value(M_c, cidx, code))
    else:
      ret.append(code)
  return tuple(ret)

def filter_and_impute_rows(where_conditions, whereclause, T, M_c, X_L_list, X_D_list, engine, query_colnames,
                           impute_confidence, num_impute_samples, tablename):
    """
    impute_confidence: if None, don't impute. otherwise, this is the imput confidence
    Iterate through all rows of T, convert codes to values, filter by all predicates in where clause,
    and fill in imputed values.
    """
    filtered_rows = list()

    if impute_confidence is not None:
      t_array = numpy.array(T, dtype=float)
      infer_colnames = query_colnames[1:] # remove row_id from front of query_columns, so that infer doesn't infer row_id
      query_col_indices = [M_c['name_to_idx'][colname] for colname in infer_colnames]

    for row_id, T_row in enumerate(T):
      row_values = convert_row_from_codes_to_values(T_row, M_c) ## Convert row from codes to values
      if is_row_valid(row_id, row_values, where_conditions, M_c, X_L_list, X_D_list, T, engine, tablename): ## Where clause filtering.
        if impute_confidence is not None:
          ## Determine which values are 'nan', which need to be imputed.
          ## Only impute columns in 'query_colnames'
          for col_id in query_col_indices:
            if numpy.isnan(t_array[row_id, col_id]):
              # Found missing value! Try to fill it in.
              # row_id, col_id is Q. Y is givens: All non-nan values in this row
              Y = [(row_id, cidx, t_array[row_id, cidx]) for cidx in M_c['name_to_idx'].values() \
                   if not numpy.isnan(t_array[row_id, cidx])]
              code = utils.infer(M_c, X_L_list, X_D_list, Y, row_id, col_id, num_impute_samples,
                                 impute_confidence, engine)
              if code is not None:
                # Inferred successfully! Fill in the new value.
                value = du.convert_code_to_value(M_c, col_id, code)
                row_values = list(row_values)
                row_values[col_id] = value
                row_values = tuple(row_values)
        filtered_rows.append((row_id, row_values))
    return filtered_rows

def order_rows(rows, order_by, M_c, X_L_list, X_D_list, T, engine, column_lists):
  """Input: rows are list of (row_id, row_values) tuples."""
  if not order_by:
      return rows
  ## Step 1: get appropriate functions. Examples are 'column' and 'similarity'.
  function_list = list()
  for orderable in order_by:
    assert type(orderable) == tuple and type(orderable[0]) == str and type(orderable[1]) == bool
    raw_orderable_string = orderable[0]
    desc = orderable[1]

    ## function_list is a list of
    ##   (f(args, row_id, data_values, M_c, X_L_list, X_D_list, engine), args, desc)
    
    s = functions.parse_similarity(raw_orderable_string, M_c, T, column_lists)
    if s:
      function_list.append((functions._similarity, s, desc))
      continue

    c = functions.parse_row_typicality(raw_orderable_string)
    if c:
      function_list.append((functions._row_typicality, c, desc))
      continue

    p = functions.parse_predictive_probability(raw_orderable_string, M_c)
    if p is not None:
      function_list.append((functions._predictive_probability, p, desc))
      continue

    if raw_orderable_string.lower() in M_c['name_to_idx']:
      function_list.append((functions._column, M_c['name_to_idx'][raw_orderable_string.lower()], desc))
      continue

    raise utils.BayesDBParseError("Invalid query argument: could not parse '%s'" % raw_orderable_string)

  ## Step 2: call order by.
  rows = _order_by(rows, function_list, M_c, X_L_list, X_D_list, T, engine)
  return rows

def _order_by(filtered_values, function_list, M_c, X_L_list, X_D_list, T, engine):
  """
  Return the original data tuples, but sorted by the given functions.
  The data_tuples must contain all __original__ data because you can order by
  data that won't end up in the final result set.
  """
  if len(filtered_values) == 0 or not function_list:
    return filtered_values

  scored_data_tuples = list() ## Entries are (score, data_tuple)
  for row_id, data_tuple in filtered_values:
    ## Apply each function to each data_tuple to get a #functions-length tuple of scores.
    scores = []
    for (f, args, desc) in function_list:
      score = f(args, row_id, data_tuple, M_c, X_L_list, X_D_list, T, engine)
      if desc:
        score *= -1
      scores.append(score)
    scored_data_tuples.append((tuple(scores), (row_id, data_tuple)))
  scored_data_tuples.sort(key=lambda tup: tup[0], reverse=False)

  return [tup[1] for tup in scored_data_tuples]


def compute_result_and_limit(rows, limit, queries, M_c, X_L_list, X_D_list, T, engine):
  data = []
  row_count = 0

  # Compute aggregate functions just once, then cache them.
  aggregate_cache = dict()
  for query_idx, (query_function, query_args, aggregate) in enumerate(queries):
    if aggregate:
      aggregate_cache[query_idx] = query_function(query_args, None, None, M_c, X_L_list, X_D_list, T, engine)

  # Only return one row if all aggregate functions (row_id will never be aggregate, so subtract 1 and don't return it).
  assert queries[0][0] == functions._row_id
  if len(aggregate_cache) == len(queries) - 1:
    limit = 1

  # Iterate through data table, calling each query_function to fill in the output values.
  for row_id, row_values in rows:
    ret_row = []
    for query_idx, (query_function, query_args, aggregate) in enumerate(queries):
      if aggregate:
        ret_row.append(aggregate_cache[query_idx])
      else:
        ret_row.append(query_function(query_args, row_id, row_values, M_c, X_L_list, X_D_list, T, engine))
    data.append(tuple(ret_row))
    row_count += 1
    if row_count >= limit:
      break
  return data

########NEW FILE########
__FILENAME__ = settings
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

#!python
import os


class path():
    user_home_dir = os.environ['HOME']
    if 'WORKSPACE' in os.environ:
        user_home_dir = os.environ['WORKSPACE']
    # target installation for deployment
    remote_code_dir = os.path.join('/home/sgeadmin', 'tabular_predDB')
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
    postgres_setup_script = os.path.join(install_script_dir, 'postgres_setup.sh')
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
    repo_suffix = 'mit-probabilistic-computing-project/tabular-predDB.git'
    repo = repo_prefix + repo_suffix
    branch = 'master'

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


project_name = 'bayesdb'
#
repo_url = 'https://github.com/mit-probabilistic-computing-project/%s.git' % project_name
get_repo_dir = lambda user: os.path.join('/home', user, project_name)
get_setup_script = lambda user: os.path.join(get_repo_dir(user), 'setup.py')


class bayesdbSetup(ClusterSetup):

    def __init__(self):
        # TODO: Could be generalized to "install a python package plugin"
        pass

    def run(self, nodes, master, user, user_shell, volumes):
        # set up some paths
        repo_dir = get_repo_dir(user)
        setup_script = get_setup_script(user)
        for node in nodes:
            # NOTE: nodes includes master
            log.info("Installing %s as root on %s" % (project_name, node.alias))
            #
            cmd_strs = [
                # FIXME: do this somewhere else
                'pip install pyparsing==2.0.1',
                'pip install patsy',
                'pip install statsmodels',
                'rm -rf %s' % repo_dir,
                'git clone %s %s' % (repo_url, repo_dir),
                'python %s develop' % setup_script,
                # 'python %s build_ext --inplace' % setup_script,
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
__FILENAME__ = test_client
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import time
import inspect
import pickle
import os
import numpy
import pytest
import random
import shutil
import pandas

import bayesdb.utils as utils
from bayesdb.client import Client
from bayesdb.engine import Engine

test_tablenames = None
client = None
test_filenames = None

def setup_function(function):
  global test_tablenames, client, test_filenames
  test_tablenames = []
  test_filenames = []
  client = Client()

def teardown_function(function):
  global tablename, client
  for test_tablename in test_tablenames:
    client.engine.drop_btable(test_tablename)

  for test_filename in test_filenames:
    if os.path.exists(test_filename):
        os.remove(test_filename)

def create_dha(path='data/dha.csv'):
  test_tablename = 'dhatest' + str(int(time.time() * 1000000)) + str(int(random.random()*10000000))
  csv_file_contents = open(path, 'r').read()
  client('create btable %s from %s' % (test_tablename, path), debug=True, pretty=False)
  
  global test_tablenames
  test_tablenames.append(test_tablename)
  
  return test_tablename

def test_drop_btable():
  """
  Test to make sure drop btable prompts the user for confirmation, and responds appropriately when
  given certain input.
  """
  import sys
  from cStringIO import StringIO

  # setup the environment
  backup = sys.stdout
  sys.stdout = StringIO()     # capture output

  # TODO

  
  out = sys.stdout.getvalue() # release output
  sys.stdout.close()  # close the stream 
  sys.stdout = backup # restore original stdout


def test_btable_list():
  global client, test_filenames

  out = set(client('list btables', pretty=False, debug=True)[0]['btable'])
  init_btable_count = len(out)
  
  test_tablename1 = create_dha()

  out = set(client('list btables', pretty=False, debug=True)[0]['btable'])
  assert len(out) == 1 + init_btable_count
  assert test_tablename1 in out
  
  test_tablename2 = create_dha()

  out = set(client('list btables', pretty=False, debug=True)[0]['btable'])
  assert len(out) == 2 + init_btable_count
  assert test_tablename1 in out
  assert test_tablename2 in out

  client('drop btable %s' % test_tablename1, yes=True, debug=True, pretty=False)
  
  out = set(client('list btables', pretty=False, debug=True)[0]['btable'])
  assert len(out) == 1 + init_btable_count
  assert test_tablename1 not in out
  assert test_tablename2 in out

  ## test to make sure btable list is persisted
  del client
  client = Client()
  
  out = set(client('list btables', pretty=False, debug=True)[0]['btable'])
  assert len(out) == 1 + init_btable_count
  assert test_tablename1 not in out
  assert test_tablename2 in out
  
    
def test_save_and_load_models():
  test_tablename1 = create_dha()
  test_tablename2 = create_dha()
  global client, test_filenames
  client('initialize 2 models for %s' % (test_tablename1), debug=True, pretty=False)
  #client('analyze %s for 1 iteration' % (test_tablename1), debug=True, pretty=False)
  pkl_path = 'test_models.pkl.gz'
  test_filenames.append(pkl_path)
  client('save models for %s to %s' % (test_tablename1, pkl_path), debug=True, pretty=False)
  original_models = client.engine.save_models(test_tablename1)
  
  client('load models %s for %s' % (pkl_path, test_tablename2), debug=True, pretty=False)
  new_models = client.engine.save_models(test_tablename1)         

  assert new_models.values() == original_models.values()

def test_column_lists():
  """ smoke test """
  test_tablename = create_dha()
  global client, test_filenames
  client('initialize 2 models for %s' % (test_tablename), debug=True, pretty=False)

  cname1 = 'cname1'
  cname2 = 'cname2'
  client('show column lists for %s' % test_tablename, debug=True, pretty=False)
  client('estimate columns from %s as %s' % (test_tablename, cname1), debug=True, pretty=False)
  client('show column lists for %s' % test_tablename, debug=True, pretty=False)
  client('show columns %s from %s' % (cname1, test_tablename), debug=True, pretty=False)
  with pytest.raises(utils.BayesDBColumnListDoesNotExistError):  
    client('show columns %s from %s' % (cname2, test_tablename), debug=True, pretty=False)  
  client('estimate columns from %s order by typicality limit 5 as %s' % (test_tablename, cname1), debug=True, pretty=False)
  client('estimate columns from %s limit 5 as %s' % (test_tablename, cname2), debug=True, pretty=False)  
  client('show column lists for %s' % test_tablename, debug=True, pretty=False)
  client('show columns %s from %s' % (cname1, test_tablename), debug=True, pretty=False)
  client('show columns %s from %s' % (cname2, test_tablename), debug=True, pretty=False)

  tmp = 'asdf_test.png'
  test_filenames.append(tmp)
  if os.path.exists(tmp):
    os.remove(tmp)
  client('estimate pairwise dependence probability from %s for columns %s save to %s' % (test_tablename, cname1, tmp), debug=True, pretty=False)
  assert os.path.exists(tmp)

  client('estimate pairwise dependence probability from %s for columns %s' % (test_tablename, cname2), debug=True, pretty=False)

  client('select %s from %s limit 10' % (cname1, test_tablename), debug=True, pretty=False)
  client('select %s from %s limit 10' % (cname2, test_tablename), debug=True, pretty=False)

  client('infer %s from %s with confidence 0.1 limit 10' % (cname1, test_tablename), debug=True, pretty=False)
  client('infer %s from %s with confidence 0.1 limit 10' % (cname2, test_tablename), debug=True, pretty=False)

  client('simulate %s from %s times 10' % (cname1, test_tablename), debug=True, pretty=False)  
  client('simulate %s from %s times 10' % (cname2, test_tablename), debug=True, pretty=False)

def test_simulate():
  """ smoke test """
  test_tablename = create_dha()
  global client, test_filenames
  client('initialize 2 models for %s' % (test_tablename), debug=True, pretty=False)

  assert len(client("simulate qual_score from %s given name='Albany NY' times 5" % test_tablename, debug=True, pretty=False)[0]) == 5
  assert len(client("simulate qual_score from %s given name='Albany NY' and ami_score = 80 times 5" % test_tablename, debug=True, pretty=False)[0]) == 5

  assert len(client("simulate name from %s given name='Albany NY' and ami_score = 80 times 5" % test_tablename, debug=True, pretty=False)[0]) == 5
  assert len(client("simulate name from %s given name='Albany NY', ami_score = 80 times 5" % test_tablename, debug=True, pretty=False)[0]) == 5
  assert len(client("simulate name from %s given name='Albany NY' AND ami_score = 80 times 5" % test_tablename, debug=True, pretty=False)[0]) == 5
  assert len(client("simulate name from %s given ami_score = 80 times 5" % test_tablename, debug=True, pretty=False)[0]) == 5

def test_estimate_columns():
  """ smoke test """
  test_tablename = create_dha()
  global client, test_filenames
  client('initialize 2 models for %s' % (test_tablename), debug=True, pretty=False)

#  client('estimate columns from %s' % test_tablename, debug=True, pretty=False)

  client('estimate columns from %s where typicality > 1' % test_tablename, debug=True, pretty=False)  
  client('estimate columns from %s where typicality > 0' % test_tablename, debug=True, pretty=False)
  client('estimate columns from %s where typicality > 0 order by typicality' % test_tablename, debug=True, pretty=False)
#  client('estimate columns from %s order by typicality limit 5' % test_tablename, debug=True, pretty=False)

  client('estimate columns from %s where dependence probability with qual_score > 0' % test_tablename, debug=True, pretty=False)
  client('estimate columns from %s order by dependence probability with qual_score' % test_tablename, debug=True, pretty=False)
  client('estimate columns from %s order by dependence probability with qual_score limit 5' % test_tablename, debug=True, pretty=False)

  client('estimate columns from %s order by correlation with qual_score limit 5' % test_tablename, debug=True, pretty=False)
  client('estimate columns from %s where correlation with qual_score > 0 order by correlation with qual_score limit 5' % test_tablename, debug=True, pretty=False)  

  client('estimate columns from %s order by mutual information with qual_score limit 5' % test_tablename, debug=True, pretty=False)
  client('estimate columns from %s where mutual information with qual_score > 1 order by typicality' % test_tablename, debug=True, pretty=False)

def test_row_clusters():
  """ smoke test """
  test_tablename = create_dha()
  global client, test_filenames
  client('initialize 2 models for %s' % (test_tablename), debug=True, pretty=False)
  row_lists = client('show row lists for %s' % test_tablename, debug=True, pretty=False)[0]['row_lists']
  assert len(row_lists) == 0
  client('estimate pairwise row similarity from %s save connected components with threshold 0.1 as rcc' % test_tablename, debug=True, pretty=False)
  row_lists = client('show row lists for %s' % test_tablename, debug=True, pretty=False)[0]['row_lists']
  assert len(row_lists) > 0
  client('select * from %s where key in rcc_0' % test_tablename, debug=True, pretty=False)
  #client("select * from %s where similarity to name='McAllen TX' > 0.5 order by similarity to name='McAllen TX' as mcallenrows" % test_tablename, debug=True, pretty=False)
  #client('select * from %s where key in mcallenrows' % test_tablename, debug=True, pretty=False)

def test_select_whereclause_functions():
  """ smoke test """
  test_tablename = create_dha()
  global client, test_filenames
  client('initialize 2 models for %s' % (test_tablename), debug=True, pretty=False)

  # similarity
  client('select name from %s where similarity to 0 > 0' % (test_tablename), debug=True, pretty=False)
  client('select name from %s where similarity to 0 = 0 order by similarity to 0' % (test_tablename), debug=True, pretty=False)      
  client('select name from %s where similarity to 1 with respect to qual_score > 0.01' % (test_tablename), debug=True, pretty=False)
  client('select name from %s where similarity to 1 with respect to qual_score, ami_score > 0.01' % (test_tablename), debug=True, pretty=False)  

  # row typicality
  client('select * from %s where typicality > 0.04' % (test_tablename), debug=True, pretty=False)
  client('select *, typicality from %s where typicality > 0.06' % (test_tablename), debug=True, pretty=False)  

  # predictive probability
  client("select qual_score from %s where predictive probability of qual_score > 0.01" % (test_tablename), debug=True, pretty=False)
  client("select qual_score from %s where predictive probability of name > 0.01" % (test_tablename), debug=True, pretty=False)
  
  # probability: aggregate, shouldn't work
  with pytest.raises(utils.BayesDBError):  
    client('select qual_score from %s where probability of qual_score = 6 > 0.01' % (test_tablename), debug=True, pretty=False)
  with pytest.raises(utils.BayesDBError):      
    client("select qual_score from %s where probability of name='Albany NY' > 0.01" % (test_tablename), debug=True, pretty=False)  

def test_model_config():
  test_tablename = create_dha()
  global client, test_filenames

  # test naive bayes
  client('initialize 2 models for %s with config naive bayes' % (test_tablename), debug=True, pretty=False)
  client('analyze %s for 2 iterations' % (test_tablename), debug=True, pretty=False)
  dep_mat = client('estimate pairwise dependence probability from %s' % test_tablename, debug=True, pretty=False)[0]['matrix']
  ## assert that all dependencies are _0_ (not 1, because there should only be 1 view and 1 cluster!)
  ## except the diagonal, where we've hardcoded every column to be dependent with itself
  assert numpy.all(dep_mat == numpy.identity(dep_mat.shape[0]))

  # test crp
  client('drop models for %s' % test_tablename, yes=True, debug=True, pretty=False)
  client('initialize 2 models for %s with config crp mixture' % (test_tablename), debug=True, pretty=False)
  client('analyze %s for 2 iterations' % (test_tablename), debug=True, pretty=False)
  dep_mat = client('estimate pairwise dependence probability from %s' % test_tablename, debug=True, pretty=False)[0]['matrix']
  ## assert that all dependencies are 1 (because there's 1 view, and many clusters)
  ## (with _very_ low probability, this test may fail due to bad luck)
  assert numpy.all(dep_mat == 1)

  # test crosscat
  client('drop models for %s' % test_tablename, yes=True, debug=True, pretty=False)
  client('initialize 2 models for %s' % (test_tablename), debug=True, pretty=False)
  client('analyze %s for 2 iterations' % (test_tablename), debug=True, pretty=False)
  dep_mat = client('estimate pairwise dependence probability from %s' % test_tablename, debug=True, pretty=False)[0]['matrix']
  ## assert that all dependencies are not all the same
  assert (not numpy.all(dep_mat == 1)) and (not numpy.all(dep_mat == 0))

  # test that you can't change model config
  with pytest.raises(utils.BayesDBError):
    client.engine.initialize_models(test_tablename, 2, 'crp mixture')

def test_using_models():
  """ smoke test """
  test_tablename = create_dha(path='data/dha_missing.csv')  
  global client, test_filenames
  client('initialize 3 models for %s' % (test_tablename), debug=True, pretty=False)

  client('select name from %s using model 1' % test_tablename, debug=True, pretty=False)
  with pytest.raises(utils.BayesDBError):
    client('infer name from %s with confidence 0.1 using models 3' % test_tablename, debug=True, pretty=False)
  with pytest.raises(utils.BayesDBError):    
    client("simulate qual_score from %s given name='Albany NY' times 5 using models 3" % test_tablename, debug=True, pretty=False)    
  with pytest.raises(utils.BayesDBError):    
    client('infer name from %s with confidence 0.1 using models 0-3' % test_tablename, debug=True, pretty=False)

  client('infer name from %s with confidence 0.1 limit 10 using models 2' % test_tablename, debug=True, pretty=False)
  client("simulate qual_score from %s given name='Albany NY' times 5 using models 1-2" % test_tablename, debug=True, pretty=False)
  client('estimate columns from %s limit 5 using models 1-2' % test_tablename, debug=True, pretty=False)
  client('estimate pairwise dependence probability from %s using models 1' % (test_tablename), debug=True, pretty=False)
  client('estimate pairwise row similarity from %s save connected components with threshold 0.1 as rcc using models 1-2' % test_tablename, debug=True, pretty=False)

  client('drop model 0 from %s' % test_tablename, debug=True, pretty=False, yes=True)
  with pytest.raises(utils.BayesDBError):
    client('infer name from %s with confidence 0.1 limit 10 using models 0-2' % test_tablename, debug=True, pretty=False)    
  
def test_select():
  """ smoke test """
  test_tablename = create_dha()
  global client, test_filenames
  client('initialize 2 models for %s' % (test_tablename), debug=True, pretty=False)

  client('select name, qual_score from %s' % (test_tablename), debug=True, pretty=False)
  client('select name, qual_score from %s limit 10' % (test_tablename), debug=True, pretty=False)
  client('select name, qual_score from %s order by qual_score limit 10' % (test_tablename), debug=True, pretty=False)
  client('select name, qual_score from %s order by qual_score ASC limit 10' % (test_tablename), debug=True, pretty=False)
  client('select name, qual_score from %s order by qual_score DESC limit 10' % (test_tablename), debug=True, pretty=False)
  client('select * from %s order by qual_score DESC limit 10' % (test_tablename), debug=True, pretty=False)
  client('select name, qual_score from %s where qual_score > 6' % (test_tablename), debug=True, pretty=False)
  client('select * from %s where qual_score > 6' % (test_tablename), debug=True, pretty=False)
  client("select * from %s where qual_score > 80 and name = 'Albany NY'" % (test_tablename), debug=True, pretty=False)
  client("select * from %s where qual_score > 80 and ami_score > 85" % (test_tablename), debug=True, pretty=False)    

  # create a column list to be used in future queries
  client('estimate columns from %s limit 5 as clist' % test_tablename, debug=True, pretty=False)    
  # similarity
  client('select name, similarity to 0 from %s' % (test_tablename), debug=True, pretty=False)
  client('select name from %s order by similarity to 0' % (test_tablename), debug=True, pretty=False)      
  client('select name, similarity to 0 from %s order by similarity to 0' % (test_tablename), debug=True, pretty=False)
  client('select name, similarity to 0 with respect to name from %s order by similarity to 1 with respect to qual_score' % (test_tablename), debug=True, pretty=False)        
  client('select name, similarity to 0 from %s order by similarity to 1 with respect to qual_score, ami_score' % (test_tablename), debug=True, pretty=False)
  client('select name, similarity to 0 from %s order by similarity to 1 with respect to clist' % (test_tablename), debug=True, pretty=False)        

  # row typicality
  client('select typicality from %s' % (test_tablename), debug=True, pretty=False)
  client('select *, typicality from %s' % (test_tablename), debug=True, pretty=False)  
  client('select typicality from %s order by typicality limit 10' % (test_tablename), debug=True, pretty=False)

  # probability
  # why is this so slow, when predictive probability is really fast? these are _observed_
  # for qual_score (continuous): probability takes 20 times longer than predictive prob (about 5 seconds total for 300 rows)
  # for name (multinomial): probability takes extremely long (about 75 seconds for 300 rows)
  #  while predictive probability takes under one second for 300 rows
  st = time.time()
  client('select probability of qual_score = 6 from %s' % (test_tablename), debug=True, pretty=False)
  el = time.time() - st
  st = time.time()  
  client("select probability of name='Albany NY' from %s" % (test_tablename), debug=True, pretty=False)
  el2 = time.time() - st

  #client("select name from %s order by probability of name='Albany NY' DESC" % (test_tablename), debug=True, pretty=False)  
  # TODO: test that probability function doesn't get evaluated 2x for each row
  #client("select probability of name='Albany NY' from %s order by probability of name='Albany NY' DESC" % (test_tablename), debug=True, pretty=False)

  # predictive probability
  # these are really fast! :) simple predictive probability, unobserved
  client("select predictive probability of qual_score from %s" % (test_tablename), debug=True, pretty=False)
  client("select predictive probability of name from %s" % (test_tablename), debug=True, pretty=False)
  client("select predictive probability of qual_score from %s order by predictive probability of name" % (test_tablename), debug=True, pretty=False)
  client("select predictive probability of qual_score from %s order by predictive probability of qual_score" % (test_tablename), debug=True, pretty=False)

  ## Aggregate functions: can't order by these.

  # mutual information
  client("select name, qual_score, mutual information of name with qual_score from %s" % (test_tablename), debug=True, pretty=False)

  # dependence probability
  client("select dependence probability of name with qual_score from %s" % (test_tablename), debug=True, pretty=False)
  client("select name, qual_score, dependence probability of name with qual_score from %s" % (test_tablename), debug=True, pretty=False)

  # correlation
  client("select name, qual_score, correlation of name with qual_score from %s" % (test_tablename), debug=True, pretty=False)

  # column typicality
  client("select typicality of qual_score, typicality of name from %s" % (test_tablename), debug=True, pretty=False)
  client("select typicality of qual_score from %s" % (test_tablename), debug=True, pretty=False)

  # correlation with missing values
  test_tablename = create_dha(path='data/dha_missing.csv')
  client("select name, qual_score, correlation of name with qual_score from %s" % (test_tablename), debug=True, pretty=False)

def test_pandas():
  test_tablename = create_dha()
  global client

  # Test that output is a dict if pretty=False and pandas_output=False
  out = client("select name, qual_score from %s limit 10" % (test_tablename), debug=True, pretty=False, pandas_output=False)
  assert type(out[0]) == dict

  # Test that output is pandas DataFrame when pretty=False and a table-like object is returned (pandas_output=True by default)
  out = client("select name, qual_score from %s limit 10" % (test_tablename), debug=True, pretty=False)
  assert type(out[0]) == pandas.DataFrame

  # Test that it still works when no rows are returned
  client("select name, qual_score from %s where qual_score < 0" % (test_tablename), debug=True, pretty=False)

  # Get the returned data frame from the first list element of the previous result.
  test_df = out[0]

  # Test creation of a btable from pandas DataFrame
  client("drop btable %s" % (test_tablename), yes=True)
  client("create btable %s from pandas" % (test_tablename), debug=True, pretty=False, pandas_df=test_df)

def test_summarize():
  test_tablename = create_dha()
  global client

  # Test that the output is a pandas DataFrame when pretty=False
  out = client('summarize select name, qual_score from %s' % (test_tablename), debug=True, pretty=False)[0]
  assert type(out) == pandas.DataFrame

  # Test that stats from summary_describe and summary_freqs made it into the output DataFrame
  # Note that all of these stats won't be present in EVERY summarize output, but all should be in the output
  # from the previous test.
  expected_indices = ['type', 'count', 'unique', 'mean', 'std', 'min', '25%', '50%', '75%', 'max', \
    'mode1', 'mode2', 'mode3', 'mode4', 'mode5', \
    'prob_mode1', 'prob_mode2', 'prob_mode3', 'prob_mode4', 'prob_mode5']
  assert all([x in list(out[' ']) for x in expected_indices])

  # Test that it works on columns of predictive functions.
  client('initialize 2 models for %s' % (test_tablename), debug=True, pretty=False)
  client('summarize select correlation of name with qual_score from %s' % (test_tablename), debug=True, pretty=False)

  # Test with fewer than 5 unique values (output should have fewer rows)
  client('summarize select name, qual_score from %s limit 3' % (test_tablename), debug=True, pretty=False)

  # Test with no rows
  client('summarize select name, qual_score from %s where qual_score < 0' % (test_tablename), debug=True, pretty=False)

  # Test with only a discrete column
  client('summarize select name from %s' % (test_tablename), debug=True, pretty=False)

  # Test with only a continuous column
  client('summarize select qual_score from %s' % (test_tablename), debug=True, pretty=False)

  # Test shorthand: summary for all columns in btable - not working yet
  # client('summarize %s' % (test_tablename), debug=True, pretty=False)

def test_select_where_col_equal_val():
  test_tablename = create_dha()
  global client, test_filenames
  client('initialize 2 models for %s' % (test_tablename), debug=True, pretty=False)
  basic_similarity = client('select * from %s where similarity to 1 > .6 limit 5' % (test_tablename),pretty=False, debug=True)[0]['row_id']
  col_val_similarity = client('select * from %s where similarity to name = "Akron OH" > .6 limit 5' % (test_tablename),pretty=False, debug=True)[0]['row_id']
  assert len(basic_similarity) == len(col_val_similarity)

def test_labeling():
  test_tablename = create_dha()
  global client, test_filenames

  client('label columns for %s set name = Name of the hospital, qual_score = Overall quality score' % (test_tablename), debug=True, pretty=False)
  client('show labels for %s name, qual_score' % (test_tablename), debug=True, pretty=False)
  client('show labels for %s' % (test_tablename), debug=True, pretty=False)

  # Test getting columns from CSV
  client('label columns for %s from data/dha_labels.csv' % (test_tablename), debug=True, pretty=False)

def test_user_metadata():
  test_tablename = create_dha()
  global client, test_filenames

  client('update metadata for %s set data_source = Dartmouth Atlas of Health, url = http://www.dartmouthatlas.org/tools/downloads.aspx' % (test_tablename), debug=True, pretty=False)
  client('update metadata for %s from data/dha_user_metadata.csv' % (test_tablename), debug=True, pretty=False)

  client('show metadata for %s data_source, url' % (test_tablename), debug=True, pretty=False)

  # Test that show metadata also works when no keys are specified
  client('show metadata for %s' % (test_tablename), debug=True, pretty=False)

########NEW FILE########
__FILENAME__ = test_demos
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import os, sys, pytest
from bayesdb.client import Client

def teardown_function(function):
    for fname in os.listdir('.'):
        if fname[-4] == '.png':
            os.remove(fname)

def run_example(name):
    client = Client()
    file_path = os.path.join('../../examples/%s/%s_analysis.bql' % (name, name))
    results = client(open(file_path, 'r'), yes=True, pretty=False, plots=False)
    for r in results:
        if 'Error' in r or ('error' in r and r['error']):
            raise Exception(str(r))

def test_dha_example():
    run_example('dha')

# ONLY SLOW BECAUSE INFER NEEDS TO BE OPTIMIZED!    
@pytest.mark.slow
def test_gss_example():
    run_example('gss')
    
def test_chicago_small_example():
    run_example('chicago_small')

def test_flights_example():
    run_example('flights')

def test_kiva_example():
    run_example('kiva')

def test_employees_example():
    run_example('employees')
    
    

########NEW FILE########
__FILENAME__ = test_engine
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import time
import inspect
import pickle
import os
import numpy
import pytest
import random

import bayesdb.data_utils as data_utils
from bayesdb.client import Client
from bayesdb.engine import Engine
engine = Engine()

test_tablenames = None

def setup_function(function):
  global test_tablenames
  test_tablenames = []
  global engine
  engine = Engine()

def teardown_function(function):
  global tablename
  for test_tablename in test_tablenames:
    engine.drop_btable(test_tablename)
    
def create_dha(path='data/dha.csv'):
  test_tablename = 'dhatest' + str(int(time.time() * 1000000)) + str(int(random.random()*10000000))
  header, rows = data_utils.read_csv(path)  
  create_btable_result = engine.create_btable(test_tablename, header, rows)
  metadata = engine.persistence_layer.get_metadata(test_tablename)
  
  global test_tablenames
  test_tablenames.append(test_tablename)
  
  return test_tablename, create_btable_result

def test_create_btable():
  test_tablename, create_btable_result = create_dha()
  assert 'columns' in create_btable_result
  assert 'data' in create_btable_result
  assert 'message' in create_btable_result
  assert len(create_btable_result['data'][0]) == 64 ## 64 is number of columns in DHA dataset
  list_btables_result = engine.list_btables()['data']
  assert [test_tablename] in list_btables_result
  engine.drop_btable(test_tablename)

def test_drop_btable():
  test_tablename, _ = create_dha()
  list_btables_result = engine.list_btables()['data']
  assert [test_tablename] in list_btables_result
  engine.drop_btable(test_tablename)
  list_btables_result = engine.list_btables()['data']
  assert [test_tablename] not in list_btables_result

def test_select():
  test_tablename, _ = create_dha()

  # Test a simple query: select two columns, no limit, no order, no where.
  # Check to make sure types of all inputs are correct, etc.
  columnstring = 'name, qual_score'
  whereclause = ''
  limit = float('inf')
  order_by = False
  select_result = engine.select(test_tablename, columnstring, whereclause, limit, order_by, None)
  assert 'columns' in select_result
  assert 'data' in select_result
  assert select_result['columns'] == ['row_id', 'name', 'qual_score']
  ## 307 is the total number of rows in the dataset.
  assert len(select_result['data']) == 307 and len(select_result['data'][0]) == len(select_result['columns'])
  assert type(select_result['data'][0][0]) == int ## type of row_id is int
  t = type(select_result['data'][0][1]) 
  assert (t == unicode) or (t == str) or (t == numpy.string_) ## type of name is unicode or string
  assert type(select_result['data'][0][2]) == float ## type of qual_score is float
  original_select_result = select_result['data']

  ## Test limit: do the same query as before, but limit to 10
  limit = 10
  select_result = engine.select(test_tablename, columnstring, whereclause, limit, order_by, None)
  assert len(select_result['data']) == limit

  ## Test order by single column: desc
  ground_truth_ordered_results = sorted(original_select_result, key=lambda t: t[2], reverse=True)[:10]
  order_by = [('qual_score', True)]
  select_result = engine.select(test_tablename, columnstring, whereclause, limit, order_by, None)
  assert select_result['data'] == ground_truth_ordered_results

  ## Test order by single column: asc
  ground_truth_ordered_results = sorted(original_select_result, key=lambda t: t[2])[:10]
  order_by = [('qual_score', False)]
  select_result = engine.select(test_tablename, columnstring, whereclause, limit, order_by, None)
  assert select_result['data'] == ground_truth_ordered_results

  engine.initialize_models(test_tablename, 2)  
  
  # SIMILARITY TO <row> [WITH RESPECT TO <col>]
  # smoke tests
  columnstring = 'name, qual_score, similarity to 5'
  order_by = [('similarity to 5', True)]
  select_result = engine.select(test_tablename, columnstring, whereclause, limit, order_by, None)

  columnstring = 'name, qual_score, similarity to 5'
  order_by = [('similarity to 5 with respect to qual_score', True)]
  select_result = engine.select(test_tablename, columnstring, whereclause, limit, order_by, None)

  columnstring = 'name, qual_score'
  order_by = [('similarity to 5 with respect to qual_score', True, )]
  select_result = engine.select(test_tablename, columnstring, whereclause, limit, order_by, None)
  
  columnstring = 'name, qual_score, similarity to 5 with respect to name'
  order_by = [('similarity to 5', False)]
  select_result = engine.select(test_tablename, columnstring, whereclause, limit, order_by, None)

  columnstring = "name, qual_score, similarity to (name='Albany NY') with respect to qual_score"
  order_by = [('similarity to 5', False)]
  select_result = engine.select(test_tablename, columnstring, whereclause, limit, order_by, None)

  columnstring = '*'
  whereclause = 'qual_score > 6'
  order_by = [('similarity to 5 with respect to name', True)]
  select_result = engine.select(test_tablename, columnstring, whereclause, limit, order_by, None)

  columnstring = '*'
  # Albany NY's row id is 3
  whereclause = "name='Albany NY'"
  order_by = [('similarity to 5 with respect to name', True)]
  select_result = engine.select(test_tablename, columnstring, whereclause, limit, order_by, None)

  
  # TYPICALITY (of row)
  # smoke tests
  columnstring = 'name, qual_score, typicality'
  order_by = False
  select_result = engine.select(test_tablename, columnstring, whereclause, limit, order_by, None)

  columnstring = 'name, qual_score, typicality'
  order_by = [('typicality', True)]
  select_result = engine.select(test_tablename, columnstring, whereclause, limit, order_by, None)

  # TODO: test all other single-column functions
  # PROBABILITY <col>=<val>
  # PREDICTIVE PROBABILITY

  # TODO: test all single-column aggregate functions
  
  # TYPICALITY OF <col>
  columnstring = 'typicality of name'
  order_by = [('typicality', True)]
  select_result = engine.select(test_tablename, columnstring, whereclause, limit, order_by, None)
  
  # DEPENDENCE PROBABILITY OF <col> WITH <col> #DEPENDENCE PROBABILITY TO <col>
  # MUTUAL INFORMATION OF <col> WITH <col> #MUTUAL INFORMATION WITH <col>
  # CORRELATION OF <col> WITH <col>
  
  # TODO: test ordering by functions

def test_delete_model():
  pass #TODO

def test_update_schema():
  test_tablename, _ = create_dha()
  m_c, m_r, t = engine.persistence_layer.get_metadata_and_table(test_tablename)
  cctypes = engine.persistence_layer.get_cctypes(test_tablename)
  assert cctypes[m_c['name_to_idx']['qual_score']] == 'continuous'
  assert cctypes[m_c['name_to_idx']['name']] == 'multinomial'
  
  mappings = dict(qual_score='multinomial')
  engine.update_schema(test_tablename, mappings)
  cctypes = engine.persistence_layer.get_cctypes(test_tablename)
  assert cctypes[m_c['name_to_idx']['qual_score']] == 'multinomial'
  
  ## Now test that it doesn't allow name to be continuous
  mappings = dict(name='continuous')
  with pytest.raises(ValueError):
    engine.update_schema(test_tablename, mappings)

def test_save_and_load_models():
  test_tablename, _ = create_dha()
  engine.initialize_models(test_tablename, 3)
  engine.analyze(test_tablename, model_indices='all', iterations=1)
  ## note that this won't save the models, since we didn't call this from the client.
  ## engine.save_models actually just turns the models.
  original_models = engine.save_models(test_tablename)
  
  test_tablename2, _ = create_dha()
  engine.load_models(test_tablename2, original_models)
  assert engine.save_models(test_tablename2).values() == original_models.values()

def test_initialize_models():
  test_tablename, _ = create_dha(path='data/dha_missing.csv')     

  engine = Engine(seed=0)
  num_models = 5
  engine.initialize_models(test_tablename, num_models)

  model_ids = engine.persistence_layer.get_model_ids(test_tablename)
  assert sorted(model_ids) == range(num_models)
  for i in range(num_models):
    model = engine.persistence_layer.get_models(test_tablename, i)
    assert model['iterations'] == 0

def test_analyze():
  test_tablename, _ = create_dha()
  num_models = 3
  engine.initialize_models(test_tablename, num_models)

  for it in (1,2):
    engine.analyze(test_tablename, model_indices='all', iterations=1)
    model_ids = engine.persistence_layer.get_model_ids(test_tablename)
    assert sorted(model_ids) == range(num_models)
    for i in range(num_models):
      model = engine.persistence_layer.get_models(test_tablename, i)
      assert model['iterations'] == it      

def test_nan_handling():
  test_tablename1, _ = create_dha(path='data/dha_missing.csv') 
  test_tablename2, _ = create_dha(path='data/dha_missing_nan.csv')
  m1 = engine.persistence_layer.get_metadata(test_tablename1)
  m2 = engine.persistence_layer.get_metadata(test_tablename2)
  assert m1['M_c'] == m2['M_c']
  assert m1['M_r'] == m2['M_r']
  assert m1['cctypes'] == m2['cctypes']
  numpy.testing.assert_equal(numpy.array(m1['T']), numpy.array(m2['T']))

def test_infer():
  ## TODO: whereclauses
  test_tablename, _ = create_dha(path='data/dha_missing.csv')

  ## dha_missing has missing qual_score in first 5 rows, and missing name in rows 6-10.
  engine = Engine(seed=0)
  engine.initialize_models(test_tablename, 20)

  columnstring = 'name, qual_score'
  whereclause = ''
  limit = float('inf')
  order_by = False
  numsamples = 30
  confidence = 0
  infer_result = engine.infer(test_tablename, columnstring, '', confidence, whereclause, limit, numsamples, order_by)
  assert 'columns' in infer_result
  assert 'data' in infer_result
  assert infer_result['columns'] == ['row_id', 'name', 'qual_score']
  ## 307 is the total number of rows in the dataset.
  assert len(infer_result['data']) == 307 and len(infer_result['data'][0]) == len(infer_result['columns'])
  assert type(infer_result['data'][0][0]) == int ## type of row_id is int
  t = type(infer_result['data'][0][1])
  assert (t == unicode) or (t == numpy.string_) ## type of name is string
  assert type(infer_result['data'][0][2]) == float ## type of qual_score is float

  all_possible_names = [infer_result['data'][row][1] for row in range(5) + range(10, 307)]
  all_observed_qual_scores = [infer_result['data'][row][2] for row in range(5,307)]

  for row in range(5):
    inferred_name = infer_result['data'][row+5][1]
    inferred_qual_score = infer_result['data'][row][2]
    assert inferred_name in all_possible_names
    assert type(inferred_qual_score) == type(1.2)
    assert inferred_qual_score > min(all_observed_qual_scores)
    assert inferred_qual_score < max(all_observed_qual_scores)

  ## Now, try infer with higher confidence, and make sure that name isn't inferred anymore.
  confidence = 0.9
  infer_result = engine.infer(test_tablename, columnstring, '', confidence, whereclause, limit, numsamples, order_by)

  for row in range(5):
    ## TODO: what do missing values look like? these should be missing
    inferred_name = infer_result['data'][row+5][1]
    inferred_qual_score = infer_result['data'][row][2]
    assert numpy.isnan(inferred_name)
    assert numpy.isnan(inferred_qual_score)

def test_simulate():
  ## TODO: whereclauses
  test_tablename, _ = create_dha()
  engine.initialize_models(test_tablename, 2)
  
  columnstring = 'name, qual_score'
  whereclause = ''
  givens = ''
  order_by = False
  numpredictions = 10
  simulate_result = engine.simulate(test_tablename, columnstring, '', givens, whereclause, numpredictions, order_by)
  assert 'columns' in simulate_result
  assert 'data' in simulate_result
  assert simulate_result['columns'] == ['name', 'qual_score']

  assert len(simulate_result['data']) == 10 and len(simulate_result['data'][0]) == len(simulate_result['columns'])
  for row in range(numpredictions):
    t = type(simulate_result['data'][row][0])
    assert (t == unicode) or (t == numpy.string_)
    assert type(simulate_result['data'][row][1]) == float

def test_estimate_pairwise_dependence_probability():
  test_tablename, _ = create_dha()
  engine.initialize_models(test_tablename, 2)
  dep_mat = engine.estimate_pairwise(test_tablename, 'dependence probability')

@pytest.mark.slow
def test_estimate_pairwise_mutual_information():
  ## TODO: speedup! Takes 27 seconds, and this is with 1 sample to estimate mutual information.
  # It definitely takes many more samples to get a good estimate - at least 100.
  test_tablename, _ = create_dha()
  engine.initialize_models(test_tablename, 2)
  mi_mat = engine.estimate_pairwise(test_tablename, 'mutual information')

def test_estimate_pairwise_correlation():
  test_tablename, _ = create_dha()
  engine.initialize_models(test_tablename, 2)
  cor_mat = engine.estimate_pairwise(test_tablename, 'correlation')

def test_list_btables():
  list_btables_result = engine.list_btables()['data']
  assert type(list_btables_result) == list
  initial_btable_count = len(list_btables_result)
  
  test_tablename1, create_btable_result = create_dha()
  test_tablename2, create_btable_result = create_dha()

  list_btables_result = engine.list_btables()['data']
  assert [test_tablename1] in list_btables_result
  assert [test_tablename2] in list_btables_result
  assert len(list_btables_result) == 2 + initial_btable_count
  
  engine.drop_btable(test_tablename1)
  test_tablename3, create_btable_result = create_dha()
  list_btables_result = engine.list_btables()['data']  
  assert [test_tablename1] not in list_btables_result
  assert [test_tablename3] in list_btables_result
  assert [test_tablename2] in list_btables_result

  engine.drop_btable(test_tablename2)
  engine.drop_btable(test_tablename3)

  list_btables_result = engine.list_btables()['data']  
  assert len(list_btables_result) == 0 + initial_btable_count

def test_execute_file():
  pass #TODO

def test_show_schema():
  test_tablename, _ = create_dha()
  m_c, m_r, t = engine.persistence_layer.get_metadata_and_table(test_tablename)
  cctypes = engine.persistence_layer.get_cctypes(test_tablename)
  assert cctypes[m_c['name_to_idx']['qual_score']] == 'continuous'
  assert cctypes[m_c['name_to_idx']['name']] == 'multinomial'

  schema = engine.show_schema(test_tablename)
  assert sorted([d[1] for d in schema['data']]) == sorted(cctypes)
  assert schema['data'][0][0] == 'name'
  
  mappings = dict(qual_score='multinomial')
  engine.update_schema(test_tablename, mappings)
  cctypes = engine.persistence_layer.get_cctypes(test_tablename)
  assert cctypes[m_c['name_to_idx']['qual_score']] == 'multinomial'
  
  schema = engine.show_schema(test_tablename)
  assert sorted([d[1] for d in schema['data']]) == sorted(cctypes)
  assert schema['data'][0][0] == 'name'

def test_show_models():
  test_tablename, _ = create_dha()
  num_models = 3
  engine.initialize_models(test_tablename, num_models)

  for it in (1,2):
    analyze_out = engine.analyze(test_tablename, model_indices='all', iterations=1)
    model_ids = engine.persistence_layer.get_model_ids(test_tablename)
    assert sorted(model_ids) == range(num_models)
    for i in range(num_models):
      model = engine.persistence_layer.get_models(test_tablename, i)
      assert model['iterations'] == it

    ## models should be a list of (id, iterations) tuples.
    models = engine.show_models(test_tablename)['models']
    assert analyze_out['models'] == models
    assert len(models) == num_models
    for iter_id, m in enumerate(models):
      assert iter_id == m[0]
      assert it == m[1]

def test_show_diagnostics():
  pass #TODO

def test_drop_models():
  pass #TODO

def test_estimate_columns():
  #TODO: add nontrivial cases
  test_tablename, _ = create_dha()
  metadata = engine.persistence_layer.get_metadata(test_tablename)
  all_columns = metadata['M_c']['name_to_idx'].keys()
  engine.initialize_models(test_tablename, 2)
  
  whereclause = ''
  limit = float('inf')
  order_by = None
  name = None
  columnstring = ''
  columns = engine.estimate_columns(test_tablename, columnstring, whereclause, limit, order_by, name)['columns']
  assert columns == all_columns
  
if __name__ == '__main__':
    run_test()

########NEW FILE########
__FILENAME__ = test_parser
7#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import time
import inspect
import pickle
import os
from pyparsing import *

from bayesdb.bql_grammar import *
from bayesdb.engine import Engine
from bayesdb.parser import Parser
engine = Engine('local')
parser = Parser()

def test_keyword_plurality_ambiguity_pyparsing():
    model = model_keyword.parseString("model",parseAll=True)
    models = model_keyword.parseString("models",parseAll=True)
    assert model[0] == 'model'
    assert models[0] == 'model'
    iteration = iteration_keyword.parseString("iteration",parseAll=True)
    iterations = iteration_keyword.parseString("iterations",parseAll=True)
    assert iteration[0] == 'iteration'
    assert iterations[0] == 'iteration'
    sample = sample_keyword.parseString("sample",parseAll=True)
    samples = sample_keyword.parseString("samples",parseAll=True)
    assert sample[0] == 'sample'
    assert samples[0] == 'sample'
    column = column_keyword.parseString('column',parseAll=True)
    columns = column_keyword.parseString('columns',parseAll=True)
    assert column[0] == 'column'
    assert columns[0] == 'column'
    list_ = list_keyword.parseString('list',parseAll=True)
    lists = list_keyword.parseString('lists',parseAll=True)
    assert list_[0] == 'list'
    assert lists[0] == 'list'
    btable = btable_keyword.parseString('btable',parseAll=True)
    btables = btable_keyword.parseString('btables',parseAll=True)
    assert btable[0] == 'btable'
    assert btables[0] == 'btable'
    second = second_keyword.parseString('second',parseAll=True)
    seconds = second_keyword.parseString('seconds',parseAll=True)
    assert second[0] == 'second'
    assert seconds[0] == 'second'

def test_composite_keywords_pyparsing():
    execute_file = execute_file_keyword.parseString('eXecute file',parseAll=True)
    assert execute_file[0] == 'execute file'
    create_btable = create_btable_keyword.parseString('cReate btable',parseAll=True)
    assert create_btable[0] == 'create btable'
    update_schema_for = update_schema_for_keyword.parseString('update Schema for',parseAll=True)
    assert update_schema_for[0] == 'update schema for'
    models_for = models_for_keyword.parseString('Models for',parseAll=True)
    assert models_for[0] == 'model for'
    model_index = model_index_keyword.parseString('model Index',parseAll=True)
    assert model_index[0] == 'model index'
    save_model = save_model_keyword.parseString("save modeL",parseAll=True)
    assert save_model[0] == 'save model'
    load_model = load_model_keyword.parseString("load Models",parseAll=True)
    assert load_model[0] == 'load model'
    save_to = save_to_keyword.parseString('save To',parseAll=True)
    assert save_to[0] == 'save to'
    list_btables = list_btables_keyword.parseString('list bTables',parseAll=True)
    assert list_btables[0] == 'list btable'
    show_schema_for = show_schema_for_keyword.parseString('show Schema for',parseAll=True)
    assert show_schema_for[0] == 'show schema for'
    show_models_for = show_models_for_keyword.parseString("show modeLs for",parseAll=True)
    assert show_models_for[0] == 'show model for'
    show_diagnostics_for = show_diagnostics_for_keyword.parseString("show diaGnostics for",parseAll=True)
    assert show_diagnostics_for[0] == 'show diagnostics for'
    estimate_pairwise = estimate_pairwise_keyword.parseString("estimate Pairwise",parseAll=True)
    assert estimate_pairwise[0] == 'estimate pairwise'
    with_confidence = with_confidence_keyword.parseString('with  confIdence',parseAll=True)
    assert with_confidence[0] == 'with confidence'
    dependence_probability = dependence_probability_keyword.parseString('dependence probability',parseAll=True)
    assert dependence_probability[0] == 'dependence probability'
    mutual_information = mutual_information_keyword.parseString('mutual inFormation',parseAll=True)
    assert mutual_information[0] == 'mutual information'
    estimate_columns_from = estimate_columns_from_keyword.parseString("estimate columns froM",parseAll=True)
    assert estimate_columns_from[0] == 'estimate column from'
    column_lists = column_lists_keyword.parseString('column Lists',parseAll=True)
    assert column_lists[0] == 'column list'
    similarity_to = similarity_to_keyword.parseString("similarity to",parseAll=True)
    assert similarity_to[0] == 'similarity to'
    with_respect_to = with_respect_to_keyword.parseString("with Respect to",parseAll=True)
    assert with_respect_to[0] == 'with respect to'
    probability_of = probability_of_keyword.parseString('probability of',parseAll=True)
    assert probability_of[0] == 'probability of'
    predictive_probability_of = predictive_probability_of_keyword.parseString('predictive Probability  of',parseAll=True)
    assert predictive_probability_of[0] == 'predictive probability of'
    save_connected_components_with_threshold = save_connected_components_with_threshold_keyword.parseString(
        'save cOnnected components with threshold',parseAll=True)
    assert save_connected_components_with_threshold[0] == 'save connected components with threshold'
    estimate_pairwise_row = estimate_pairwise_row_keyword.parseString("estimate Pairwise row",parseAll=True)
    assert estimate_pairwise_row[0] == 'estimate pairwise row'

def test_valid_values_names_pyparsing():
    valid_values=[
        '4',
        '42.04',
        '.4',
        '4.',
        "'\sjekja8391(*^@(%()!@#$%^&*()_+=-~'",
        "a0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!\"#$%&'()*+,-./:;<=>?@[\]^_`{|}~",
        'b0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~',
        '"c0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!\\"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~"',
        "'d0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!\"#$%&\\'()*+,-./:;<=>?@[\]^_`{|}~'",
        "'numbers 0'", 
        "'k skj s'",
        ]
    valid_values_results=[
        '4',
        '42.04',
        '.4',
        '4.',
        '\sjekja8391(*^@(%()!@#$%^&*()_+=-~',
        "a0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!\"#$%&'()*+,-./:;<=>?@[\]^_`{|}~",
        'b0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~',
        "c0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!\"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~",
        "d0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!\"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~",
        'numbers 0', 
        'k skj s',
        ]

    for i in range(len(valid_values)):
        assert value.parseString(valid_values[i],parseAll=True)[0] == valid_values_results[i]

    valid_column_identifiers = [
        "a",
        "a1",
        "a_1",
        "a_a",
        "a_",
        "aa"
        ]
    valid_column_identifiers_results = [
        "a",
        "a1",
        "a_1",
        "a_a",
        "a_",
        "aa"
        ]
    for i in range(len(valid_column_identifiers)):
        assert value.parseString(valid_column_identifiers[i],parseAll=True)[0] == valid_column_identifiers_results[i]
    assert float_number.parseString('1',parseAll=True)[0] == '1'
    assert int_number.parseString('1',parseAll=True)[0] == '1'
    assert float_number.parseString('1.')[0] == '1'
    assert float_number.parseString('.1',parseAll=True)[0] == '.1'
    assert float_number.parseString('0.1',parseAll=True)[0] == '0.1'
    assert float_number.parseString('11',parseAll=True)[0] == '11'
    assert int_number.parseString('11',parseAll=True)[0] == '11'
    assert float_number.parseString('11.01',parseAll=True)[0] == '11.01'
    assert filename.parseString("~/filename.csv",parseAll=True)[0] == "~/filename.csv"
    assert filename.parseString("!\"/#$%&'()*+,-.:;<=>?@[\]^_`{|}~",parseAll=True)[0] == "!\"/#$%&'()*+,-.:;<=>?@[\]^_`{|}~"
    assert filename.parseString("'/filename with space.csv'",parseAll=True)[0] == "/filename with space.csv"

def test_simple_functions():
    assert list_btables_function.parseString("LIST BTABLES",parseAll=True).statement_id == 'list btable'
    assert list_btables_function.parseString("LIST BTABLE",parseAll=True).statement_id == 'list btable'
    assert show_for_btable_statement.parseString("SHOW SCHEMA FOR table_1",parseAll=True).statement_id == 'show schema for'
    assert show_for_btable_statement.parseString("SHOW SCHEMA FOR table_1",parseAll=True).btable == 'table_1'
    assert show_for_btable_statement.parseString("SHOW MODELS FOR table_1",parseAll=True).statement_id == 'show model for'
    assert show_for_btable_statement.parseString("SHOW MODEL FOR table_1",parseAll=True).btable == 'table_1'
    assert show_for_btable_statement.parseString("SHOW DIAGNOSTICS FOR table_1",parseAll=True).statement_id == 'show diagnostics for'
    assert show_for_btable_statement.parseString("SHOW DIAGNOSTICS FOR table_1",parseAll=True).btable == 'table_1'

    assert show_for_btable_statement.parseString("SHOW COLUMN LISTS FOR table_1",parseAll=True).btable == 'table_1'
    assert show_for_btable_statement.parseString("SHOW COLUMNS LIST FOR table_1",parseAll=True).statement_id == 'show column list for'
    assert show_for_btable_statement.parseString("SHOW COLUMNS FOR table_1",parseAll=True).btable == 'table_1'
    assert show_for_btable_statement.parseString("SHOW column FOR table_1",parseAll=True).statement_id == 'show column for'
    assert show_for_btable_statement.parseString("SHOW ROW LISTS FOR table_1",parseAll=True).statement_id == 'show row list for'
    assert show_for_btable_statement.parseString("SHOW ROW list FOR table_1",parseAll=True).btable == 'table_1'
    assert load_model_function.parseString("LOAD MODELS ~/filename.csv INTO table_1",parseAll=True).statement_id == 'load model'
    assert load_model_function.parseString("LOAD MODEL ~/filename.csv INTO table_1",parseAll=True).statement_id == 'load model'
    assert load_model_function.parseString("LOAD MODELS ~/filename.csv INTO table_1",parseAll=True).filename == '~/filename.csv'
    assert load_model_function.parseString("LOAD MODELS '~/filena me.csv' INTO table_1",parseAll=True).filename == '~/filena me.csv'
    assert load_model_function.parseString("LOAD MODELS ~/filename.csv INTO table_1",parseAll=True).btable == 'table_1'
    assert save_model_from_function.parseString("SAVE MODEL FROM table_1 to filename.pkl.gz",parseAll=True).btable == 'table_1'
    assert save_model_from_function.parseString("SAVE MODEL FROM table_1 to filename.pkl.gz",parseAll=True).statement_id == 'save model'
    assert save_model_from_function.parseString("SAVE MODEL FROM table_1 to filename.pkl.gz",parseAll=True).filename == 'filename.pkl.gz'
    assert drop_btable_function.parseString("DROP BTABLE table_1",parseAll=True).statement_id == 'drop btable'
    assert drop_btable_function.parseString("DROP BTABLES table_1",parseAll=True).statement_id == 'drop btable'
    assert drop_btable_function.parseString("DROP BTABLE table_1",parseAll=True).btable == 'table_1'
    drop_model_1 = drop_model_function.parseString("DROP MODEL 1 FROM table_1",parseAll=True)
    drop_model_2 = drop_model_function.parseString("DROP MODELS 1-5 FROM table_1",parseAll=True)
    drop_model_3 = drop_model_function.parseString("DROP MODELS 1,2,6-9 FROM table_1",parseAll=True)
    drop_model_4 = drop_model_function.parseString("DROP MODELS 1-5,1-5 FROM table_1",parseAll=True)
    assert drop_model_1.statement_id == 'drop model'
    assert drop_model_1.btable == 'table_1'
    assert drop_model_1.index_list.asList() == [1]
    assert drop_model_2.index_list.asList() == [1,2,3,4,5]
    assert drop_model_3.index_list.asList() == [1,2,6,7,8,9]
    assert drop_model_4.index_list.asList() == [1,2,3,4,5]
    assert help_function.parseString("HELp",parseAll=True).statement_id == 'help'

def test_update_schema_pyparsing():
    update_schema_1 = update_schema_for_function.parseString("UPDATE SCHEMA FOR test_btablE SET col_1 = Categorical,col.2=numerical , col_3  =  ignore",parseAll=True)
    assert update_schema_1.statement_id == 'update schema for'
    assert update_schema_1.btable == 'test_btable'
    assert update_schema_1.type_clause[0][0] == 'col_1'
    assert update_schema_1.type_clause[0][1] == 'categorical'
    assert update_schema_1.type_clause[1][0] == 'col.2'
    assert update_schema_1.type_clause[1][1] == 'numerical'
    assert update_schema_1.type_clause[2][0] == 'col_3'
    assert update_schema_1.type_clause[2][1] == 'ignore'
    update_schema_2 = update_schema_for_function.parseString("UPDATE SCHEMA FOR test_btablE SET col_1 = key",parseAll=True)
    assert update_schema_2.type_clause[0][0] == 'col_1'
    assert update_schema_2.type_clause[0][1] == 'key'

def test_create_btable_pyparsing():
    create_btable_1 = create_btable_function.parseString("CREATE BTABLE test.btable FROM '~/filenam e.csv'", parseAll=True)
    create_btable_2 = create_btable_function.parseString("CREATE BTABLE test_btable FROM ~/filename.csv", parseAll=True)
    assert create_btable_1.statement_id == 'create btable'
    assert create_btable_1.btable == 'test.btable'
    assert create_btable_1.filename == '~/filenam e.csv'
    assert create_btable_2.btable == 'test_btable'
    assert create_btable_2.filename == '~/filename.csv'

def test_execute_file_pyparsing():
    execute_file_1 = execute_file_function.parseString("EXECUTE FILE '/filenam e.bql'",parseAll=True)
    execute_file_2 = execute_file_function.parseString("EXECUTE FILE /filename.bql",parseAll=True)
    assert execute_file_1.filename == "/filenam e.bql"
    assert execute_file_2.filename == "/filename.bql"

def test_initialize_pyparsing():
    initialize_1 = initialize_function.parseString("INITIALIZE 3 MODELS FOR test_table",parseAll=True)
    assert initialize_1.statement_id == 'initialize'
    assert initialize_1.num_models == '3'
    assert initialize_1.btable == 'test_table'
    initialize_2 = initialize_function.parseString("INITIALIZE 3 MODEL FOR test_table",parseAll=True)
    assert initialize_2.statement_id == 'initialize'
    assert initialize_2.num_models == '3'
    assert initialize_2.btable == 'test_table'

def test_analyze_pyparsing():
    analyze_1 = analyze_function.parseString("ANALYZE table_1 FOR 10 ITERATIONS",parseAll=True)
    analyze_2 = analyze_function.parseString("ANALYZE table_1 FOR 1 ITERATION",parseAll=True)
    analyze_3 = analyze_function.parseString("ANALYZE table_1 FOR 10 SECONDS",parseAll=True)
    analyze_4 = analyze_function.parseString("ANALYZE table_1 FOR 1 SECOND",parseAll=True)
    analyze_5 = analyze_function.parseString("ANALYZE table_1 MODEL 1 FOR 10 SECONDS",parseAll=True)
    analyze_6 = analyze_function.parseString("ANALYZE table_1 MODELS 1-3 FOR 1 ITERATION",parseAll=True)
    analyze_7 = analyze_function.parseString("ANALYZE table_1 MODELS 1,2,3 FOR 10 SECONDS",parseAll=True)
    analyze_8 = analyze_function.parseString("ANALYZE table_1 MODELS 1, 3-5 FOR 1 ITERATION",parseAll=True)
    analyze_9 = analyze_function.parseString("ANALYZE table_1 MODELS 1-3, 5 FOR 10 SECONDS",parseAll=True)
    analyze_10 = analyze_function.parseString("ANALYZE table_1 MODELS 1-3, 5-7, 9, 10 FOR 1 ITERATION",parseAll=True)
    analyze_11 = analyze_function.parseString("ANALYZE table_1 MODELS 1, 1, 2, 2 FOR 10 SECONDS",parseAll=True)
    analyze_12 = analyze_function.parseString("ANALYZE table_1 MODELS 1-5, 1-5, 5 FOR 1 ITERATION",parseAll=True)
    assert analyze_1.statement_id == 'analyze'
    assert analyze_1.btable == 'table_1'
    assert analyze_1.index_lust == ''
    assert analyze_1.index_clause == ''
    assert analyze_1.num_iterations == '10'
    assert analyze_1.num_seconds == ''
    assert analyze_2.num_iterations == '1'
    assert analyze_2.num_seconds == ''
    assert analyze_3.num_iterations == ''
    assert analyze_3.num_seconds == '10'
    assert analyze_4.num_iterations == ''
    assert analyze_4.num_seconds == '1'
    assert analyze_5.index_list.asList() == [1]
    assert analyze_6.index_list.asList() == [1,2,3]
    assert analyze_7.index_list.asList() == [1,2,3]
    assert analyze_8.index_list.asList() == [1,3,4,5]
    assert analyze_9.index_list.asList() == [1,2,3,5]
    assert analyze_10.index_list.asList() == [1,2,3,5,6,7,9,10]
    assert analyze_11.index_list.asList() == [1,2]
    assert analyze_12.index_list.asList() == [1,2,3,4,5]

def test_subclauses_pyparsing():
    assert save_to_clause.parseString("save to filename.csv").filename == 'filename.csv'

def test_row_clause_pyparsing():
    row_1 = row_clause.parseString('1', parseAll=True)
    row_2 = row_clause.parseString("column = 1", parseAll=True)
    row_3 = row_clause.parseString("column = 'value'", parseAll=True)
    row_4 = row_clause.parseString("column = value", parseAll=True)
    assert row_1.row_id == '1'
    assert row_1.column == ''
    assert row_2.row_id == ''
    assert row_2.column == 'column'
    assert row_2.column_value == '1'
    assert row_3.column_value == 'value'
    assert row_4.column_value == 'value'
    
def test_row_functions_pyparsing():
    similarity_1 = similarity_to_function.parseString("SIMILARITY TO 1", 
                                                      parseAll=True)
    similarity_2 = similarity_to_function.parseString("SIMILARITY TO col_2 = 1", 
                                                      parseAll=True)
    similarity_3 = similarity_to_function.parseString("SIMILARITY TO col_2 = 'a'", 
                                                      parseAll=True)
    similarity_4 = similarity_to_function.parseString("SIMILARITY TO col_2 = a", 
                                                      parseAll=True)
    similarity_5 = similarity_to_function.parseString("SIMILARITY TO 1 WITH RESPECT TO col_1", 
                                                      parseAll=True)
    similarity_6 = similarity_to_function.parseString("SIMILARITY TO col_2 = 1 WITH RESPECT TO col_1,col_2", 
                                                      parseAll=True)
    similarity_7 = similarity_to_function.parseString("SIMILARITY TO col_2 = 'a' WITH RESPECT TO col_1 , col_3", 
                                                      parseAll=True)
    similarity_8 = similarity_to_function.parseString("SIMILARITY TO col_2 = a WITH RESPECT TO col_1", 
                                                      parseAll=True)
    assert similarity_1.function.function_id == 'similarity to'
    assert similarity_1.function.row_id == '1'
    assert similarity_2.function.column == 'col_2'
    assert similarity_2.function.column_value == '1'
    assert similarity_3.function.column == 'col_2'
    assert similarity_3.function.column_value == 'a'
    assert similarity_4.function.column == 'col_2'
    assert similarity_4.function.column_value == 'a'
    assert similarity_4.function.with_respect_to == ''
    assert not similarity_5.function.with_respect_to == ''
    assert similarity_5.function.column_list.asList() == ['col_1']
    assert similarity_6.function.column_list.asList() == ['col_1', 'col_2']
    assert similarity_7.function.column_list.asList() == ['col_1', 'col_3']
    assert similarity_8.function.column_list.asList() == ['col_1']
    assert typicality_function.parseString('Typicality',parseAll=True).function.function_id == 'typicality'

def test_column_functions_pyparsing():
    dependence_1 = dependence_probability_function.parseString('DEPENDENCE PROBABILITY WITH column_1',
                                                                    parseAll=True)
    dependence_2 = dependence_probability_function.parseString('DEPENDENCE PROBABILITY OF column_2 WITH column_1',
                                                                    parseAll=True)
    assert dependence_1.function.function_id == 'dependence probability'
    assert dependence_2.function.function_id == 'dependence probability'
    assert dependence_1.function.with_column == 'column_1'
    assert dependence_2.function.with_column == 'column_1'
    assert dependence_2.function.of_column == 'column_2'
    mutual_1 = mutual_information_function.parseString('MUTUAL INFORMATION WITH column_1',
                                                                    parseAll=True)
    mutual_2 = mutual_information_function.parseString('MUTUAL INFORMATION OF column_2 WITH column_1',
                                                                    parseAll=True)
    assert mutual_1.function.function_id == 'mutual information'
    assert mutual_2.function.function_id == 'mutual information'
    assert mutual_1.function.with_column == 'column_1'
    assert mutual_2.function.with_column == 'column_1'
    assert mutual_2.function.of_column == 'column_2'
    correlation_1 = correlation_function.parseString('CORRELATION WITH column_1',
                                                                    parseAll=True)
    correlation_2 = correlation_function.parseString('CORRELATION OF column_2 WITH column_1',
                                                                    parseAll=True)
    assert correlation_1.function.function_id == 'correlation'
    assert correlation_2.function.function_id == 'correlation'
    assert correlation_1.function.with_column == 'column_1'
    assert correlation_2.function.with_column == 'column_1'
    assert correlation_2.function.of_column == 'column_2'
    

def test_probability_of_function_pyparsing():
    probability_of_1 = probability_of_function.parseString("PROBABILITY OF col_1 = 1",parseAll=True)
    probability_of_2 = probability_of_function.parseString("PROBABILITY OF col_1 = 'value'",parseAll=True)
    probability_of_3 = probability_of_function.parseString("PROBABILITY OF col_1 = value",parseAll=True)
    assert probability_of_1.function.function_id == 'probability of'
    assert probability_of_1.function.column == 'col_1'
    assert probability_of_1.function.value == '1'
    assert probability_of_2.function.value == 'value'
    assert probability_of_3.function.value == 'value'

def test_predictive_probability_of_pyparsing():
    assert predictive_probability_of_function.parseString("PREDICTIVE PROBABILITY OF column_1",
                                                          parseAll=True).function.function_id == 'predictive probability of'
    assert predictive_probability_of_function.parseString("PREDICTIVE PROBABILITY OF column_1",
                                                          parseAll=True).function.column == 'column_1'

def test_typicality_of_pyparsing():
    assert typicality_of_function.parseString("TYPICALITY OF column_1",
                                                          parseAll=True).function.function_id == 'typicality of'
    assert typicality_of_function.parseString("TYPICALITY OF column_1",
                                                          parseAll=True).function.column == 'column_1'

def test_order_by_clause_pyparsing():
    order_by_1 = order_by_clause.parseString("ORDER BY column_1"
                                             ,parseAll=True)
    order_by_2 = order_by_clause.parseString("ORDER BY column_1,column_2 , column_3"
                                             ,parseAll=True)
    assert order_by_1.order_by.order_by_set[0].column=='column_1'
    assert order_by_2.order_by.order_by_set[1].column=='column_2'
    order_by_3 = order_by_clause.parseString("ORDER BY TYPICALITY",
                                             parseAll=True)
    assert order_by_3.order_by.order_by_set[0].function_id == 'typicality'
    order_by_4 = order_by_clause.parseString("ORDER BY TYPICALITY, column_1",
                                             parseAll=True)
    assert order_by_4.order_by.order_by_set[0].function_id == 'typicality'
    assert order_by_4.order_by.order_by_set[1].column == 'column_1'    
    order_by_5 = order_by_clause.parseString("ORDER BY column_1, TYPICALITY",
                                             parseAll=True)
    assert order_by_5.order_by.order_by_set[0].column == 'column_1'
    assert order_by_5.order_by.order_by_set[1].function_id == 'typicality'
    order_by_6 = order_by_clause.parseString("ORDER BY PREDICTIVE PROBABILITY OF column_1",
                                             parseAll=True)
    assert order_by_6.order_by.order_by_set[0].function_id == 'predictive probability of'
    assert order_by_6.order_by.order_by_set[0].column == 'column_1'
    
    order_by_7 = order_by_clause.parseString("ORDER BY PREDICTIVE PROBABILITY OF column_1, column_1",
                                             parseAll=True)
    assert order_by_7.order_by.order_by_set[1].column == 'column_1'
    assert order_by_7.order_by.order_by_set[0].function_id == 'predictive probability of'
    assert order_by_7.order_by.order_by_set[0].column == 'column_1'

    order_by_8 = order_by_clause.parseString("ORDER BY column_1, TYPICALITY, PREDICTIVE PROBABILITY OF column_1, column_2, SIMILARITY TO 2, SIMILARITY TO column_1 = 1 WITH RESPECT TO column_4",
                                             parseAll=True)
    assert order_by_8.order_by.order_by_set[0].column == 'column_1'
    assert order_by_8.order_by.order_by_set[1].function_id == 'typicality'
    assert order_by_8.order_by.order_by_set[2].function_id == 'predictive probability of'
    assert order_by_8.order_by.order_by_set[2].column == 'column_1'
    assert order_by_8.order_by.order_by_set[3].column == 'column_2'
    assert order_by_8.order_by.order_by_set[4].function_id == 'similarity to'
    assert order_by_8.order_by.order_by_set[4].row_id == '2'
    assert order_by_8.order_by.order_by_set[5].function_id == 'similarity to'
    assert order_by_8.order_by.order_by_set[5].column == 'column_1'
    assert order_by_8.order_by.order_by_set[5].column_value == '1'
    assert order_by_8.order_by.order_by_set[5].with_respect_to[1][0] == 'column_4' #todo names instead of indexes

def test_whereclause_pyparsing():
    # WHERE <column> <operation> <value>
    whereclause_1 = "WHERE column_1 = 1"
    parsed_1 = where_clause.parseString(whereclause_1,parseAll=True)
    assert parsed_1.where_keyword == 'where'
    assert parsed_1.where_conditions[0].function.column == 'column_1'
    assert parsed_1.where_conditions[0].operation == '='
    assert parsed_1.where_conditions[0].value == '1'
    whereclause_2 = "WHERE column_1 <= 1"
    parsed_2 = where_clause.parseString(whereclause_2,parseAll=True)
    assert parsed_2.where_conditions[0].function.column == 'column_1'
    assert parsed_2.where_conditions[0].operation == '<='
    assert parsed_2.where_conditions[0].value == '1'
    whereclause_3 = "WHERE column_1 > 1.0"
    parsed_3 = where_clause.parseString(whereclause_3,parseAll=True)
    assert parsed_3.where_conditions[0].operation == '>'
    assert parsed_3.where_conditions[0].value == '1.0'
    whereclause_4 = "WHERE column_1 = a"
    parsed_4 = where_clause.parseString(whereclause_4,parseAll=True)
    assert parsed_4.where_conditions[0].operation == '='
    assert parsed_4.where_conditions[0].value == 'a'
    whereclause_5 = "WHERE column_1 = 'a'"
    parsed_5 = where_clause.parseString(whereclause_5,parseAll=True)
    assert parsed_5.where_conditions[0].value == 'a'
    whereclause_6 = "WHERE column_1 = 'two words'"
    parsed_6 = where_clause.parseString(whereclause_6,parseAll=True)
    assert parsed_6.where_conditions[0].value == 'two words'
    # Functions
    whereclause_7 = "WHERE TYPICALITY > .8"
    parsed_7 = where_clause.parseString(whereclause_7,parseAll=True)
    assert parsed_7.where_conditions[0].function.function_id == 'typicality'
    assert parsed_7.where_conditions[0].operation == '>'
    assert parsed_7.where_conditions[0].value == '.8'
    whereclause_8 = "WHERE PREDICTIVE PROBABILITY OF column_1 > .1"
    parsed_8 = where_clause.parseString(whereclause_8,parseAll=True)
    assert parsed_8.where_conditions[0].function.function_id == 'predictive probability of'
    assert parsed_8.where_conditions[0].function.column == 'column_1'
    assert parsed_8.where_conditions[0].operation == '>'
    assert parsed_8.where_conditions[0].value == '.1'
    whereclause_9 = "WHERE SIMILARITY TO 2 > .1"
    parsed_9 = where_clause.parseString(whereclause_9,parseAll=True)
    assert parsed_9.where_conditions[0].function.function_id == 'similarity to'
    assert parsed_9.where_conditions[0].function.row_id == '2'
    assert parsed_9.where_conditions[0].operation == '>'
    assert parsed_9.where_conditions[0].value == '.1'
    whereclause_10 = "WHERE SIMILARITY TO 2 WITH RESPECT TO column_1 > .4"
    parsed_10 = where_clause.parseString(whereclause_10,parseAll=True)
    assert parsed_10.where_conditions[0].function.function_id == 'similarity to'
    assert parsed_10.where_conditions[0].function.row_id == '2'
    assert parsed_10.where_conditions[0].function.with_respect_to.column_list[0] == 'column_1'
    assert parsed_10.where_conditions[0].operation == '>'
    assert parsed_10.where_conditions[0].value == '.4'
    whereclause_11 = "WHERE SIMILARITY TO column_1 = 1 = .5"
    parsed_11 = where_clause.parseString(whereclause_11,parseAll=True)
    assert parsed_11.where_conditions[0].function.function_id == 'similarity to'
    assert parsed_11.where_conditions[0].function.column == 'column_1'
    assert parsed_11.where_conditions[0].function.column_value == '1'
    assert parsed_11.where_conditions[0].operation == '='
    assert parsed_11.where_conditions[0].value == '.5'
    whereclause_12 = "WHERE SIMILARITY TO column_1 = 'a' WITH RESPECT TO column_2 > .5"
    parsed_12 = where_clause.parseString(whereclause_12,parseAll=True)
    assert parsed_12.where_conditions[0].function.function_id == 'similarity to'
    assert parsed_12.where_conditions[0].function.column == 'column_1'
    assert parsed_12.where_conditions[0].function.column_value == 'a'
    assert parsed_12.where_conditions[0].operation == '>'
    assert parsed_12.where_conditions[0].value == '.5'    
    assert parsed_12.where_conditions[0].function.with_respect_to.column_list[0] == 'column_2'
    whereclause_13 = "WHERE SIMILARITY TO column_1 = 1.2 WITH RESPECT TO column_2 > .5"
    parsed_13 = where_clause.parseString(whereclause_13,parseAll=True)
    assert parsed_13.where_conditions[0].function.function_id == 'similarity to'
    assert parsed_13.where_conditions[0].function.column == 'column_1'
    assert parsed_13.where_conditions[0].function.column_value == '1.2'
    assert parsed_13.where_conditions[0].operation == '>'
    assert parsed_13.where_conditions[0].value == '.5'    
    assert parsed_13.where_conditions[0].function.with_respect_to.column_list[0] == 'column_2'
    whereclause_14 = "WHERE SIMILARITY TO column_1 = a WITH RESPECT TO column_2 > .5"
    parsed_14 = where_clause.parseString(whereclause_14,parseAll=True)
    assert parsed_14.where_conditions[0].function.function_id == 'similarity to'
    assert parsed_14.where_conditions[0].function.column == 'column_1'
    assert parsed_14.where_conditions[0].function.column_value == 'a'
    assert parsed_14.where_conditions[0].operation == '>'
    assert parsed_14.where_conditions[0].value == '.5'    
    assert parsed_14.where_conditions[0].function.with_respect_to.column_list[0] == 'column_2'
    # With Confidence
    whereclause_15 = "WHERE TYPICALITY > .8 WITH CONFIDENCE .5"
    parsed_15 = where_clause.parseString(whereclause_15,parseAll=True)
    assert parsed_15.where_conditions[0].confidence == '.5'
    whereclause_16 = "WHERE PREDICTIVE PROBABILITY OF column_1 > .1 WITH CONFIDENCE .5"
    parsed_16 = where_clause.parseString(whereclause_16,parseAll=True)
    assert parsed_16.where_conditions[0].confidence == '.5'
    whereclause_17 = "WHERE SIMILARITY TO 2 > .1 WITH CONFIDENCE .5"
    parsed_17 = where_clause.parseString(whereclause_17,parseAll=True)
    assert parsed_17.where_conditions[0].confidence == '.5'
    whereclause_18 = "WHERE SIMILARITY TO 2 WITH RESPECT TO column_1 > .4 WITH CONFIDENCE .5"
    parsed_18 = where_clause.parseString(whereclause_18,parseAll=True)
    assert parsed_18.where_conditions[0].confidence == '.5'
    whereclause_19 = "WHERE SIMILARITY TO column_1 = 1 = .5 WITH CONFIDENCE .5"
    parsed_19 = where_clause.parseString(whereclause_19,parseAll=True)
    assert parsed_19.where_conditions[0].confidence == '.5'
    whereclause_20 = "WHERE SIMILARITY TO column_1 = 'a' WITH RESPECT TO column_2 > .5 WITH CONFIDENCE .5"
    parsed_20 = where_clause.parseString(whereclause_20,parseAll=True)
    assert parsed_20.where_conditions[0].confidence == '.5'
    whereclause_21 = "WHERE SIMILARITY TO column_1 = 1.2 WITH RESPECT TO column_2 > .5 WITH CONFIDENCE .5"
    parsed_21 = where_clause.parseString(whereclause_21,parseAll=True)
    assert parsed_21.where_conditions[0].confidence == '.5'
    whereclause_22 = "WHERE SIMILARITY TO column_1 = a WITH RESPECT TO column_2 > .5 WITH CONFIDENCE .5"
    parsed_22 = where_clause.parseString(whereclause_22,parseAll=True)
    assert parsed_22.where_conditions[0].confidence == '.5'
    # AND
    whereclause_23 = "WHERE column_1 = 'a' AND column_2 >= 3"
    parsed_23 = where_clause.parseString(whereclause_23,parseAll=True)
    assert parsed_23.where_conditions[0].function.column == 'column_1'
    assert parsed_23.where_conditions[1].function.column == 'column_2'
    whereclause_24 = "WHERE TYPICALITY > .8 AND PREDICTIVE PROBABILITY OF column_1 > .1 AND SIMILARITY TO 2 > .1"
    parsed_24 = where_clause.parseString(whereclause_24,parseAll=True)
    assert parsed_24.where_conditions[0].function.function_id == 'typicality'
    assert parsed_24.where_conditions[1].function.function_id == 'predictive probability of'
    assert parsed_24.where_conditions[2].function.function_id == 'similarity to'
    whereclause_25 = "WHERE TYPICALITY > .8 WITH CONFIDENCE .4 AND PREDICTIVE PROBABILITY OF column_1 > .1 WITH CONFIDENCE .6 AND SIMILARITY TO 2 > .1 WITH CONFIDENCE .5"
    parsed_25 = where_clause.parseString(whereclause_25,parseAll=True)
    assert parsed_25.where_conditions[0].confidence == '.4'
    assert parsed_25.where_conditions[1].confidence == '.6'
    assert parsed_25.where_conditions[2].confidence == '.5'
    whereclause_26 = "WHERE KEY IN row_list_1 AND column_1 = 'a' AND TYPICALITY > .4"
    parsed_26 = where_clause.parseString(whereclause_26,parseAll=True)
    assert parsed_26.where_conditions[0].function.function_id == 'key in'
    assert parsed_26.where_conditions[0].function.row_list == 'row_list_1'
    assert parsed_26.where_conditions[1].function.column == 'column_1'
    assert parsed_26.where_conditions[2].function.function_id == 'typicality'

def test_key_in_rowlist():
    assert key_in_rowlist_clause.parseString("key in row_list_1",parseAll=True).function.function_id == "key in"
    assert key_in_rowlist_clause.parseString("key in row_list_1",parseAll=True).function.row_list == "row_list_1"

def test_basic_select_pyparsing():
    select_1 = "SELECT * FROM table_1"
    select_1_parse = query.parseString(select_1,parseAll=True)
    assert select_1_parse.query_id == 'select'
    assert select_1_parse.btable == 'table_1'
    assert select_1_parse.functions[0].columns[0] == '*'
    select_2 = "SELECT column_1,column_3 FROM table_1"
    select_2_parse = query.parseString(select_2,parseAll=True)
    assert select_2_parse.functions[0].columns.asList() == ['column_1','column_3']
    select_3 = "SELECT HIST column_1 FROM table_1 WHERE column_2 = 3"
    select_3_parse = query.parseString(select_3,parseAll=True)
    assert select_3_parse.hist == 'hist'
    assert select_3_parse.functions[0].columns.asList() == ['column_1']
    assert select_3_parse.where_keyword == 'where'
    assert select_3_parse.where_conditions[0].value == '3'
    assert select_3_parse.where_conditions[0].function.column == 'column_2'
    assert select_3_parse.where_conditions[0].operation == '='
    select_4 = "SELECT col_1 FROM table_1 ORDER BY TYPICALITY LIMIT 10 SAVE TO ~/test.txt"
    select_4_parse = query.parseString(select_4,parseAll=True)
    assert select_4_parse.functions[0].columns.asList() == ['col_1']
    assert select_4_parse.order_by.order_by_set[0].function_id == 'typicality'
    assert select_4_parse.limit == '10'
    assert select_4_parse.filename == '~/test.txt'
    
def test_select_functions_pyparsing():
    query_1 = "SELECT TYPICALITY FROM table_1"
    query_2 = "SELECT TYPICALITY OF column_1 FROM table_1"
    query_3 = "SELECT PREDICTIVE PROBABILITY OF column_1 FROM table_1"
    query_4 = "SELECT PROBABILITY OF column_1 = 4 FROM table_1"
    query_5 = "SELECT SIMILARITY TO 0 FROM table_1"
    query_5 = "SELECT SIMILARITY TO column_1 = 4 FROM table_1"
    query_6 = "SELECT DEPENDENCE PROBABILITY WITH column_1 FROM table_1"
    query_7 = "SELECT MUTUAL INFORMATION OF column_1 WITH column_2 FROM table_1"
    query_8 = "SELECT CORRELATION OF column_1 WITH column_2 FROM table_1"
    query_9 = "SELECT TYPICALITY, PREDICTIVE PROBABILITY OF column_1 FROM table_1"
    select_ast_1 = query.parseString(query_1,parseAll=True)
    select_ast_2 = query.parseString(query_2,parseAll=True)
    select_ast_3 = query.parseString(query_3,parseAll=True)
    select_ast_4 = query.parseString(query_4,parseAll=True)
    select_ast_5 = query.parseString(query_5,parseAll=True)
    select_ast_6 = query.parseString(query_6,parseAll=True)
    select_ast_7 = query.parseString(query_7,parseAll=True)
    select_ast_8 = query.parseString(query_8,parseAll=True)
    select_ast_9 = query.parseString(query_9,parseAll=True)
    assert select_ast_1.query_id == 'select'
    assert select_ast_2.query_id == 'select'
    assert select_ast_3.query_id == 'select'
    assert select_ast_4.query_id == 'select'
    assert select_ast_5.query_id == 'select'
    assert select_ast_5.query_id == 'select'
    assert select_ast_6.query_id == 'select'
    assert select_ast_7.query_id == 'select'
    assert select_ast_8.query_id == 'select'
    assert select_ast_9.query_id == 'select'    
    assert select_ast_1.functions[0].function_id == 'typicality'
    assert select_ast_2.functions[0].function_id == 'typicality of'
    assert select_ast_3.functions[0].function_id == 'predictive probability of'
    assert select_ast_4.functions[0].function_id == 'probability of'
    assert select_ast_5.functions[0].function_id == 'similarity to'
    assert select_ast_5.functions[0].function_id == 'similarity to'
    assert select_ast_6.functions[0].function_id == 'dependence probability'
    assert select_ast_7.functions[0].function_id == 'mutual information'
    assert select_ast_8.functions[0].function_id == 'correlation'
    assert select_ast_9.functions[0].function_id == 'typicality'
    assert select_ast_9.functions[1].function_id == 'predictive probability of'

def test_infer_pyparsing():
    infer_1 = "INFER * FROM table_1"
    infer_1_parse = query.parseString(infer_1,parseAll=True)
    assert infer_1_parse.query_id == 'infer'
    assert infer_1_parse.btable == 'table_1'
    assert infer_1_parse.functions[0].columns[0] == '*'
    infer_2 = "infer column_1,column_3 FROM table_1"
    infer_2_parse = query.parseString(infer_2,parseAll=True)
    assert infer_2_parse.functions[0].columns.asList() == ['column_1','column_3']
    infer_3 = "infer HIST column_1 FROM table_1 WHERE column_2 = 3"
    infer_3_parse = query.parseString(infer_3,parseAll=True)
    assert infer_3_parse.hist == 'hist'
    assert infer_3_parse.functions[0].columns.asList() == ['column_1']
    assert infer_3_parse.where_keyword == 'where'
    assert infer_3_parse.where_conditions[0].value == '3'
    assert infer_3_parse.where_conditions[0].function.column == 'column_2'
    assert infer_3_parse.where_conditions[0].operation == '='
    infer_4 = "infer col_1 FROM table_1 ORDER BY TYPICALITY LIMIT 10 SAVE TO ~/test.txt"
    infer_4_parse = query.parseString(infer_4,parseAll=True)
    assert infer_4_parse.functions[0].columns.asList() == ['col_1']
    assert infer_4_parse.order_by.order_by_set[0].function_id == 'typicality'
    assert infer_4_parse.limit == '10'
    assert infer_4_parse.filename == '~/test.txt'
    query_1 = "INFER TYPICALITY FROM table_1 WITH CONFIDENCE .4 WITH 4 SAMPLES"
    query_2 = "INFER TYPICALITY OF column_1 FROM table_1 WITH CONFIDENCE .4 WITH 4 SAMPLES"
    query_3 = "INFER PREDICTIVE PROBABILITY OF column_1 FROM table_1 WITH CONFIDENCE .4 WITH 4 SAMPLES"
    query_4 = "INFER PROBABILITY OF column_1 = 4 FROM table_1 WITH CONFIDENCE .4 WITH 4 SAMPLES"
    query_5 = "INFER SIMILARITY TO 0 FROM table_1 WITH CONFIDENCE .4 WITH 4 SAMPLES"
    query_5 = "INFER SIMILARITY TO column_1 = 4 FROM table_1 WITH CONFIDENCE .4 WITH 4 SAMPLES"
    query_6 = "INFER DEPENDENCE PROBABILITY WITH column_1 FROM table_1 WITH CONFIDENCE .4 WITH 4 SAMPLES"
    query_7 = "INFER MUTUAL INFORMATION OF column_1 WITH column_2 FROM table_1 WITH CONFIDENCE .4 WITH 4 SAMPLES"
    query_8 = "INFER CORRELATION OF column_1 WITH column_2 FROM table_1 WITH CONFIDENCE .4 WITH 4 SAMPLES"
    query_9 = "INFER TYPICALITY, PREDICTIVE PROBABILITY OF column_1 FROM table_1 WITH CONFIDENCE .4 WITH 4 SAMPLES"
    infer_ast_1 = query.parseString(query_1,parseAll=True)
    infer_ast_2 = query.parseString(query_2,parseAll=True)
    infer_ast_3 = query.parseString(query_3,parseAll=True)
    infer_ast_4 = query.parseString(query_4,parseAll=True)
    infer_ast_5 = query.parseString(query_5,parseAll=True)
    infer_ast_6 = query.parseString(query_6,parseAll=True)
    infer_ast_7 = query.parseString(query_7,parseAll=True)
    infer_ast_8 = query.parseString(query_8,parseAll=True)
    infer_ast_9 = query.parseString(query_9,parseAll=True)
    assert infer_ast_1.query_id == 'infer'
    assert infer_ast_2.query_id == 'infer'
    assert infer_ast_3.query_id == 'infer'
    assert infer_ast_4.query_id == 'infer'
    assert infer_ast_5.query_id == 'infer'
    assert infer_ast_5.query_id == 'infer'
    assert infer_ast_6.query_id == 'infer'
    assert infer_ast_7.query_id == 'infer'
    assert infer_ast_8.query_id == 'infer'
    assert infer_ast_9.query_id == 'infer'    
    assert infer_ast_1.functions[0].function_id == 'typicality'
    assert infer_ast_2.functions[0].function_id == 'typicality of'
    assert infer_ast_3.functions[0].function_id == 'predictive probability of'
    assert infer_ast_4.functions[0].function_id == 'probability of'
    assert infer_ast_5.functions[0].function_id == 'similarity to'
    assert infer_ast_5.functions[0].function_id == 'similarity to'
    assert infer_ast_6.functions[0].function_id == 'dependence probability'
    assert infer_ast_7.functions[0].function_id == 'mutual information'
    assert infer_ast_8.functions[0].function_id == 'correlation'
    assert infer_ast_9.functions[0].function_id == 'typicality'
    assert infer_ast_9.functions[1].function_id == 'predictive probability of'
    assert infer_ast_1.samples == '4'
    assert infer_ast_1.confidence == '.4'
    assert infer_ast_2.samples == '4'
    assert infer_ast_2.confidence == '.4'
    assert infer_ast_3.samples == '4'
    assert infer_ast_3.confidence == '.4'
    assert infer_ast_4.samples == '4'
    assert infer_ast_4.confidence == '.4'
    assert infer_ast_5.samples == '4'
    assert infer_ast_5.confidence == '.4'
    assert infer_ast_6.samples == '4'
    assert infer_ast_6.confidence == '.4'
    assert infer_ast_7.samples == '4'
    assert infer_ast_7.confidence == '.4'
    assert infer_ast_8.samples == '4'
    assert infer_ast_8.confidence == '.4'
    assert infer_ast_9.samples == '4'
    assert infer_ast_9.confidence == '.4'

def test_simulate_pyparsing():
    query_1 = "SIMULATE * FROM table_1 WHERE column_1 = 4 TIMES 4 SAVE TO ~/test.csv"
    simulate_ast = query.parseString(query_1,parseAll=True)
    assert simulate_ast.query_id == 'simulate'
    assert simulate_ast.functions[0].columns[0] == '*'
    assert simulate_ast.where_keyword == 'where'
    assert simulate_ast.times == '4'
    assert simulate_ast.filename == '~/test.csv'
    query_2 = "SIMULATE col1,col2 FROM table_1 WHERE column_1 = 4 TIMES 4 SAVE TO ~/test.csv"
    simulate_ast = query.parseString(query_2,parseAll=True)
    assert simulate_ast.functions[0].columns.asList() == ['col1','col2']

def test_estimate_columns_from_pyparsing():
    query_1 = "ESTIMATE COLUMNS FROM table_1 WHERE col_1 = 4 ORDER BY TYPICALITY LIMIT 10 AS col_list_1"
    est_col_ast_1 = query.parseString(query_1,parseAll=True)
    assert est_col_ast_1.query_id == 'estimate'
    assert est_col_ast_1.btable == 'table_1'
    assert est_col_ast_1.where_keyword == 'where'
    assert est_col_ast_1.where_conditions[0].function.column == 'col_1'
    assert est_col_ast_1.where_conditions[0].value == '4'
    assert est_col_ast_1.order_by.order_by_set[0].function_id == 'typicality'
    assert est_col_ast_1.limit == '10'
    assert est_col_ast_1.as_column_list == 'col_list_1'
    query_2 = "ESTIMATE COLUMNS FROM table_1"
    est_col_ast_2 = query.parseString(query_2,parseAll=True)
    assert est_col_ast_2.query_id == 'estimate'
    assert est_col_ast_2.btable == 'table_1'

def test_estimate_pairwise_pyparsing():
    query_1 = "ESTIMATE PAIRWISE CORRELATION WITH col_1 FROM table_1"
    est_pairwise_ast_1 = query.parseString(query_1,parseAll=True)
    assert est_pairwise_ast_1.query_id == 'estimate pairwise'
    assert est_pairwise_ast_1.functions[0].function_id == 'correlation'
    assert est_pairwise_ast_1.functions[0].with_column == 'col_1'
    assert est_pairwise_ast_1.btable == 'table_1'
    query_2 = "ESTIMATE PAIRWISE DEPENDENCE PROBABILITY WITH col_1 FROM table_1 FOR col_1,col_2 SAVE TO file.csv SAVE CONNECTED COMPONENTS WITH THRESHOLD .4 AS col_list_1"
    est_pairwise_ast_2 = query.parseString(query_2,parseAll=True)
    assert est_pairwise_ast_2.query_id == 'estimate pairwise'
    assert est_pairwise_ast_2.functions[0].function_id == 'dependence probability'
    assert est_pairwise_ast_2.functions[0].with_column == 'col_1'
    assert est_pairwise_ast_2.btable == 'table_1'
    assert est_pairwise_ast_2.columns.asList() == ['col_1','col_2']
    assert est_pairwise_ast_2.filename == 'file.csv'
    assert est_pairwise_ast_2.connected_components_clause.threshold == '.4'
    assert est_pairwise_ast_2.connected_components_clause.as_label == 'col_list_1'
    query_3 = "ESTIMATE PAIRWISE MUTUAL INFORMATION WITH col_1 FROM table_1"
    est_pairwise_ast_3 = query.parseString(query_3,parseAll=True)
    assert est_pairwise_ast_3.functions[0].function_id == 'mutual information'

def test_estimate_pairwise_row_pyparsing():
    query_1 = "ESTIMATE PAIRWISE ROW SIMILARITY FROM table_1 SAVE CONNECTED COMPONENTS WITH THRESHOLD .4 INTO table_2"
    est_pairwise_ast_1 = query.parseString(query_1,parseAll=True)
    assert est_pairwise_ast_1.query_id == 'estimate pairwise'
    assert est_pairwise_ast_1.functions[0] == 'row similarity'
    assert est_pairwise_ast_1.btable == 'table_1'
    query_2 = "ESTIMATE PAIRWISE ROW SIMILARITY FROM table_1 FOR 1,2 SAVE TO file.csv SAVE CONNECTED COMPONENTS WITH THRESHOLD .4 AS table_2"
    est_pairwise_ast_2 = query.parseString(query_2,parseAll=True)
    assert est_pairwise_ast_2.query_id == 'estimate pairwise'
    assert est_pairwise_ast_2.functions[0] == 'row similarity'
    assert est_pairwise_ast_2.btable == 'table_1'
    assert est_pairwise_ast_2.rows.asList() == ['1','2']
    assert est_pairwise_ast_2.filename == 'file.csv'
    assert est_pairwise_ast_2.connected_components_clause.threshold == '.4'
    assert est_pairwise_ast_2.connected_components_clause.as_label == 'table_2'

def test_nested_queries_basic_pyparsing():
    query_1 = "SELECT * FROM ( SELECT col_1,col_2 FROM table_2)"
    ast = query.parseString(query_1,parseAll=True)
    assert ast.query_id == 'select'
    assert ast.sub_query == " SELECT col_1,col_2 FROM table_2"
    ast_2 = query.parseString(ast.sub_query,parseAll=True)
    assert ast_2.query_id == 'select'
    assert ast_2.functions[0].columns.asList() == ['col_1','col_2']

def test_list_btables():
    method, args, client_dict = parser.parse_statement('list btables')
    assert method == 'list_btables'
    assert args == {}

def test_initialize_models():
    method, args, client_dict = parser.parse_statement('initialize 5 models for t')
    assert method == 'initialize_models'
    assert args == dict(tablename='t', n_models=5, model_config=None)

def test_create_btable():
    method, args, client_dict = parser.parse_statement('create btable t from fn')
    assert method == 'create_btable'
    assert args == dict(tablename='t', cctypes_full=None)
    assert client_dict == dict(csv_path=os.path.join(os.getcwd(), 'fn'))

def test_drop_btable():
    method, args, client_dict = parser.parse_statement('drop btable t')
    assert method == 'drop_btable'
    assert args == dict(tablename='t')

def test_drop_models():
    method, args, client_dict = parser.parse_statement('drop models for t')
    assert method == 'drop_models'
    assert args == dict(tablename='t', model_indices=None)

    method, args, client_dict = parser.parse_statement('drop models 2-6 for t')
    assert method == 'drop_models'
    assert args == dict(tablename='t', model_indices=range(2,7))

def test_analyze():
    method, args, client_dict = parser.parse_statement('analyze t models 2-6 for 3 iterations')
    assert method == 'analyze'
    assert args == dict(tablename='t', model_indices=range(2,7), iterations=3, seconds=None, ct_kernel=0)

    method, args, client_dict = parser.parse_statement('analyze t for 6 iterations')
    assert method == 'analyze'
    assert args == dict(tablename='t', model_indices=None, iterations=6, seconds=None, ct_kernel=0)

    method, args, client_dict = parser.parse_statement('analyze t for 7 seconds')
    assert method == 'analyze'
    assert args == dict(tablename='t', model_indices=None, iterations=None, seconds=7, ct_kernel=0)
    
    method, args, client_dict = parser.parse_statement('analyze t models 2-6 for 7 seconds')
    assert method == 'analyze'
    assert args == dict(tablename='t', model_indices=range(2,7), iterations=None, seconds=7, ct_kernel=0)

    method, args, client_dict = parser.parse_statement('analyze t models 2-6 for 7 seconds with mh kernel')
    assert method == 'analyze'
    assert args == dict(tablename='t', model_indices=range(2,7), iterations=None, seconds=7, ct_kernel=1)    

def test_load_models():
    method, args, client_dict = parser.parse_statement('load models fn for t')
    assert method == 'load_models'
    assert args == dict(tablename='t')
    assert client_dict == dict(pkl_path='fn')

def test_save_models():
    method, args, client_dict = parser.parse_statement('save models for t to fn')
    assert method == 'save_models'
    assert args == dict(tablename='t')
    assert client_dict == dict(pkl_path='fn')

def test_select():
    tablename = 't'
    columnstring = '*'
    whereclause = ''
    limit = float('inf')
    order_by = False
    plot = False

    method, args, client_dict = parser.parse_statement('select * from t')
    d = dict(tablename=tablename, columnstring=columnstring, whereclause=whereclause,
             limit=limit, order_by=order_by, plot=plot, modelids=None, summarize=False)
    assert method == 'select'
    assert args == d

    method, args, client_dict = parser.parse_statement('summarize select * from t')
    d = dict(tablename=tablename, columnstring=columnstring, whereclause=whereclause,
             limit=limit, order_by=order_by, plot=plot, modelids=None, summarize=True)
    assert method == 'select'
    assert args == d
    
    columnstring = 'a, b, a_b'
    method, args, client_dict = parser.parse_statement('select a, b, a_b from t')
    d = dict(tablename=tablename, columnstring=columnstring, whereclause=whereclause,
             limit=limit, order_by=order_by, plot=plot, modelids=None, summarize=False)
    assert method == 'select'
    assert args == d

    whereclause = 'a=6 and b = 7'
    columnstring = '*'
    method, args, client_dict = parser.parse_statement('select * from t where a=6 and b = 7')
    d = dict(tablename=tablename, columnstring=columnstring, whereclause=whereclause,
             limit=limit, order_by=order_by, plot=plot, modelids=None, summarize=False)
    assert method == 'select'
    assert args == d

    limit = 10
    method, args, client_dict = parser.parse_statement('select * from t where a=6 and b = 7 limit 10')
    d = dict(tablename=tablename, columnstring=columnstring, whereclause=whereclause,
             limit=limit, order_by=order_by, plot=plot, modelids=None, summarize=False)
    assert method == 'select'
    assert args == d

    order_by = [('b', True)]
    method, args, client_dict = parser.parse_statement('select * from t where a=6 and b = 7 order by b limit 10')
    d = dict(tablename=tablename, columnstring=columnstring, whereclause=whereclause,
             limit=limit, order_by=order_by, plot=plot, modelids=None, summarize=False)
    assert method == 'select'
    assert args == d

def test_simulate():
    tablename = 't'
    newtablename = ''
    columnstring = ''
    whereclause = ''
    order_by = ''
    numpredictions = ''
    d = dict(tablename=tablename, columnstring=columnstring, whereclause=whereclause,
             newtablename=newtablename, order_by=order_by, numpredictions=numpredictions)
    

def test_infer():
    tablename = 't'
    newtablename = ''
    columnstring = ''
    confidence = ''
    whereclause = ''
    limit = ''
    numsamples = ''
    order_by = ''
    d = dict(tablename=tablename, columnstring=columnstring, whereclause=whereclause,
             newtablename=newtablename, order_by=order_by, numsamples=numsamples, confidence=confidence)


#SELECT <columns> FROM <btable> [WHERE <whereclause>] [LIMIT <limit>] [ORDER BY <columns>]

#INFER <columns> FROM <btable> [WHERE <whereclause>] [WITH CONFIDENCE <confidence>] [LIMIT <limit>] [WITH <numsamples> SAMPLES] [ORDER BY <columns]

#SIMULATE <columns> FROM <btable> [WHERE <whereclause>] TIMES <times> [ORDER BY <columns>]

########NEW FILE########
__FILENAME__ = utils
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import inspect
import numpy
import os
import re
import inspect
import ast
import pylab
import matplotlib.cm
import time
import pandas

import data_utils as du
import select_utils
import functions

class BayesDBError(Exception):
    """ Base class for all other exceptions in this module. """
    pass

class BayesDBParseError(BayesDBError):
    def __init__(self, msg=None):
        if msg:
            self.msg = msg
        else:
            self.msg = "BayesDB parsing error. Try using 'help' to see the help menu for BQL syntax."
    
    def __str__(self):
        return self.msg

class BayesDBNoModelsError(BayesDBError):
    def __init__(self, tablename):
        self.tablename = tablename

    def __str__(self):
        return "Btable %s has no models, but this command requires models. Please create models first with INITIALIZE MODELS, and then ANALYZE." % self.tablename

class BayesDBInvalidBtableError(BayesDBError):
    def __init__(self, tablename):
        self.tablename = tablename

    def __str__(self):
        return "Btable %s does not exist. Please create it first with CREATE BTABLE, or view existing btables with LIST BTABLES." % self.tablename

class BayesDBColumnDoesNotExistError(BayesDBError):
    def __init__(self, column, tablename):
        self.column = column
        self.tablename = tablename

    def __str__(self):
        return "Column %s does not exist in btable %s." % (self.column, self.tablename)

class BayesDBColumnListDoesNotExistError(BayesDBError):
    def __init__(self, column_list, tablename):
        self.column_list = column_list
        self.tablename = tablename

    def __str__(self):
        return "Column list %s does not exist in btable %s." % (self.column_list, self.tablename)

class BayesDBRowListDoesNotExistError(BayesDBError):
    def __init__(self, row_list, tablename):
        self.row_list = row_list
        self.tablename = tablename

    def __str__(self):
        return "Row list %s does not exist in btable %s." % (self.row_list, self.tablename)
        
        
def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False    

def is_float(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def infer(M_c, X_L_list, X_D_list, Y, row_id, col_id, numsamples, confidence, engine):
    q = [row_id, col_id]
    out = engine.call_backend('impute_and_confidence', dict(M_c=M_c, X_L=X_L_list, X_D=X_D_list, Y=Y, Q=[q], n=numsamples))
    code, conf = out
    if conf >= confidence:
      return code
    else:
      return None

def check_for_duplicate_columns(column_names):
    column_names_set = set()
    for name in column_names:
        if name in column_names_set:
            raise BayesDBError("Error: Column list has duplicate entries of column: %s" % name)
        column_names_set.add(name)
    

def get_all_column_names_in_original_order(M_c):
    colname_to_idx_dict = M_c['name_to_idx']
    colnames = map(lambda tup: tup[0], sorted(colname_to_idx_dict.items(), key=lambda tup: tup[1]))
    return colnames

def get_cctype_from_M_c(M_c, column):
    if column in M_c['name_to_idx'].keys():
        column_index = M_c['name_to_idx'][column]
        modeltype = M_c['column_metadata'][column_index]['modeltype']
        cctype = 'continuous' if modeltype == 'normal_inverse_gamma' else 'multinomial'
    else:
        # If the column name wasn't found in metadata, it's a function, so the output will be continuous
        cctype = 'continuous'
    return cctype

def summarize_table(data, columns, M_c):
    """
    Returns a summary of the data.
    Input: data is a list of lists, of raw data values about to be shown to the user.
    Input: columns is a list of column names, as they will be displayed to the user. Note
    that some column names may be things like "row_id" or predictive functions, not actually
    columns.

    Return: columns should be the same, except with another column prepended called like "summaries" or something.
    Return: data should be summaries now.
    """
    # The 'inplace' argument to df.drop() was added to pandas in a version (which one??) that many people may
    # not have. So, check to see if 'inplace' exists, otherwise don't pass it -- this just copies the dataframe.
    def df_drop(df, column_list, **kwargs):
        if 'inplace' in inspect.getargspec(df.drop).args:
            df.drop(column_list, inplace=True, **kwargs)
        else:
            df = df.drop(column_list, **kwargs)

    if len(data) > 0:
        # Construct a pandas.DataFrame out of data and columns
        df = pandas.DataFrame(data=data, columns=columns)

        # Remove row_id column since summary stats of row_id are meaningless
        if 'row_id' in df.columns:
            df_drop(df, ['row_id'], axis=1)

        # Get column types as one-row DataFrame
        cctypes = pandas.DataFrame([[get_cctype_from_M_c(M_c, col) for col in df.columns]], columns=df.columns, index=['type'])

        # Run pandas.DataFrame.describe() on each column - it'll compute every stat that it can for each column,
        # depending on its type (assume it's not a problem to overcompute here - for example, computing a mean on a
        # discrete variable with numeric values might not have meaning, but it's easier just to do it and
        # leave interpretation to the user, rather than try to figure out what's meaningful, especially with
        # columns that are the result of predictive functions.
        summary_describe = df.apply(pandas.Series.describe)

        # If there were discrete columns, remove 'top' and 'freq' rows, because we'll replace those
        # with the mode and empirical probabilities
        if 'top' in summary_describe.index and 'freq' in summary_describe.index:
            summary_describe = summary_describe.drop(['top', 'freq'])

        # Function to calculate the most frequent values for each column
        def get_column_freqs(x, n=5):
            """
            Function to return most frequent n values of each column of the DataFrame being summarized.
            Input: a DataFrame column, by default as Series type

            Return: most frequent n values in x. Fill with numpy.nan if fewer than n unique values exist.
            """
            x_freqs  = x.value_counts()
            x_probs  = list(x_freqs / len(x))
            x_values = list(x_freqs.index)

            if len(x_values) > n:
                x_probs = x_probs[:n]
                x_values = x_values[:n]

            # Create index labels ('mode1/2/3/... and prob_mode1/2/3...')
            x_range = range(1, len(x_values) + 1)
            x_index = ['mode' + str(i) for i in x_range]
            x_index += ['prob_mode' + str(i) for i in x_range]

            # Combine values and probabilities into a single list
            x_values.extend(x_probs)

            return pandas.Series(data = x_values, index = x_index)

        summary_freqs = df.apply(get_column_freqs)

        # Attach continuous and discrete summaries along row axis (unaligned values will be assigned NaN)
        summary_data = pandas.concat([cctypes, summary_describe, summary_freqs], axis=0)

        # Reorder rows: count, unique, mean, std, min, 25%, 50%, 75%, max, modes, prob_modes
        if hasattr(summary_data, 'loc'):
            potential_index = pandas.Index(['type', 'count', 'unique', 'mean', 'std', 'min', '25%', '50%', '75%', 'max', \
                'mode1', 'mode2', 'mode3', 'mode4', 'mode5', \
                'prob_mode1', 'prob_mode2', 'prob_mode3', 'prob_mode4', 'prob_mode5'])

            reorder_index = potential_index[potential_index.isin(summary_data.index)]
            summary_data = summary_data.loc[reorder_index]

        # Insert column of stat descriptions - we're going to leave this column name as a single space to avoid
        # having to prevent column name duplication (allow_duplicates is a newer pandas argument, and can't be sure it's available)
        summary_data.insert(0, ' ', summary_data.index)

        data = summary_data.to_records(index=False)
        columns = list(summary_data.columns)

    return data, columns

def column_string_splitter(columnstring, M_c=None, column_lists=None):
    """
    If '*' is a possible input, M_c must not be None.
    If column_lists is not None, all column names are attempted to be expanded as a column list.
    """
    paren_level = 0
    output = []
    current_column = []

    def end_column(current_column, output):
      if '*' in current_column:
        assert M_c is not None
        output += get_all_column_names_in_original_order(M_c)
      else:
        current_column_name = ''.join(current_column)
        if column_lists and current_column_name in column_lists.keys():
            ## First, check if current_column is a column_list
            output += column_lists[current_column_name]
        else:
            ## If not, then it is a normal column name: append it.            
            output.append(current_column_name.strip())
      return output
    
    for i,c in enumerate(columnstring):
      if c == '(':
        paren_level += 1
      elif c == ')':
        paren_level -= 1

      if (c == ',' and paren_level == 0):
        output = end_column(current_column, output)
        current_column = []
      else:
        current_column.append(c)
    output = end_column(current_column, output)
    return output

    

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# BayesDB documentation build configuration file, created by
# sphinx-quickstart on Wed Oct  9 00:37:57 2013.
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
sys.path.insert(0, os.path.abspath('../../bayesdb'))
sys.path.insert(0, os.path.abspath('../../bayesdb/tests'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

pdf_documents = [('index', u'rst2pdf', u'BayesDB Doc', u'Jay Baxter'),]

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.intersphinx', 'sphinx.ext.todo', 'sphinx.ext.coverage', 'sphinx.ext.pngmath', 'sphinx.ext.viewcode', 'IPython.sphinxext.ipython_directive', 'rst2pdf.pdfbuilder']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'BayesDB'
copyright = u'2014, Jay Baxter, Dan Lovell, Vikash Mansinghka, Pat Shafto, Baxter Eaves'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.2'
# The full version, including alpha/beta/rc tags.
release = '0.2.0-alpha'

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
htmlhelp_basename = 'BayesDBdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'BayesDB.tex', u'BayesDB Documentation',
   u'Jay Baxter, Dan Lovell, Vikash Mansinghka, Pat Shafto, Baxter Eaves', 'manual'),
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

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'bayesdb', u'BayesDB Documentation',
     [u'Jay Baxter, Dan Lovell, Vikash Mansinghka, Pat Shafto, Baxter Eaves'], 1)
]


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = run_chicago_example
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import os
import sys
from bayesdb.client import Client

def run_example():
    client = Client()
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(cur_dir, 'chicago_small_analysis.bql')
    print "\nA series of BQL commands will be displayed. Hit <Enter> to execute the displayed command.\n"
    client(open(file_path, 'r'), wait=True)

if __name__ == '__main__':
    run_example()

########NEW FILE########
__FILENAME__ = run_dha_example
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import os
import sys
from bayesdb.client import Client

def run_example():
    client = Client()
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(cur_dir, 'dha_analysis.bql')
    print "\nA series of BQL commands will be displayed. Hit <Enter> to execute the displayed command.\n"
    client(open(file_path, 'r'), wait=True)

if __name__ == '__main__':
    run_example()

########NEW FILE########
__FILENAME__ = run_employees_example
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import os
import sys
from bayesdb.client import Client

def run_example():
    client = Client()
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(cur_dir, 'employees_analysis.bql')
    print "\nA series of BQL commands will be displayed. Hit <Enter> to execute the displayed command.\n"
    client(open(file_path, 'r'), wait=True)

if __name__ == '__main__':
    run_example()

########NEW FILE########
__FILENAME__ = run_flights_example
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import os
import sys
from bayesdb.client import Client

def run_example():
    client = Client()
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(cur_dir, 'flights_analysis.bql')
    print "\nA series of BQL commands will be displayed. Hit <Enter> to execute the displayed command.\n"
    client(open(file_path, 'r'), wait=True)

if __name__ == '__main__':
    run_example()

########NEW FILE########
__FILENAME__ = run_gss_example
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import os
import sys
from bayesdb.client import Client

def run_example():
    client = Client()
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(cur_dir, 'gss_analysis.bql')
    print "\nA series of BQL commands will be displayed. Hit <Enter> to execute the displayed command.\n"
    client(open(file_path, 'r'), wait=True)

if __name__ == '__main__':
    run_example()

########NEW FILE########
__FILENAME__ = run_kiva_example
#
#   Copyright (c) 2010-2014, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import os
import sys
from bayesdb.client import Client

def run_example():
    client = Client()
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(cur_dir, 'kiva_analysis.bql')
    print "\nA series of BQL commands will be displayed. Hit <Enter> to execute the displayed command.\n"
    client(open(file_path, 'r'), wait=True)

if __name__ == '__main__':
    run_example()

########NEW FILE########
