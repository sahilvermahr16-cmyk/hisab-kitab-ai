from enum import Enum
from typing import get_args, get_origin

from pydantic import BaseModel


def _format_type(annotation) -> str:
    origin = get_origin(annotation)
    if origin is None:
        if hasattr(annotation, "__name__"):
            return annotation.__name__
        return str(annotation).replace("typing.", "")
    if origin is list:
        args = get_args(annotation)
        return f"List[{_format_type(args[0])}]"
    if origin is tuple:
        args = get_args(annotation)
        return " | ".join(_format_type(arg) for arg in args)
    args = get_args(annotation)
    if args:
        return " | ".join(_format_type(arg) for arg in args)
    return str(annotation).replace("typing.", "")


def format_schema(schema: type[BaseModel]) -> str:
    """
    Convert a Pydantic model into a compact human-readable schema.
    """
    lines = []
    for field_name, field in schema.model_fields.items():
        field_type = _format_type(field.annotation)
        lines.append(f"{field_name}: {field_type}")
        if field.description:
            lines.append(f"    {field.description}")
        annotation = field.annotation
        if isinstance(annotation, type) and issubclass(annotation, Enum):
            values = ", ".join(member.value for member in annotation)
            lines.append(f"    Allowed Values: {values}")
        lines.append("")
    return "\n".join(lines).strip()

