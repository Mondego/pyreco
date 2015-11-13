__FILENAME__ = extend_example
from mapper import ObjectMapper

class Person(object):

    def __init__(self):

        self.name = 'john'
        self.age = 22

        #this properties are ignored
        self._some_information = 'Not saved in table'
        self.__other_stuff = 'Also ignored'


class PersonMapper(ObjectMapper):
    """
        This class overrides get_table and get_id methods to
        customize the ObjectMapper according to the tables I have.

        Usage demo and tests

        >>> p = Person()
        >>> m = PersonMapper(p)

        >>> m.insert()
        ("INSERT INTO people(age,name) VALUES ('?','?')", '22', 'john')

        >>> m.get_by_id(id=1)
        ('SELECT age, name FROM people WHERE id_people = ?', 1)

        >>> m.get_all()
        'SELECT age, name FROM people'

        >>> m.delete(id=1)
        ('DELETE FROM people WHERE id_people = ?', 1)

        >>> m.update(id=1)
        ("UPDATE people SET age = '?', name = '?' WHERE id_people = ?", '22', 'john', 1)
    """

    def get_table(self):
        """
            Returns the table name
        """

        return "people"

    def get_id(self):
        """
            Returns the id field name
        """

        return "id_people"


if __name__ == '__main__':

    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = mapper
"""
    Python data layer generator
    Author: Juan MAnuel Garcia <jmg.utn@gmail.com>
"""

class ObjectMapper(object):

    SQL_PARAM_SYMBOL = "?"

    def __init__(self, entity):
        self.entity = entity

    def _get_pairs(self):
        return [(k,str(v)) for k,v in self.entity.__dict__.iteritems() if not k.startswith("_") and not k.startswith("__")]

    def _get_names(self):
        return [pair[0] for pair in self._get_pairs()]

    def _get_values(self):
        return [pair[1] for pair in self._get_pairs()]

    def _get_names_values(self):
        return self._get_names(), self._get_values()

    def insert(self):
        names, values = self._get_names_values()
        names = "%s" % ",".join(names)
        params = ",".join(["'?'" for x in values])
        return ("INSERT INTO %s(%s) VALUES (%s)" % (self.get_table(), names, params), ) + tuple(values)

    def update(self, id):
        pairs = self._get_pairs()
        fields = ", ".join(["%s = '%s'" % (k, self.SQL_PARAM_SYMBOL) for k,v in pairs])
        values = self._get_values()
        return ("UPDATE %s SET %s WHERE %s = %s" % (self.get_table(), fields, self.get_id(), self.SQL_PARAM_SYMBOL), ) + tuple(values) + (id, )

    def delete(self, id):
        return ("DELETE FROM %s WHERE %s = %s" % (self.get_table(), self.get_id(), self.SQL_PARAM_SYMBOL), id)

    def get_all(self):
        names = ", ".join(self._get_names())
        return "SELECT %s FROM %s" % (names, self.get_table())

    def get_by_id(self, id):
        names = ", ".join(self._get_names())
        return ("SELECT %s FROM %s WHERE %s = %s" % (names, self.get_table(), self.get_id(), self.SQL_PARAM_SYMBOL), id)

    #Overridables

    #You can Extend from this class and override the following methods in order to configurate
    #the table name and the id_name

    def get_table(self):
        return self.entity.__class__.__name__.lower()

    def get_id(self):
        return "id_%s" % self.entity.__class__.__name__.lower()

########NEW FILE########
__FILENAME__ = tests
import unittest
from mapper import ObjectMapper

class Person(object):

    def __init__(self):

        self.name = 'john'
        self.age = 22

        #this properties are ignored
        self._some_information = 'Not saved in table'
        self.__other_stuff = 'Also ignored'


class TestMapper(unittest.TestCase):

    def setUp(self):

        p = Person()
        self.m = ObjectMapper(p)

    def test_insert(self):
        self.assertEquals(self.m.insert(), ("INSERT INTO person(age,name) VALUES ('?','?')", '22', 'john'))

    def test_get_by_id(self):
        self.assertEquals(self.m.get_by_id(id=1), ('SELECT age, name FROM person WHERE id_person = ?', 1))

    def test_select_all(self):
        self.assertEquals(self.m.get_all(), "SELECT age, name FROM person")

    def test_delete(self):
        self.assertEquals(self.m.delete(id=1), ('DELETE FROM person WHERE id_person = ?', 1))

    def test_update(self):
        self.assertEquals(self.m.update(id=1), ("UPDATE person SET age = '?', name = '?' WHERE id_person = ?", '22', 'john', 1))


unittest.main()

########NEW FILE########
