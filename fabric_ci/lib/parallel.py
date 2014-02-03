#!/usr/bin/env python
"""
Very ugly monkey patching to show the parallel job statuses and add the return
codes to the responses
"""

from __future__ import with_statement
import time
import Queue
import sys
from fabric.network import ssh
from fabric.context_managers import settings
from utils import red, green, yellow, white


WHIPE = '\r' + ' '*80 + '\r'


def run(self):
    """
    This is the workhorse. It will take the intial jobs from the _queue,
    start them, add them to _running, and then go into the main running
    loop.

    This loop will check for done procs, if found, move them out of
    _running into _completed. It also checks for a _running queue with open
    spots, which it will then fill as discovered.

    To end the loop, there have to be no running procs, and no more procs
    to be run in the queue.

    This function returns an iterable of all its children's exit codes.
    """
    def _advance_the_queue(self):
        """
        Helper function to do the job of poping a new proc off the queue
        start it, then add it to the running queue. This will eventually
        depleate the _queue, which is a condition of stopping the running
        while loop.

        It also sets the env.host_string from the job.name, so that fabric
        knows that this is the host to be making connections on.
        """
        self._status()
        job = self._queued.pop()
        if self._debug:
            print("Popping '%s' off the queue and starting it" % job.name)
        with settings(clean_revert=True, host_string=job.name, host=job.name):
            job.start()
        self._running.append(job)
        self._status()

    self._time_start = time.time()
    # Prep return value so we can start filling it during main loop
    results = {}
    for job in self._queued:
        results[job.name] = dict.fromkeys(('exit_code', 'results'))

    if not self._closed:
        raise Exception("Need to close() before starting.")

    if self._debug:
        print("Job queue starting.")

    while len(self._running) < self._max:
        _advance_the_queue(self)
    self._status()

    # Main loop!
    while not self._finished:
        while len(self._running) < self._max and self._queued:
            _advance_the_queue(self)

        if not self._all_alive():
            for id, job in enumerate(self._running):
                if not job.is_alive():
                    if self._debug:
                        print("Job queue found finished proc: %s." %
                                job.name)
                    done = self._running.pop(id)
                    self._completed.append(done)

            if self._debug:
                print("Job queue has %d running." % len(self._running))

        if not (self._queued or self._running):
            if self._debug:
                print("Job queue finished.")

            for job in self._completed:
                job.join()

            self._finished = True

        # Each loop pass, try pulling results off the queue to keep its
        # size down.
        self._fill_results(results)

        self._status()
        time.sleep(ssh.io_sleep)

    self._status()
    # Consume anything left in the results queue
    self._fill_results(results)

    self._errors = 0
    # Attach exit codes now that we're all done & have joined all jobs
    for job in self._completed:
        results[job.name]['exit_code'] = job.exitcode
        if job.exitcode != 0:
            self._errors += 1

    self._status(final=True)
    return results


def _status(self, final=False):
    if not final:
        new = (green(len(self._completed)),
           white(len(self._running)),
           yellow(len(self._queued)),
           green('finished'),
           white('running'),
           yellow('queued'))
        if hasattr(self, 'last_status') and new == self.last_status:
            return
        self.last_status = (green(len(self._completed)),
            white(len(self._running)),
            yellow(len(self._queued)),
            green('finished'),
            white('running'),
            yellow('queued'))
        print WHIPE, "[%s/%s/%s] %s, %s, %s" % new
    else:
        print "\n[ %s OK / %s ERROR ] in %s seconds" % (
                green(self._num_of_jobs - self._errors, True),
                red(self._errors),
                time.time() - self._time_start)
        if self._errors:
            print red("Failures:", True)
            for job in self._completed:
                if job.exitcode != 0:
                    print red(job.name)
    sys.stdout.flush()


def _fill_results(self, results):
    """
    Attempt to pull data off self._comms_queue and add to 'results' dict.
    """
    while True:
        try:
            datum = self._comms_queue.get(timeout=1)
            results[datum['name']]['results'] = datum['result']
        except Queue.Empty:
            break


def monkey_patch(mod):
    mod.job_queue.JobQueue.run = run
    mod.job_queue.JobQueue._status = _status
    mod.job_queue.JobQueue._fill_results = _fill_results
