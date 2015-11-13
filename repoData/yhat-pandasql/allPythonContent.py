__FILENAME__ = demo
from sklearn.datasets import load_iris
import pandas as pd
from pandasql import sqldf
from pandasql import load_meat, load_births
import re


births = load_births()
meat = load_meat()
iris = load_iris()
iris_df = pd.DataFrame(iris.data, columns=iris.feature_names)
iris_df['species'] = pd.Categorical(iris.target, levels=iris.target_names)
iris_df.columns = [re.sub("[() ]", "", col) for col in iris_df.columns]

print sqldf("select * from iris_df limit 10;", locals())
print sqldf("select sepalwidthcm, species from iris_df limit 10;", locals())

q = """
      select
        species
        , avg(sepalwidthcm)
        , min(sepalwidthcm)
        , max(sepalwidthcm)
      from
        iris_df
      group by
        species;
        
"""
print "*"*80
print "aggregation"
print "-"*80
print q
print sqldf(q, locals())


def pysqldf(q):
    "add this to your script if you get tired of calling locals()"
    return sqldf(q, globals())

print "*"*80
print "calling from a helper function"
print '''def pysqldf(q):
    "add this to your script if you get tired of calling locals()"
        return sqldf(q, globals())'''
print "-"*80
print q
print pysqldf(q)


q = """
    select
        a.*
    from
        iris_df a
    inner join
        iris_df b
            on a.species = b.species
    limit 10;
"""

print "*"*80
print "joins"
print "-"*80
print q
print pysqldf(q)


q = """
    select
        *
    from
        iris_df
    where
        species = 'virginica'
        and sepallengthcm > 7.7;
"""
print "*"*80
print "where clause"
print "-"*80
print q
print pysqldf(q)
iris_df['id'] = range(len(iris_df))
q = """
    select
        *
    from
        iris_df
    where
        id in (select id from iris_df where sepalwidthcm*sepallengthcm > 25);
"""
print "*"*80
print "subqueries"
print "-"*80
print q
print pysqldf(q)

q = """
    SELECT
        m.*
        , b.births
    FROM
        meat m
    INNER JOIN
        births b
            on m.date = b.date
    ORDER BY
        m.date;
"""

print pysqldf(q).head()


########NEW FILE########
__FILENAME__ = sqldf
import sqlite3 as sqlite
import sqlparse
from sqlparse.tokens import Whitespace
import pandas as pd
import numpy as np
from pandas.io.sql import write_frame, frame_query
import os
import re

def _ensure_data_frame(obj, name):
    """
    obj a python object to be converted to a DataFrame

    take an object and make sure that it's a pandas data frame
    """
    #we accept pandas Dataframe, and also dictionaries, lists, tuples
        #we'll just convert them to Pandas Dataframe
    if isinstance(obj, pd.DataFrame):
        df = obj
    elif isinstance(obj, (tuple, list)) :
        #tuple and list case
        if len(obj)==0:
            return pd.Dataframe()

        firstrow = obj[0]

        if isinstance(firstrow, (tuple, list)):
            #multiple-columns
            colnames = ["c%d" % i for i in range(len(firstrow))]
            df = pd.DataFrame(obj, columns=colnames)
        else:
            #mono-column
            df = pd.DataFrame(obj, columns=["c0"])

    if not isinstance(df, pd.DataFrame) :
        raise Exception("%s is not a Dataframe, tuple, list, nor dictionary" % name)

    for col in df:
        if df[col].dtype==np.int64:
            df[col] = df[col].astype(np.float)

    return df

def _extract_table_names(q):
    "extracts table names from a sql query"

    tables = set()
    next_is_table = False
    for query in sqlparse.parse(q):
        for token in query.tokens:
            if token.value.upper() == "FROM" or "JOIN" in token.value.upper():
                next_is_table = True
            elif token.ttype is Whitespace:
                continue
            elif token.ttype is None and next_is_table:
                tables.add(token.value)
                next_is_table = False
    return list(tables)


def _write_table(tablename, df, conn):
    "writes a dataframe to the sqlite database"

    for col in df.columns:
        if re.search("[() ]", col):
            msg = "please follow SQLite column naming conventions: "
            msg += "http://www.sqlite.org/lang_keywords.html"
            raise Exception(msg)

    write_frame(df, name=tablename, con=conn, flavor='sqlite')


def sqldf(q, env, inmemory=True):
    """
    query pandas data frames using sql syntax

    q: a sql query using DataFrames as tables
    env: variable environment; locals() or globals() in your function
         allows sqldf to access the variables in your python environment
    dbtype: memory/disk
        default is in memory; if not memory then it will be temporarily
        persisted to disk

    Example
    -----------------------------------------

    # example with a data frame
    df = pd.DataFame({
        x: range(100),
        y: range(100)
    })

    from pandasql import sqldf
    sqldf("select * from df;", locals())
    sqldf("select avg(x) from df;", locals())

    #example with a list

    """

    if inmemory:
        dbname = ":memory:"
    else:
        dbname = ".pandasql.db"
    conn = sqlite.connect(dbname, detect_types=sqlite.PARSE_DECLTYPES)
    tables = _extract_table_names(q)
    for table in tables:
        if table not in env:
            conn.close()
            if not inmemory :
                os.remove(dbname)
            raise Exception("%s not found" % table)
        df = env[table]
        df = _ensure_data_frame(df, table)
        _write_table(table, df, conn)

    try:
        result = frame_query(q, conn)
    except:
        result = None
    finally:
        conn.close()
        if not inmemory:
            os.remove(dbname)
    return result


########NEW FILE########
__FILENAME__ = tests
import pandas as pd
from pandasql import sqldf
import string
import unittest


class PandaSQLTest(unittest.TestCase):

    def setUp(self):
        return

    def test_select(self):
        df = pd.DataFrame({
                 "letter_pos": [i for i in range(len(string.ascii_letters))],
                 "l2": list(string.ascii_letters)
        })
        result = sqldf("select * from df LIMIT 10;", locals())
        self.assertEqual(len(result), 10)

    def test_join(self):

        df = pd.DataFrame({
            "letter_pos": [i for i in range(len(string.ascii_letters))],
            "l2": list(string.ascii_letters)
        })

        df2 = pd.DataFrame({
            "letter_pos": [i for i in range(len(string.ascii_letters))],
            "letter": list(string.ascii_letters)
        })

        result = sqldf("SELECT a.*, b.letter FROM df a INNER JOIN df2 b ON a.l2 = b.letter LIMIT 20;", locals())
        self.assertEqual(len(result), 20)

    def test_query_with_spacing(self):

        df = pd.DataFrame({
            "letter_pos": [i for i in range(len(string.ascii_letters))],
            "l2": list(string.ascii_letters)
        })

        df2 = pd.DataFrame({
            "letter_pos": [i for i in range(len(string.ascii_letters))],
            "letter": list(string.ascii_letters)
        })
        
        result = sqldf("SELECT a.*, b.letter FROM df a INNER JOIN df2 b ON a.l2 = b.letter LIMIT 20;", locals())
        self.assertEqual(len(result), 20)

        q = """
            SELECT
            a.*
        FROM
            df a
        INNER JOIN
            df2 b
        on a.l2 = b.letter
        LIMIT 20
        ;"""
        result = sqldf(q, locals())
        self.assertEqual(len(result), 20)

    def test_query_single_list(self):

        mylist = [i for i in range(10)]

        result = sqldf("SELECT * FROM mylist", locals())
        self.assertEqual(len(result), 10)

    def test_query_list_of_lists(self):

        mylist = [[i for i in range(10)], [i for i in range(10)]]

        result = sqldf("SELECT * FROM mylist", locals())
        self.assertEqual(len(result), 2)

    def test_query_list_of_tuples(self):

        mylist = [tuple([i for i in range(10)]), tuple([i for i in range(10)])]

        result = sqldf("SELECT * FROM mylist", locals())
        self.assertEqual(len(result), 2)


if __name__=="__main__":
    unittest.main()


########NEW FILE########
