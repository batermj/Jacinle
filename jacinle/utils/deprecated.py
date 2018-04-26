#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# File   : deprecated.py
# Author : Jiayuan Mao
# Email  : maojiayuan@gmail.com
# Date   : 04/21/2018
# 
# Distributed under terms of the MIT license.

import functools

from jacinle.logging import get_logger
from .naming import func_name

logger = get_logger(__file__)

__all__ = ['deprecated']


def deprecated(func):
    @functools.wraps
    def new_func(*args, **kwargs):
        if func not in deprecated.logged:
            deprecated.logged.add(func)
            logger.warning(func.__doc__)
        return func(*args, **kwargs)
    return new_func

deprecated.logged = set()
