#!/usr/bin/env python
#encoding: utf-8
"""
This module implements the main tasks used to provision hosts with foreman
"""

COUNTER = True
try:
    from collections import Counter
except ImportError:
    COUNTER = False
from fabric.api import (
    task,
    runs_once,
    env,
)
from fabric import state
from fabric_ci.lib.utils import (
    green,
    white,
    blue,
    red,
    puts,
    ifilter_glob,
)
from foreman.client import Foreman
from fabric_ci.lib.foreman import foreman_defaults

state.output['running'] = False
state.output['status'] = False


@runs_once
@task
@foreman_defaults
def hostgroups_summary(foreman, user, passwd):
    """
    Show a summary of the current used and unused profiles and machines

    :param foreman: URL to the foreman server
    :param user: username to login into Foreman
    :param passwd: Password to use when logging in
    """
    frm = Foreman(foreman, (user, passwd))
    hgdict = {}
    for hg in frm.index_hostgroups(per_page=900):
        hgdict[hg['hostgroup']['id']] = hg['hostgroup']['name']
    notused = dict(hgdict.iteritems())
    groups = []
    ## Available
    hosts = frm.index_hosts(per_page=1000)
    puts(green("Total Available hosts: ", True) + green(len(hosts)))
    puts(blue("Available hosts by hostgroup:", True))
    for next_host in hosts:
        gid = next_host['host']['hostgroup_id']
        if gid:
            groups.append((hgdict[gid], gid))
            gid in notused and notused.pop(gid)
        else:
            groups.append(('No group', 'None'))
    if COUNTER:
        groups_count = dict(Counter(groups)).items()
    else:
        dict([(item, groups.count(item))
              for item in sorted(set(groups))]).items()
    groups_count.sort()
    for group, count in groups_count:
        gname, gid = group
        if gname != 'No group':
            puts(blue("\t%s (id=%d) = %s" % (gname, gid, white(count))))
        else:
            puts(blue("\tNo group = %s" % white(count)))
    ## Unused
    puts(blue("Unused hostgroups:", True))
    for gid, name in notused.iteritems():
        puts(blue("\t%s (id=%s)" % (name, gid)))


@foreman_defaults
def _iget_properties(props, foreman, user, passwd):
    """
    Gets the given properties from the hosts. From the host properties or
    parameters (you can search for example mac_addres property or RESERVED
    parameter). Returns an iterator, if you want a list, you can pass it to
    the list function `list(_iget_properties(*args))`

    :param props: comma separated list of glob patterns to match the
        properties names
    :param foreman: URL to the foreman server
    :param user: username to login into Foreman
    :param passwd: Password to use when logging in
    """
    frm = Foreman(foreman, (user, passwd))
    props = props.split(':')
    host = frm.show_hosts(env['host'])
    if not host:
        raise Exception("Host %s not found in foreman" % env['host'])
    host = host['host']
    for match in ifilter_glob(host.keys(), props):
        yield (match, host[match])
    params_dict = dict((
        (x['parameter']['name'], x['parameter']['value'])
        for x in host['parameters']
    ))
    for host_param in ifilter_glob(params_dict.keys(), props):
        yield (host_param, params_dict[host_param])


@task
@foreman_defaults
def get_properties(props, foreman, user, passwd):
    """
    Gets the given properties from the hosts. From the host properties or
    parameters (you can search for example mac_addres property or RESERVED
    parameter)

    :param props: comma separated list of glob patterns to match the
        properties names
    :param foreman: URL to the foreman server
    :param user: username to login into Foreman
    :param passwd: Password to use when logging in
    """
    for prop, value in _iget_properties(
            props, foreman=foreman, user=user, passwd=passwd):
        puts(green(prop) + '=' + blue(value))


@task
@foreman_defaults
def get_subnet(foreman, user, passwd):
    """"
    Return the subnet name and network for the hosts

    :param foreman: URL to the foreman server
    :param user: username to login into Foreman
    :param passwd: Password to use when logging in
    """
    subnet_id = dict((
        _iget_properties('subnet_id', foreman=foreman,
                         user=user, passwd=passwd)
    ))
    frm = Foreman(foreman, (user, passwd))
    subnet = frm.show_subnets(subnet_id['subnet_id'])
    if subnet:
        puts(green(env.host + '=')
             + white(subnet['subnet']['name'])
             + '|' + blue(subnet['subnet']['network']))
    else:
        puts(red(env.host + ' no subnet found'))
