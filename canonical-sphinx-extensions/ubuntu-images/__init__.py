"""
The ``.. ubuntu-images`` directive is a custom directive to generate bulleted
download lists of supported Ubuntu distro images for specific release ranges,
suffixes, image-types, and architectures.

The options that may be specified under the directive are as follows:

``:releases:`` *releases (list of ranges)*
    A comma or space-separated list of partial dash-delimited release ranges
    (as release codenames). See below for examples. If unspecified, all
    releases will be included.

``:state:`` *support state (text)*
    The support state of listed images. Defaults to ``supported`` indicating
    that only actively supported images are to be included. Other valid values
    are ``unsupported`` to list legacy images only, and ``all`` to list both
    supported and unsupported images.

``:lts-only:`` *(no value)*
    If specified, only LTS releases will be included in the output. Interim
    releases are excluded.

``:image-types:`` *image types (list of strings)*
    Filter images by their "type". This is simply the string after the release
    version, and before the architecture. For example, in
    ``ubuntu-20.04.5-preinstalled-server-armhf+raspi.img.xz``, the image type
    is "preinstalled-server". The list may be comma or space separated. If
    unspecified, all image types are included.

``:archs:`` *architectures (list of strings)*
    Filter images by their architecture. The list may be comma or space
    separated. If unspecified, all architectures are included.

``:suffix:`` *image +suffix (string)*
    Filter images by their (plus-prefixed) suffix. If unspecified, any suffix
    (including images with no suffix) will be included in the output. If
    specified but blank, only images with no suffix will be included in the
    output.

``:matches:`` *regular expression (string)*
    Filter images to those with filenames matching the specified regular
    expression. Use of this filter is discouraged; try and use the other
    filters first, and only resort to regular expressions if you find it
    absolutely necessary for complex cases.

``:empty:`` *string*
    If no images match the specified filters, output the given string instead
    of reporting an error and failing the build. The string may be blank in
    which case no output will be generated.

Examples of valid values for the ``:releases:`` option:

jammy
    Just the 22.04 release

jammy, noble
    Just the 22.04 and 24.04 releases

focal-noble
    All releases from 20.04 to 24.04

jammy-
    All releases from 22.04 onwards

-noble
    All releases up to 24.04

focal, noble-
    The 20.04 release, and all releases from 24.04 onwards

Examples of usage::

    All supported raspi images from jammy onwards

    .. ubuntu-images:
        :releases: jammy-
        :suffix: +raspi

    All visionfive images, regardless of support status

    .. ubuntu-images::
        :suffix: +visionfive
        :state: all

    All supported LTS armhf and arm64 images

    .. ubuntu-images::
        :archs: armhf, arm64
        :lts-only:

    All riscv64 images from plucky onwards, suppressing the error and
    outputting a message when no images match

    .. ubuntu-images::
        :releases: plucky-
        :archs: riscv64
        :empty: Will be supported from the plucky release onwards
"""

# pylint: disable=too-many-lines
# It's long, but only just (and most of it is test-suite and doc-strings)

# pylint: disable=invalid-name
# This is the naming convention used in this repo (and it makes a certain sense
# given we're defining reST directives)

from __future__ import annotations

import io
import re
import time
import functools
import itertools
import contextlib
import typing as t
import datetime as dt
from email.utils import parsedate
from html.parser import HTMLParser
from urllib.request import urlopen
from urllib.error import HTTPError

from docutils import nodes
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective
from sphinx.util.typing import ExtensionMetadata  # pylint: disable=no-name-in-module # noqa: E501
from sphinx.addnodes import download_reference


def setup(app: Sphinx) -> ExtensionMetadata:
    "Called by Sphinx to install the extension."
    app.add_directive('ubuntu-images', UbuntuImagesDirective)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


def parse_state(s: str) -> t.Optional[bool]:
    """
    Converts the :class:`str` *s* into a :class:`bool` or :data:`None` for the
    various supported states.

    "supported" or "unsupported" translate to :data:`True` and :data:`False`
    respectively, "all" (indicating both supported and unsupported releases)
    translates to :data:`None`. For example::

        >>> parse_state('All')
        >>> parse_state(' supported ')
        True
        >>> parse_state('unsupported')
        False
    """
    try:
        return {
            'supported':   True,
            'unsupported': False,
            'all':         None,
        }[s.strip().lower()]
    except KeyError:
        raise ValueError(f'invalid state: {s}') from None


def parse_set(s: str) -> set[str]:
    """
    Splits a :class:`str` *s* containing a comma or space-separated list of
    items and returns them as a :class:`set`. Intended for parsing various
    options of :class:`UbuntuImagesDirective`. For example::

        >>> sorted(parse_set('1,2,3,4'))
        ['1', '2', '3', '4']
        >>> sorted(parse_set('foo bar baz'))
        ['bar', 'baz', 'foo']
        >>> sorted(parse_set('foo,bar baz'))
        ['bar', 'baz', 'foo']
    """
    return {elem.strip() for elem in s.replace(',', ' ').split()}


class UbuntuImagesDirective(SphinxDirective):
    option_spec = {
        'releases': str,
        'state': parse_state,
        'lts-only': lambda s: True,
        'image-types': parse_set,
        'archs': parse_set,
        'suffix': lambda s: '' if s is None else str(s),
        'matches': re.compile,
        'empty': str,
        # The following options are intended for testing / advanced purposes
        # only; they override the URLs used to fetch information
        'meta-release': str,
        'meta-release-development': str,
        'cdimage-template': str,
    }

    def run(self) -> list[nodes.Node]:
        meta_release_url = self.options.get(
            'meta-release',
            'https://changelogs.ubuntu.com/meta-release')
        meta_release_dev_url = self.options.get(
            'meta-release-development',
            'https://changelogs.ubuntu.com/meta-release-development')
        cdimage_template = self.options.get(
            'cdimage-template',
            'https://cdimage.ubuntu.com/releases/{release.codename}/release/')

        empty = True
        release_list = nodes.bullet_list()
        releases = filter_releases(
            get_releases(urls=(meta_release_url, meta_release_dev_url)),
            spec=self.options.get('releases', ''),
            lts=self.options.get('lts-only'),
            supported=self.options.get('state', True))
        for release in reversed(releases):
            release_item = nodes.list_item('', nodes.paragraph(
                text=f'Ubuntu {release.version} ({release.name}) images:'))
            images = filter_images(
                get_images(
                    url=cdimage_template.format(release=release),
                    supported=release.supported),
                archs=self.options.get('archs'),
                image_types=self.options.get('image-types'),
                suffix=self.options.get('suffix'),
                matches=self.options.get('matches'))
            if images:
                empty = False
                image_list = nodes.bullet_list()
                for image in images:
                    image_ref = download_reference(
                        '', text=image.name, reftarget=image.url)
                    image_item = nodes.list_item('', image_ref)
                    image_list.append(image_item)
                release_item.append(image_list)
                release_list.append(release_item)
        if empty:
            if 'empty' in self.options:
                return [nodes.emphasis('', self.options['empty'])]
            raise ValueError('no images found for specified filters')
        return [release_list]


# Copy doc-string from the module for the class
UbuntuImagesDirective.__doc__ = __doc__


class Release(t.NamedTuple):
    """
    A named-tuple representing a single Ubuntu release.

    .. attribute:: codename

        The codename of the release; the first word of the name in lowercase,
        e.g. noble.

    .. attribute:: name

        The full alliterative name of the release, e.g. Noble Numbat.

    .. attribute:: version

        The version of the release. A string of the form "YY.MM.P" with an
        optional " LTS" suffix, e.g. '24.04.1 LTS'

    .. attribute:: date

        A :class:`~datetime.datetime` indicating the timestamp of the release.

    .. attribute:: supported

        A :class:`bool` indicating whether the release is currently supported
        or not.
    """

    codename: str
    name: str
    version: str
    date: dt.datetime
    supported: bool

    @property
    def is_lts(self) -> bool:
        """
        A :class:`bool` indicating whether the release is a :abbr:`LTS (Long
        Term Service)` release or not.
        """
        return self.version.endswith('LTS')


image_re = re.compile(
    r'^ubuntu-(?P<version>[\d.]+)'
    r'-(?P<image_type>[^+.]*)'
    r'-(?P<arch>[^-+.]+)'
    r'(?P<suffix>\+.*)?'
    r'\.(?P<file_type>img|iso)'
    r'(?:\.(?P<compression>gz|bz2|xz|zst))?$')


class Image(t.NamedTuple):
    """
    A named-tuple representing a single OS image on cdimage.ubuntu.com.

    .. attribute:: url

        The full URL from which the image can be downloaded.

    .. attribute:: name

        The filename of the image.

    .. attribute:: date

        A :class:`~datetime.date` indicate the date the image was built.

    .. attribute:: sha256

        A :class:`str` containing the SHA256 checksum of the file.
    """

    url: str
    name: str
    date: dt.date
    sha256: str

    def _parse_field(self, field: str) -> str:
        matched = image_re.match(self.name)
        assert matched is not None
        return matched.group(field) or ''

    @property
    def version(self) -> str:
        """
        A :class:`str` of the version of Ubuntu within the image, for example
        "24.04" or "23.10".
        """
        return self._parse_field('version')

    @property
    def image_type(self) -> str:
        """
        A :class:`str` indicating the type of image, for example
        "preinstalled-server" or "live-server".
        """
        return self._parse_field('image_type')

    @property
    def arch(self) -> str:
        """
        The architecture of the image, for example "amd64", "armhf", "riscv64".
        """
        return self._parse_field('arch')

    @property
    def suffix(self) -> str:
        """
        A :class:`str` containing the suffix of the image filename. This is
        typically a blank string, or a plus-prefixed string. For example
        "+raspi", "+visionfive".
        """
        return self._parse_field('suffix')

    @property
    def file_type(self) -> str:
        """
        A :class:`str` containing the first part of the file's extension,
        typically "img" or "iso".
        """
        return self._parse_field('file_type')

    @property
    def compression(self) -> str:
        """
        A :class:`str` containing the last part of the file's extension, if
        present, indicating the compression used on the image. A blank string
        indicates no compression. For example "gz", "xz", or "zst".
        """
        return self._parse_field('compression')


@functools.lru_cache()
def get_releases(
    urls: tuple[str] = ('https://changelogs.ubuntu.com/meta-release',),
) -> list[Release]:
    """
    Given a meta-release *url*, return a :class:`list` of :class:`Release`
    tuples corresponding to all Ubuntu releases. For example::

        >>> with _test_server(_make_releases()) as url:
        ...     releases = get_releases([url + 'meta-release'])
        >>> len(releases)
        3
        >>> releases[0] # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
        Release(codename='warty', name='Warty Warthog', version='04.10',
        date=datetime.datetime(2004, 10, 20, 7, 28, 17), supported=False)
    """
    releases = {}
    for url in urls:
        with (
            urlopen(url) as data,
            io.TextIOWrapper(data, encoding='utf-8', errors='strict') as text
        ):
            for release in meta_parser(text):
                releases[release.codename] = release
    return list(releases.values())


def filter_releases(
    releases: t.Sequence[Release],
    spec: str = "",
    lts: t.Optional[bool] = None,
    supported: t.Optional[bool] = None,
) -> t.Sequence[Release]:
    """
    Filters *releases*, a sequence of :class:`Release` tuples, according to
    the options specified in the ubuntu-images directive. See the documentation
    of :class:`UbuntuImageDirective` for a detailed description of these
    options. For example::

        >>> with _test_server(_make_releases()) as url:
        ...     releases = get_releases([url + 'meta-release'])
        >>> [r.codename for r in releases]
        ['warty', 'disco', 'jammy']
        >>> [r.codename for r in filter_releases(releases, spec='disco-')]
        ['disco', 'jammy']
        >>> [r.codename for r in filter_releases(releases, spec='disco')]
        ['disco']
        >>> [r.codename for r in filter_releases(releases, spec='warty,jammy')]
        ['warty', 'jammy']
        >>> [r.codename for r in filter_releases(releases, supported=True)]
        ['jammy']
        >>> [r.codename for r in filter_releases(releases, lts=True)]
        ['jammy']

    .. note::

        The *releases* sequence must be sorted in ascending release order for
        dash-separated ranges to work correctly. This function also returns
        the filtered result in the same order.
    """
    if spec:
        rel_order = [release.codename for release in releases]
        rel_spec = {
            tuple(elem.split('-', 1)) if '-' in elem else (elem, elem)
            for elem in {
                elem.strip() for elem in spec.replace(",", " ").split()
            }
        }
        rel_selected = []
        for elem in rel_spec:
            i = 0 if elem[0] == '' else rel_order.index(elem[0])
            j = len(rel_order) if elem[1] == '' else rel_order.index(elem[1])
            rel_selected.extend(rel_order[i:j + 1])
        rel_map = {release.codename: release for release in releases}
        result = [
            rel_map[rel] for rel in sorted(rel_selected, key=rel_order.index)
        ]
    else:
        result = list(releases)
    result = [
        rel
        for rel in result
        if (lts is None or rel.is_lts == lts)
        and (supported is None or rel.supported == supported)
    ]
    return result


@functools.lru_cache
def get_images(url: str, supported: bool = True) -> list[Image]:
    """
    Given the *url* of a cdimage directory containing images, returns a
    sequence of :class:`Image` named tuples. For example::

        >>> images = {
        ...     'ubuntu-21.10-foo-armhf+raspi.img.xz': b'foo' * 123456,
        ...     'ubuntu-21.10-bar-arm64+raspi.img.xz': b'bar' * 234567,
        ... }
        >>> ts = dt.datetime(2021, 10, 25)
        >>> with _test_server(_make_index(_make_sums(images), ts)) as url:
        ...     index = get_images(url)
        >>> len(index)
        2
        >>> index[1] # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
        Image(url='http://.../ubuntu-21.10-bar-arm64+raspi.img.xz',
        name='ubuntu-21.10-bar-arm64+raspi.img.xz',
        date=datetime.date(2021, 10, 25),
        sha256='e9cd9718e97ac951c0ead5de8069d0ff5de188620b12b02...')
    """
    # pylint: disable=too-many-locals
    # NOTE: This code relies on the current layout of pages on
    # cdimage.ubuntu.com; if extra tables or columns are introduced or
    # re-ordered this will need revisiting...
    parser = TableParser()
    try:
        with (
            urlopen(url) as data,
            io.TextIOWrapper(data, encoding='utf-8', errors='strict') as page,
        ):
            parser.feed(page.read())
    except HTTPError as exc:
        if not supported and exc.code == 404:
            # Expect to get nothing for unsupported releases
            return []
        # Supported releases should *always* have images
        raise ValueError(
            f'unable to get {url}; are you sure the path '
            f'is correct?') from None
    # Grab all the files in the directory
    files = {}
    for row in parser.table:
        try:
            _, name, date_str, _, _ = row
            name = name.strip()
            date = dt.datetime.strptime(
                date_str.strip(), '%Y-%m-%d %H:%M').date()
        except ValueError:
            # Evidently not a file row
            continue
        files[name] = (url + name, date)
    if 'SHA256SUMS' not in files:
        raise ValueError(f'SHA256SUMS file is missing from {url}')
    # Add SHA256 checksums and filter out anything that isn't an image
    result = []
    with (
        urlopen(url + 'SHA256SUMS') as data,
        io.TextIOWrapper(data, encoding='utf-8', errors='strict') as hashes
    ):
        for line in hashes:
            cksum, name = line.strip().split(None, 1)
            cksum = cksum.strip().lower()
            if name.startswith('*'):
                name = name[1:]
            try:
                url, date = files[name]
                image = Image(url, name, date, cksum)
                if image_re.match(image.name):
                    result.append(image)
            except (KeyError, ValueError):
                continue
    return result


def filter_images(
    images: t.Sequence[Image],
    archs: t.Optional[set[str]] = None,
    image_types: t.Optional[set[str]] = None,
    suffix: t.Optional[str] = None,
    matches: t.Optional[re.Pattern[str]] = None,
) -> t.Sequence[Image]:
    """
    Filters *images*, a sequence of :class:`Image` tuples, according to the
    options specified in the ubuntu-images directive. See the documentation of
    :class:`UbuntuImageDirective` for a detailed description of these options.
    For example::

        >>> foo = b'foo' * 123456
        >>> images = {
        ... 'ubuntu-24.04.1-live-server-riscv64.img.gz': foo,
        ... 'ubuntu-24.04.1-preinstalled-server-armhf+raspi.img.xz': foo,
        ... 'ubuntu-24.04.1-preinstalled-server-arm64+raspi.img.xz': foo,
        ... 'ubuntu-24.04.1-preinstalled-server-riscv64+unmatched.img.xz': foo,
        ... 'ubuntu-24.04.1-preinstalled-desktop-arm64+raspi.img.xz': foo,
        ... }
        >>> with _test_server(_make_index(_make_sums(images))) as url:
        ...     images = get_images(url)
        >>> [i.name for i in filter_images(images, archs={'armhf'})]
        ['ubuntu-24.04.1-preinstalled-server-armhf+raspi.img.xz']
        >>> [i.name for i in filter_images(images,
        ... image_types={'preinstalled-desktop'})]
        ['ubuntu-24.04.1-preinstalled-desktop-arm64+raspi.img.xz']
        >>> [i.name for i in filter_images(images, suffix='+unmatched')]
        ['ubuntu-24.04.1-preinstalled-server-riscv64+unmatched.img.xz']
        >>> [i.name for i in filter_images(images, suffix='')]
        ['ubuntu-24.04.1-live-server-riscv64.img.gz']
        >>> regex = re.compile(r'(24\\.04.*\\.gz|server.*\\+unmatched)')
        >>> [i.name # doctest: +NORMALIZE_WHITESPACE
        ... for i in filter_images(images, matches=regex)]
        ['ubuntu-24.04.1-live-server-riscv64.img.gz',
        'ubuntu-24.04.1-preinstalled-server-riscv64+unmatched.img.xz']
    """
    return [
        image
        for image in images
        if (archs is None or image.arch in archs)
        and (image_types is None or image.image_type in image_types)
        and (suffix is None or image.suffix == suffix)
        and (matches is None or matches.search(image.name))
    ]


def meta_parser(file: t.TextIO) -> t.Iterable[Release]:
    """
    Given a file-like object *file* which yields lines when iterated, yield
    :class:`Release` tuples from each successive stanza in the file.

    The expected source is https://changelogs.ubuntu.com/meta-release or any
    of the compatible URLs.
    """
    # I should use debian.deb822 for this ... but it's not packaged on PyPI
    # and this needs to run in an isolated venv, so that's out.
    # chain to guarantee our file ends with at least one blank line
    for line in itertools.chain(file, ['\n']):
        line = line.strip()
        if line:
            field, value = line.split(':', 1)
            field = field.strip().lower()
            value = value.strip()
            if field == 'dist':
                codename = value
            elif field == 'name':
                name = value
            elif field == 'version':
                version = value
            elif field == 'supported':
                supported = bool(int(value))
            elif field == 'date':
                parsed = parsedate(value)
                if parsed is not None:
                    time_tuple = time.struct_time(parsed)
                    date = dt.datetime(
                        time_tuple.tm_year,
                        time_tuple.tm_mon,
                        time_tuple.tm_mday,
                        time_tuple.tm_hour,
                        time_tuple.tm_min,
                        time_tuple.tm_sec,
                    )
        elif set(Release._fields) <= locals().keys():
            yield Release(codename, name, version, date, supported)
            del codename, name, version, date, supported


class TableParser(HTMLParser):
    """
    A sub-class of :class:`html.parser.HTMLParser` that finds all ``<table>``
    tags (indirectly) under the ``<html>`` tag.

    It stores the content of all ``<th>`` and ``<td>`` tags under each ``<tr>``
    tag in the :attr:`table` attribute as a list of lists (the outer list of
    rows, the inner lists of cells within those rows). All data is represented
    as strings. For example::

        >>> html = '''
        ... <html><body><table>
        ... <p>A table:
        ... <tr><th>#</th><th>Name</th></tr>
        ... <tr><td>1</td><td>foo</td></tr>
        ... <tr><td>2</td><td>bar</td></tr>
        ... <tr><td></td><td>quux</td></tr>
        ... </table></body></html>
        ... '''
        >>> parser = TableParser()
        >>> parser.feed(html)
        >>> parser.table
        [['#', 'Name'], ['1', 'foo'], ['2', 'bar'], ['', 'quux']]

    .. note::

        As this is a subclass of an HTML parser (as opposed to an XML parser)
        there is no requirement that the input is strictly valid XML, hence the
        lack of a closing ``<p>`` tag above is acceptable.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.state = 'html'
        self.table: list[list[str]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, t.Optional[str]]]
    ) -> None:
        if self.state == 'html' and tag == 'table':
            self.state = 'table'
        elif self.state == 'table' and tag == 'tr':
            self.state = 'tr'
            self.table.append([])
        elif self.state == 'tr' and tag in ('th', 'td'):
            self.state = 'td'
            self.table[-1].append('')

    def handle_data(self, data: str) -> None:
        if self.state == 'td':
            self.table[-1][-1] += data

    def handle_endtag(self, tag: str) -> None:
        if self.state == 'table' and tag == 'table':
            self.state = 'html'
        elif self.state == 'tr' and tag == 'tr':
            self.state = 'table'
        elif self.state == 'td' and tag in ('th', 'td'):
            self.state = 'tr'


# TEST SUITE ################################################################
#
# Everything from here on down is solely for the test-suite, which is
# implemented as doctests. To test the module, just run the module directly.


@contextlib.contextmanager
def _test_server(
    files: dict[str, bytes], *,
    host: str = '127.0.0.1', port: int = 0
) -> t.Iterator[str]:
    """
    This function provides a test HTTP server for the doctest suite.

    It expects to be called with *content*, a :class:`dict` mapping filenames
    to byte-strings representing file contents. All contents will be written to
    a temporary directory, and a trivial HTTP server will be started to serve
    its content on the specified *host* and *port* (defaults to an ephemeral
    port on localhost).

    The function acts as a context manager, cleaning up the http daemon and
    temporary directory upon exit. The URL of the root of the server is yielded
    by the context manager.
    """
    # pylint: disable=import-outside-toplevel, too-many-locals
    # These imports are for the test-suite only
    import tempfile
    import http.server
    from pathlib import Path
    from threading import Thread

    class SilentHandler(http.server.SimpleHTTPRequestHandler):
        """
        Trivial derivative of SimpleHTTPRequestHandler that doesn't spam the
        console with log messages.
        """

        # pylint: disable=redefined-builtin
        # The super-class uses format here
        def log_message(self, format: str, *args: t.Any) -> None:
            pass

    with tempfile.TemporaryDirectory() as temp:
        for filename, data in files.items():
            filepath = Path(temp) / filename
            filepath.write_bytes(data)

        handler = functools.partial(SilentHandler, directory=temp)
        with http.server.ThreadingHTTPServer((host, port), handler) as httpd:
            host_raw, port, *_ = httpd.server_address
            host = (
                host_raw if isinstance(host_raw, str) else
                host_raw.decode('ascii'))
            httpd_thread = Thread(target=httpd.serve_forever)
            httpd_thread.start()
            try:
                yield f'http://{host}:{port}/'
            finally:
                httpd.shutdown()
                httpd_thread.join(timeout=5)
                assert not httpd_thread.is_alive()


def _make_sums(files: dict[str, bytes]) -> dict[str, bytes]:
    """
    This function exists to generate SHA256SUMS files for the doctest suite.

    Given *files*, a :class:`dict` mapping filenames to byte-strings of
    file contents, this function returns a new :class:`dict` which is a copy of
    *files* with one additional entry titled "SHA256SUMS" which contains the
    output of the "sha256sum" command for the given content.
    """
    # pylint: disable=import-outside-toplevel
    # These imports are for the test-suite only
    import hashlib

    files = files.copy()
    files['SHA256SUMS'] = '\n'.join(
        f'{hashlib.sha256(data).hexdigest()}  {filename}'
        for filename, data in files.items()
    ).encode('ascii')
    return files


def _make_releases() -> dict[str, bytes]:
    # pylint: disable=import-outside-toplevel
    # These imports are for the test-suite only
    from email.utils import formatdate

    releases = [
        ('Warty Warthog', '04.10', '2004-10-20T07:28:17Z', False),
        ('Disco Dingo', '19.04', '2019-04-18T19:04:00Z', False),
        ('Jammy Jellyfish', '22.04.5 LTS', '2022-04-21T22:04:00Z', True),
    ]

    paras = []
    pre = 'http://archive.ubuntu.com/ubuntu/dists'
    suf = 'main/dist-upgrader-all/current'
    for name, version, date_str, supported in releases:
        codename = name.lower().split()[0]
        atime = dt.datetime.fromisoformat(date_str)
        paras.append(
            f"""
Dist: {codename}
Name: {name}
Version: {version}
Date: {formatdate(atime.timestamp())}
Supported: {int(supported)}
Description: This is the {version} release
Release-File: {pre}/{codename}-updates/Release
ReleaseNotes: {pre}/{codename}-updates/{suf}/ReleaseAnnouncement
ReleaseNotesHtml: {pre}/{codename}-updates/{suf}/ReleaseAnnouncement.html
UpgradeTool: {pre}/{codename}-updates/{suf}/{codename}.tar.gz
UpgradeToolSignature: {pre}/{codename}-updates/{suf}/{codename}.tar.gz.gpg""")
    files = {
        'meta-release': '\n'.join(paras).strip().encode('utf-8'),
        'meta-release-development': b'',
    }
    return files


def _make_index(
    files: dict[str, bytes],
    timestamp: t.Optional[dt.datetime] = None
) -> dict[str, bytes]:
    """
    This function generates index.html files for the doctest suite.

    Given *files*, a :class:`dict` mapping image filenames to byte-strings
    of file contents, this function generates an appropriate "index.html" file,
    returning a copy of the original :class:`dict` with this new entry.

    Additionally *timestamp*, a :class:`~datetime.datetime` representing the
    last modification date, can be specified. It defaults to the current time
    if not given.
    """
    if timestamp is None:
        timestamp = dt.datetime.now()
    files = files.copy()
    rows = '\n'.join(
        f'<tr><td>Icon</td><td>{filename}</td>'
        f'<td>{timestamp.strftime("%Y-%m-%d %H:%M")}</td>'
        f'<td>{len(data) // 1024}K</td><td>Descriptive text</td></tr>'
        for filename, data in files.items()
    )
    files['index.html'] = f"""
    <html><body>
      <p>The following files are available:</p>
      <table>
      <tr><th></th><th>Name</th><th>LastMod</th><th>Size</th><th>Desc</th></tr>
      {rows}
      </table>
    </body></html>
    """.encode('utf-8')
    return files


__test__ = {
    'bad-state': """
    Reject bad support states::

        >>> parse_state('foo')
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
          File "./downloads.py", line 56, in parse_state
            raise ValueError(f'invalid state: {s}') from None
        ValueError: invalid state: foo
    """,

    'tuple-properties': """
    Ensure calculated Release properties operate as expected::

        >>> noble = Release('noble', 'Noble Numbat', '24.04.1 LTS',
        ... dt.datetime(2024, 8, 29, 12, 0, 0), 1)
        >>> dingo = Release('dingo', 'Disco Dingo', '19.04',
        ... dt.datetime(2019, 4, 15, 12, 0, 0), 0)
        >>> noble.is_lts
        True
        >>> dingo.is_lts
        False

    Ensure calculated Image properties operate as expected::

        >>> pi_img = Image(
        ... 'http://cdimage.ubuntu.com/releases/noble/release/'
        ... 'ubuntu-24.04.1-preinstalled-desktop-arm64+raspi.img.xz',
        ... 'ubuntu-24.04.1-preinstalled-desktop-arm64+raspi.img.xz',
        ... dt.datetime(2024, 8, 27, 14, 46, 0),
        ... '5bd01d2a51196587b3fb2899a8f078a2a080278a83b3c8faa91f8daba750d00c')
        >>> arm_img = Image(
        ... 'http://cdimage.ubuntu.com/releases/noble/release/'
        ... 'ubuntu-24.04.1-live-server-arm64.iso',
        ... 'ubuntu-24.04.1-live-server-arm64.iso',
        ... dt.datetime(2024, 8, 27, 15, 43, 0),
        ... '5ceecb7ef5f976e8ab3fffee7871518c8e9927ec221a3bb548ee1193989e1773')
        >>> pi_img.version
        '24.04.1'
        >>> pi_img.image_type
        'preinstalled-desktop'
        >>> pi_img.suffix
        '+raspi'
        >>> pi_img.arch
        'arm64'
        >>> pi_img.file_type
        'img'
        >>> pi_img.compression
        'xz'
        >>> arm_img.version
        '24.04.1'
        >>> arm_img.image_type
        'live-server'
        >>> arm_img.arch
        'arm64'
        >>> arm_img.file_type
        'iso'
        >>> arm_img.compression
        ''
    """,

    'bad-url': """
    The URL provided to get_entry must be valid::

        >>> images = {
        ...     'ubuntu-21.10-foo-armhf+raspi.img.xz': b'foo' * 123456,
        ...     'ubuntu-21.10-bar-arm64+raspi.img.xz': b'bar' * 234567,
        ... }
        >>> with _test_server(_make_index(_make_sums(images))) as url:
        ...     wrong_url = f'{url}wrong/index.html'
        ...     get_images(wrong_url) # doctest: +ELLIPSIS
        Traceback (most recent call last):
          File "<stdin>", line 5, in <module>
            get_images(wrong_url) # doctest: +ELLIPSIS
          File ".../downloads.py", line 370, in get_images
            raise ValueError(...)
        ValueError: unable to get http://...; are you sure the path is correct?
    """,

    'no-checksums': """
    The SHA256SUMS file must exist on the server::

        >>> images = {
        ...     'ubuntu-21.10-foo-armhf+raspi.img.xz': b'foo' * 123456,
        ...     'ubuntu-21.10-bar-arm64+raspi.img.xz': b'bar' * 234567,
        ... }
        >>> with _test_server(_make_index(images)) as url:
        ...     get_images(url + 'index.html') # doctest: +ELLIPSIS
        Traceback (most recent call last):
          File "<stdin>", line 3, in <module>
            get_images(image_url)
          File ".../downloads.py", line 385, in get_images
            raise ValueError(...)
        ValueError: SHA256SUMS file is missing from http://...
    """,

    'ignore-star-prefixes': """
    Filenames in checksum files can have star prefixes (indicating binary
    input) which should be ignored::

        >>> images = _make_sums({
        ...     'ubuntu-21.10-foo-armhf+raspi.img.xz': b'foo' * 123456,
        ...     'ubuntu-21.10-bar-arm64+raspi.img.xz': b'bar' * 234567,
        ... })
        >>> cksums = images['SHA256SUMS'].decode('utf-8').splitlines(True)
        >>> cksums = [f'{cksum} *{filename}' for line in cksums
        ...     for cksum, filename in (line.split(None, 1),)]
        >>> images['SHA256SUMS'] = ''.join(cksums).encode('utf-8')
        >>> ts = dt.datetime(2021, 10, 25)
        >>> with _test_server(_make_index(images, ts)) as url:
        ...     index = get_images(url)
        >>> index[1] # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
        Image(url='http://.../ubuntu-21.10-bar-arm64+raspi.img.xz',
        name='ubuntu-21.10-bar-arm64+raspi.img.xz',
        date=datetime.date(2021, 10, 25),
        sha256='e9cd9718e97ac951c0ead5de8069d0ff5de188620b12b02...')
    """,

    'ignore-extra-cksums': """
    Files may be present in the checksum file which we didn't find (or more
    likely ignored) in the index.html. This should not cause an error::

        >>> images = _make_sums({
        ...     'ubuntu-21.10-foo-armhf+raspi.img.xz': b'foo' * 123456,
        ...     'ubuntu-21.10-bar-arm64+raspi.img.xz': b'bar' * 234567,
        ... })
        >>> cksums = images['SHA256SUMS'].decode('utf-8')
        >>> cksums += '\\n' + '0123abcd' * 8 + ' weird-hash.img.xz'
        >>> images['SHA256SUMS'] = cksums.encode('utf-8')
        >>> ts = dt.datetime(2021, 10, 25)
        >>> with _test_server(_make_index(images, ts)) as url:
        ...     index = get_images(url)
        >>> index[1] # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
        Image(url='http://.../ubuntu-21.10-bar-arm64+raspi.img.xz',
        name='ubuntu-21.10-bar-arm64+raspi.img.xz',
        date=datetime.date(2021, 10, 25),
        sha256='e9cd9718e97ac951c0ead5de8069d0ff5de188620b12b02...')
    """,

    'full-run': """
    Check that we can parse some reST containing the custom directive, and
    get sensible output::

        >>> import tempfile
        >>> from pathlib import Path
        >>> ts = dt.datetime(2021, 10, 25)
        >>> foo = b'foo' * 123456
        >>> images = {
        ... 'ubuntu-22.04.5-live-server-riscv64.img.gz': foo,
        ... 'ubuntu-22.04.5-preinstalled-server-armhf+raspi.img.xz': foo,
        ... 'ubuntu-22.04.5-preinstalled-server-arm64+raspi.img.xz': foo,
        ... 'ubuntu-22.04.5-preinstalled-server-riscv64+unmatched.img.xz': foo,
        ... 'ubuntu-22.04.5-preinstalled-desktop-arm64+raspi.img.xz': foo,
        ... }
        >>> files = _make_index(_make_sums(images), ts) | _make_releases()
        >>> tmp_dir = tempfile.TemporaryDirectory()
        >>> tmp = Path(tmp_dir.name)
        >>> with tmp_dir, _test_server(files) as url:
        ...     (tmp / 'src').mkdir()
        ...     (tmp / 'build').mkdir()
        ...     (tmp / 'tree').mkdir()
        ...     _ = (tmp / 'src' / 'index.rst').write_text(f'''\
        ...     Download one of the supported images:
        ...
        ...     .. ubuntu-images::
        ...         :releases: jammy-
        ...         :archs: armhf,arm64
        ...         :image-types: preinstalled-server
        ...         :meta-release: {url}meta-release
        ...         :meta-release-development: {url}meta-release-development
        ...         :cdimage-template: {url}
        ...     ''')
        ...     app = Sphinx(
        ...         srcdir=tmp / 'src', confdir=None,
        ...         outdir=tmp / 'build', doctreedir=tmp / 'tree',
        ...         buildername='html', status=None, warning=None)
        ...     _ = setup(app)
        ...     app.build()
        ...     print(
        ...         (tmp / 'build' / 'index.html').read_text()
        ...     ) # doctest: +NORMALIZE_WHITESPACE +ELLIPSIS
        <!DOCTYPE html>
        <BLANKLINE>
        <html...>
        ...
        <ul>
        <li><p>Ubuntu 22.04.5 LTS (Jammy Jellyfish) images:</p>
        <ul>
        <li><a class="reference download external" download=""
        href="...">ubuntu-22.04.5-preinstalled-server-armhf+raspi...</a></li>
        <li><a class="reference download external" download=""
        href="...">ubuntu-22.04.5-preinstalled-server-arm64+raspi...</a></li>
        </ul>
        </li>
        </ul>
        ...
        </html>
    """,
}


if __name__ == '__main__':
    import sys
    import doctest

    # Undecorate get_releases and get_images to prevent the cache from breaking
    # many tests (could use func.cache_clear but this hack is marginally
    # cleaner at least from the perspective of the tests themselves)
    get_releases = get_releases.__wrapped__  # type: ignore
    get_images = get_images.__wrapped__  # type: ignore
    failures, total = doctest.testmod()
    sys.exit(bool(failures))
