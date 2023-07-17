######################################################################
# This extension allows adding related links on a per-page basis
# in two ways (which can be combined):
#
# - Add links to Discourse topics by specifying the Discourse prefix
#   in the html_context variable in conf.py, for example:
#
#   html_context = {
#       "discourse_prefix": "https://discuss.linuxcontainers.org/t/"
#   }
#
#   Then add the topic IDs that you want to link to the metadata at
#   the top of the page using the tag "discourse".
#   For example (in MyST syntax):
#
#   ---
#   discourse: 12033,13128
#   ---
#
#   You can use different Discourse instances by defining prefixes
#   for each instance. For example:
#
#   html_context = {
#       "discourse_prefix": {
#           "lxc": "https://discuss.linuxcontainers.org/t/",
#           "ubuntu": "https://discourse.ubuntu.com/t/"
#       }
#   }
#
#   Use these prefixes when linking (no prefix = first dict entry)
#
#   ---
#   discourse: ubuntu:12033,lxc:13128
#   ---
#
# - Add related URLs to the metadata at the top of the page using
#   the tag "relatedlinks". The link text is extracted automatically
#   or can be specified in Markdown syntax. Note that spaces are
#   ignored; if you need spaces in the title, replace them with &#32;.
#   Some examples (in MyST syntax):
#
#   ---
#   relatedlinks: https://www.example.com
#   ---
#
#   ---
#   relatedlinks: https://www.example.com, https://www.google.com
#   ---
#
#   ---
#   relatedlinks: "[Link&#32;text](https://www.example.com)"
#   ---
#
#   If Sphinx complains about the metadata value because it starts
#   with "[", enclose the full value in double quotes.
#
# For both ways, check for errors in the output. Invalid links are
# not added to the output.
######################################################################

import requests
import json
from bs4 import BeautifulSoup
from sphinx.util import logging
from . import common

cache = {}
logger = logging.getLogger(__name__)


def setup_func(app, pagename, templatename, context, doctree):
    def discourse_links(IDlist):

        if context["discourse_prefix"] and IDlist:

            posts = IDlist.strip().replace(" ", "").split(",")

            linklist = "<ul>"

            for post in posts:
                title = ""

                if type(context["discourse_prefix"]) is dict:
                    ID = post.split(":")
                    if len(ID) == 1:
                        linkurl = list(
                            context["discourse_prefix"].values()
                        )[0] + post
                    elif ID[0] in context["discourse_prefix"]:
                        linkurl = context["discourse_prefix"][ID[0]] + ID[1]
                    else:
                        logger.warning(
                            pagename
                            + ": Discourse prefix "
                            + ID[0]
                            + " is not defined."
                        )
                        continue
                else:
                    linkurl = context["discourse_prefix"] + post

                if post in cache:
                    title = cache[post]
                else:
                    try:
                        r = requests.get(linkurl + ".json")
                        r.raise_for_status()
                        title = json.loads(r.text)["title"]
                        cache[post] = title
                    except requests.HTTPError as err:
                        logger.warning(pagename + ": " + str(err))
                    except requests.ConnectionError as err:
                        logger.warning(pagename + ": " + str(err))

                if title:
                    linklist += '<li><a href="' + linkurl
                    linklist += '" target="_blank">' + title + "</a></li>"

            linklist += "</ul>"

            return linklist

        else:
            return ""

    def related_links(linklist):

        if linklist:

            links = linklist.strip().replace(" ", "").split(",")

            linklist = "<ul>"

            for link in links:
                title = ""

                if link in cache:
                    title = cache[link]
                elif link.startswith("[") and link.endswith(")"):
                    split = link.partition("](")
                    title = split[0][1:]
                    link = split[2][:-1]
                else:
                    try:
                        r = requests.get(link)
                        r.raise_for_status()
                        soup = BeautifulSoup(r.text, "html.parser")
                        if soup.title is None:
                            logger.warning(
                                pagename
                                + ": "
                                + link
                                + " doesn't have a title."
                            )
                        else:
                            title = soup.title.get_text()
                            cache[link] = title
                    except requests.HTTPError as err:
                        logger.warning(pagename + ": " + str(err))
                    except requests.ConnectionError as err:
                        logger.warning(pagename + ": " + str(err))

                if title:
                    linklist += '<li><a href="' + link + '" target="_blank">'
                    linklist += title + "</a></li>"

            linklist += "</ul>"

            return linklist

        else:
            return ""

    context["discourse_links"] = discourse_links
    context["related_links"] = related_links


def setup(app):
    app.connect("html-page-context", setup_func)

    common.add_css(app, "related-links.css")

    return {"version": "0.1", "parallel_read_safe": True,
            "parallel_write_safe": True}
