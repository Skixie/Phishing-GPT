from jinja2 import (
    ChainableUndefined,
    DebugUndefined,
    Environment,
    FunctionLoader,
    StrictUndefined,
)

def create_environment():
    env = Environment()
    return env

def render_template(template, context):
    env = create_environment()
    result = env.from_string(template).render(context)
    return result
