from erp_ai.ai.registry import register_tool


def ai_tool(
    name: str,
    description: str,
    parameters=None,
):

    def decorator(func):

        register_tool(
            name=name,
            description=description,
            parameters=parameters,
            func=func,
        )

        return func

    return decorator