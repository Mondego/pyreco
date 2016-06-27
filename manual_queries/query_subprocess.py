"""Relevant method: communicate"""
import subprocess

print '\nread:'
proc = subprocess.Popen(['echo', '"to stdout"'], 
                        stdout=subprocess.PIPE,
                        )
stdout_value = proc.
