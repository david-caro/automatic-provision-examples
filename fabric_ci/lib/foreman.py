#!/usr/bin/env python
#encoding: utf-8
from functools import wraps
from fabric.api import env
from getpass import getpass
from fabric_ci.lib.utils import check_param


def foreman_defaults(func):
    """
    Decorator to pass the defaults to the function

    All the default params will be passed as keyword arguments. positional
    arguments will be respected
    """

    @wraps(func)
    def newfunc(*args, **kwargs):
        """
        Wrapper to add the foerman parameters to the task
        """
        check_param('FOREMAN_URL', 'foreman', kwargs)
        check_param('FOREMAN_USER', 'user', kwargs)
        check_param('FOREMAN_PASSWORD', 'passwd', kwargs, input_func=getpass)
        kwargs['foreman'] = kwargs.get('foreman', env.FOREMAN_URL)
        kwargs['user'] = kwargs.get('user', env.FOREMAN_USER)
        kwargs['passwd'] = kwargs.get('passwd', env.FOREMAN_PASSWORD)
        return func(*args, **kwargs)
    return newfunc
