# -*- coding: utf-8 -*-
"""工况包：单工况与批量工况的配置、生成与运行。"""
from .single import SingleCaseConfig, generate_single_case
from .batch import BatchConfig, generate_batch_cases
from .template import update_fast_file, set_olaf_panels

__all__ = ['SingleCaseConfig', 'generate_single_case',
           'BatchConfig', 'generate_batch_cases',
           'update_fast_file', 'set_olaf_panels']
