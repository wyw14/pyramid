unreleased
==========

Features
--------

- Add `Configurator.resolve_asset` and `Request.resolve_asset` methods.  See
  https://github.com/Pylons/pyramid/pull/3815.

- Add ``Configurator.renderer_overrides_report`` which, after configuration
  is committed, lists the renderer factories finally registered per
  extension together with the registration sources overridden during the
  configuration period (duplicate extensions and include override order),
  as well as referenced renderer types for which no factory was registered.
  The report reads registration metadata only; it never instantiates a
  renderer factory or reads template contents.

Bug Fixes
---------

Backward Incompatibilities
--------------------------

Deprecations
------------

Documentation Changes
---------------------

