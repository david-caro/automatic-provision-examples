#!/usr/bin/env python
#encoding: utf-8
"""
Upload a file to a host only if the md5sum is different. And optionally using
templates
"""

from fabric.api import (
    task,
    serial,
    run,
    put,
    local,
    settings,
    hide,
    env,
)
from fabric_ci.lib.utils import (
    info,
    green,
)


def gen_from_template(tpl, **kwargs):
    """
    :param tpl:
        Template file path
    :param \*\*kwargs:
        Whatever variables you want to substitute in the template
    """
    with open(tpl) as tpl_fd:
        data = tpl_fd.read()
    gen_file_name = env['TMPDIR'] + '/' + tpl.rsplit('/', 1)[-1]
    with open(gen_file_name, 'w') as dst_fd:
        dst_fd.write(data.format(**kwargs))
    return gen_file_name

## Not working with parallel execution
@task(defaut=True)
@serial
def ensure_content(origin, remote=None, **kwargs):
    """
    Makes sure that the contents (md5) of the given file are the given one.

    :param origin:
        original file or template
    :param remote:
        remote file to look for, if none given the same as origin will be
        used.

    You can use 'templates' that will be parsed with python string.format and
    the extra params passed (others than origin and remote). For example::

    ####### Template #######
    this is the content of the file, here you can use {variables} like you do
    when using strings in {language}.
    ########################

    then with::

    > fab file.ensure_content:origin=mytemplate,variables=vars,language=python

    you will generate the content::

    ########################
    this is the content of the file, here you can use vars like you do
    when using strings in python.
    ########################
    """
    if not remote:
        remote = origin
    if kwargs:
        origin = gen_from_template(origin, **kwargs)
    orig_md5 = local("md5sum %s" % origin, capture=True)
    with settings(hide('running', 'stdout', 'stderr', 'warnings'),
                  warn_only=True):
        rem_md5 = run("md5sum %s" % remote)
    if rem_md5.failed or rem_md5.split(' ', 1)[0] != orig_md5.split(' ', 1)[0]:
        info("Uploading: %s - %s" % (remote, orig_md5.split(' ', 1)[0]))
        put(origin, remote)
        info(green("OK"))
    else:
        info("Already OK: %s - %s" % (remote, orig_md5.split(' ', 1)[0]))
