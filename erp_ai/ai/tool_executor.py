from erp_ai.ai.registry import get_tool


def execute_tool(name, arguments=None):

    arguments = arguments or {}

    tool = get_tool(name)

    if not tool:
        raise Exception(f"Unknown tool: {name}")

    return tool["function"](**arguments)