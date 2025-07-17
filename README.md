# Canonical Sphinx extensions

This package provides several Sphinx extensions that are used in Canonical documentation (for example, in the [documentation starter pack](https://github.com/canonical/sphinx-docs-starter-pack)).

**Note:** This package used to be called `lxd-sphinx-extensions` but has been renamed to `canonical-sphinx-extensions`.

## Installation

Install the package with the following command:

    pip install canonical-sphinx-extensions

## Provided extensions

The package provides several Sphinx extensions that can be used in combination or separately.

### Related links

This extension allows adding related links (Discourse links and general related links) on a per-page basis.
The links are specified as metadata in the RST files.
They can be displayed at any place in the output by adapting the Sphinx template.

#### Enable the extension

Add `related-links` to your extensions list in `conf.py` to enable the extension:

    extensions = [
                  (...),
             ￼    "canonical.related-links"
                 ]

If you want to add Discourse links, you must also configure the prefix for your Discourse instance in the `html_context` variable:

    html_context = {
                    (...),
                    "discourse_prefix": "https://discuss.linuxcontainers.org/t/"
                   }

You can configure different Discourse prefixes by specifying a dict:

    html_context = {
                    (...),
                    "discourse_prefix": {
                        "lxc": "https://discuss.linuxcontainers.org/t/",
                        "ubuntu": "https://discourse.ubuntu.com/t/"}
                    }

#### Add related links to the template

The extension provides two functions that can be used in your template:

* `discourse_links(meta.discourse)`: Returns an unordered list (`<ul>`) of Discourse links.
* `related_links(meta.relatedlinks)`: Returns an unordered list (`<ul>`) of related links.

For example, to include the related links in your template based on the Furo theme, place code similar to the following in your `_templates/page.html` file:

```
{% if meta and ((meta.discourse and discourse_prefix) or meta.relatedlinks) %}
   {% set furo_hide_toc_orig = furo_hide_toc %}
   {% set furo_hide_toc=false %}
{% endif %}

{% block right_sidebar %}
<div class="toc-sticky toc-scroll">
   {% if not furo_hide_toc_orig %}
    <div class="toc-title-container">
      <span class="toc-title">
       {{ _("Contents") }}
      </span>
    </div>
    <div class="toc-tree-container">
      <div class="toc-tree">
        {{ toc }}
      </div>
    </div>
   {% endif %}
    {% if meta and ((meta.discourse and discourse_prefix) or meta.relatedlinks) %}
    <div class="relatedlinks-title-container">
      <span class="relatedlinks-title">
       Related links
      </span>
    </div>
    <div class="relatedlinks-container">
      <div class="relatedlinks">
        {% if meta.discourse and discourse_prefix %}
          {{ discourse_links(meta.discourse) }}
        {% endif %}
        {% if meta.relatedlinks %}
          {{ related_links(meta.relatedlinks) }}
        {% endif %}
      </div>
    </div>
    {% endif %}
  </div>
{% endblock right_sidebar %}
```

See the [Sphinx documentation](https://www.sphinx-doc.org/en/master/templating.html#jinja-sphinx-templating-primer) for information on how templating works in Sphinx.

#### Style the output

The extension comes with a CSS file that is suitable for the template example as given above.
You can override these styles or define your own, depending on the theme and template that you use.

#### Specify links for a page

Specify your Discourse links and related links in the metadata at the top of the page.

For Discourse links, specify only the topic IDs (in a comma-separated list).
If you have defined several Discourse prefixes, specify both key and ID (for example, `abc:1234`).

For related links, specify the full URLs (in a comma-separated list).

The link text is extracted automatically or can be specified in Markdown syntax.
You can also specify a backup link text (using curly brackets instead of square brackets) that is used only if the link title cannot be extracted.
Note that spaces are ignored; if you need spaces in the title, replace them with `&#32;`.
If Sphinx complains about the metadata value because it starts with "\[", enclose the full value in double quotes.

The following example uses MyST syntax for the metadata:

```
---
discourse: 1234, abc:56789, abc:[Link&#32;text](1234)
relatedlinks: https://www.example.com, [Link&#32;text](https://www.example.com), {Backup&#32;text}(https://www.example.com)
---
```

### YouTube links

This extension adds a `:youtube:` directive that you can use to add links to YouTube videos at any place in an input file.

#### Enable the extension

Add `youtube-links` to your extensions list in `conf.py` to enable the extension:

    extensions = [
                  (...),
             ￼    "canonical.youtube-links"
                 ]

#### Style the output

The extension comes with a CSS file that implements the style for the `p.youtube_link` element.
You can override the style in your own style sheet.

#### Add YouTube links

To add a YouTube link to your page, use the `:youtube:` directive and specify the link to the video.

For example, in MyST syntax:

````
```{youtube} https://www.youtube.com/watch?v=4iNpiL-lrXU
```
````

To override the title, add a `:title:` option.
For example:

````
```{youtube} https://www.youtube.com/watch?v=4iNpiL-lrXU
:title: Watch on YouTube!
```
````

### Custom roles

This extension adds custom roles that can be used in rST.

Currently implemented:

- `spellexception` - Includes the provided text in `<spellexception></spellexception>`, which makes it possible to exclude it from a spelling checker.
- `literalref` - Renders the provided reference in code-style, which excludes the link text from the spelling checker.
   You can provide either just the link (for example, ``:literalref:`www.example.com` ``, which results in `www.example.com` as the link text and `https://www.example.com` as the link URL) or a separate link text and URL (for example, ``:literalref:`xyzcommand <www.example.com>` ``). This also now works for internal headings such as ``:literalref:`some.command` `` if the internal link has a defined anchor.
- `none` - Excludes the provided text from the output.
  This is useful for comments, especially when providing `wokeignore` rules.

### Config options

This extension adds a `:config:option:` directive that you can use to generate expandable configuration options, a `:config:option:` role for linking to those options, and an index that lists all config options.

#### Enable the extension

Add `config-options` to your extensions list in `conf.py` to enable the extension:

    extensions = [
                  (...),
                  "canonical.config-options"
                 ]

#### Style the output

The extension comes with a CSS file that implements the classes needed to style the configuration options.
This CSS file requires the following colour variables to be defined:

- `color-content-foreground`: normal text colour
- `color-link`: link text colour
- `color-table-border`: colour for table borders
- `color-orange`: contrast colour (used for table cell background)

You can override the style in your own style sheet.

#### Add configuration options

Use the `:config:option:` directive to add a configuration option.
It takes two parameters: the config option name and the scope.
If the scope is not provided, `server` is used as the default scope.

You must provide a `:shortdesc:` option.
Optional options are `:type:`, `:liveupdate:`, `:condition:`, `:readonly:`, `:resource:`, `:managed:`, `:required:`, and `:scope:` (this scope is not related to the option scope specified by the parameter).

You can use formatting in the short description, the options, and the main description.
When starting a value with markup, or if you want to prevent a value from being processed (for example, to prevent a "no" value to be transformed to "False"), put quotes around the value.

For example, in MyST syntax:

````
```{config:option} backups.compression_algorithm server
:shortdesc: Compression algorithm for images
:type: string
:scope: global
:default: "`gzip`"

Compression algorithm to use for new images (`bzip2`, `gzip`, `lzma`, `xz` or `none`)
```
````

For more examples, see https://linuxcontainers.org/lxd/docs/latest/networks/config_options_cheat_sheet.

#### Link to configuration options

To link to a configuration option, use the `:config:option:` role.
You cannot override the link text (which wouldn't make much sense anyway, because it is displayed as code).

For example, in MyST syntax:

```
{config:option}`instance:migration.incremental.memory.iterations`
```

#### Link to the index

You can link to the index of configuration options with the `config-options` anchor.

For example, in MyST syntax:

```
{ref}`config-options`
```

### Terminal output

This extension adds a `:terminal:` directive that you can use to show a terminal view with commands and output.
You can customise the prompt and configure whether the lines should wrap.

#### Enable the extension

Add `terminal-output` to your extensions list in `conf.py` to enable the extension:

    extensions = [
                  (...),
             ￼    "canonical.terminal-output"
                 ]

#### Style the output

The extension comes with a CSS file that implements the classes needed to style the terminal output.
You can override the style in your own style sheet.

#### Add a terminal view

To add a terminal view to your page, use the `:terminal:` directive and specify the the input (as `:input:` option) and output (as the main content of the directive).
Any lines prefixed with `:input:` in the main content are treated as input as well.

To override the prompt (`user@host:~$` by default), specify the `:user:`, `:dir:` and/or `:host:` options.
To make the terminal scroll horizontally instead of wrapping long lines, add `:scroll:`.

For example, in MyST syntax:

````
Single command sample:

```{terminal}
:input: single command
:user: root
:host: vm
:dir: /tmp/dir/

output line one
output line two
```

Multiple command sample:

```{terminal}
:user: root
:host: vm
:dir: /tmp/dir/

:input: a command
output line one
output line two

:input: another command
more output
```
````

Note: This supports `:input` as part of the initial configuration block. but requires a space between the first input and any successive input lines. For example:

````
```{terminal}
:user: root
:host: vm
:input: command#1

:input: command#2
:input: command#3
```
````

Note: You can use the `:copy:` option, or `copybutton` class to enable terminal inputs to be copyable.

### Filtered ToC

This extension adds a `:filtered-toctree:` directive that is almost the same as the normal `:toctree:` directive but allows excluding pages based on specified filters.

#### Enable the extension

Add `filtered-toc` to your extensions list in `conf.py` to enable the extension:

    extensions = [
                  (...),
             ￼    "canonical.filtered-toc"
                 ]

#### Configure the filters

Define filters that you want to exclude from your documentation in the `toc_filter_exclude` variable in your `conf.py`.
For example:

    toc_filter_exclude = ['draft','internal']

You can use environment variables or build parameters to distinguish between different settings for the `toc_filter_exclude` variable in your `conf.py`.
For example:

    if ('TOPICAL' in os.environ) and (os.environ['TOPICAL'] == 'True'):
        toc_filter_exclude = ['diataxis']
    else:
        toc_filter_exclude = ['topical']

#### Use the `:filtered-toctree:` directive

The `:filtered-toctree:` directive works just as the normal `:toctree:` directive, but you can add a filter to each line.
The filter must start and end with a colon (`:`) and contains any string in between.
The string between the colons is what you would specify in the `toc_filter_exclude` variable (however, you can use any string, even if it's not specified in the `toc_filter_exclude` variable).

You can put the filter either at the front of the line or right in front of the file name or path.
You can only specify one filter per line.

For example, in MyST syntax:

````
```{filtered-toctree}
:maxdepth: 1

:internal:/tutorial/first_steps
:draft:Installation </installing>
Get support <:external:/support>
```
````

In this case, all three topics would be included by default.
When setting `toc_filter_exclude = ['draft','internal']`, only `Get support` would be included.

### Contributor listing

This extension allows adding a link that displays all contributors for a page.
The contributors are retrieved from the Git history of each file.
The link can be displayed at any place in the output by adapting the Sphinx template.

#### Enable the extension

Add `canonical.contributor-listing` to your extensions list in `conf.py` to enable the extension:

    extensions = [
                  (...),
             ￼    "canonical.contributor-listing"
                 ]

You can then control whether contributors are displayed by setting the `display_contributors` field in the `html_context` variable:

    html_context = {
                    (...),
                    "display_contributors": True,
                   }

You can configure a time frame for retrieving contributors by specifying a value for `display_contributors_since`:

    html_context = {
                    (...),
                    "display_contributors_since": "3 months",
                    }

#### Add contributor link to the template

The extension provides a `get_contributors_for_file` function that can be used in your template.
This function returns an alphabetical list of tuples that contain the name of the contributor and the link to their latest commit to the file.

For example, to include the contributor link in your template based on the Furo theme, place code similar to the following at an appropriate location in your `_templates/footer.html` file:

```
    {% if display_contributors and pagename and page_source_suffix %}
        {% set contributors = get_contributors_for_file(pagename, page_source_suffix) %}
        {% if contributors %}
          {% if contributors | length > 1 %}
              <a class="display-contributors">Thanks to the {{ contributors |length }} contributors!</a>
          {% else %}
              <a class="display-contributors">Thanks to our contributor!</a>
          {% endif %}
          <div id="overlay"></div>
          <ul class="all-contributors">
              {% for contributor in contributors %}
                  <li>
                      <a href="{{ contributor[1] }}" class="contributor">{{ contributor[0] }}</a>
                  </li>
              {% endfor %}
          </ul>
        {% endif %}
    {% endif %}
```

See the [Sphinx documentation](https://www.sphinx-doc.org/en/master/templating.html#jinja-sphinx-templating-primer) for information on how templating works in Sphinx.

#### Style the output

The extension comes with a CSS file that is suitable for the template example as given above.
You can override these styles or define your own, depending on the theme and template that you use.

### Ubuntu images

This extension generates lists of Ubuntu installation images available from
[cdimage.ubuntu.com][cdimage], after applying various filters. See [the
README][ubuntu-image-readme] for more information.

[cdimage]: https://cdimage.ubuntu.com/
[ubuntu-image-readme]: canonical-sphinx-extensions/ubuntu-images/README.rst

