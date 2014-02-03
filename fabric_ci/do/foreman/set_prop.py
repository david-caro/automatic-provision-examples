#!/usr/bin/env python
#encoding: utf-8
"""
Manage hosts properties
"""

from foreman import client as cli
from fabric.api import task
from fabric_ci.lib import utils
from fabric_ci.lib.foreman import foreman_defaults



@task(default=True)
@foreman_defaults
def set_prop(what, m_from, m_to, foreman, user, passwd):
    """
    Update the given property if it matches the given value

    :param what: Property to update, ex: medium_id.
    :param m_from: Value to match, only update if it matches this value.
    :param m_to: New value to set.
    """
    fcli = cli.Foreman(foreman, (user, passwd))
    hosts_index = fcli.index_hosts(per_page='1000')
    for host in hosts_index:
        host = fcli.show_hosts(id=host['host']['id'])
        if what in host['host'] and str(host['host'][what]) == m_from:
            utils.info('Updating host %s, [ %s: from %s to %s ]'
                    % (host['host']['name'], what, m_from, m_to))
            fcli.update_hosts(id=host['host']['id'], host={what: m_to})
