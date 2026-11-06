unreleased
==========

Features
--------

- Add `Configurator.resolve_asset` and `Request.resolve_asset` methods.  See
  https://github.com/Pylons/pyramid/pull/3815.
- Add ``pyramid.response.get_over_budget_header_indexes`` helper which
  reports the indexes of response headers that exceed caller-supplied
  per-header and total encoded-byte budgets, without recording header
  values or modifying the response.

Bug Fixes
---------

Backward Incompatibilities
--------------------------

Deprecations
------------

Documentation Changes
---------------------

