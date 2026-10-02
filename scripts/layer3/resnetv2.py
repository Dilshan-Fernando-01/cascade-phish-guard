from collections import OrderedDict

import torch
import torch.nn as nn
import torch.nn.functional as F


class StdConv2d(nn.Conv2d):
    def forward(self, x):
        w = self.weight
        v, m = torch.var_mean(w, dim=[1, 2, 3], keepdim=True, unbiased=False)
        w = (w - m) / torch.sqrt(v + 1e-10)
        return F.conv2d(x, w, self.bias, self.stride, self.padding, self.dilation, self.groups)


def conv3x3(cin, cout, stride=1, groups=1, bias=False):
    return StdConv2d(cin, cout, kernel_size=3, stride=stride, padding=1, bias=bias, groups=groups)


def conv1x1(cin, cout, stride=1, bias=False):
    return StdConv2d(cin, cout, kernel_size=1, stride=stride, padding=0, bias=bias)


class PreActBottleneck(nn.Module):
    def __init__(self, cin, cout=None, cmid=None, stride=1):
        super().__init__()
        cout = cout or cin
        cmid = cmid or cout // 4

        self.gn1 = nn.GroupNorm(32, cin)
        self.conv1 = conv1x1(cin, cmid)
        self.gn2 = nn.GroupNorm(32, cmid)
        self.conv2 = conv3x3(cmid, cmid, stride)
        self.gn3 = nn.GroupNorm(32, cmid)
        self.conv3 = conv1x1(cmid, cout)
        self.relu = nn.ReLU(inplace=True)

        if stride != 1 or cin != cout:
            self.downsample = conv1x1(cin, cout, stride)

    def forward(self, x):
        out = self.relu(self.gn1(x))
        residual = x
        if hasattr(self, "downsample"):
            residual = self.downsample(out)
        out = self.conv1(out)
        out = self.conv2(self.relu(self.gn2(out)))
        out = self.conv3(self.relu(self.gn3(out)))
        return out + residual


class ResNetV2(nn.Module):
    """Pre-activation (v2) ResNet, as used by Phishpedia's siamese logo matcher."""

    def __init__(self, block_units, width_factor, head_size=21843, zero_head=False):
        super().__init__()
        wf = width_factor

        self.root = nn.Sequential(OrderedDict([
            ("conv", StdConv2d(3, 64 * wf, kernel_size=7, stride=2, padding=3, bias=False)),
            ("pad", nn.ConstantPad2d(1, 0)),
            ("pool", nn.MaxPool2d(kernel_size=3, stride=2, padding=0)),
        ]))

        self.body = nn.Sequential(OrderedDict([
            ("block1", nn.Sequential(OrderedDict(
                [("unit01", PreActBottleneck(cin=64 * wf, cout=256 * wf, cmid=64 * wf))] +
                [(f"unit{i:02d}", PreActBottleneck(cin=256 * wf, cout=256 * wf, cmid=64 * wf))
                 for i in range(2, block_units[0] + 1)],
            ))),
            ("block2", nn.Sequential(OrderedDict(
                [("unit01", PreActBottleneck(cin=256 * wf, cout=512 * wf, cmid=128 * wf, stride=2))] +
                [(f"unit{i:02d}", PreActBottleneck(cin=512 * wf, cout=512 * wf, cmid=128 * wf))
                 for i in range(2, block_units[1] + 1)],
            ))),
            ("block3", nn.Sequential(OrderedDict(
                [("unit01", PreActBottleneck(cin=512 * wf, cout=1024 * wf, cmid=256 * wf, stride=2))] +
                [(f"unit{i:02d}", PreActBottleneck(cin=1024 * wf, cout=1024 * wf, cmid=256 * wf))
                 for i in range(2, block_units[2] + 1)],
            ))),
            ("block4", nn.Sequential(OrderedDict(
                [("unit01", PreActBottleneck(cin=1024 * wf, cout=2048 * wf, cmid=512 * wf, stride=2))] +
                [(f"unit{i:02d}", PreActBottleneck(cin=2048 * wf, cout=2048 * wf, cmid=512 * wf))
                 for i in range(2, block_units[3] + 1)],
            ))),
        ]))

        self.zero_head = zero_head
        self.head = nn.Sequential(OrderedDict([
            ("gn", nn.GroupNorm(32, 2048 * wf)),
            ("relu", nn.ReLU(inplace=True)),
            ("avg", nn.AdaptiveAvgPool2d(output_size=1)),
            ("conv", nn.Conv2d(2048 * wf, head_size, kernel_size=1, bias=True)),
        ]))

    def features(self, x):
        x = self.head[:-1](self.body(self.root(x)))
        return x.squeeze(-1).squeeze(-1)

    def forward(self, x):
        x = self.head(self.body(self.root(x)))
        return x[..., 0, 0]


def bit_m_r50x1(head_size=21843, zero_head=False):
    return ResNetV2([3, 4, 6, 3], 1, head_size=head_size, zero_head=zero_head)
