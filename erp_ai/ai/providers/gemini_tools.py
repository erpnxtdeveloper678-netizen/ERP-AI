from google.genai import types

from erp_ai.ai.registry import list_tools


def build_gemini_tools():

    declarations = []

    for tool in list_tools():

        properties = {}

        required = []

        for key, value in tool["parameters"].items():

            field_type = value.get("type", "string")

            if field_type == "integer":
                api_type = types.Type.INTEGER

            elif field_type == "number":
                api_type = types.Type.NUMBER

            elif field_type == "boolean":
                api_type = types.Type.BOOLEAN

            elif field_type == "array":
                api_type = types.Type.ARRAY

            elif field_type == "object":
                api_type = types.Type.OBJECT

            else:
                api_type = types.Type.STRING

            properties[key] = types.Schema(
                type=api_type,
                description=value.get("description", ""),
            )

            if value.get("required"):
                required.append(key)

        declarations.append(

            types.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties=properties,
                    required=required,
                ),
            )

        )

    return [
        types.Tool(
            function_declarations=declarations
        )
    ]