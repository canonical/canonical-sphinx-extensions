from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.parsers.rst import directives
from . import common


class TerminalOutput(Directive):

    required_arguments = 0
    optional_arguments = 0
    has_content = True
    option_spec = {
        "input": directives.unchanged,
        "user": directives.unchanged,
        "host": directives.unchanged,
        "dir": directives.unchanged,
        "scroll": directives.unchanged,
    }

    @staticmethod
    def input_line(prompt_text, command):

        inpline = nodes.container()
        inpline["classes"].append("input")

        prompt = nodes.literal(text=prompt_text)
        prompt["classes"].append("prompt")
        inpline.append(prompt)

        inp = nodes.literal(text=command)
        inp["classes"].append("command")
        inpline.append(inp)

        return inpline

    def run(self):
        # Build prompt with :user:, :host: and :dir: (whichever is provided)
        user = self.options.get("user")
        host = self.options.get("host")
        dir = self.options["dir"] if "dir" in self.options else "~"
        command = self.options["input"] if "input" in self.options else ""

        user_symbol = '#' if user == "root" else '$'

        if user and host:
            prompt_text = f"{user}@{host}:{dir}{user_symbol} "
        elif user and not host:
            # Only the user is supplied
            prompt_text = f"{user}:{dir}{user_symbol} "
        else:
            # Omit both user and host, just showing the host
            # doesn't really make sense
            prompt_text = f"{dir}{user_symbol} "

        out = nodes.container()
        out["classes"].append("terminal")
        if "scroll" in self.options:
            out["classes"].append("scroll")

        # Add the original prompt and input if the command is present

        if command:
            out.append(self.input_line(prompt_text, command))

        # Go through the content and append all lines as output
        # except for the ones that start with ":input: " - those get
        # a prompt

        for output in self.content:
            if output.startswith(":input: "):
                out.append(self.input_line(prompt_text, output[8:]))
            else:
                if output == "":
                    output = " "
                outp = nodes.literal(text=output)
                outp["classes"].append("output")
                out.append(outp)

        return [out]


def setup(app):
    app.add_directive("terminal", TerminalOutput)

    common.add_css(app, "terminal-output.css")

    return {"version": "0.1", "parallel_read_safe": True,
            "parallel_write_safe": True}
