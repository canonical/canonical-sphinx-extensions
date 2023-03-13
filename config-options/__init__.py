from collections import defaultdict
from docutils import nodes
from docutils.parsers.rst import directives
from docutils.statemachine import ViewList
from sphinx.domains import Domain, Index
from sphinx.roles import XRefRole
from sphinx.directives import ObjectDescription
from sphinx.util.nodes import make_refnode
from sphinx.errors import SphinxWarning
from . import common


# Parse rST inside an option (":something:")
def parseOption(obj, option):
    newNode = nodes.inline()
    parseNode = ViewList()
    parseNode.append(option, "parsing", 1)
    obj.state.nested_parse(parseNode, 0, newNode)
    return newNode


class ConfigOption(ObjectDescription):

    optional_fields = {
        "type": "Type",
        "liveupdate": "Live update",
        "condition": "Condition",
        "readonly": "Read-only",
        "resource": "Resource",
        "managed": "Managed",
        "required": "Required",
        "scope": "Scope",
    }

    required_arguments = 1
    optional_arguments = 1
    has_content = True
    option_spec = {
        "shortdesc": directives.unchanged_required,
        "default": directives.unchanged,
    }
    for field in optional_fields:
        option_spec[field] = directives.unchanged

    def run(self):

        # Generate the output

        key = nodes.inline()
        key += nodes.literal(text=self.arguments[0])
        key["classes"].append("key")

        shortDesc = parseOption(self, self.options["shortdesc"])
        shortDesc["classes"].append("shortdesc")

        default = nodes.inline()
        default["classes"].append("default")
        if "default" in self.options:
            default += nodes.strong(text="Default: ")
            parsedDefault = parseOption(self, self.options["default"])
            parsedDefault["classes"].append("ignoreP")
            default += parsedDefault

        firstLine = nodes.container()
        firstLine["classes"].append("basicinfo")
        firstLine += key
        firstLine += shortDesc
        firstLine += default

        details = nodes.container()
        details["classes"].append("details")
        fields = nodes.bullet_list()
        fields["classes"].append("fields")
        for field in self.optional_fields:
            if field in self.options:
                item = nodes.list_item()
                item += nodes.strong(text=self.optional_fields[field] + ": ")
                parsedOption = parseOption(self, self.options[field])
                parsedOption["classes"].append("ignoreP")
                item += parsedOption
                fields += item
        details += fields
        self.state.nested_parse(self.content, self.content_offset, details)

        # Create a new container node with the content

        newNode = nodes.container()
        newNode["classes"].append("configoption")
        newNode += firstLine
        newNode += details

        # Create a target

        scope = "server"
        if len(self.arguments) > 1:
            scope = self.arguments[1]
        targetID = scope + ":" + self.arguments[0]
        targetNode = nodes.target("", "", ids=[targetID])

        # Register the target with the domain

        configDomain = self.env.get_domain("config")
        configDomain.add_option(self.arguments[0], scope)

        # Return the content and target node

        return [targetNode, newNode]


class ConfigIndex(Index):

    # To link to the index: {ref}`config-options`
    name = "options"
    localname = "Configuration options"

    def generate(self, docnames=None):
        content = defaultdict(list)

        options = self.domain.get_objects()
        # sort by key name
        options = sorted(options, key=lambda option: option[0])

        for _name, dispname, typ, docname, anchor, _priority in options:
            # group by scope
            content[anchor.partition(":")[0]].append(
                (dispname, 0, docname, anchor, "", "", "")
            )

        content = sorted(content.items())

        return content, True


class ConfigDomain(Domain):

    name = "config"
    label = "Configuration Options"
    roles = {"option": XRefRole()}
    directives = {"option": ConfigOption}
    indices = {ConfigIndex}
    initial_data = {"config_options": []}

    def get_objects(self):
        yield from self.data["config_options"]

    # Find the node that is being referenced
    def resolve_xref(self, env, fromdocname, builder, typ, target,
                     node, contnode):

        # If the scope isn't specified, default to "server"
        if ":" not in target:
            target = "server:" + target

        match = [
            (key, docname, anchor)
            for key, sig, typ, docname, anchor, prio in self.get_objects()
            if anchor == target and typ == "option"
        ]

        if len(match) > 0:
            title = match[0][0]
            todocname = match[0][1]
            targ = match[0][2]

            refNode = make_refnode(
                builder, fromdocname, todocname, targ,
                child=nodes.literal(text=title)
            )
            refNode["classes"].append("configref")
            return refNode

        else:
            raise SphinxWarning(
                "Could not find target " + target + " in " + fromdocname
            )
            return []

    # We don't want to link with "any" role, but only with "config:option"
    def resolve_any_xref(self, env, fromdocname, builder, target, node,
                         contnode):
        return []

    # Store the option
    def add_option(self, key, scope):

        self.data["config_options"].append(
            (key, key, "option", self.env.docname, scope + ":" + key, 0)
        )


def setup(app):
    app.add_domain(ConfigDomain)

    common.add_css(app, "config-options.css")
    common.add_js(app, "config-options.js")

    return {"version": "0.1", "parallel_read_safe": True,
            "parallel_write_safe": True}
