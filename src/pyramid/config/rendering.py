from pyramid import renderers
from pyramid.config.actions import action_method
from pyramid.interfaces import PHASE1_CONFIG, IRendererFactory

DEFAULT_RENDERERS = (
    ('json', renderers.json_renderer_factory),
    ('string', renderers.string_renderer_factory),
)


class RenderingConfiguratorMixin:
    def add_default_renderers(self):
        for name, renderer in DEFAULT_RENDERERS:
            self.add_renderer(name, renderer)

    @action_method
    def add_renderer(self, name, factory):
        """
        Add a :app:`Pyramid` :term:`renderer` factory to the
        current configuration state.

        The ``name`` argument is the renderer name.  Use ``None`` to
        represent the default renderer (a renderer which will be used for all
        views unless they name another renderer specifically).

        The ``factory`` argument is Python reference to an
        implementation of a :term:`renderer` factory or a
        :term:`dotted Python name` to same.
        """
        factory = self.maybe_dotted(factory)
        # if name is None or the empty string, we're trying to register
        # a default renderer, but registerUtility is too dumb to accept None
        # as a name
        if not name:
            name = ''

        def register():
            # record the metadata of any factory this executed registration
            # is about to replace (e.g. an override committed earlier or one
            # made under autocommit); metadata only, the factory is not
            # called
            self._note_renderer_replacement(name)
            self.registry.registerUtility(factory, IRendererFactory, name=name)

        intr = self.introspectable(
            'renderer factories',
            name,
            self.object_description(factory),
            'renderer factory',
        )
        intr['factory'] = factory
        intr['name'] = name
        intr['includepath'] = self.includepath
        # we need to register renderers early (in phase 1) because they are
        # used during view configuration (which happens in phase 3)
        self.action(
            (IRendererFactory, name),
            register,
            order=PHASE1_CONFIG,
            introspectables=(intr,),
        )

    def _note_renderer_replacement(self, name):
        """Record metadata for a renderer factory about to be replaced by an
        executed registration.  Only registration metadata is read; the
        factories are never instantiated and template contents are never
        touched."""
        registry = self.registry
        previous = registry.queryUtility(IRendererFactory, name=name)
        if previous is None:
            return
        source = None
        includepath = None
        introspector = getattr(registry, 'introspector', None)
        if introspector is not None:
            previous_intr = introspector.get('renderer factories', name)
            if previous_intr is not None:
                source = previous_intr.action_info
                includepath = previous_intr.get('includepath')
        log = getattr(registry, '_renderer_override_log', None)
        if log is None:
            log = {}
            registry._renderer_override_log = log
        log.setdefault(name, []).append(
            {
                'name': name,
                'factory': previous,
                'source': source,
                'includepath': includepath,
            }
        )

    def renderer_overrides_report(self, names=()):
        """Return a metadata-only report describing the renderer factory
        registrations in effect after :meth:`commit` has been called.

        The report is a dictionary with three keys:

        ``registered``
            A mapping of renderer name/extension to a dictionary describing
            the factory that ultimately won registration:

            ``name``
                The renderer name (extension, e.g. ``'.pt'``).

            ``factory``
                The registered factory object itself.  The factory is never
                called by this method.

            ``source``
                The :class:`pyramid.interfaces.IActionInfo` of the
                ``add_renderer`` call that won, or ``None`` if it is
                unavailable.

            ``includepath``
                The tuple of include specs active when the winning
                registration was made (an empty tuple for the local
                configuration).

        ``overridden``
            A mapping of renderer name/extension to a list of dictionaries
            (in override order) describing registration sources that lost
            during the configuration period: registrations silently dropped
            by conflict resolution because a shorter include path overrode
            them, and factories registered by an earlier executed
            registration that a later registration replaced.

        ``unregistered``
            A sorted list of renderer types referenced by registered
            templates (or passed explicitly using ``names``) for which no
            renderer factory ended up registered.

        This method only reads registration metadata.  It never
        instantiates a renderer factory and it never reads template
        contents.

        .. versionadded:: 2.2
        """
        registry = self.registry
        introspector = getattr(registry, 'introspector', None)

        registered = {}
        for name, factory in registry.getUtilitiesFor(IRendererFactory):
            intr = None
            if introspector is not None:
                intr = introspector.get('renderer factories', name)
            registered[name] = {
                'name': name,
                'factory': factory,
                'source': intr.action_info if intr is not None else None,
                'includepath': (
                    intr.get('includepath') if intr is not None else None
                ),
            }

        overridden = {}

        def add_overridden(name, factory, source, includepath):
            entry = {
                'name': name,
                'factory': factory,
                'source': source,
                'includepath': includepath,
            }
            entries = overridden.setdefault(name, [])
            if entry not in entries:
                entries.append(entry)

        # registrations executed earlier that were replaced in place by a
        # later executed registration (separate commits or autocommit)
        for name, entries in getattr(
            registry, '_renderer_override_log', {}
        ).items():
            for entry in entries:
                add_overridden(
                    entry['name'],
                    entry['factory'],
                    entry['source'],
                    entry['includepath'],
                )

        # registrations that never executed because conflict resolution
        # dropped them in favor of a shorter include path during this
        # configuration period
        for action in self.action_state.overridden_actions:
            discriminator = action.get('discriminator')
            if (
                not isinstance(discriminator, tuple)
                or len(discriminator) != 2
                or discriminator[0] is not IRendererFactory
            ):
                continue
            name = discriminator[1]
            factory = None
            for introspectable in action.get('introspectables') or ():
                if introspectable.category_name == 'renderer factories':
                    factory = introspectable.get('factory')
                    break
            add_overridden(
                name,
                factory,
                action.get('info'),
                action.get('includepath'),
            )

        # renderer types referenced by registered templates, plus any types
        # named explicitly, for which no factory is currently registered
        referenced = set(names)
        if introspector is not None:
            templates = introspector.get_category('templates', default=())
            for item in templates or ():
                rtype = item['introspectable'].get('type')
                if rtype:
                    referenced.add(rtype)
        unregistered = sorted(
            rtype
            for rtype in referenced
            if registry.queryUtility(IRendererFactory, name=rtype) is None
        )

        return {
            'registered': dict(sorted(registered.items())),
            'overridden': dict(sorted(overridden.items())),
            'unregistered': unregistered,
        }
