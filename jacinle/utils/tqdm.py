#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# File   : tqdm.py
# Author : Jiayuan Mao
# Email  : maojiayuan@gmail.com
# Date   : 03/23/2017
#
# This file is part of Jacinle.
# Distributed under terms of the MIT license.

from tqdm import tqdm as _tqdm
from .meta import gofor

__all__ = ['get_tqdm_defaults', 'tqdm', 'tqdm_pbar', 'tqdm_gofor', 'tqdm_zip']

__tqdm_defaults = {'dynamic_ncols': True, 'ascii': True}


def get_tqdm_defaults():
    return __tqdm_defaults


def tqdm(iterable, **kwargs):
    """Wrapped tqdm, where default kwargs will be load, and support `for i in tqdm(10)` usage."""
    for k, v in get_tqdm_defaults().items():
        kwargs.setdefault(k, v)

    if type(iterable) is int:
        iterable, total = range(iterable), iterable
    else:
        try:
            total = len(iterable)
        except TypeError:
            total = None

    if 'total' not in kwargs and total is not None:
        kwargs['total'] = total

    return _tqdm(iterable, **kwargs)


def tqdm_pbar(**kwargs):
    for k, v in get_tqdm_defaults().items():
        kwargs.setdefault(k, v)
    return _tqdm(**kwargs)


def tqdm_gofor(iterable, **kwargs):
    kwargs.setdefault('total', len(iterable))
    return tqdm(gofor(iterable), **kwargs)


def tqdm_zip(*iterable, **kwargs):
    kwargs.setdefault('total', len(iterable[0]))
    return tqdm(zip(*iterable), **kwargs)

