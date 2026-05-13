"""Module B — Constrained Resource Allocation Optimizer.

Public scope (Jan–Apr 2018 reconstruction window):

* Ingest synthetic dirty budget, volunteer log, and media-sheet artifacts.
* Normalize PYG <-> USD with a Jan–Apr 2018 tiered FX layer (BCP reference
  vs. retail spread).
* Build (department, channel) reach caps with salience, attention,
  diminishing-returns, and tier eligibility metadata.
* Solve a weekly LP/MILP allocation with bundle constraints and 11-channel
  cardinality enforcement using PuLP/CBC.
* Run a seeded TSP heuristic (nearest-insertion + 2-opt) over a department
  cost matrix with weather/surface/regime constraints.
* Counterfactual reallocation engine for broadcast-to-direct stress tests.

This subpackage is the canonical producer of:

* ``schema_contracts/allocation_output.yaml``
* ``schema_contracts/reachability_caps_dept_channel.yaml``
* ``schema_contracts/routing_cost_matrix.yaml``

It is the canonical consumer of:

* ``schema_contracts/population_master_clean.yaml``
* ``schema_contracts/segment_labels.yaml``
* ``schema_contracts/participation_propensity.yaml``
* ``schema_contracts/media_reachability_by_segment.yaml``
* ``schema_contracts/media_reachability_by_segment_department.yaml``
"""

from module_b_resource_allocation._version import __version__

__all__ = ["__version__"]
