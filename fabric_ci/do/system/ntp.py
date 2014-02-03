#!/usr/bin/env python
#encoding: utf-8
"""
Tasks to manage ntp
"""


from fabric.api import (
    run,
    task,
    settings,
    hide,
    env,
)
from fabric_ci.lib.utils import (
    info,
)


@task
def sync(ntp_server=None):
    """
    Sync the server with the given ntp server, stops and restarts the ntpd
    service if it was enabled.

    :param ntp_server:
        NTP server to use, default = config.NTP_SERVER
    """
    start = False
    if ntp_server == None:
        ntp_server = env['NTP_SERVER']
    with settings(hide('running', 'status', 'stderr', 'stdout', 'warnings'),
                  warn_only=True):
        res = run("service ntpd status")
    if res.succeeded:
        info("Stopping ntpd")
        run("service ntpd stop")
        start = True
    info("Synching the time")
    run("ntpdate %s" % ntp_server)
    if start:
        info("Starting ntpd again")
        run("service ntpd start")
