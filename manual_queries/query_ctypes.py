"""Relevant method:raw"""
from ctypes import *
p = create_string_buffer(3)      # create a 3 byte buffer, initialized to NUL bytes
print sizeof(p), repr(p.
