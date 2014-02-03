#!/usr/bin/env python
#encoding: utf-8
"""
Fetch facts from the given hosts, using facteri
"""

from fabric.api import task, runs_once, hide, settings, run, execute
## json ruby gems are not usually installed, yaml comes with stdlib
import yaml
import sys
from pprint import pprint


def get_fact_obj(fname):
    """
    Retrieves the given facts, you can specify multiple facts and aliases like
    this: "fname|alias fname2|alias2"

    :param fname:
        Facts string, can be in the form "fname|alias1 fname2|alias2"
    """
    facts_alias = {}
    for fact in fname.split(' '):
        if not fact:
            continue
        if '|' in fact:
            fact, alias = fact.split('|')
        else:
            alias = fact
        facts_alias[fact] = alias
    with hide('running', 'warnings', 'stdout'):
        out = run("facter -y %s" % ' '.join(facts_alias.keys()))
    facts = yaml.load(out)
    if facts_alias:
        facts = dict(((facts_alias[f], v) for f, v in facts.iteritems()))
    return facts


@task(default=True)
@runs_once
def get(fname='', show=True):
    """
    Retrieves the given facts, you can specify multiple facts and aliases like
    this: "fname|alias fname2|alias2"

    It is actually just a wrapper of get_fact_obj to parallelize the fact
    fetching

    :param fname:
        Facts string, can be in the form "fname|alias1 fname2|alias2", all by
        default
    """
    with hide('stdout', 'stderr', 'aborts', 'warnings'):
        with settings(hide('running', 'warnings', 'stdout'),
                      warn_only=True):
            res = execute(get_fact_obj, fname)
    if show:
        pprint(res)
        sys.stdout.flush()
    else:
        return res
