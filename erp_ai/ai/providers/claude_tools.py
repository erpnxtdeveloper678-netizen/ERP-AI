from erp_ai.ai.registry import get_tools


def build_claude_tools():

    result = []

    for tool in get_tools().values():

        properties = {}
        required = []

        for name, info in tool["parameters"].items():

            properties[name] = {
                "type": info.get("type", "string"),
                "description": info.get(
                    "description",
                    ""
                )
            }

            if info.get("required", True):
                required.append(name)

        result.append({

            "name": tool["name"],

            "description": tool["description"],

            "input_schema": {

                "type": "object",

                "properties": properties,

                "required": required

            }

        })

    return result