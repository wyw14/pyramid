unreleased
==========

Features
--------

- Add `Configurator.resolve_asset` and `Request.resolve_asset` methods.  See
  https://github.com/Pylons/pyramid/pull/3815.

- Add a ``Request.check_route_params`` method (and a ``check_route_params``
  function in the :mod:`pyramid.url` module) which, given a registered route
  name and a mapping or sequence of ``(name, value)`` pairs, returns the
  names of any missing required dynamic segments (including a trailing
  ``*remainder`` wildcard) and any supplied names unused by the route,
  stably ordered by the route declaration and the input, respectively.
  The check is purely static: no URL is generated, the route pregenerator
  is not called, and no view code is executed.  A ``KeyError`` is raised
  for an unknown route name.

Bug Fixes
---------

Backward Incompatibilities
--------------------------

Deprecations
------------

Documentation Changes
---------------------

