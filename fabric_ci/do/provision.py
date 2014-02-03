#!/usr/bin/env python
#encoding: utf-8
"""
This module implements the main tasks used to provision hosts with foreman
"""
import time
import datetime
try:
    from collections import Counter
    COUNTER = True
except ImportError:
    COUNTER = False
import traceback
from requests.exceptions import (
    ConnectionError,
    Timeout,
)
from fabric.api import (
    task,
    serial,
    runs_once,
    run,
    execute,
    env,
    settings,
    hide,
    prompt,
)
from ssh.ssh_exception import SSHException
from fabric.network import disconnect_all
from fabric.utils import (
    error as fail,
    abort,
)
from fabric import exceptions
from fabric import state
from fabric_ci.lib.utils import (
    absolute_import,
    green,
    white,
    blue,
    cyan,
    red,
    TTY,
    info,
    error,
    warn,
    puts,
    ts,
    fancy,
)
from fabric_ci.lib.foreman import foreman_defaults
frm_cli = absolute_import('foreman.client', ['Foreman', 'Unacceptable'])

state.output['running'] = False
state.output['status'] = False


class BuildTimeout(Exception):
    """
    Helper exception when there's a timeout when building a host
    """
    pass


def get_prop_dict(host):
    """
    Helper to get a dictionary with the properties of a host

    :param host: Host to get the properties from as returned from foreman api
    """
    prop_dict = {}
    host = host['host']
    if 'host_parameters' in host:
        params = host['host_parameters']
        par_key = 'host_parameter'
    else:
        params = host['parameters']
        par_key = 'parameter'
    for prop in params:
        prop_dict[prop[par_key]['name']] \
            = prop[par_key]['value']
    return prop_dict


def add_hosts_to_query(query='', hosts=None):
    """
    Add the env.hosts or the given hosts to the given foreman query.

    :param query: Original query
    :param hosts: list of hosts if not using env.hosts
    """
    hosts = hosts or env.hosts
    if hosts:
        query += (query and ' AND' or '') \
            + ' ( name=%s )' % ' OR name='.join(hosts)
    return query


def is_user_reserved(host):
    props = get_prop_dict(host)
    if 'RESERVED' in props and 'RESERVED' in props['RESERVED']:
        return props['RESERVED']
    return False


def is_unavailable(host):
    props = get_prop_dict(host)
    if 'RESERVED' in props and 'UNAVAILABLE' in props['RESERVED'].upper():
        return props['RESERVED']
    return False


def is_stuck(host, timeout=60*60*23):
    reason = ''
    host = host['host']
    if 'host_parameters' in host:
        params = host['host_parameters']
        par_key = 'host_parameter'
    else:
        params = host['parameters']
        par_key = 'parameter'
    for param in params:
        if param[par_key]['name'].lower() == 'RESERVED'.lower():
            reason = param[par_key]['value']
            updated = param[par_key]['updated_at']
            break
    if reason:
        updated = int(
            datetime.datetime.strptime(
                updated,
                '%Y-%m-%dT%H:%M:%SZ'
            ).strftime('%s')
        )
        now = int(datetime.datetime.now().strftime('%s'))
        if timeout < (now - updated):
            return reason
    return False


@runs_once
@task
@foreman_defaults
def show(foreman=None, user=None, passwd=None):
    """
    Show host specific info

    """
    query = add_hosts_to_query()
    frm = frm_cli.Foreman(foreman, (user, passwd))
    hgdict = {}
    hgdict[None] = "No group"
    for hg in frm.index_hostgroups(per_page=999):
        hgdict[hg['hostgroup']['id']] = hg['hostgroup']['name']
    if TTY:
        puts("{0:<38}\t{1:<35}\t{2:<28}".format(blue("Host", True),
                                                cyan("Profile", True),
                                                green("Reason", True)))
    hosts_info = frm.index_hosts(search=query, per_page=999)
    for next_host in hosts_info:
        next_host = frm.show_hosts(next_host['host']['id'])
        props = get_prop_dict(next_host)
        puts("{0:<38}\t{1:<35}\t{2:<28}".format(
            blue(next_host['host']['name']),
            cyan(hgdict[next_host['host']['hostgroup_id']]),
            'RESERVED' in props
            and green(props['RESERVED']) or ''))


@runs_once
@task
@foreman_defaults
def show_stuck(query='', foreman=None, user=None, passwd=None):
    """
    Show all the hosts that are stuck
    """
    frm = frm_cli.Foreman(foreman, (user, passwd))
    hgdict = {}
    for hg in frm.index_hostgroups(per_page=999):
        hgdict[hg['hostgroup']['id']] = hg['hostgroup']['name']
    if TTY:
        puts("{0:<38}\t{1:<35}\t{2:<28}".format(blue("Host", True),
                                                cyan("Profile", True),
                                                green("Reason", True)))
    for host, reason in ((host, is_stuck(host))
                         for host in frm.show_reserved(query=query)
                         if is_stuck(host)):
        puts("{0:<38}\t{1:<35}\t{2:<28}".format(
            blue(host['host']['name']),
            cyan(hgdict[host['host']['hostgroup_id']]),
            green(reason)))


@runs_once
@task
@foreman_defaults
def show_user_reserved(query='', foreman=None, user=None, passwd=None):
    """
    Show all the hosts that are reserved by users (not automatically reserved)
    """
    frm = frm_cli.Foreman(foreman, (user, passwd))
    hgdict = {}
    for hg in frm.index_hostgroups(per_page=999):
        hgdict[hg['hostgroup']['id']] = hg['hostgroup']['name']
    if TTY:
        puts("{0:<38}\t{1:<35}\t{2:<28}".format(blue("Host", True),
                                                cyan("Profile", True),
                                                green("Reason", True)))
    for host, reason in ((host, is_user_reserved(host))
                         for host in frm.show_reserved(query=query)
                         if is_user_reserved(host)):
        puts("{0:<38}\t{1:<35}\t{2:<28}".format(
            blue(host['host']['name']),
            cyan(hgdict[host['host']['hostgroup_id']]),
            green(reason)))


@runs_once
@task
@foreman_defaults
def show_unavailable(query='', foreman=None, user=None, passwd=None):
    """
    Show all the hsots that are set as unavailable (not reachable through ssh)
    """
    frm = frm_cli.Foreman(foreman, (user, passwd))
    hgdict = {}
    for hg in frm.index_hostgroups(per_page=999):
        hgdict[hg['hostgroup']['id']] = hg['hostgroup']['name']
    if TTY:
        puts("{0:<38}\t{1:<35}\t{2:<28}".format(blue("Host", True),
                                                cyan("Profile", True),
                                                green("Reason", True)))
    for host, reason in ((host, is_unavailable(host))
                         for host in frm.show_reserved(query=query)
                         if is_unavailable(host)):
        puts("{0:<38}\t{1:<35}\t{2:<28}".format(
            blue(host['host']['name']),
            cyan(hgdict[host['host']['hostgroup_id']]),
            green(reason)))


@runs_once
@task
@foreman_defaults
def show_profiles(foreman, user, passwd):
    """
    Show the list of available profiles
    """
    if 'PROVISION_GROUP_PREFIX' not in env:
        fail("Please set up PROVISION_GROUP_PREFIX in the fabricrc file")
    frm = frm_cli.Foreman(foreman, (user, passwd))
    for group in frm.index_hostgroups(
            per_page=999,
            search='name~%s' % env.PROVISION_GROUP_PREFIX):
        puts(group['hostgroup']['name'])


@runs_once
@task
@foreman_defaults
def show_summary(foreman, user, passwd):
    """
    Show a summary of the current used and unused profiles and machines

    :param foreman: URL to the foreman server
    :param user: username to login into Foreman
    :param passwd: Password to use when logging in
    """
    if 'PROVISION_GROUP_PREFIX' not in env:
        fail("Please set up PROVISION_GROUP_PREFIX in the fabricrc file")
    frm = frm_cli.Foreman(foreman, (user, passwd))
    hgdict = {}
    for hg in frm.index_hostgroups(per_page=999):
        if hg['hostgroup']['name'].startswith(env.PROVISION_GROUP_PREFIX):
            hgdict[hg['hostgroup']['id']] = hg['hostgroup']['name']
    a_groups, r_groups = [], []
    ## Available
    available_hosts = frm.show_available(query="hostgroup ~ %s%%"
                                         % env.PROVISION_GROUP_PREFIX)
    puts(green("Total Available hosts: ", True) + green(len(available_hosts)))
    puts(blue("Available hosts by profile:", True))
    for next_host in available_hosts:
        a_groups.append(next_host['host']['hostgroup_id'])
    ## For python 2.6 compatibility
    if COUNTER:
        a_groups_count = dict(Counter(a_groups))
    else:
        a_groups_count = dict([(item, a_groups.count(item))
                               for item in sorted(set(a_groups))])
    for gid, count in a_groups_count.iteritems():
        puts(blue("\t%s (id=%d) = %s" % (hgdict[gid], gid, white(count))))
    ## Reserved
    reserved_hosts = frm.show_reserved()
    puts(green("Total Reserved hosts: ", True) + green(len(reserved_hosts)))
    puts(blue("Resrved hosts by profile:", True))
    for next_host in reserved_hosts:
        r_groups.append(next_host['host']['hostgroup_id'])
    if COUNTER:
        r_groups_count = dict(Counter(r_groups))
    else:
        r_groups_count = dict([(item, r_groups.count(item))
                               for item in sorted(set(r_groups))])
    for gid, count in r_groups_count.iteritems():
        puts(blue("\t%s (id=%d) = %s" % (hgdict[gid], gid, white(count))))
    ## Unused
    puts(blue("Unused profiles:", True))
    for gid in a_groups_count.iterkeys():
        if gid in hgdict:
            hgdict.pop(gid)
    for gid in r_groups_count.iterkeys():
        if gid in hgdict:
            hgdict.pop(gid)
    for gid, name in hgdict.iteritems():
        puts(blue("\t%s (id=%s)" % (name, gid)))


@runs_once
@task
@foreman_defaults
def show_available(query='', amount=0, foreman=None, user=None, passwd=None):
    """
    Show the lis of available machines

    :param query: Show only the ones that match this query
    :param amount: show only that amount
    :param foreman: URL to the foreman server
    :param user: username to login into Foreman
    :param passwd: Password to use when logging in
    """
    if 'PROVISION_GROUP_PREFIX' not in env:
        fail("Please set up PROVISION_GROUP_PREFIX in the fabricrc file")
    frm = frm_cli.Foreman(foreman, (user, passwd))
    if query:
        query = "( %s ) AND hostgroup ~ %s%%" \
                % (query, env.PROVISION_GROUP_PREFIX)
    else:
        query = "hostgroup ~ %s%%" % env.PROVISION_GROUP_PREFIX
    hgdict = {}
    for hg in frm.index_hostgroups(per_page=999):
        hgdict[hg['hostgroup']['id']] = hg['hostgroup']['name']
    if TTY:
        puts("{0:<40}\t{1:<38}".format(blue("Host", True),
                                       cyan("Profile", True)))
    for next_host in frm.show_available(query=query, amount=amount):
        puts("{0:<40}\t{1:<38}".format(
            blue(next_host['host']['name']),
            cyan(hgdict[next_host['host']['hostgroup_id']])))


@runs_once
@task
@foreman_defaults
def show_reserved(query='', foreman=None, user=None, passwd=None):
    """
    Show the list of reserved hosts

    :param query: Show only the ones that match this query
    :param foreman: URL to the foreman server
    :param user: username to login into Foreman
    :param passwd: Password to use when logging in
    """
    frm = frm_cli.Foreman(foreman, (user, passwd))
    hgdict = {}
    for hg in frm.index_hostgroups(per_page=999):
        hgdict[hg['hostgroup']['id']] = hg['hostgroup']['name']
    if TTY:
        puts("{0:<38}\t{1:<35}\t{2:<28}".format(blue("Host", True),
                                                cyan("Profile", True),
                                                green("Reason", True)))
    for next_host in frm.show_reserved(query=query):
        props = get_prop_dict(next_host)
        puts("{0:<38}\t{1:<35}\t{2:<28}".format(
            blue(next_host['host']['name']),
            cyan(hgdict[next_host['host']['hostgroup_id']]),
            'RESERVED' in props
            and green(props['RESERVED']) or ''))


@runs_once
@task
@foreman_defaults
def update_reason(reason, query='', add_ts='true', add_tag='true', foreman=None, user=None, passwd=None):
    """
    Update the reasom of a reserved host or hosts

    :param reason: New reason to put into
    :param query: Use this query for selecting the hosts
    :param add_ts: Add the timestamp to the reason message
    :param add_tag: Add the 'USER_RESERVED' tag
    :param foreman: URL to the foreman server
    :param user: username to login into Foreman
    :param passwd: Password to use when logging in
    """
    query = add_hosts_to_query(query)
    if add_tag == 'true':
        reason = '[USER_RESERVED] ' + reason
    if add_ts == 'true':
        reason = ts(reason)
    frm = frm_cli.Foreman(foreman, (user, passwd))
    hgdict = {}
    for hg in frm.index_hostgroups(per_page=999):
        hgdict[hg['hostgroup']['id']] = hg['hostgroup']['name']
    if TTY:
        info("Updating all the hosts matching this query:")
        info("\t%s" % query)
        info("With the reason:")
        info("\t%s" % reason)
        puts("{0:<38}\t{1:<35}\t{2:<28}".format(blue("Host", True),
                                                cyan("Profile", True),
                                                green("Reason", True)))
    for next_host in frm.update_reserved_reason(reason=reason, query=query):
        props = get_prop_dict(next_host)
        puts("{0:<38}\t{1:<35}\t{2:<28}".format(
            blue(next_host['host']['name']),
            cyan(hgdict[next_host['host']['hostgroup_id']]),
            'RESERVED' in props
            and green(props['RESERVED']) or ''))


@runs_once
@task
@foreman_defaults
def release(query='', foreman=None, user=None, passwd=None):
    """
    Release the given host or hosts

    :param query: Use this query for selecting the hosts
    :param foreman: URL to the foreman server
    :param user: username to login into Foreman
    :param passwd: Password to use when logging in
    """
    query = add_hosts_to_query(query)
    if not query:
        warn("This will release all the hosts, are you sure?")
        res = prompt("[y/n]:")
        if res.lower() == 'n':
            info("Quitting")
            return
    frm = frm_cli.Foreman(foreman, (user, passwd))
    if TTY:
        info("Releasing all the hosts matching this query:")
        info("\t%s" % query)
        puts("{0:<80}".format(green("Released hosts", True)))
    for hostname in frm.hosts_release(query=query):
        puts("{0:<80}".format(green(hostname)))


def test_ssh(host, command='uptime'):
    """
    Test if a host is reachable through ssh

    :param host: Host to test
    :param command: Command to run when connecting
    """
    try:
        with settings(
                hide('running', 'stdout', 'stderr'),
                warn_only=True,
                host_string=host,
                disable_known_hosts=True):
            return run(command).succeeded
    except SSHException:
        ## that's usually because the ssh connection got broken, diconnect_all
        ## forces fabric to reconnect
        traceback.print_exc()
        disconnect_all()
    except exceptions.NetworkError:
        pass
    return False


@runs_once
@serial
@task
@foreman_defaults
def reserve(query='', reason='', amount=0, tries=120, timeout=60, ensure_ssh='true', add_tag='true', show=True, foreman=None, user=None, passwd=None):
    """
    Reserve the given host or hosts (just the task wrapper)

    :param foreman: URL to the foreman server
    :param user: username to login into Foreman
    :param passwd: Password to use when logging in
    :param query: Use this query for selecting the hosts
    :param reason: New reason to put into
    :param amount: Reserve only this amount of hosts
    :param tries: Number of attempts to reserve
    :param ensure_ssh: Try to connect using ssh before reservingf the host
    :param add_tag: Add the 'RESERVED' tg to the reason, for nagios to ignore
    :param add_ts: Add the timestamp to the reasom message
    :param show: Show the results, used when not called from fab client
                 directly
    """
    _reserve(foreman=foreman, user=user, passwd=passwd,
             query=query, reason=reason, amount=amount,
             tries=tries, timeout=timeout, ensure_ssh=ensure_ssh,
             add_tag=add_tag, show=show)


def _reserve(query='', reason='', amount=0, tries=120, timeout=60, ensure_ssh='true', add_tag='true', show=True, foreman=None, user=None, passwd=None):
    """
    Reserve the given host or hosts (real function)

    :param foreman: URL to the foreman server
    :param user: username to login into Foreman
    :param passwd: Password to use when logging in
    :param query: Use this query for selecting the hosts
    :param reason: New reason to put into
    :param amount: Reserve only this amount of hosts
    :param tries: Number of attempts to reserve
    :param ensure_ssh: Try to connect using ssh before reservingf the host
    :param add_tag: Add the 'RESERVED' tg to the reason, for nagios to ignore
    :param add_ts: Add the timestamp to the reasom message
    :param show: Show the results, used when not called from fab client
                 directly
    """
    tries = int(tries)
    timeout = int(timeout)
    hosts_list = []
    up_hosts = []
    down_hosts = []
    to_explore_hosts = []
    if not amount and env.hosts:
        amount = len(env.hosts)
    else:
        amount = int(amount)
    query = add_hosts_to_query(query)
    if not int(amount):
        fail('Cowardly refusing to reserve all the hosts, set an amount != 0')
    if add_tag == 'true':
        reason = '[USER_RESERVED] ' + reason
    frm = None
    while not frm and tries:
        try:
            frm = frm_cli.Foreman(foreman, (user, passwd))
        except (ConnectionError, Timeout):
            error("Got an exception while trying to connect to foreman.")
            traceback.print_exc()
            info("Waiting %ds before retrying..." % timeout)
            time.sleep(timeout)
            tries -= 1
    hgdict = {}
    for hg in frm.index_hostgroups(per_page=999):
        hgdict[hg['hostgroup']['id']] = hg['hostgroup']['name']
    ############################
    ## Reserve
    ############################
    try:
        while len(up_hosts) < amount and tries:
            info(("Trying to get enough hosts each %ds, have %d of %d, %d "
                 "tries left") % (timeout, len(up_hosts), amount, tries))
            tries -= 1
            try:
                hosts_list = frm.hosts_reserve(query=query,
                                               amount=(amount - len(up_hosts)),
                                               reason=ts('[QUEUED] %s'
                                                         % reason))
                if not hosts_list:
                    raise frm_cli.Unacceptable(None, None)
            except frm_cli.Unacceptable:
                hosts_list = []
            if ensure_ssh == 'true':
                to_explore_hosts = [h for h in hosts_list]
                for index, next_host in enumerate(hosts_list):
                    puts("Connecting to %s: " % next_host['host']['name'],
                         end='')
                    if test_ssh(next_host['host']['name']):
                        up_hosts.append(next_host)
                        puts(green("up and running."))
                        to_explore_hosts.pop(0)
                    else:
                        down_hosts.append(next_host)
                        puts(red("UNAVAILABLE."))
                        to_explore_hosts.pop(0)
                        hosts_list.pop(index)
            else:
                for host in hosts_list:
                    up_hosts.append(host['host']['name'])
            if len(up_hosts) < amount and tries:
                time.sleep(timeout)
    except Exception:
        traceback.print_exc()
        raise
    finally:
        ## Cleanup if needed
        ## Mark the hosts that failed to connect
        if down_hosts:
            down_names = [h['host']['name'] for h in down_hosts]
            warn("Removing unavailable hosts from the pool.\n%s"
                 % down_names)
            down_query = add_hosts_to_query(hosts=down_names)
            frm.update_reserved_reason(reason=ts("[UNAVAILABLE] %s"
                                                 % reason),
                                       query=down_query)
            down_hosts = []
        ## If not able to get enough, free all the reserved ones
        if len(up_hosts) < amount:
            warn("Not enough hosts available for query %s." % query)
            if to_explore_hosts:
                to_explore_hosts = [h['host']['name']
                                    for h in to_explore_hosts]
                puts("Releasing untested hosts:\n\t%s" % to_explore_hosts)
                query = add_hosts_to_query(hosts=to_explore_hosts)
                hosts_list = frm.hosts_release(query=query)
            if up_hosts:
                up_hosts = [h['host']['name'] for h in up_hosts]
                info("Releasing healthy hosts:\n\t%s" % up_hosts)
                query = add_hosts_to_query(hosts=up_hosts)
                hosts_list = frm.hosts_release(query=query)
            return []
        else:
            ## Update the reason to the original one, we finished
            query = add_hosts_to_query(hosts=[h['host']['name']
                                              for h in up_hosts])
            hosts_list = frm.update_reserved_reason(query=query,
                                                    reason=ts(reason))
            if TTY and show and up_hosts:
                puts("{0:<38}\t{1:<35}\t{2:<28}".format(blue("Host", True),
                                                        cyan("Profile", True),
                                                        green("Reason", True)))
                for next_host in hosts_list:
                    puts("{0:<38}\t{1:<35}\t{2:<28}".format(
                        blue(next_host['host']['name']),
                        cyan(hgdict[next_host['host']['hostgroup_id']]),
                        green(ts(reason))))
            return hosts_list


@task
@foreman_defaults
def rebuild(profile='', reason=False, wait='true', reserve='true', release='true', timeout=120, foreman=None, user=None, passwd=None):
    """
    Rebuild the host. NOTE: it will adapt the host os to the specified
    hostgroup

    :param foreman: URL to the foreman server
    :param user: username to login into Foreman
    :param passwd: Password to use when logging in
    :param profile: Rebuid the host with the given profile, if none given it
                    will use the current one
    :param reason: Use the given reason, 'RESERVED' by default
    :param wait: Wait for the host to be built before exitting, default 'true'
    :param reserve: If the host is not already reserved, reserve it, default
                    'true'
    :param release: Release the host at the end, default 'true'
    :param timeout: number of minutes to wait before failing
    """
    frm = frm_cli.Foreman(foreman, (user, passwd))
    ## If no reason provided, assume that is user-made and add the reserved
    ## tag
    if not reason:
        reason = 'RESERVED'
    hg2id = {}
    for hg in frm.index_hostgroups(per_page=999):
        hg2id[hg['hostgroup']['name']] = (
            hg['hostgroup']['id'],
            hg['hostgroup']['operatingsystem_id']
        )
    up_query = add_hosts_to_query(hosts=[env.host])
    ## Mark the hosts as building and change the hostgroup if necessary,
    ## reboot
    res = frm.update_reserved_reason(reason=ts("[BUILDING] %s" % reason),
                                     query=up_query)
    if not res and reserve == 'true':
        frm.hosts_reserve(reason=ts("[BUILDING] %s" % reason),
                          query=up_query,
                          amount=1)
    new_host = {'build': True}
    if profile:
        new_host['hostgroup_id'], new_host['operatingsystem_id'] = \
            hg2id[profile]
    frm.update_hosts(id=env.host, host=new_host)
    ## force a reboot for the host to start building
    with settings(warn_only=True,
                  disable_known_hosts=True):
        try:
            info("Rebooting host %s" % env.host)
            with hide('stdout'):
                run("reboot")
                ## force fabric to reconnect
                disconnect_all()
            time.sleep(5)
        except Exception:
            traceback.print_exc()
            abort(red("Unable to reboot host %s" % env.host))
    if wait == 'true':
        wait_for_host_built(timeout=timeout)
    if release == 'true':
        frm.hosts_release(query=up_query)


@task
@foreman_defaults
def wait_for_host_built(timeout='30', foreman=None, user=None, passwd=None):
    """
    Wait until the host is built in foreman or until timeout expires

    :param foreman: URL to the foreman server
    :param user: username to login into Foreman
    :param passwd: Password to use when logging in
    :param timeout: number minutes to wait before failing
    """
    frm = frm_cli.Foreman(foreman, (user, passwd))
    info("Waiting for %s to be built" % env.host)
    ## the number of loops is the amount of minutes to wait
    for _ in range(int(timeout)):
        new_status = frm.show_hosts(id=env.host)
        if new_status['host']['build'] is False and test_ssh(env.host):
            info("Host %s done" % env.host)
            break
        else:
            if new_status['host']['build'] is True:
                info("Waiting for %s to be built" % env.host)
            else:
                info("Waiting for %s to be reachable through ssh" % env.host)
        time.sleep(60)
    else:
        raise BuildTimeout("Timeout while waiting for the host %s"
                           % env.host)
    return True


@task(default=True)
@runs_once
@serial
@foreman_defaults
def provision(profile, query='', change_profile='false', force_rebuild='false', reason='', amount="0", outfile=None, add_tag='true', tries=300, timeout=60,  foreman=None, user=None, passwd=None):
    """
    Provision the given host or hosts

    :param profile: Use this profile
    :param query: Use this query when selecting the hosts
    :param change_profile: Change the profile of the hosts if no free hosts
        found for the given profile (false by default)
    :param force_rebuild: Rebuild the host from scratch (false by default)
    :param reason: New reason to put into
    :param amount: Reserve only this amount of hosts
    :param outfile: Write the csv list of provisioned hosts in that file
    :param add_tag: Add the [UESR RESERVED] tag to the reason (true by default)
    :param tries: Times to try in case of failure (300 by default)
    :param timeout: How much time in seconds to wait between tries
        (60 by default)
    :param foreman: URL to the foreman server
    :param user: username to login into Foreman
    :param passwd: Password to use when logging in
    """
    if 'PROVISION_GROUP_PREFIX' not in env:
        fail("Please set up PROVISION_GROUP_PREFIX in the fabricrc file")
    frm = None
    ## if 'amount=0' passed, just end
    if not int(amount):
        warn("No hosts will be provisioned as amount=0")
        return
    tries = int(tries)
    while not frm and tries:
        try:
            frm = frm_cli.Foreman(foreman, (user, passwd))
        except (ConnectionError, Timeout):
            error("Got an exception while trying to connect to foreman.")
            traceback.print_exc()
            info("Waiting %ds before retrying..." % timeout)
            time.sleep(timeout)
            tries -= 1
    frm = frm_cli.Foreman(foreman, (user, passwd))
    ## Get the hostgroup_name -> id mapping
    hg2id = {}
    for hg in frm.index_hostgroups(per_page=999):
        hg2id[hg['hostgroup']['name']] = hg['hostgroup']['id']
    if not profile.startswith(env.PROVISION_GROUP_PREFIX):
        profile = env.PROVISION_GROUP_PREFIX + profile
    ## If the profile requested does not exist, throw error
    if profile not in hg2id:
        error("Profile %s not found" % profile)
        show_profiles()
        return
    ## Prepare the query with profile
    prof_query = (query and '( %s ) AND ' % query or '') \
        + 'hostgroup=%s' % profile
    ## query to search other provisionable hosts
    query = '( %s ) AND hostgroup ~ %s%%' % (query,
                                             env.PROVISION_GROUP_PREFIX)
    #### get the available hosts  with the given profile ####
    hosts_list = []
    to_release = []
    info("########## Reserving hosts")
    try:
        if change_profile != 'false':
            ## spend 10% with a minimum of 1 of the tries looking inside the
            ## same profile
            same_prof_tries = tries/10 or 1
            other_prof_tries = tries - same_prof_tries
        else:
            same_prof_tries = tries
            other_prof_tries = 0
        try:
            info("Seeing if we have free hosts for the given profile.")
            hosts_list = _reserve(foreman=foreman, user=user, passwd=passwd,
                                  query=prof_query,
                                  reason='[QUEUED] %s' % reason,
                                  amount=amount, tries=same_prof_tries,
                                  add_tag=add_tag, show=False)
            if not hosts_list:
                raise frm_cli.Unacceptable(None, None)
        except frm_cli.Unacceptable:
            if change_profile != 'false':
                info("We were not, looking for free hosts outside the given "
                     "profile.")
                hosts_list = _reserve(foreman=foreman, user=user,
                                      passwd=passwd,
                                      query=query,
                                      reason='[QUEUED] %s' % reason,
                                      amount=amount, add_tag=add_tag,
                                      show=False, tries=other_prof_tries,
                                      timeout=timeout)
                force_rebuild = 'got hosts outside the profile'
    except Exception:
        traceback.print_exc()
        raise
    finally:
        if len(hosts_list) < int(amount):
            error("Not enough hosts available.")
            if change_profile == 'false':
                info("You can try using change_profile=true to rebuild free "
                     "hosts from other profiles")
            fail("Not enough hosts available.")
    info("########## Provisioning hosts")
    try:
        if force_rebuild != 'false':
            info("force_rebuild=%s, rebuilding the hosts." % force_rebuild)
            with settings(parallel=True,
                          hosts=[h['host']['name'] for h in hosts_list],
                          warn_only=True,
                          clean_revert=True):
                res = execute(
                    rebuild,
                    foreman=foreman, user=user, passwd=passwd,
                    profile=profile,
                    reason="[PROVISIONING] %s" % reason,
                    wait='true',
                    reserve='true',
                    release='false',
                    timeout=timeout)
            for host, out in res.iteritems():
                print host, out
        else:
            info("force_rebuild not set and no hosts outside the profile "
                 "reserved, not rebuilding the hosts.")
    ############################
    ## Finish
    ############################
        info(green("########## Everything went perfect."))
        hostnames = [h['host']['name'] for h in hosts_list]
        frm.update_reserved_reason(query=add_hosts_to_query(hosts=hostnames),
                                   reason=ts(reason))
        if outfile:
            with open(outfile, 'w') as ofd:
                ofd.write(','.join(hostnames))
        puts(green(fancy("Done"), True))
    except BuildTimeout:
        pass
    finally:
        info('########## Cleaning up...')
        if to_release:
            error("Some hosts failed to build, releasing the healthy ones.")
            to_release = [h['host']['name'] for h in to_release]
            info("\tReleasing: %s" % to_release)
            frm.hosts_release(query=add_hosts_to_query(hosts=to_release))
            fail("Some hosts failed to build.")
