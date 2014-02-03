#!/usr/bin/env python
#encoding: utf-8


from fabric.utils import (
    error as fail,
)
from fabric.api import (
    task,
    settings,
    hide,
    run,
)
from fabric_ci.lib.utils import (
    info,
)


@task
def clear():
    with settings(
            hide('status', 'running', 'stdout', 'stderr', 'warnings'),
            warn_only=True,):
        out = run("rpm -q sanlock")
    if not out.succeeded:
        info("Sanlock was not installed.")
        return
    out = run("sanlock client status")
    if out.failed:
        fail("Failed to check sanlock status")
    locks = []
    for line in out.splitlines():
        if line.startswith('s '):
            locks.append(line.split(' ')[-1])
    info("Got %d locks" % len(locks))
    for lock in locks:
        info("  Freeing lock %s" % lock)
        with settings(
                hide('running', 'stdout', 'stderr', 'warnings'),
                warn_only=True,
                disable_known_hosts=True):
            run("sanlock rem_lockspace -s '%s'" % lock)
    info("Done")
