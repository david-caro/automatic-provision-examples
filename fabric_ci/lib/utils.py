#!/usr/bin/env python
#encoding: utf-8

import datetime
import sys
import re
import socket
import getpass
from fnmatch import translate
from fabric import (
    colors,
    utils,
)
from fabric.api import (
    env,
    task,
    settings,
    hide,
    local,
    run,
)


TTY = sys.stdout.isatty()


class CmdResponse():
    """
    class that behaves as a boolean, `True` if there was a match, `False`
    otherwise, and when printed shows the output of the command.
    """
    def __init__(self, cmd_out, boolval):
        self.boolval = boolval
        self.out = cmd_out

    def __nonzero__(self):
        return self.boolval

    def __str__(self):
        return str(self.out)


def absolute_import(modname, fromlist=None):
    fromlist = fromlist or []
    mod = __import__(modname, globals(), locals(), fromlist, 0)
    return mod


def blue(msg, bold=False):
    msg = str(msg)
    return TTY and colors.blue(msg, bold) or msg


def red(msg, bold=False):
    msg = str(msg)
    return TTY and colors.red(msg, bold) or msg


def green(msg, bold=False):
    msg = str(msg)
    return TTY and colors.green(msg, bold) or msg


def yellow(msg, bold=False):
    msg = str(msg)
    return TTY and colors.yellow(msg, bold) or msg


def white(msg, bold=False):
    msg = str(msg)
    return TTY and colors.white(msg, bold) or msg


def magenta(msg, bold=False):
    msg = str(msg)
    return TTY and colors.magenta(msg, bold) or msg


def cyan(msg, bold=False):
    msg = str(msg)
    return TTY and colors.cyan(msg, bold) or msg


def warn(msg, end='\n', with_ts=True):
    msg = str(msg)
    if with_ts:
        utils.fastprint(ts('[WARNING] ', yellow, True) + yellow(msg), end=end)
    else:
        utils.fastprint(yellow('[WARNING] ', True) + yellow(msg), end=end)


def error(msg, end='\n', with_ts=True):
    msg = str(msg)
    if with_ts:
        utils.fastprint(ts('[ERROR] ', red, True) + red(msg), end=end)
    else:
        utils.fastprint(red('[ERROR] ', True) + red(msg), end=end)


def info(msg, end='\n', with_ts=True):
    msg = str(msg)
    if with_ts:
        utils.fastprint(ts('[INFO] ', blue, True) + blue(msg), end=end)
    else:
        utils.fastprint(blue('[INFO] ') + blue(msg), end=end)


def puts(msg, end='\n', with_ts=False):
    msg = str(msg)
    if with_ts:
        utils.fastprint(ts(msg), end=end)
    else:
        utils.fastprint(msg, end=end)


def ts(msg, color=None, bold=False, with_origin=True, with_target=False, utc=False):
    if color is None:
        color = lambda x, y: x
    msg = str(msg)
    if utc:
        now = datetime.datetime.utcnow()
    else:
        now = datetime.datetime.now()
    text = '[' + now.strftime("%d/%m/%Y %H:%M:%S")
    if TTY:
        text = color(text, bold)
    if with_target or env.parallel:
        target = "on %s" % env.host
        if TTY:
            text += color("|", bold) + white(target)
        else:
            text += "|" + target
    if with_origin:
        origin = "by %s@%s" % (getpass.getuser(), socket.gethostname())
        if TTY:
            text += color("|", bold) \
                + blue(origin) \
                + color("] %s" % msg, bold)
        else:
            text += "|" + origin + "] %s" % msg
    return text


def smiley():
    import random
    eyes = ':XB8'
    noses = ['-', '']
    mouths = 'Ddb)9]'
    face = ''
    for lst in [eyes, noses, mouths]:
        face += random.choice(lst)
    return face


def fancy(msg):
    msg += ' ' + smiley()
    with settings(warn_only=True):
        with hide('warnings'):
            out = local('cowsay "%s"' % msg, capture=True)
    if out.failed:
        return msg
    else:
        return out
    msg += ' ' + smiley()


@task
def run_cmd(command, regexp=''):
    """
    Run the given command, and maybe look if it matches the given regexp

    :param comman: command to run
    :param regexp: regexp to match, empy by default
    """
    if not regexp:
        run(command)

    else:
        res = run_match(command, regexp)
        if res:
            puts(res)
        else:
            sys.exit(1)


def run_match(command, regexp, hide_out=True):
    """
    Helper function to check if the output of a command matches a regexp

    :param comman: Command to run
    :param regexp: Regexp to matches
    :param hide_out: Hide the commands output, True by default
    :rtype: :class:`.CmdResponse`

    """
    if hide_out:
        to_hide = ['warnings', 'stdout']
    else:
        to_hide = []
    with hide(*to_hide):
        out = run(command)
    res = re.search(regexp, out)
    if res:
        return CmdResponse(out, True)
    else:
        return CmdResponse(out, False)


def matches_glob(what, pattern):
    return re.match(translate(pattern), what)


def ifilter_glob(what_list, patterns):
    for what in what_list:
        for pattern in patterns:
            if matches_glob(what, pattern):
                yield what
                break


def filter_glob(what_list, patterns):
    return list(ifilter_glob(what_list, patterns))


def check_param(env_name, param_name, params, input_func=raw_input):
    if env_name not in env:
        if param_name not in params and TTY:
            env[env_name] = input_func('Provide %s: ' % param_name)
        elif param_name not in params:
            raise Exception('Missing parameter %s and %s not found in '
                            'configuration file' % (param_name, env_name))
        else:
            env[env_name] = params[param_name]
