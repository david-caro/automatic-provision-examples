#!/usr/bin/env python
#encoding: utf-8
"""
Fabric decorets mess up all the autoloading of the functions, so to generate
the doc we must read the source files...
"""

import os
import sys
from importlib import import_module
from subprocess import call
from itertools import chain

PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(PATH)


def get_iter_tasks_from_file(task_fd):
    fun_path = task_fd.name[len(PATH) + 1:].replace('/', '.')
    for line in task_fd:
        if line.startswith('def '):
            name, sig = line[4:].split(':')[0].split('(')
            yield fun_path[:-3] + '.' + name, '(' + sig, 'autofunction'
        elif line.startswith('class '):
            name, sig = line[6:].split(':')[0].split('(')
            yield fun_path[:-3] + '.' + name, '', 'autoclass'


def get_task_files(file, flatten=True):
    if os.path.isdir(file):
        if file.split('/')[-1] == 'doc':
            return []
        res = [get_task_files(file + '/' + x) for x in os.listdir(file)
               if get_task_files(file + '/' + x)]
        if flatten:
            return list(chain.from_iterable(res))
        else:
            return res
    else:
        if file.endswith('.py') and not file.split('/')[-1].startswith('__'):
            return [open(file, 'r')]
        else:
            return []


def footer(doc):
    doc.write("""
Indices and tables
============================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
""")
    doc.close()


def header(doc):
    doc.write("""
Welcome to fabric_ci's documentation!
====================================

Here is a list of the available tasks for CI's fabric module

.. toctree::
    :titlesonly:

""")


def document_dir(directory, doc):
    module_docs = {}
    for task_file in get_task_files(PATH + '/fabric_ci/' + directory):
        module = task_file.name[len(PATH) + 1:][:-3].replace('/', '.')
        task_mod = import_module(module)
        if module not in module_docs:
            module_docs[module] = open('{0}.rst'.format(module[10:]), 'w')
            module_docs[module].write("""
{0}
=====================
.. currentmodule:: {0}

{1}

    """.format(module[10:], task_mod.__doc__ or ''))
        doc.write('    {0}\n'.format(module[10:]))
        try:
            for task_func_name, task_sig, doc_cmd \
                    in get_iter_tasks_from_file(task_file):
                module_docs[module].write("""
.. {2}:: {0}{1}
""".format(task_func_name, task_sig, doc_cmd))
        except Exception as e:
            print "Exception: {0}".format(e)
            raise
    return module_docs


def main():
    ## delete old rst files
    for x in os.listdir('.'):
        if x.endswith('.rst'):
            os.remove(x)
    ## main index file
    doc = open('index.rst', 'w')
    header(doc)
    sys.path.insert(0, PATH)
    module_docs = {}
    for directory in ('lib', 'do', 'out', 'on'):
        module_docs.update(document_dir(directory, doc))
    for open_mod in module_docs.itervalues():
        open_mod.close()
    footer(doc)
    ## generate the html files
    os.environ['PYTHONPATH'] = ':'.join(sys.path)
    call(['make', 'html'])


if __name__ == '__main__':
    main()
