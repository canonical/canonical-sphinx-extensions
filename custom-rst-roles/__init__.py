from docutils import nodes
import re


def spellexception_role(
    name, rawtext, text, lineno, inliner, options=None, content=None
):
    node = nodes.raw(
        text="<spellexception>" + text + "</spellexception>", format="html"
    )
    return [node], []


def literalref_role(
    name, rawtext, text, lineno, inliner, options=None, content=None
):

    findURL = re.compile(r"^(.+)<(.+)>$")
    m = findURL.match(text)

    if m is not None:
        linktext = m.groups()[0]
        linkurl = m.groups()[1]
    else:
        linktext = text
        linkurl = text

    if linkurl.find("://") < 0:
        linkurl = "https://" + linkurl

    node = nodes.reference("", "", internal=False, refuri=linkurl)
    node.append(nodes.literal(text=linktext))

    return [node], []


def setup(app):
    app.add_role("spellexception", spellexception_role)
    app.add_role("literalref", literalref_role)

    return
