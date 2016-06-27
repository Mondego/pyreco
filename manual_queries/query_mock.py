"""Relevant method:_fooValue"""
from mock import Mock
fooSpec = ["_fooValue", "callFoo", "doFoo"]
mockFoo = Mock(spec = fooSpec)
print mockFoo
print mockFoo.
