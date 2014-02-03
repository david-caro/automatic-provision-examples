#!/usr/bin/env python
#encoding: utf-8
from decorator import FunctionMaker

def decorator_apply(dec, func):
    return FunctionMaker.create(
        func, 'return decorated(%(signature)s)',
        dict(decorated=dec(func)), __wrapped__=func)

def task(func):
    return decorator_apply(origtask, func)

