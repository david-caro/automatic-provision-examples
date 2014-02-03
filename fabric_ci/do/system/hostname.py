#!/usr/bin/env python
#encoding: utf-8
"""
Tasks to manage the hostname of a machine
"""

from fabric.api import task, run


@task(default=True)
def hset(hostname, old_hostname=None):
    """
    Set the hostname

    :param hostname:
        Hostname to set up on the host
    :param old_hostname:
        Old hostname to clean up when setting the new, deafult = None
    """
    run("hostname %s" % hostname)
    run("sed -i '/HOSTNAME=.*/d' /etc/sysconfig/network")
    run("echo 'HOSTNAME=%s' >> /etc/sysconfig/network" % hostname)
    if old_hostname:
        run(r"sed -i 's/[[:space:]]%s\([[:space:]]\|$\)/ %s /g' /etc/hosts"
                % (old_hostname, hostname))
    else:
        run("echo '127.0.0.1 %s' >> /etc/hosts" % hostname)
