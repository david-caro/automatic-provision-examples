#!/usr/bin/env python
#encoding: utf-8


import sys
from pprint import pprint


class Limit():
    def __init__(self, warn_lvl='', crit_lvl='',
                 cmp_func=None,
                 min_value='', max_value='',
                 uom=''):
        self.warn_lvl = warn_lvl
        self.crit_lvl = crit_lvl
        self.min_value = min_value
        self.max_value = max_value
        self.uom = uom
        if not cmp_func:
            cmp_func = lambda x, y: x > y
        self.cmp_func = cmp_func

    def test(self, value):
        if self.cmp_func(value, self.crit_lvl):
            return 'critical'
        elif self.cmp_func(value, self.warn_lvl):
            return 'warning'
        else:
            return 'ok'

    def __repr__(self):
        return "w:%s/c:%s" % (str(self.warn_lvl), str(self.crit_lvl))


class DataItem():
    def __init__(self, label, value, limit=None, uom='', warn='', crit='',
                 vmin='', vmax=''):
        self.value = value
        self.label = label
        self.uom = uom or limit.uom
        self.warn = warn or limit.warn_lvl
        self.crit = crit or limit.crit_lvl
        self.vmin = vmin or limit.min_value
        self.vmax = vmax or limit.max_value

    def perf(self):
        return self.label + "'=" \
            + ";".join((str(self.value) + str(self.uom),
                        str(self.warn), str(self.crit),
                        str(self.vmin), str(self.vmax)))

    def __repr__(self):
        return repr(self.value)

    def __str__(self):
        return str(self.value)


class DataSet(dict):
    def __init__(self, limits):
        if len(limits) == 0:
            raise Exception("Need at least 1 limit")
        self.limits = limits
        self.num_values = len(limits)

    def add_data(self, tag_name, *values):
        if len(values) != self.num_values:
            raise Exception("Need %d values, %d passed" % (self.num_values,
                                                           len(values)))
        self[tag_name] = [DataItem(v[0], v[1], limit=self.limits[i])
                          for i, v in enumerate(values)]

    def complies(self, *limits):
        limits = limits or self.limits
        if len(limits) != self.num_values:
            raise Exception("Need %d limits, %d passed" % (self.num_values,
                                                           len(limits)))
        detailed = {}
        error_str = ''
        gstatus = 'ok'
        for tag, data in self.iteritems():
            detailed[tag] = []
            for dataitem, limit in zip(data, limits):
                res = limit.test(dataitem.value)
                if gstatus == 'ok':
                    gstatus = res
                elif res == 'critical':
                    gstatus = 'critical'
                detailed[tag].append(res)
                if res != 'ok':
                    error_str += "%s:%s.%s=%s " % (res, tag,
                                                   dataitem.label,
                                                   dataitem.value)
        return gstatus, error_str, detailed, self.perf()

    def perf(self):
        perf_str = ''
        for tag, values in self.iteritems():
            perf_str += ' '.join(["'%s.%s" % (tag, v.perf())
                                  for v in values])
            perf_str += ' '
        return perf_str


class NagiosPlugin():
    """
    Simple class to manage nagios plugin login

    Example:
    > mycheck = NagiosPlugin('Provision', num_values=3)
    > mycheck.set_limits(Limit(2, 5),
                         Limit(10, 2, lambda x, y: x < y),
                         Limit(0, 0, lambda *x: False))
    > mycheck.add_data('Global', ('reserved', 5), ('free', 10), ('other', 2))
    > mycheck.add_data('Hostgroup 1', ('reserved', 1), ('free', 1), ('other', 1))
    > mycheck.add_data('Hostgroup 2', ('reserved', 4), ('free', 9), ('other', 1))
    > mycheck.do_check()
    Provision CRITICAL: {'Globally reserved/free/other': ['warning', 'ok',
    'ok'], 'Hostgroup 1 reserved/free/other': ['ok', 'critical', 'ok'],
    'Hostgroup 2 reserved/free/other': ['warning', 'warning', 'ok']}
    An exception has occurred, use %tb to see the full traceback.

    SystemExit: 1
    """

    def __init__(self, name, *limits):
        """
        One limit per value
        """
        self.name = name
        self.dataset = DataSet(limits)

    def add_data(self, tag_name, *values):
        self.dataset.add_data(tag_name, *values)

    def set_limits(self, *limits):
        self.dataset.set_limits(*limits)

    def critical(self, msg, perf='', long_msg=''):
        print "%s CRITICAL: %s | %s " % (self.name, msg, perf)
        pprint(long_msg)
        sys.exit(2)

    def warning(self, msg, perf, long_msg):
        print "%s WARNING: %s | %s" % (self.name, msg, perf)
        pprint(long_msg)
        sys.exit(1)

    def ok(self, msg, perf, long_msg):
        print "%s OK: %s | %s" % (self.name, msg, perf)
        pprint(long_msg)
        sys.exit(0)

    def unknown(self, msg, perf, long_msg):
        print "%s UNKNOWN: %s | %s" % (self.name, msg, perf)
        pprint(long_msg)
        sys.exit(3)

    def do_check(self):
        res, info, det_info, perf = self.dataset.complies()
        getattr(self, res)(info, perf, det_info)
