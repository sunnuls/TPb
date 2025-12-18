from __future__ import annotations

from enum import Enum


class ProductMode(str, Enum):
    REVIEW = "review"
    TRAIN = "train"
    LIVE_RESTRICTED = "live_restricted"
    INSTANT_REVIEW = "instant_review"
