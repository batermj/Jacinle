#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# File   : pool.py
# Author : Jiayuan Mao
# Email  : maojiayuan@gmail.com
# Date   : 01/28/2018
#
# This file is part of Jacinle.
# Distributed under terms of the MIT license.

import sys
import multiprocessing as mp
import threading
import queue
import functools
import collections

from jacinle.logging import get_logger
from jacinle.utils.enum import JacEnum
from jacinle.utils.meta import map_exec_method
from jacinle.utils.tqdm import tqdm_pbar

logger = get_logger(__file__)

__all__ = ['Pool', 'TQDMPool', 'default_pool', 'multiprocessing_map', 'tqdm_multiprocessing_map']


class _ResultType(JacEnum):
    RESULT = 'result'
    COUNT = 'count'
    EXC = 'exc'


class Pool(object):
    def Queue(self, *args, **kwargs):
        return mp.Queue(*args, **kwargs)

    def Process(self, *args, **kwargs):
        return mp.Process(*args, **kwargs)

    def __init__(self, nr_workers=None):
        if nr_workers is None:
            nr_workers = mp.cpu_count()
        self._nr_workers = nr_workers

        self._worker_pool = None
        self._task_queue = None
        self._result_queue = None
        self._task_dispatcher_thread = None
        self._task_dispatcher_queue = None
        self._task_dispatcher_result = None

        self.__started = False

    def start(self):
        assert not self.__started
        self._task_queue = self.Queue(maxsize=self._nr_workers * 8)
        self._result_queue = self.Queue(maxsize=self._nr_workers * 8)
        self._worker_pool = [self.Process(target=self._worker, args=(i, ), daemon=True) for i in range(
            self._nr_workers)]
        self._task_dispatcher_thread = threading.Thread(target=self._task_dispatcher, daemon=True)
        self._task_dispatcher_queue = queue.Queue(maxsize=1)
        self._task_dispatcher_result = queue.Queue(maxsize=1)

        map_exec_method('start', self._worker_pool)
        self._task_dispatcher_thread.start()

        self.__started = True

    def try_start(self):
        if not self.__started:
            self.start()

    def terminate(self):
        self._task_dispatcher_queue.put(None)
        self._task_dispatcher_thread.join()
        map_exec_method('join', self._worker_pool)

    def _worker(self, worker_id):
        while True:
            task = self._task_queue.get()
            if task is None:
                break

            try:
                func, chunk = task
                result = []
                for i, val in chunk:
                    result.append((i, func(val)))
                self._result_queue.put(('result', result))
            except Exception:
                print(sys.exc_info())
                self._result_queue.put(('exc', _format_exc(sys.exc_info())))

    def _task_dispatcher(self):
        while True:
            task_desc = self._task_dispatcher_queue.get()
            if task_desc is None:
                for i in range(self._nr_workers):
                    self._task_queue.put(None)
                break

            func, iterable, chunksize = task_desc

            nr_total = 0
            chunk = list()
            for i, val in enumerate(iterable):
                chunk.append((i, val))
                nr_total += 1
                if len(chunk) >= chunksize:
                    self._task_queue.put((func, chunk))
                chunk = list()
            if len(chunk):
                self._task_queue.put((func, chunk))
            self._result_queue.put(('count', nr_total))

    def map(self, func, iterable, chunksize=1, sort=True, callback=None):
        self.try_start()
        self._task_dispatcher_queue.put((func, iterable, chunksize))

        all_result = []
        nr_total = None
        while True:
            result_type, result = self._result_queue.get()
            result_type = _ResultType.from_string(result_type)
            if result_type is _ResultType.COUNT:
                nr_total = result
            elif result_type is _ResultType.RESULT:
                if callback is not None:
                    for r in result:
                        callback(*r)
                all_result.extend(result)
            elif result_type is _ResultType.EXC:
                # TODO(Jiayuan Mao @ 04/24): show the worker process ID, etc.
                logger.warning('Worker got exception: ' + result)
                break

            if nr_total is not None and len(all_result) >= nr_total:
                break
        if sort:
            all_result.sort(key=lambda x: x[0])
        return [r[1] for r in all_result]


class TQDMPool(Pool):
    def map(self, func, iterable, chunksize=1, sort=True, total=None, desc='', callback=None, use_tqdm=True, **kwargs):
        if total is None and isinstance(iterable, collections.Sized):
            total = len(iterable)
        if use_tqdm:
            pbar = tqdm_pbar(total=total, **kwargs)
            return super().map(func, iterable, chunksize, sort, callback=self._wrap_callback(callback, pbar, desc))
        else:
            return super().map(func, iterable, chunksize, sort, callback=callback)

    def _wrap_callback(self, callback, pbar, desc):
        def wrapped(i, val):
            if callback is not None:
                callback(i, val)
            d = desc
            if type(d) is str:
                d += ' (iter={})'.format(i)
            if callable(d):
                d = d(i, val)
            assert type(d) is str
            pbar.set_description(desc)
            pbar.update()
        return wrapped


def _format_exc(ei):
    import io
    import traceback

    sio = io.StringIO()
    tb = ei[2]
    # See issues #9427, #1553375. Commented out for now.
    #if getattr(self, 'fullstack', False):
    #    traceback.print_stack(tb.tb_frame.f_back, file=sio)
    traceback.print_exception(ei[0], ei[1], tb, None, sio)
    s = sio.getvalue()
    sio.close()
    if s[-1:] == "\n":
        s = s[:-1]
    return s


default_pool = TQDMPool(1)

multiprocessing_map = functools.partial(default_pool.map, use_tqdm=False)
tqdm_multiprocessing_map = functools.partial(default_pool.map, use_tqdm=True)
