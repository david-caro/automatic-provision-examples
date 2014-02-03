#!/usr/bin/env python
#encoding: utf-8
"""
Some examples:

* See the list of available tasks.
    ~# fab --list
* Execute the given task with the given parameter:
    ~# fab mytask:myparam=myvalue
* or (using positional parameters)
    ~# fab mytask:myvalue
* Execute the given task on a host range:
    ~# fab hostrange:myhost10:20range mytask
* or using letter ranges
    ~# fab hostrange:myhostA:Zrange mytask
* Execute an arbitrary command (ls -la):
    ~# fab on.hostrange:myhost10:20range -- ls -la
"""

import sys
import os
import fabric
## Fix the path to include the fabfiles
sys.path.append(os.path.abspath(os.path.dirname(__file__).rsplit('/', 1)[0]))
from fabric_ci.lib.parallel import monkey_patch
monkey_patch(fabric)


def load_from_mod(mod, basename):
    """
    Load all the modules and packages for the given module
    """
    path = os.path.dirname(mod.__file__)
    to_load = []
    for dirpath, dirnames, filenames in os.walk(path):
        for fname in filenames:
            if fname.startswith('__') or not fname.endswith('.py'):
                continue
            to_load.append(fname[:-3])
        to_load.extend(dirnames)
        modname = dirpath.replace(basename + '/', '').replace('/', '.')
        break
    mod = __import__(modname.rsplit('.', 1)[0], locals(), globals(), to_load)
    globals()[modname] = mod


def load_tasks():
    """
    Load the tasks defined in thedirectories 'on', 'do' and 'out'.
    """
    mydir = os.path.abspath(os.path.dirname(__file__))
    for dirname in ('on', 'do'):
        globals()[dirname] = __import__(dirname, locals(), globals())
        load_from_mod(globals()[dirname], mydir)


load_tasks()
