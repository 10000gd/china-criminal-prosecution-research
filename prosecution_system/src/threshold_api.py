# -*- coding: utf-8 -*-
"""
入罪门槛 API - threshold_api.py

提供各省市各罪名入罪门槛的查询和对比接口：
- GET /api/threshold?crime=盗窃罪        → 所有省份门槛
- GET /api/threshold?crime=盗窃罪&province=北京  → 单一省份详情
- GET /api/threshold?amount=5000&crime=盗窃罪  → 判断是否达到入罪标准
"""

import sys

import logging
logger = logging.getLogger(__name__)
