#!/usr/bin/env python
#encoding: utf-8
"""
This module provides the capability to select hosts from foreman with a search
string.
"""


from fabric.api import task, runs_once, serial, env, abort, prompt
from fabric_ci.lib.foreman import foreman_defaults
from fabric_ci.lib.utils import (
    yellow,
    absolute_import,
)


## To avoid collisions with local module
frm_cli = absolute_import('foreman.client', ['Foreman'])


@task(default=True)
@runs_once
@serial
@foreman_defaults
def search(firstcond='', sure='no', foreman=None, user=None, passwd=None, *conds, **kwconds):
    """
    Use the given foreman search result as the hosts list.

    :param sure:
        If set to `yes`, it will not ask for confirmation before running.
    :param foreman:
        The foreman server url, like 'http://localhost:3000'
    :param user:
        Username to use when logging into foreman, default None (do not
        authenticate)
    :param passwd:
        Password to use when logging into foreman

    You can specify multiple condition like strings or parameters, that means
    that passing *fab on.foreman:'name=cinteg'* as a not named parameter or
    setting *fab on.foreman:name=cinteg* are the same. Any foreman searchstr
    string can be used. All the conditions will be agreggated with 'or'.
    """
    conds = list(conds)
    if sure not in ('yes', 'no'):
        conds.append(sure)
    if firstcond:
        conds.append(firstcond)
    searchstr = ' or '.join(conds)
    searchstr += ' or '.join('%s=%s' % item for item in kwconds.iteritems())
    if user:
        auth = (user, passwd)
    else:
        auth = None
    frm = frm_cli.Foreman(foreman, auth)
    for host in frm.index_hosts(search=searchstr, per_page=999):
        env.hosts.append(host['host']['name'])
    print(yellow("Query used: \n\t\"%s\"" % searchstr))
    print(yellow("Got %d hosts: \n\t" % len(env.hosts)
                 + '\n\t'.join(env.hosts)))
    if sure != 'yes' and not env.parallel:
        if prompt('Is what you expected? y|n', default='y').lower() == 'n':
            abort('Ended by user request.')
