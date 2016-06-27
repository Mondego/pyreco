"""relevant method: close"""
import os

command = " "
while (command != "exit"):
    command = raw_input("Command: ")
    handle = os.popen(command)
    line = " "
    while line:
        line = handle.read()
        print line
    handle.
