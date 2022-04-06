# LXD Sphinx extensions

This package provides several Sphinx extensions that are used in the [LXD documentation](https://linuxcontainers.org/lxd/docs/master/), but can also be useful for other documentation sets.

## Installation

Install the package with the following command:

    pip install lxd-sphinx-extensions

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
             ￼    "related-links"
                 ]

If you want to add Discourse links, you must also configure the prefix for your Discourse instance in the `html_context` variable:

    html_context = {
                    (...),
                    "discourse_prefix": "https://discuss.linuxcontainers.org/t/"
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

For related links, specify the full URLs (in a comma-separated list).
The link text is extracted automatically or can be specified in Markdown syntax.
Note that spaces are ignored; if you need spaces in the title, replace them with `&#32;`.
If Sphinx complains about the metadata value because it starts with "[", enclose the full value in double quotes.

The following example uses MyST syntax for the metadata:

```
---
discourse: 1234,56789
relatedlinks: https://www.example.com, [Link&#32;text](https://www.example.com)
---
```

### YouTube links

This extension adds a `:youtube:` directive that you can use to add links to YouTube videos at any place in an input file.

#### Enable the extension

Add `youtube-links` to your extensions list in `conf.py` to enable the extension:

    extensions = [
                  (...),
             ￼    "youtube-links"
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
