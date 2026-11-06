import io
import mimetypes
import os
import unittest

from pyramid import testing


class TestResponse(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.response import Response

        return Response

    def test_implements_IResponse(self):
        from pyramid.interfaces import IResponse

        cls = self._getTargetClass()
        self.assertTrue(IResponse.implementedBy(cls))

    def test_provides_IResponse(self):
        from pyramid.interfaces import IResponse

        inst = self._getTargetClass()()
        self.assertTrue(IResponse.providedBy(inst))


class TestFileResponse(unittest.TestCase):
    def _makeOne(self, file, **kw):
        from pyramid.response import FileResponse

        return FileResponse(file, **kw)

    def _getPath(self, suffix='txt'):
        here = os.path.dirname(__file__)
        return os.path.join(here, 'fixtures', f'minimal.{suffix}')

    def test_with_image_content_type(self):
        path = self._getPath('jpg')
        r = self._makeOne(path, content_type='image/jpeg')
        self.assertEqual(r.content_type, 'image/jpeg')
        self.assertEqual(r.headers['content-type'], 'image/jpeg')
        path = self._getPath()
        r.app_iter.close()

    def test_with_xml_content_type(self):
        path = self._getPath('xml')
        r = self._makeOne(path, content_type='application/xml')
        self.assertEqual(r.content_type, 'application/xml')
        self.assertEqual(
            r.headers['content-type'], 'application/xml; charset=UTF-8'
        )
        r.app_iter.close()

    def test_with_pdf_content_type(self):
        path = self._getPath('xml')
        r = self._makeOne(path, content_type='application/pdf')
        self.assertEqual(r.content_type, 'application/pdf')
        self.assertEqual(r.headers['content-type'], 'application/pdf')
        r.app_iter.close()

    def test_without_content_type(self):
        for suffix in ('txt', 'xml', 'pdf'):
            path = self._getPath(suffix)
            r = self._makeOne(path)
            self.assertEqual(
                r.headers['content-type'].split(';')[0],
                mimetypes.guess_type(path, strict=False)[0],
            )
            r.app_iter.close()

    def test_python_277_bug_15207(self):
        # python 2.7.7 on windows has a bug where its mimetypes.guess_type
        # function returns Unicode for the content_type, unlike any previous
        # version of Python.  See https://github.com/Pylons/pyramid/issues/1360
        # for more information.
        import mimetypes as old_mimetypes

        from pyramid import response
        from pyramid.util import text_

        class FakeMimetypesModule:
            def guess_type(self, *arg, **kw):
                return text_('foo/bar'), None

        fake_mimetypes = FakeMimetypesModule()
        try:
            response.mimetypes = fake_mimetypes
            path = self._getPath('xml')
            r = self._makeOne(path)
            self.assertEqual(r.content_type, 'foo/bar')
            self.assertEqual(type(r.content_type), str)
        finally:
            response.mimetypes = old_mimetypes


class TestFileIter(unittest.TestCase):
    def _makeOne(self, file, block_size):
        from pyramid.response import FileIter

        return FileIter(file, block_size)

    def test___iter__(self):
        f = io.BytesIO(b'abc')
        inst = self._makeOne(f, 1)
        self.assertEqual(inst.__iter__(), inst)

    def test_iteration(self):
        data = b'abcdef'
        f = io.BytesIO(b'abcdef')
        inst = self._makeOne(f, 1)
        r = b''
        for x in inst:
            self.assertEqual(len(x), 1)
            r += x
        self.assertEqual(r, data)

    def test_close(self):
        f = io.BytesIO(b'abc')
        inst = self._makeOne(f, 1)
        inst.close()
        self.assertTrue(f.closed)


class TestResponseAdapter(unittest.TestCase):
    def setUp(self):
        registry = Dummy()
        self.config = testing.setUp(registry=registry)

    def tearDown(self):
        self.config.end()

    def _makeOne(self, *types_or_ifaces, **kw):
        from pyramid.response import response_adapter

        return response_adapter(*types_or_ifaces, **kw)

    def test_register_single(self):
        from zope.interface import Interface

        class IFoo(Interface):
            pass

        dec = self._makeOne(IFoo)

        def foo():  # pragma: no cover
            pass

        config = DummyConfigurator()
        scanner = Dummy()
        scanner.config = config
        dec.register(scanner, None, foo)
        self.assertEqual(config.adapters, [(foo, IFoo)])

    def test_register_multi(self):
        from zope.interface import Interface

        class IFoo(Interface):
            pass

        class IBar(Interface):
            pass

        dec = self._makeOne(IFoo, IBar)

        def foo():  # pragma: no cover
            pass

        config = DummyConfigurator()
        scanner = Dummy()
        scanner.config = config
        dec.register(scanner, None, foo)
        self.assertEqual(config.adapters, [(foo, IFoo), (foo, IBar)])

    def test___call__(self):
        from zope.interface import Interface

        class IFoo(Interface):
            pass

        dec = self._makeOne(IFoo)
        dummy_venusian = DummyVenusian()
        dec.venusian = dummy_venusian

        def foo():  # pragma: no cover
            pass

        dec(foo)
        self.assertEqual(
            dummy_venusian.attached, [(foo, dec.register, 'pyramid', 1)]
        )

    def test___call___with_venusian_args(self):
        from zope.interface import Interface

        class IFoo(Interface):
            pass

        dec = self._makeOne(IFoo, _category='foo', _depth=1)
        dummy_venusian = DummyVenusian()
        dec.venusian = dummy_venusian

        def foo():  # pragma: no cover
            pass

        dec(foo)
        self.assertEqual(
            dummy_venusian.attached, [(foo, dec.register, 'foo', 2)]
        )


class TestGetResponseFactory(unittest.TestCase):
    def test_get_factory(self):
        from pyramid.registry import Registry
        from pyramid.response import Response, _get_response_factory

        registry = Registry()
        response = _get_response_factory(registry)(None)
        self.assertTrue(isinstance(response, Response))


class DummyHeaderResponse:
    def __init__(self, headerlist):
        self.headerlist = list(headerlist)


class TestGetOverBudgetHeaderIndexes(unittest.TestCase):
    def _callFUT(self, *args, **kwargs):
        from pyramid.response import get_over_budget_header_indexes

        return get_over_budget_header_indexes(*args, **kwargs)

    def test_empty_response(self):
        response = DummyHeaderResponse([])
        self.assertEqual(
            self._callFUT(response, max_header_bytes=1, max_total_bytes=1),
            [],
        )

    def test_empty_response_with_none_headerlist(self):
        response = DummyHeaderResponse([])
        response.headerlist = None
        self.assertEqual(
            self._callFUT(response, max_header_bytes=1, max_total_bytes=1),
            [],
        )

    def test_empty_webob_response(self):
        from pyramid.response import Response

        response = Response()
        response.headerlist = []
        self.assertEqual(
            self._callFUT(response, max_header_bytes=0, max_total_bytes=0),
            [],
        )

    def test_empty_pairs_sequence(self):
        self.assertEqual(
            self._callFUT([], max_header_bytes=1, max_total_bytes=1),
            [],
        )

    def test_within_budget(self):
        # sizes: ('X-A','bb')=5, ('X-B','ccc')=6, ('X-C','dddd')=7
        response = DummyHeaderResponse(
            [('X-A', 'bb'), ('X-B', 'ccc'), ('X-C', 'dddd')]
        )
        self.assertEqual(
            self._callFUT(response, max_header_bytes=7, max_total_bytes=18),
            [],
        )

    def test_no_limits_means_nothing_is_over_budget(self):
        response = DummyHeaderResponse([('X-A', 'z' * 5000)])
        self.assertEqual(self._callFUT(response), [])
        self.assertEqual(self._callFUT(response, max_header_bytes=None), [])

    def test_per_header_limit_boundary_is_inclusive(self):
        response = DummyHeaderResponse([('X-A', 'bb')])
        self.assertEqual(self._callFUT(response, max_header_bytes=5), [])
        response = DummyHeaderResponse([('X-A', 'bbb')])
        self.assertEqual(self._callFUT(response, max_header_bytes=5), [0])

    def test_per_header_limit_returns_indexes(self):
        # sizes: 5, 6, 7
        response = DummyHeaderResponse(
            [('X-A', 'bb'), ('X-B', 'ccc'), ('X-C', 'dddd')]
        )
        self.assertEqual(self._callFUT(response, max_header_bytes=6), [2])
        self.assertEqual(
            self._callFUT(response, max_header_bytes=4), [0, 1, 2]
        )

    def test_total_limit_boundary_is_inclusive(self):
        # running totals: 5, 11, 18
        response = DummyHeaderResponse(
            [('X-A', 'bb'), ('X-B', 'ccc'), ('X-C', 'dddd')]
        )
        self.assertEqual(self._callFUT(response, max_total_bytes=18), [])
        self.assertEqual(self._callFUT(response, max_total_bytes=5), [1, 2])

    def test_total_limit_flags_crossing_and_following_indexes(self):
        # running totals: 5, 11, 18
        response = DummyHeaderResponse(
            [('X-A', 'bb'), ('X-B', 'ccc'), ('X-C', 'dddd')]
        )
        self.assertEqual(self._callFUT(response, max_total_bytes=10), [1, 2])

    def test_duplicate_headers_counted_separately_in_order(self):
        response = DummyHeaderResponse(
            [
                ('Set-Cookie', 'a=1'),
                ('X-Mid', 'v'),
                ('Set-Cookie', 'z' * 20),
            ]
        )
        # sizes: 13 ('Set-Cookie'=10 + 3), 6, 10 + 20 = 30
        self.assertEqual(self._callFUT(response, max_header_bytes=13), [2])
        # running totals: 13, 19, 49
        self.assertEqual(self._callFUT(response, max_total_bytes=19), [2])
        self.assertEqual(self._callFUT(response, max_total_bytes=13), [1, 2])

    def test_duplicate_headers_on_real_response_order(self):
        from pyramid.response import Response

        response = Response()
        response.headerlist[:] = []
        response.headerlist.append(('Set-Cookie', 'first=1'))
        response.headerlist.append(('X-Other', 'x'))
        response.headerlist.append(('Set-Cookie', 'second=' + '2' * 30))
        result = self._callFUT(response, max_header_bytes=20)
        # only the third header (index 2) is over the per-header budget
        self.assertEqual(result, [2])

    def test_non_ascii_value_counted_as_utf8_bytes(self):
        # 'X-Tag' is 5 bytes, '\u4e2d\u6587' is 6 bytes in UTF-8 -> 11
        response = DummyHeaderResponse([('X-Tag', '\u4e2d\u6587')])
        self.assertEqual(self._callFUT(response, max_header_bytes=10), [0])
        self.assertEqual(self._callFUT(response, max_header_bytes=11), [])

    def test_non_ascii_name_counted_as_utf8_bytes(self):
        # 'X-' is 2 bytes, '\u6807' is 3 bytes, value 'v' is 1 byte -> 6
        response = DummyHeaderResponse([('X-\u6807', 'v')])
        self.assertEqual(self._callFUT(response, max_header_bytes=5), [0])
        self.assertEqual(self._callFUT(response, max_header_bytes=6), [])

    def test_encoding_argument(self):
        # 'caf\u00e9': 4 chars, 5 UTF-8 bytes but 4 latin-1 bytes
        response = DummyHeaderResponse([('X-E', 'caf\u00e9')])
        # name (3) + latin-1 value (4) = 7
        self.assertEqual(
            self._callFUT(response, max_header_bytes=7, encoding='latin-1'),
            [],
        )
        # name (3) + utf-8 value (5) = 8
        self.assertEqual(
            self._callFUT(response, max_header_bytes=7, encoding='utf-8'),
            [0],
        )

    def test_bytes_name_and_value_counted_raw(self):
        # raw 0xff/0xfe cannot be decoded as utf-8; length must be 2
        response = DummyHeaderResponse([(b'X-B', b'\xff\xfe')])
        self.assertEqual(self._callFUT(response, max_header_bytes=5), [])
        self.assertEqual(self._callFUT(response, max_header_bytes=4), [0])

    def test_empty_name_and_value(self):
        response = DummyHeaderResponse([('', '')])
        self.assertEqual(self._callFUT(response, max_header_bytes=0), [])
        response = DummyHeaderResponse([('X-Empty', '')])
        # name only: 7 bytes
        self.assertEqual(self._callFUT(response, max_header_bytes=6), [0])
        self.assertEqual(self._callFUT(response, max_header_bytes=7), [])

    def test_plain_pairs_tuple_input(self):
        pairs = (('X-A', 'bb'), ('X-B', 'ccc'))
        self.assertEqual(self._callFUT(pairs, max_header_bytes=5), [1])

    def test_result_contains_only_integer_indexes(self):
        response = DummyHeaderResponse(
            [('X-A', 'bb'), ('X-B', 'ccc'), ('X-C', 'dddd')]
        )
        result = self._callFUT(
            response, max_header_bytes=5, max_total_bytes=10
        )
        self.assertEqual(result, [1, 2])
        self.assertTrue(all(isinstance(i, int) for i in result))

    def test_response_is_not_modified(self):
        from pyramid.response import Response

        response = Response()
        response.headerlist[:] = []
        response.headerlist.append(('Set-Cookie', 'a=1'))
        response.headerlist.append(('Set-Cookie', 'b=2'))
        before = list(response.headerlist)
        headerlist = response.headerlist
        self._callFUT(response, max_header_bytes=1, max_total_bytes=1)
        self.assertIs(response.headerlist, headerlist)
        self.assertEqual(response.headerlist, before)
        self.assertEqual(response.headers.getall('Set-Cookie'), ['a=1', 'b=2'])

    def test_input_sequence_is_not_modified(self):
        pairs = [('X-A', 'bb'), ('X-B', 'ccc')]
        self._callFUT(pairs, max_header_bytes=4)
        self.assertEqual(pairs, [('X-A', 'bb'), ('X-B', 'ccc')])

    def test_alias(self):
        from pyramid.response import check_header_byte_budget
        from pyramid.response import get_over_budget_header_indexes

        self.assertIs(check_header_byte_budget, get_over_budget_header_indexes)
        response = DummyHeaderResponse([('X-A', 'z' * 10)])
        self.assertEqual(
            check_header_byte_budget(response, max_header_bytes=5), [0]
        )


class Dummy:
    pass


class DummyConfigurator:
    def __init__(self):
        self.adapters = []

    def add_response_adapter(self, wrapped, type_or_iface):
        self.adapters.append((wrapped, type_or_iface))


class DummyVenusian:
    def __init__(self):
        self.attached = []

    def attach(self, wrapped, fn, category=None, depth=None):
        self.attached.append((wrapped, fn, category, depth))
