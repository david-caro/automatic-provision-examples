#!/usr/bin/env python
#encoding: utf-8
"""
Tasks to manage services
"""


from fabric.api import (
    run,
    task,
    settings,
)


@task
def stop(service):
    run("service %s stop" % service)


@task
def start(service):
    run("service %s start" % service)


@task
def restart(service):
    run("service %s restart" % service)


@task
def reload(service):
    run("service %s reload" % service)


@task
def status(service):
    run("service %s status" % service)


@task
def add(service):
    run("chkconfig --add " + service)


@task
def delete(service):
    run("chkconfig --del " + service)


@task
def disable(service):
    with settings(warn_only=True):
        add(service)
    run("chkconfig %s off" % service)


@task
def enable(service):
    with settings(warn_only=True,
                  hide=['messages', 'output']):
        add(service)
    run("chkconfig %s off" % service)
