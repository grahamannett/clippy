from transformers import LlamaForCausalLM

from torch import nn


class Cllama(nn.Module):
    pass


from concurrent.futures import ThreadPoolExecutor
import torch
import asyncio
from transformers import LlamaTokenizer, LlamaForCausalLM


# model = LlamaForCausalLM.from_pretrained("alpaca", load_in_8bit=True, torch_dtype=torch.float16, device_map="auto")


import copy
from typing import Any, Dict, Union

import torch
import torch.nn as nn
import torch.nn.functional as F


def _randomized_positions(from_v, to_v):
    pos = torch.rand_like(from_v) * (to_v - from_v)
    return pos.int()


def _rounded_mean_positions(from_v, to_v):
    pos = (from_v + to_v).float() / 2
    return pos.round()


# tokenizer


def mu_law_encode(x, mu=100, m=256):
    numerator = torch.log(x.abs(), *mu + 1.0)
    denominator = torch.log(m * mu + 1.0)
    return (numerator / denominator) * x.sign()


def tokenize_continous_value(x, mu=100, m=256, bins=1024, shift=None):
    # appenddix B agent data tokenization
    # finally they are discretized using bins of uniform width on the domain[-1, 1]
    x = mu_law_encode(x, mu, m)

    # we use 1024 bins and shift the resulting integers
    # so they are not overlapping with the ones used for text tokens
    c = (c + 1) * (bins / 2)  # noqa: F821
    c = c.int()
    if shift is not None:
        c += shift
    return c


# config


class GatoConfig:
    @staticmethod
    def large():
        return GatoConfig(
            num_transformer_blocks=24,
            num_attention_heads=16,
            layer_width=2048,
            feedforward_hidden_size=8192,
            key_value_size=128,
        )

    @staticmethod
    def baseline():
        return GatoConfig(
            num_transformer_blocks=12,
            num_attention_heads=12,
            layer_width=1536,
            feedforward_hidden_size=6144,
            key_value_size=128,
        )

    @staticmethod
    def small():
        return GatoConfig(
            num_transformer_blocks=8,
            num_attention_heads=24,
            layer_width=768,
            feedforward_hidden_size=3072,
            key_value_size=32,
        )

    def __init__(self, **kwargs):
        self.input_dim = kwargs.pop("input_dim", 768)
        self.img_patch_size = kwargs.pop("img_patch_size", 16)

        # Section 2.3. Training
        self.token_sequence_length = kwargs.pop("token_sequence_length", 1024)

        # Section 2.1. Tokenization
        # Text - SentencePiece
        self.vocabulary_size = kwargs.pop("vocabulary_size", 32000)
        # Discrete values
        self.actions_size = kwargs.pop("actions_size", 1024)
        # Continuous values
        self.continuous_values_size = kwargs.pop("continuous_values_size", 1024)

        # Appendix C.1. Transformer Hyperparameters
        self.num_transformer_blocks = kwargs.pop("num_transformer_blocks", 8)
        self.num_attention_heads = kwargs.pop("num_attention_heads", 24)
        self.layer_width = kwargs.pop("layer_width", 768)
        self.feedforward_hidden_size = kwargs.pop("feedforward_hidden_size", 3072)
        self.key_value_size = kwargs.pop("key_value_size", 32)

        # Appendix E. Regularization
        self.dropout_rate = kwargs.pop("dropout_rate", 0.1)

        # Appendix C.2. Embedding Function
        self.num_group_norm_groups = kwargs.pop("num_group_norm_groups", 32)

        # Appendix C.3. Position Encodings > Patch Position Encodings
        self.discretize_depth = kwargs.pop("discretize_depth", 128)
        # Appendix C.3. Position Encodings > Local Observation Position Encodings
        self.local_position_encoding_size = kwargs.pop("local_position_encoding_size", 512)

        self.max_seq_len = kwargs.pop("max_seq_len", 8192)

    @property
    def embedding_input_size(self):
        return self.vocabulary_size + self.continuous_values_size + self.actions_size + 1

    @property
    def output_target_size(self):
        return self.vocabulary_size + self.actions_size

    def to_dict(self) -> Dict[str, Any]:
        output = copy.deepcopy(self.__dict__)
        return output

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "GatoConfig":
        config = cls(**config_dict)
        return config


class PatchPositionEncoding(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.embedding_dim = config.layer_width
        self.discretize_depth = config.discretize_depth
        self.patch_size = config.img_patch_size

        self.row_embedding = nn.Embedding(self.discretize_depth, self.embedding_dim)
        self.col_embedding = nn.Embedding(self.discretize_depth, self.embedding_dim)

    def _discretize(self, pos):
        return (pos * self.discretize_depth).round()

    def _discretize_interval(self, interval):
        pos_from, pos_to = interval
        return self._discretize(pos_from), self._discretize(pos_to)

    def forward(self, input_ids, pos):
        row_pos, col_pos = pos

        row_pos_from, row_pos_to = self._discretize_interval(row_pos)
        col_pos_from, col_pos_to = self._discretize_interval(col_pos)

        if self.training:
            row_pos = row_pos_from + _randomized_positions(row_pos_from, row_pos_to)
            col_pos = col_pos_from + _randomized_positions(col_pos_from, col_pos_to)
        else:
            row_pos = _rounded_mean_positions(row_pos_from, row_pos_to)
            col_pos = _rounded_mean_positions(col_pos_from, col_pos_to)

        return input_ids + self.row_embedding(row_pos.long()) + self.col_embedding(col_pos.long())

    def get_config(self):
        config = super(PatchPositionEncoding, self).get_config()
        config.update(
            {
                "config": self.config.to_dict(),
            }
        )
        return config


class ResidualUnit(nn.Module):
    def __init__(self, num_groups: int, filters: int):
        super().__init__()
        self.num_groups = num_groups
        self.filters = filters
        self.conv1 = nn.Conv2d(in_channels=filters, out_channels=filters // 2, kernel_size=3, stride=1, padding=1)
        self.conv2 = nn.Conv2d(in_channels=filters // 2, out_channels=filters, kernel_size=3, stride=2, padding=1)

        self.conv_proj = nn.Conv2d(in_channels=filters, out_channels=filters, kernel_size=1, stride=2, padding=0)
        self.gn1 = nn.GroupNorm(num_groups=self.num_groups, num_channels=filters)
        self.gn2 = nn.GroupNorm(num_groups=self.num_groups, num_channels=filters // 2)
        self.gn_proj = nn.GroupNorm(num_groups=self.num_groups, num_channels=filters)

    def forward(self, x):
        residual = self.conv_prok(self.gn_proj(x))

        x = F.gelu(self.gn1(x))
        x = self.conv1(x)

        x = F.gelu(self.gn2(x))
        x = self.conv2(x)

        return x + residual


class ResidualEmbedding(nn.Module):
    def __init__(self, config):
        super().__init__()

        self.root_conv = nn.Sequential(
            nn.Conv2d(in_channels=config.input_dim, out_channels=96, kernel_size=7, stride=2, padding=3),
            nn.GroupNorm(num_channels=96, num_groups=config.num_group_norm_groups),
            nn.GELU(),
        )

        self.residual_units = nn.ModuleList(
            [ResidualUnit(num_groups=config.num_group_norm_groups, filters=96 * 2 ** (i + 1)) for i in range(3)]
        )

        if config.input_dim != config.layer_width:
            self.conv_proj = nn.Conv2d(
                in_channels=96 * 2**3, out_channels=config.layer_width, kernel_size=1, stride=1, padding=0
            )

    def forward(self, images):
        x = self.root_conv(images)

        for unit in self.residual_units:
            x = unit(x)

        if self.config.input_dim != self.config.layer_width:
            x = self.conv_proj(x)

        return x

    def get_config(self):
        config = super(ResidualEmbedding, self).get_config()
        config.update({"config": self.config.to_dict()})
        return config


class PatchEmbedding(nn.Module):
    def __init__(self, config):
        super(PatchEmbedding, self).__init__()

        if isinstance(config, dict):
            config = GatoConfig(**config)
        self.config = config

        self.residual_embedding = ResidualEmbedding(config)
        self.pos_encoding = PatchPositionEncoding(config)

    def forward(self, inputs):
        input_ids, (row_pos, col_pos) = inputs
        patch_size = self.config.img_patch_size
        depth = self.config.input_dim // (patch_size * patch_size)

        x = input_ids.view(-1, input_ids.size(1), patch_size, patch_size, depth)
        x = self.residual_embedding(x)
        x = self.pos_encoding((x, (row_pos, col_pos)))
        return x

    def get_config(self):
        return super(PatchEmbedding, self).get_config()


config = GatoConfig.small()
image_embedding = PatchEmbedding(config)


out = image_embedding(torch.rand(1, 768, 16, 16), (torch.rand(1, 16, 16), torch.rand(1, 16, 16)))

print()
