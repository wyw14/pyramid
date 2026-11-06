unreleased
==========

Features
--------

- Add `Configurator.resolve_asset` and `Request.resolve_asset` methods.  See
  https://github.com/Pylons/pyramid/pull/3815.

- Add ``pyramid.csrf.rotate_csrf_token`` and a ``rotate_csrf_token`` method
  to ``ICSRFStoragePolicy`` and the built-in storage policies, allowing
  callers to explicitly invalidate the current CSRF token and obtain a new
  one. Token validation and the lazy token generation performed by
  ``get_csrf_token`` are unchanged.

Bug Fixes
---------

Backward Incompatibilities
--------------------------

Deprecations
------------

Documentation Changes
---------------------

