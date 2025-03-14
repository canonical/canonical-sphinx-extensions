.. Copied from the top of __init__.py

The ``.. ubuntu-images`` directive is a custom directive to generate bulleted
download lists of supported Ubuntu distro images for specific release ranges,
suffixes, image-types, and architectures.

The options that may be specified under the directive are as follows:

``:releases:`` *releases (list of ranges)*
    A comma or space-separated list of partial dash-delimited release ranges
    (as release codenames). See below for examples. If unspecified, all
    releases will be included.

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

    All visionfive images

    .. ubuntu-images::
        :suffix: +visionfive

    All supported LTS armhf and arm64 images

    .. ubuntu-images::
        :archs: armhf, arm64
        :lts-only:

