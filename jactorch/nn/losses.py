# -*- coding: utf-8 -*-
# File   : losses.py
# Author : Jiayuan Mao
# Email  : maojiayuan@gmail.com
# Date   : 25/01/2018
# 
# This file is part of Jacinle.

import torch
import torch.nn as nn

from jacinle.utils.enum import JacEnum
from jactorch.functional.indexing import one_hot
from jactorch.graph.variable import var_with


class LossAverageMethod(JacEnum):
    NONE = 'none'
    ALL = 'all'
    VALID = 'valid'


class AverageLoss(nn.Module):
    def __init__(self, average):
        super().__init__()
        self.average_method = JacEnum.from_string(average)

    def _average(self, loss, mask):
        if self.average_method is not LossAverageMethod.NONE:
            if mask is not None:
                loss = loss * mask

                if self.average_method is LossAverageMethod.ALL:
                    loss = loss.mean()
                elif self.average_method is LossAverageMethod.VALID:
                    loss = loss.sum() / mask.sum()
                else:
                    raise ValueError('Unknown average method: {}.'.format(self.average_method))
            else:
                loss = loss.mean()
        return loss


class CrossEntropyLossWithProbs(AverageLoss):
    _eps = 1e-8

    def __init__(self, dim=-1, average=LossAverageMethod.VALID):
        super().__init__(average)
        self.dim = dim

    def forward(self, probs, target, mask=None):
        log_prob = torch.log(probs + self._eps)
        neg_xent = log_prob.gather(self.dim, target.unsqueeze(self.dim))
        return -self._average(neg_xent, mask)


class CompatibleCrossEntropyLossWithProbs(CrossEntropyLossWithProbs):
    def __init__(self, dim=-1, weight=None, ignore_index=None):
        super().__init__(dim, average=LossAverageMethod.NONE)
        self.weight = weight
        self.ignore_index = ignore_index

    def forward(self, probs, target, mask=None):
        assert mask is None
        loss = super().forward(probs, target)
        return weighted_loss(loss, target, self.weight, self.ignore_index)


class MSEProbabilityLoss(nn.Module):
    def __init__(self, weight=None, ignore_index=None):
        super().__init__()
        self.weight = weight
        self.ignore_index = ignore_index

    def forward(self, probs, target):
        target_onehot = one_hot(target, probs.size(1))
        loss = 0.5 * ((probs - target_onehot) ** 2.).sum(dim=1)
        return weighted_loss(loss, target, self.weight, self.ignore_index)


class SmoothL1Loss(AverageLoss):
    def __init__(self, sigma=3.0, average=LossAverageMethod.VALID):
        super().__init__(average)
        self.sigma2 = sigma * sigma

    def forward(self, input, target, sidechain=None):
        x = input - target
        a = (x >= 1.0 / self.sigma2).float()
        b = (x <= -1.0 / self.sigma2).float()
        loss = a * (x - 0.5 / self.sigma2) + b * (-x - 0.5 / self.sigma2) + (1 - a - b) * 0.5 * x * x * self.sigma2
        loss = loss.sum(dim=1)

        mask = None
        if sidechain is not None:
            mask = (sidechain > 0).float()
        return self._average(loss, mask)


def masked_average(tensor, mask, eps=1e-8):
    tensor = tensor.float()
    mask = mask.float()
    masked = tensor * mask
    return masked.sum() / torch.max(mask.sum(), eps)


def weighted_loss(loss, target, weight, ignore_index):
    if weight is not None:
        weight = var_with(weight, target)
        weight = weight[target]
    else:
        weight = 1
    if ignore_index is not None:
        weight *= (target.ne(ignore_index).float())

    if type(weight) is int and weight == 1:
        return loss.mean()
    else:
        return masked_average(loss, weight)