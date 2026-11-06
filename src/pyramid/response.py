import mimetypes
from os.path import getmtime, getsize
import venusian
from webob import Response as _Response
from zope.interface import implementer

from pyramid.interfaces import IResponse, IResponseFactory

_BLOCK_SIZE = 4096 * 64  # 256K


@implementer(IResponse)
class Response(_Response):
    pass


def _encoded_header_part_size(value, encoding):
    # Return the on-the-wire byte length of a header name or value.
    # ``bytes`` are measured as-is; everything else is encoded using the
    # caller-supplied codec (UTF-8 by default) so non-ASCII text is
    # counted by its encoded byte length rather than its character count.
    if isinstance(value, bytes):
        return len(value)
    return len(str(value).encode(encoding))


def get_over_budget_header_indexes(
    response,
    max_header_bytes=None,
    max_total_bytes=None,
    encoding='utf-8',
):
    """
    Check a response's headers against a caller-supplied byte budget.

    The headers are inspected in the exact order in which they will be
    sent, as given by ``response.headerlist``.  Each occurrence of a
    repeated header field is therefore inspected as its own entry.  For
    every header the encoded byte length of its field name and field
    value is tallied; delimiter overhead such as ``": "`` or CRLF is not
    included.

    Two limits, both optional and both inclusive, may be supplied by the
    caller:

    ``max_header_bytes``
        Per-header limit.  The index of a header is returned when the
        combined encoded size of its name and value is greater than this
        number.

    ``max_total_bytes``
        Overall limit.  Headers are summed in order, and the index of
        every header at or after which the running total becomes greater
        than this number is returned.

    ``encoding``
        The codec used to determine the byte length of non-ASCII header
        names and values (UTF-8 by default).  ``bytes`` names or values
        are always counted as-is.

    A list of zero-based indexes (in ascending order) of the headers
    that exceed either limit is returned.  Only indexes are returned:
    header names and values are never copied into the result, and the
    response itself is not modified in any way.  A response without
    headers yields an empty list.

    Any object exposing a ``headerlist`` sequence of ``(name, value)``
    pairs is accepted, as is such a sequence passed directly.

    .. code-block:: python
        :linenos:

        from pyramid.response import Response
        from pyramid.response import get_over_budget_header_indexes

        response = Response()
        response.headerlist.append(('X-Trace', 'a' * 100))
        over = get_over_budget_header_indexes(
            response, max_header_bytes=80, max_total_bytes=8192
        )

    .. versionadded:: 2.2
    """
    headerlist = getattr(response, 'headerlist', response)
    if not headerlist:
        return []

    over_budget_indexes = []
    total_bytes = 0
    for index, (name, value) in enumerate(headerlist):
        header_bytes = _encoded_header_part_size(
            name, encoding
        ) + _encoded_header_part_size(value, encoding)
        total_bytes += header_bytes
        if (
            max_header_bytes is not None and header_bytes > max_header_bytes
        ) or (max_total_bytes is not None and total_bytes > max_total_bytes):
            over_budget_indexes.append(index)
    return over_budget_indexes


# alternate public name for the header byte budget checker
check_header_byte_budget = get_over_budget_header_indexes


class FileResponse(Response):
    """
    A Response object that can be used to serve a static file from disk
    simply.

    ``path`` is a file path on disk.

    ``request`` must be a Pyramid :term:`request` object.  Note
    that a request *must* be passed if the response is meant to attempt to
    use the ``wsgi.file_wrapper`` feature of the web server that you're using
    to serve your Pyramid application.

    ``cache_max_age`` is the number of seconds that should be used
    to HTTP cache this response.

    ``content_type`` is the content_type of the response.

    ``content_encoding`` is the content_encoding of the response.
    It's generally safe to leave this set to ``None`` if you're serving a
    binary file.  This argument will be ignored if you also leave
    ``content-type`` as ``None``.
    """

    def __init__(
        self,
        path,
        request=None,
        cache_max_age=None,
        content_type=None,
        content_encoding=None,
    ):
        if content_type is None:
            content_type, content_encoding = _guess_type(path)
        super().__init__(
            conditional_response=True,
            content_type=content_type,
            content_encoding=content_encoding,
        )
        self.last_modified = getmtime(path)
        content_length = getsize(path)
        f = open(path, 'rb')
        app_iter = None
        if request is not None:
            environ = request.environ
            if 'wsgi.file_wrapper' in environ:
                app_iter = environ['wsgi.file_wrapper'](f, _BLOCK_SIZE)
        if app_iter is None:
            app_iter = FileIter(f, _BLOCK_SIZE)
        self.app_iter = app_iter
        # assignment of content_length must come after assignment of app_iter
        self.content_length = content_length
        if cache_max_age is not None:
            self.cache_expires = cache_max_age


class FileIter:
    """A fixed-block-size iterator for use as a WSGI app_iter.

    ``file`` is a Python file pointer (or at least an object with a ``read``
    method that takes a size hint).

    ``block_size`` is an optional block size for iteration.
    """

    def __init__(self, file, block_size=_BLOCK_SIZE):
        self.file = file
        self.block_size = block_size

    def __iter__(self):
        return self

    def __next__(self):
        val = self.file.read(self.block_size)
        if not val:
            raise StopIteration
        return val

    def close(self):
        self.file.close()


class response_adapter:
    """Decorator activated via a :term:`scan` which treats the function
    being decorated as a :term:`response adapter` for the set of types or
    interfaces passed as ``*types_or_ifaces`` to the decorator constructor.

    For example, if you scan the following response adapter:

    .. code-block:: python

        from pyramid.response import Response
        from pyramid.response import response_adapter

        @response_adapter(int)
        def myadapter(i):
            return Response(status=i)

    You can then return an integer from your view callables, and it will be
    converted into a response with the integer as the status code.

    More than one type or interface can be passed as a constructor argument.
    The decorated response adapter will be called for each type or interface.

    .. code-block:: python

        import json

        from pyramid.response import Response
        from pyramid.response import response_adapter

        @response_adapter(dict, list)
        def myadapter(ob):
            return Response(json.dumps(ob))

    This method will have no effect until a :term:`scan` is performed
    agains the package or module which contains it, ala:

    .. code-block:: python

        from pyramid.config import Configurator
        config = Configurator()
        config.scan('somepackage_containing_adapters')

    Two additional keyword arguments which will be passed to the
    :term:`venusian` ``attach`` function are ``_depth`` and ``_category``.

    ``_depth`` is provided for people who wish to reuse this class from another
    decorator. The default value is ``0`` and should be specified relative to
    the ``response_adapter`` invocation. It will be passed in to the
    :term:`venusian` ``attach`` function as the depth of the callstack when
    Venusian checks if the decorator is being used in a class or module
    context. It's not often used, but it can be useful in this circumstance.

    ``_category`` sets the decorator category name. It can be useful in
    combination with the ``category`` argument of ``scan`` to control which
    views should be processed.

    See the :py:func:`venusian.attach` function in Venusian for more
    information about the ``_depth`` and ``_category`` arguments.

    .. versionchanged:: 1.9.1
       Added the ``_depth`` and ``_category`` arguments.

    """

    venusian = venusian  # for unit testing

    def __init__(self, *types_or_ifaces, **kwargs):
        self.types_or_ifaces = types_or_ifaces
        self.depth = kwargs.pop('_depth', 0)
        self.category = kwargs.pop('_category', 'pyramid')
        self.kwargs = kwargs

    def register(self, scanner, name, wrapped):
        config = scanner.config
        for type_or_iface in self.types_or_ifaces:
            config.add_response_adapter(wrapped, type_or_iface, **self.kwargs)

    def __call__(self, wrapped):
        self.venusian.attach(
            wrapped,
            self.register,
            category=self.category,
            depth=self.depth + 1,
        )
        return wrapped


def _get_response_factory(registry):
    """Obtain a :class: `pyramid.response.Response` using the
    `pyramid.interfaces.IResponseFactory`.
    """
    response_factory = registry.queryUtility(
        IResponseFactory, default=lambda r: Response()
    )

    return response_factory


def _guess_type(path):
    content_type, content_encoding = mimetypes.guess_type(path, strict=False)
    if content_type is None:
        content_type = 'application/octet-stream'
    return content_type, content_encoding
