import sys
import re
import torch.nn as nn
import deepxml.models.residual_layer as residual_layer
import deepxml.models.astec as astec
import json
from collections import OrderedDict


class _Identity(nn.Module):
    def __init__(self, *args, **kwargs):
        super(_Identity, self).__init__()

    def forward(self, x):
        x, _ = x
        return x

    def initialize(self, *args, **kwargs):
        pass


class Identity(nn.Module):
    def __init__(self, *args, **kwargs):
        super(Identity, self).__init__()

    def forward(self, x):
        return x

    def initialize(self, *args, **kwargs):
        pass


elements = {
    'dropout': nn.Dropout,
    'batchnorm1d': nn.BatchNorm1d,
    'linear': nn.Linear,
    'relu': nn.ReLU,
    'residual': residual_layer.Residual,
    'identity': Identity,
    '_identity': _Identity,
    'astec': astec.Astec
}


class Transform(nn.Module):
    """
    Transform document representation!
    transform_string: string for sequential pipeline
        eg relu#,dropout#p:0.1,residual#input_size:300-output_size:300
    params: dictionary like object for default params
        eg {emb_size:300}
    """

    def __init__(self, modules, device="cuda:0"):
        super(Transform, self).__init__()
        self.device = device
        if len(modules) == 1:
            self.transform = modules[0]
        else:
            self.transform = nn.Sequential(*modules)

    def forward(self, x):
        """
            Forward pass for transform layer
            Args:
                x: torch.Tensor: document representation
            Returns:
                x: torch.Tensor: transformed document representation
        """
        return self.transform(x)

    def _initialize(self, x):
        """Initialize parameters from existing ones
        Typically for word embeddings
        """
        if isinstance(self.transform, nn.Sequential):
            self.transform[0].initialize(x)
        else:
            self.transform.initialize(x)

    def initialize(self, x):
        # Currently implemented for:
        #  * initializing first module of nn.Sequential
        #  * initializing module
        self._initialize(x)

    def to(self):
        super().to(self.device)

    def get_token_embeddings(self):
        return self.transform.get_token_embeddings()

    @property
    def sparse(self):
        try:
            _sparse = self.transform.sparse
        except AttributeError:
            _sparse = False
        return _sparse


def get_functions(obj, params=None):
    return list(map(lambda x: elements[x](**obj[x]), obj['order']))
