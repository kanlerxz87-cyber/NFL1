"""NFL1 - verified-data-first NFL line origination and strategy research engine.

Design rule enforced across the whole package: no value is ever invented.
Every number carries an explicit provenance tier (see provenance.py). Where a
required input cannot be confirmed from an official source the value is None
and the dependent output is BLOCKED, not estimated.
"""
__version__ = "0.1.0"
