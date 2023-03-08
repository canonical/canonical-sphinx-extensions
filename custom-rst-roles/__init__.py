from docutils import nodes


def spellexception_role(
    name, rawtext, text, lineno, inliner, options=None, content=None
):
    node = nodes.raw(
        text="<spellexception>" + text + "</spellexception>", format="html"
    )
    return [node], []


def setup(app):
    app.add_role("spellexception", spellexception_role)

    return
