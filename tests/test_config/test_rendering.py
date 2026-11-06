import os
import unittest


class TestRenderingConfiguratorMixin(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from pyramid.config import Configurator

        config = Configurator(*arg, **kw)
        return config

    def test_add_default_renderers(self):
        from pyramid.config.rendering import DEFAULT_RENDERERS
        from pyramid.interfaces import IRendererFactory

        config = self._makeOne(autocommit=True)
        config.add_default_renderers()
        for name, impl in DEFAULT_RENDERERS:
            self.assertTrue(
                config.registry.queryUtility(IRendererFactory, name)
                is not None
            )

    def test_add_renderer(self):
        from pyramid.interfaces import IRendererFactory

        config = self._makeOne(autocommit=True)
        renderer = object()
        config.add_renderer('name', renderer)
        self.assertEqual(
            config.registry.getUtility(IRendererFactory, 'name'), renderer
        )

    def test_add_renderer_dottedname_factory(self):
        from pyramid.interfaces import IRendererFactory

        config = self._makeOne(autocommit=True)
        import tests.test_config

        config.add_renderer('name', 'tests.test_config')
        self.assertEqual(
            config.registry.getUtility(IRendererFactory, 'name'),
            tests.test_config,
        )

    def test_renderer_overrides_report_defaults(self):
        config = self._makeOne()
        report = config.renderer_overrides_report()
        registered = report['registered']
        for name in ('json', 'string'):
            self.assertIn(name, registered)
            entry = registered[name]
            self.assertEqual(entry['name'], name)
            self.assertIsNotNone(entry['factory'])
            self.assertEqual(entry['includepath'], ())
            self.assertIsNotNone(entry['source'])
        self.assertEqual(report['overridden'], {})
        self.assertEqual(report['unregistered'], [])

    def test_renderer_overrides_report_does_not_instantiate_factories(self):
        class BoomFactory:
            def __call__(self, info):
                raise AssertionError('renderer factory was instantiated')

        winner = BoomFactory()
        loser = BoomFactory()

        def includeme(config):
            config.add_renderer('.pt', loser)

        config = self._makeOne()
        config.include(includeme)
        config.add_renderer('.pt', winner)
        config.commit()
        # generating the report must not call either factory
        report = config.renderer_overrides_report()
        self.assertIs(report['registered']['.pt']['factory'], winner)

    def test_renderer_overrides_report_duplicate_extension_via_include(self):
        local_factory = object()
        included_factory = object()

        def includeme(config):
            config.add_renderer('.pt', included_factory)

        config = self._makeOne()
        config.include(includeme)
        config.add_renderer('.pt', local_factory)
        config.commit()

        report = config.renderer_overrides_report()

        winner = report['registered']['.pt']
        self.assertIs(winner['factory'], local_factory)
        self.assertEqual(winner['includepath'], ())
        self.assertIsNotNone(winner['source'])

        losers = report['overridden']['.pt']
        self.assertEqual(len(losers), 1)
        loser = losers[0]
        self.assertEqual(loser['name'], '.pt')
        self.assertIs(loser['factory'], included_factory)
        self.assertEqual(
            loser['includepath'],
            ('%s:%s' % (__name__, 'includeme'),),
        )
        # the overridden source points at the add_renderer call in the
        # included function in this file
        self.assertEqual(
            os.path.abspath(loser['source'].file), os.path.abspath(__file__)
        )
        self.assertGreater(loser['source'].line, 0)

    def test_renderer_overrides_report_include_order_nested(self):
        local_factory = object()
        outer_factory = object()
        inner_factory = object()

        def inner(config):
            config.add_renderer('.jinja2', inner_factory)

        def outer(config):
            config.add_renderer('.jinja2', outer_factory)
            config.include(inner)

        config = self._makeOne()
        config.include(outer)
        config.add_renderer('.jinja2', local_factory)
        config.commit()

        report = config.renderer_overrides_report()
        self.assertIs(
            report['registered']['.jinja2']['factory'], local_factory
        )
        losers = report['overridden']['.jinja2']
        # shorter (more outer) include paths are listed first, the local
        # configuration at path () wins
        self.assertEqual(
            [entry['factory'] for entry in losers],
            [outer_factory, inner_factory],
        )
        self.assertEqual(
            [len(entry['includepath']) for entry in losers], [1, 2]
        )
        self.assertEqual(
            losers[0]['includepath'],
            ('%s:%s' % (__name__, 'outer'),),
        )
        self.assertEqual(
            losers[1]['includepath'],
            (
                '%s:%s' % (__name__, 'outer'),
                '%s:%s' % (__name__, 'inner'),
            ),
        )

    def test_renderer_overrides_report_across_commits(self):
        first_factory = object()
        second_factory = object()

        config = self._makeOne()
        config.add_renderer('.x', first_factory)
        config.commit()
        config.add_renderer('.x', second_factory)
        config.commit()

        report = config.renderer_overrides_report()
        self.assertIs(report['registered']['.x']['factory'], second_factory)
        self.assertEqual(
            [entry['factory'] for entry in report['overridden']['.x']],
            [first_factory],
        )

    def test_renderer_overrides_report_autocommit(self):
        first_factory = object()
        second_factory = object()

        config = self._makeOne(autocommit=True)
        config.add_renderer('.y', first_factory)
        config.add_renderer('.y', second_factory)

        report = config.renderer_overrides_report()
        self.assertIs(report['registered']['.y']['factory'], second_factory)
        self.assertEqual(
            [entry['factory'] for entry in report['overridden']['.y']],
            [first_factory],
        )

    def test_renderer_overrides_report_unregistered_template_type(self):
        def aview(request):  # pragma: no cover
            return request

        config = self._makeOne()
        config.add_view(aview, renderer='templates/foo.unregistered')
        config.commit()

        report = config.renderer_overrides_report(names=('nostatic',))
        self.assertIn('.unregistered', report['unregistered'])
        self.assertIn('nostatic', report['unregistered'])
        # types with a registered factory must not be reported
        for registered in report['registered']:
            self.assertNotIn(registered, report['unregistered'])

    def test_renderer_overrides_report_introspection_disabled(self):
        factory = object()

        config = self._makeOne(introspection=False)
        config.add_renderer('.pt', factory)
        config.commit()

        report = config.renderer_overrides_report()
        self.assertIs(report['registered']['.pt']['factory'], factory)
        # source metadata is unavailable without introspection
        self.assertIsNone(report['registered']['.pt']['source'])
