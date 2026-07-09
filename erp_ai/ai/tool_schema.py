from erp_ai.ai.registry import get_tools


def get_tool_schema():

    schema = []

    for tool in get_tools().values():

        schema.append({

            "name": tool["name"],

            "description": tool["description"],

            "parameters": tool["parameters"],

        })

    return schema