"""
Expression Parser for Observed Variables

Parse and evaluate observed equations like "y ~ k*x" where k is a parameter.
"""
import re
import numpy as np
from typing import Dict, List, Tuple, Any


class ObservedExpressionEvaluator:
    """
    Evaluate observed variable expressions by parsing and computing them.

    Handles expressions like:
    - "k*x" where k is parameter, x is state
    - "2*x + 3*v"
    - "k*(x + v)"
    - More complex expressions
    """

    def __init__(self, expression: str, state_names: List[str], param_dict: Dict[str, float]):
        """
        Initialize evaluator.

        Args:
            expression: RHS expression string (e.g., "k*x", "2*x+v")
            state_names: List of available state variable names
            param_dict: Dictionary of parameter values
        """
        self.expression = expression.strip()
        self.state_names = state_names
        self.param_dict = param_dict
        self.variables = self._extract_variables()

    def _extract_variables(self) -> List[str]:
        """Extract variable names from expression."""
        # Find all potential variable names (alphanumeric + underscore)
        # Match pattern: word boundaries around identifiers
        pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'
        matches = re.findall(pattern, self.expression)

        # Filter out Python keywords and math functions
        keywords = {'and', 'or', 'not', 'in', 'is', 'if', 'else',
                   'sin', 'cos', 'tan', 'exp', 'log', 'sqrt', 'abs'}

        variables = []
        for match in matches:
            if match not in keywords:
                variables.append(match)

        return list(set(variables))  # Remove duplicates

    def evaluate(self, state_values: Dict[str, np.ndarray]) -> np.ndarray:
        """
        Evaluate expression for all time points.

        Args:
            state_values: Dictionary mapping variable names to their time series
                         e.g., {"x": array([...]), "v": array([...])}

        Returns:
            Evaluated expression as numpy array
        """
        # Build namespace for evaluation
        namespace = {}

        # Add numpy functions
        namespace.update({
            'sin': np.sin,
            'cos': np.cos,
            'tan': np.tan,
            'exp': np.exp,
            'log': np.log,
            'sqrt': np.sqrt,
            'abs': np.abs,
            'pi': np.pi,
            'e': np.e
        })

        # Replace Julia operators with Python operators
        expr = self._convert_julia_to_python(self.expression)

        # Replace dotted names with safe names and build namespace
        # e.g., "plant.k" -> "_plant_k"
        safe_expr = expr
        name_mapping = {}

        # First pass: collect all dotted names
        dotted_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_.]*)\b'
        for match in re.finditer(dotted_pattern, expr):
            dotted_name = match.group(1)
            safe_name = dotted_name.replace('.', '_')
            name_mapping[dotted_name] = safe_name

        # Replace in expression (longest first to avoid partial replacements)
        for dotted_name in sorted(name_mapping.keys(), key=len, reverse=True):
            safe_name = name_mapping[dotted_name]
            safe_expr = safe_expr.replace(dotted_name, safe_name)

            # Add to namespace
            if dotted_name in self.param_dict:
                namespace[safe_name] = self.param_dict[dotted_name]
            elif dotted_name in state_values:
                namespace[safe_name] = state_values[dotted_name]
            else:
                raise ValueError(f"Variable '{dotted_name}' not found in state_values or param_dict")

        try:
            # Evaluate the expression
            result = eval(safe_expr, {"__builtins__": {}}, namespace)

            # Ensure result is numpy array
            if not isinstance(result, np.ndarray):
                result = np.array(result)

            return result
        except Exception as e:
            raise ValueError(
                f"Failed to evaluate expression '{self.expression}': {e}\n"
                f"Safe expression: '{safe_expr}'\n"
                f"Available variables: {list(state_values.keys())}\n"
                f"Parameters: {list(self.param_dict.keys())}"
            )

    def _convert_julia_to_python(self, expr: str) -> str:
        """Convert Julia syntax to Python syntax."""
        # Replace ^ with **
        expr = expr.replace('^', '**')

        # Handle other Julia-specific syntax if needed
        # ...

        return expr

    def get_required_variables(self) -> Tuple[List[str], List[str]]:
        """
        Get lists of required state variables and parameters.

        Returns:
            (state_vars, params): Lists of required state variables and parameters
        """
        state_vars = []
        params = []

        for var in self.variables:
            if var in self.state_names:
                state_vars.append(var)
            elif var in self.param_dict:
                params.append(var)
            else:
                # Unknown variable - could be a state we haven't found yet
                state_vars.append(var)

        return state_vars, params


def parse_observed_equation(equation_str: str) -> Tuple[str, str]:
    """
    Parse observed equation string to extract LHS and RHS.

    Args:
        equation_str: String like "plant.y ~ plant.k*plant.x"

    Returns:
        (lhs, rhs): Tuple of left and right hand side strings
    """
    if '~' not in equation_str:
        raise ValueError(f"Invalid equation format: {equation_str}")

    parts = equation_str.split('~', 1)
    lhs = parts[0].strip()
    rhs = parts[1].strip()

    return lhs, rhs


def extract_module_prefix(variable_name: str) -> Tuple[str, str]:
    """
    Extract module prefix from variable name.

    Args:
        variable_name: String like "plant.k" or "plant.x"

    Returns:
        (module, var): Tuple of module name and variable name
    """
    if '.' in variable_name:
        parts = variable_name.split('.', 1)
        return parts[0], parts[1]
    else:
        return '', variable_name


# Example usage:
if __name__ == "__main__":
    # Test the evaluator
    state_names = ["plant.x", "plant.v"]
    params = {"plant.k": 2.0}

    evaluator = ObservedExpressionEvaluator("plant.k*plant.x", state_names, params)

    # Mock state values
    t = np.linspace(0, 1, 10)
    state_values = {
        "plant.x": np.sin(t),
        "plant.v": np.cos(t)
    }

    result = evaluator.evaluate(state_values)
    print(f"Result: {result}")
    print(f"Expected (2*sin(t)): {2*np.sin(t)}")
    print(f"Match: {np.allclose(result, 2*np.sin(t))}")
