"""Convert Python type hints to JSON Schema. Zero external dependencies."""

from __future__ import annotations

import inspect
import re
from dataclasses import fields as dc_fields
from dataclasses import is_dataclass
from enum import Enum
from typing import Any, Union, get_args, get_origin, get_type_hints


def python_type_to_json_schema(tp: Any) -> dict[str, Any]:
    """Convert a Python type annotation to JSON Schema."""
    if tp is str:
        return {"type": "string"}
    if tp is int:
        return {"type": "integer"}
    if tp is float:
        return {"type": "number"}
    if tp is bool:
        return {"type": "boolean"}
    if tp is type(None):
        return {"type": "null"}
    if tp is Any:
        return {}

    origin = get_origin(tp)
    args = get_args(tp)

    if origin is Union:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return python_type_to_json_schema(non_none[0])
        return {"anyOf": [python_type_to_json_schema(a) for a in non_none]}

    if origin is list or (origin is not None and issubclass(origin, list)):
        if args:
            return {"type": "array", "items": python_type_to_json_schema(args[0])}
        return {"type": "array"}

    if origin is dict or (origin is not None and issubclass(origin, dict)):
        schema: dict[str, Any] = {"type": "object"}
        if args and len(args) == 2:
            schema["additionalProperties"] = python_type_to_json_schema(args[1])
        return schema

    # typing.Literal
    if origin is getattr(__import__("typing"), "Literal", None):
        return {"type": "string", "enum": list(args)}

    if isinstance(tp, type) and issubclass(tp, Enum):
        return {"type": "string", "enum": [e.value for e in tp]}

    if is_dataclass(tp) and isinstance(tp, type):
        props = {}
        required = []
        hints = get_type_hints(tp)
        for f in dc_fields(tp):
            props[f.name] = python_type_to_json_schema(hints.get(f.name, Any))
            if f.default is f.default_factory and f.default is dc_fields.__class__:
                required.append(f.name)
        schema = {"type": "object", "properties": props}
        if required:
            schema["required"] = required
        return schema

    if tp is dict:
        return {"type": "object"}
    if tp is list:
        return {"type": "array"}

    return {"type": "string"}


def parse_docstring_args(docstring: str | None) -> dict[str, str]:
    """Extract parameter descriptions from a Google-style Args: block."""
    if not docstring:
        return {}

    descriptions: dict[str, str] = {}
    in_args = False
    current_param = ""
    current_desc = ""

    for line in docstring.split("\n"):
        stripped = line.strip()

        if stripped.lower().startswith("args:"):
            in_args = True
            continue

        if in_args:
            if stripped and not stripped.startswith(" ") and ":" not in stripped:
                if re.match(r"^[A-Z]", stripped) and not re.match(r"^\w+\s*[\(:]", stripped):
                    break

            param_match = re.match(r"(\w+)\s*(?:\([^)]*\))?\s*:\s*(.*)", stripped)
            if param_match:
                if current_param:
                    descriptions[current_param] = current_desc.strip()
                current_param = param_match.group(1)
                current_desc = param_match.group(2)
            elif current_param and stripped:
                current_desc += " " + stripped
            elif not stripped and current_param:
                descriptions[current_param] = current_desc.strip()
                current_param = ""
                current_desc = ""
                break

    if current_param:
        descriptions[current_param] = current_desc.strip()

    return descriptions


def extract_schema(fn: Any) -> dict[str, Any]:
    """Extract JSON Schema from a function's type hints and docstring."""
    try:
        hints = get_type_hints(fn)
    except (NameError, AttributeError, TypeError):
        hints = {}

    sig = inspect.signature(fn)
    doc_args = parse_docstring_args(fn.__doc__)

    properties: dict[str, Any] = {}
    required: list[str] = []

    for name, param in sig.parameters.items():
        if name in ("self", "cls"):
            continue

        tp = hints.get(name, Any)
        origin = get_origin(tp)
        args = get_args(tp)
        is_optional = origin is Union and type(None) in args

        prop = python_type_to_json_schema(tp)
        if name in doc_args:
            prop["description"] = doc_args[name]

        properties[name] = prop

        if param.default is inspect.Parameter.empty and not is_optional:
            required.append(name)

    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema
