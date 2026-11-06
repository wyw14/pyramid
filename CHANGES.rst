unreleased
==========

Features
--------

- Add a ``Configurator.action_stats`` method that returns statistics about the
  configuration actions pending before the next ``commit``, aggregated by
  their ``include`` source.  For each source the report includes the number
  of pending actions, how many of them carry a discriminator, the distinct
  execution orders in use, and the number of duplicate discriminators.  The
  method is purely introspective: it never executes an action, does not
  resolve deferred discriminators, and does not expose action callables,
  arguments, keyword arguments or introspectables.

- Add `Configurator.resolve_asset` and `Request.resolve_asset` methods.  See
  https://github.com/Pylons/pyramid/pull/3815.

Bug Fixes
---------

Backward Incompatibilities
--------------------------

Deprecations
------------

Documentation Changes
---------------------

