#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# File   : loglinear.py
# Author : Jiayuan Mao
# Email  : maojiayuan@gmail.com
# Date   : 05/31/2018
#
# This file is part of Jacinle.
# Distributed under terms of the MIT license.

import torch

from .shape import concat_shape, move_dim

__all__ = ['logaddexp', 'logsumexp', 'logmatmulexp', 'batch_logmatmulexp', 'logits_and', 'logits_or']


def logaddexp(x, y):
    return torch.max(x, y) + torch.log(1 + torch.exp(-torch.abs(y - x)))


def logsumexp(inputs, dim=-1, keepdim=False):
    inputs_max = inputs.max(dim=dim, keepdim=True)[0]
    inputs = inputs - inputs_max
    if not keepdim:
        inputs_max = inputs_max.squeeze(dim)
    return _safe_log(inputs.exp().sum(dim=dim, keepdim=keepdim)) + inputs_max
    # return (inputs - F.log_softmax(inputs, dim=dim)).mean(dim, keepdim=keepdim)


def logmatmulexp(mat1, mat2, use_mm=False):
    mat1_shape = mat1.size()
    mat2_shape = mat2.size()
    mat1 = mat1.contiguous().view(-1, mat1_shape[-1])
    mat2 = move_dim(mat2, 0, -1)
    mat2 = mat2.contiguous().view(-1, mat2_shape[0])

    if use_mm:
        mat1_max = mat1.max(dim=-1, keepdim=True)[0]
        mat2_max = mat2.max(dim=-1, keepdim=True)[0]
        mat1 = mat1 - mat1_max
        mat2 = mat2 - mat2_max

        out = _safe_log(torch.matmul(mat1.exp(), mat2.exp().t()))
        out = out + mat1_max + mat2_max.t()
    else:
        out_sum = mat1.unsqueeze(1) + mat2.unsqueeze(0)
        out = logsumexp(out_sum, dim=-1)

    return out.view(concat_shape(mat1_shape[:-1], mat2_shape[1:]))


def batch_logmatmulexp(mat1, mat2, use_mm=False):
    mat1_shape = mat1.size()
    mat2_shape = mat2.size()
    mat1 = mat1.contiguous().view(mat1_shape[0], -1, mat1_shape[-1])
    mat2 = move_dim(mat2, 1, -1)
    mat2 = mat2.contiguous().view(mat2_shape[0], -1, mat2_shape[1])

    if use_mm:
        mat1_max = mat1.max(dim=-1, keepdim=True)[0]
        mat2_max = mat2.max(dim=-1, keepdim=True)[0]
        mat1 = mat1 - mat1_max
        mat2 = mat2 - mat2_max

        out = _safe_log(torch.bmm(mat1.exp(), mat2.exp().permute(0, 2, 1)))
        out = out + mat1_max + mat2_max.permute(0, 2, 1)
    else:
        out_sum = mat1.unsqueeze(2) + mat2.unsqueeze(1)
        out = logsumexp(out_sum, dim=-1)

    return out.view(concat_shape(mat1_shape[:-1], mat2_shape[2:]))


def logits_and(x, y):
    t = (x + y) / 2
    f = logaddexp(logaddexp((x - y) / 2, (y - x) / 2), -t)
    return t - f


def logits_or(x, y):
    f = -(x + y) / 2
    t = logaddexp(logaddexp((x - y) / 2, (y - x) / 2), -f)
    return t - f


def _safe_log(x):
    # mask = (x < 1e-8).float()
    # return x.clamp(min=1e-8).log() * (1 - mask) + -1e5 * mask
    return x.log()

