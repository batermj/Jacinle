#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# File   : indexing.py
# Author : Jiayuan Mao
# Email  : maojiayuan@gmail.com
# Date   : 01/24/2018
#
# This file is part of Jacinle.
# Distributed under terms of the MIT license.

import torch

from jacinle.utils.numeric import prod
from jactorch.utils.grad import no_grad_func

__all__ = [
    'reversed',
    'one_hot', 'one_hot_nd', 'one_hot_dim',
    'inverse_permutation',
    'index_one_hot', 'set_index_one_hot_',
    'index_one_hot_ellipsis']


def reversed(x, dim=-1):
    # https://github.com/pytorch/pytorch/issues/229#issuecomment-350041662
    xsize = x.size()
    dim = x.dim() + dim if dim < 0 else dim
    x = x.view(-1, *xsize[dim:])
    inds = torch.arange(x.size(1) - 1, -1, -1, dtype=torch.long, device=x.device)
    x = x.view(x.size(0), x.size(1), -1)[:, inds, :]
    return x.view(xsize)


@no_grad_func
def one_hot(index, nr_classes):
    assert index.dim() == 1
    mask = torch.zeros(index.size(0), nr_classes, dtype=torch.float32, device=index.device)
    ones = torch.ones(index.size(0), 1, dtype=torch.float32, device=index.device)
    ret = mask.scatter_(1, index.unsqueeze(1), ones)
    return ret


@no_grad_func
def one_hot_nd(index, nr_classes):
    index_size = index.size()
    return one_hot(index.view(-1), nr_classes).view(index_size + (nr_classes, ))


@no_grad_func
def one_hot_dim(index, nr_classes, dim):
    return one_hot_nd(index, nr_classes).transpose(-1, dim)


@no_grad_func
def inverse_permutation(perm):
    length = perm.size(0)
    inv = torch.zeros(length, dtype=torch.long, device=perm.device)
    inv.scatter_(0, perm, torch.arange(0, length, dtype=torch.long, device=perm.device))
    return inv.long()


def index_one_hot(tensor, dim, index):
    """Return tensor[:, :, index, :, :]"""
    return tensor.gather(dim, index.unsqueeze(dim)).squeeze(dim)


def set_index_one_hot_(tensor, dim, index, value):
    """Return tensor[:, :, index, :, :]"""
    if not isinstance(value, (int, float)):
        value = value.unsqueeze(dim)
    return tensor.scatter_(dim, index.unsqueeze(dim), value)


def index_one_hot_ellipsis(tensor, dim, index):
    """Return tensor[:, :, index, ...]"""
    tensor_shape = tensor.size()
    tensor = tensor.view(prod(tensor_shape[:dim]), tensor_shape[dim], prod(tensor_shape[dim+1:]))
    assert tensor.size(0) == index.size(0)
    index = index.unsqueeze(-1).unsqueeze(-1)
    index = index.expand(tensor.size(0), 1, tensor.size(2))
    tensor = tensor.gather(1, index)
    return tensor.view(tensor_shape[:dim] + tensor_shape[dim+1:])
