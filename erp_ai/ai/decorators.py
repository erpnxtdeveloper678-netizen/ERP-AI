from erp_ai.ai.registry import register_tool


def ai_tool(
    name: str,
    description: str,
    parameters=None,
    providers=None,
):

    def decorator(func):

        register_tool(
            name=name,
            description=description,
            parameters=parameters,
            func=func,
            providers=providers,
        )

        return func

    return decorator
    
