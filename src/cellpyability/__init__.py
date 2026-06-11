"""
CellPyAbility: Open-source cell viability and dose-response analysis tool

CellPyAbility is an automated analysis tool for dose-response experiments 
via nuclei counting. It provides three modules:
- GDA: dose-response analysis of two cell lines with one drug gradient
- synergy: dose-response and synergy analysis with two drug gradients
- simple: raw nuclei count matrix in 96-well format
"""

from ._version import __version__
__author__ = "James Elia"
__email__ = "james.elia@yale.edu"

__all__ = [
    'toolbox',
    'gda_analysis',
    'synergy_analysis',
    'simple_analysis',
    'interactive_map',
]


def __getattr__(name):
    """Lazy-load submodules so lightweight commands do not import plotting stacks."""
    if name in __all__:
        from importlib import import_module

        return import_module(f'.{name}', __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
