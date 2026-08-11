"""scorebook — every ball of the IPL, 2008 to 2026.

A loader and a cleaner for Cricsheet's ball-by-ball archive. The analysis is not in here
on purpose: see docs/decisions/0006-analysis-in-notebooks.md.

    from scorebook import clean
    from scorebook.data import loaders

    deliveries = clean.prepare(loaders.load_deliveries())
"""

from __future__ import annotations

__version__ = "0.1.0"

# Submodules are deliberately not imported here. `plots` calls matplotlib.use() at import
# time, and making `import scorebook` pay for matplotlib would slow every CLI run that
# never draws anything.
__all__ = ["__version__"]
