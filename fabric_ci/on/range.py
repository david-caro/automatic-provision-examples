#!/usr/bin/env python
"""
This task allows you to define a range of hosts like this:
    myhost01:10.mydomain.com
    myhostA:Z.mydomain.com
"""

from fabric.api import serial, task, runs_once, env
import re


def range_expand(range_def):
    """
    :param range_def:
        Range definition

    Generates a list of strings expanding the first match of the range
    letter:letter or int:int on the given string.
    """
    res = []
    range_exp = r'((?P<digit>\d+:\d+)|(?P<char>[a-zA-Z]:[a-zA-Z]))'
    comp_reg = re.compile(range_exp)
    match = comp_reg.search(range_def)
    if not match:
        return [range_def]
    for mtype, val in match.groupdict().iteritems():
        if val == None:
            continue
        prestr = range_def[:match.start()]
        poststr = range_def[match.end():]
        prechar, postchar = val.split(':')
        if mtype == 'char':
            for i in range(ord(prechar), ord(postchar) + 1):
                res.append(prestr + chr(i) + poststr)
        elif mtype == 'digit':
            padding = len(prechar)
            for i in range(int(prechar), int(postchar) + 1):
                res.append("{0}{1}{2}".format(prestr,
                                               str(i).zfill(padding),
                                               poststr))
    return res


@task(default=True)
@runs_once
@serial
def hostrange(*args):
    r"""
    :param \*args:
        List of hosts/host ranges

    Use the given host range as target hosts.
    A range is defined by a ':'  between chars or numbers.
    example::

        host1:10  -> host1, host2, ..., host10
        hostA-Z -> hostA, hostB, ..., hostZ
    """
    for host_range in args:
        env.hosts.extend(range_expand(host_range))
