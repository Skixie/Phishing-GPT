import importlib
import sys

def fully_qualified_name(function):
    return f"{function.__module__}.{function.__name__}"

def raise_if_function_is_invalid(fully_qualified_function_name):
    """Checks whether the function identified by the fully qualified function name may be called,
    and raises an exception if it is not valid.

    Valid functions are all functions in the spo_automation.workflows.* modules.

    """
    elements = fully_qualified_function_name.split('.')

    if elements[0:2] != ['spo_automation', 'workflows']:
        raise Exception(f"{fully_qualified_function_name}: Only functions within spo_automation.workflows are valid")
    return

def load_function(f_name):
    # Check that this function may be called
    raise_if_function_is_invalid(f_name)

    # Identify the module and function name
    elements = f_name.split('.')
    module_name = ".".join(elements[0:-1])
    function_name = elements[-1]

    # Load the module, if necessary
    if module_name in sys.modules:
        # the module is already loaded
        pass
    else:
        try:
            importlib.import_module(module_name)
        except ImportError as e:
            raise ImportError(f"Module not found: {module_name}") from e

    workflow_module = sys.modules[module_name]

    func = workflow_module.__dict__[function_name]

    return func, workflow_module

def load_module(category, mapped_subcategory):
    # Try to load a module for this workflow
    module_name = ".".join([
        sys.modules[__name__].__package__,
        "workflows",
        category.lower(),
        mapped_subcategory,
    ])
    f_name = f"{module_name}.on_create"
    return load_function(f_name)
