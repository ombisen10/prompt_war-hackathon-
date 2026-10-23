"""Pure-Python standard-library Pydantic v2 compatible layer."""
from __future__ import annotations
import inspect
import json
import re
from enum import Enum
from typing import Any, Callable, Optional, get_type_hints, get_origin, get_args


class ValidationError(ValueError):
    def __init__(self, errors: list[dict]):
        self._errors = errors
        super().__init__(str(errors))

    def errors(self) -> list[dict]:
        return self._errors


class FieldInfo:
    def __init__(
        self,
        default: Any = ...,
        default_factory: Optional[Callable[[], Any]] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        ge: Optional[float] = None,
        le: Optional[float] = None,
        pattern: Optional[str] = None,
        **kwargs: Any,
    ):
        self.default = default
        self.default_factory = default_factory
        self.min_length = min_length
        self.max_length = max_length
        self.ge = ge
        self.le = le
        self.pattern = pattern
        self.extra = kwargs


def Field(
    default: Any = ...,
    *,
    default_factory: Optional[Callable[[], Any]] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    ge: Optional[float] = None,
    le: Optional[float] = None,
    pattern: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    return FieldInfo(
        default=default,
        default_factory=default_factory,
        min_length=min_length,
        max_length=max_length,
        ge=ge,
        le=le,
        pattern=pattern,
        **kwargs,
    )


def field_validator(*fields: str, mode: str = "after") -> Callable:
    def decorator(fn: Callable) -> Callable:
        fn.__field_validator_fields__ = fields
        fn.__field_validator_mode__ = mode
        return fn
    return decorator


def _dump_value(val: Any) -> Any:
    if isinstance(val, BaseModel):
        return val.model_dump()
    if isinstance(val, Enum):
        return val.value
    if isinstance(val, list):
        return [_dump_value(v) for v in val]
    if isinstance(val, dict):
        return {k: _dump_value(v) for k, v in val.items()}
    return val


class BaseModel:
    def __init__(self, **data: Any):
        cls = self.__class__
        type_hints = {}
        try:
            type_hints = get_type_hints(cls)
        except Exception:
            type_hints = getattr(cls, "__annotations__", {})

        # Collect field info from class hierarchy
        field_infos: dict[str, FieldInfo] = {}
        for base in reversed(cls.__mro__):
            for k, v in getattr(base, "__dict__", {}).items():
                if isinstance(v, FieldInfo):
                    field_infos[k] = v

        # Collect validators from class hierarchy
        validators: dict[str, list[tuple[Any, Callable]]] = {}
        for base in cls.__mro__:
            for attr_name, raw_attr in getattr(base, "__dict__", {}).items():
                func = raw_attr
                if isinstance(raw_attr, (classmethod, staticmethod)):
                    func = raw_attr.__func__
                fields = getattr(raw_attr, "__field_validator_fields__", None) or getattr(func, "__field_validator_fields__", None)
                if fields:
                    for target_field in fields:
                        validators.setdefault(target_field, []).append((raw_attr, func))

        # Process each defined attribute or data key
        all_keys = set(type_hints.keys()) | set(field_infos.keys()) | set(data.keys())
        errors = []

        for key in all_keys:
            if key.startswith("_"):
                continue
            f_info = field_infos.get(key)
            expected_type = type_hints.get(key)

            if key in data:
                val = data[key]
            elif f_info is not None:
                if f_info.default_factory is not None:
                    val = f_info.default_factory()
                elif f_info.default is not ...:
                    val = f_info.default
                else:
                    errors.append({"loc": (key,), "msg": "Field required", "type": "missing"})
                    continue
            elif hasattr(cls, key):
                default_val = getattr(cls, key)
                if not callable(default_val):
                    val = default_val
                else:
                    val = None
            else:
                val = None

            # Type conversion / coercion
            if val is not None and expected_type is not None:
                try:
                    val = self._coerce_type(val, expected_type)
                except Exception as e:
                    errors.append({"loc": (key,), "msg": str(e), "type": "type_error"})
                    continue

            # Custom validators (run first to allow transforms like strip)
            if key in validators:
                for raw_attr, func in validators[key]:
                    try:
                        sig = inspect.signature(func)
                        if len(sig.parameters) == 1:
                            val = func(val)
                        else:
                            val = func(cls, val)
                    except Exception as exc:
                        errors.append({"loc": (key,), "msg": str(exc), "type": "value_error"})

            # Field constraints validation
            if f_info is not None and val is not None:
                if f_info.min_length is not None and len(val) < f_info.min_length:
                    errors.append({"loc": (key,), "msg": f"Length must be >= {f_info.min_length}", "type": "value_error"})
                if f_info.max_length is not None and len(val) > f_info.max_length:
                    errors.append({"loc": (key,), "msg": f"Length must be <= {f_info.max_length}", "type": "value_error"})
                if f_info.ge is not None and val < f_info.ge:
                    errors.append({"loc": (key,), "msg": f"Value must be >= {f_info.ge}", "type": "value_error"})
                if f_info.le is not None and val > f_info.le:
                    errors.append({"loc": (key,), "msg": f"Value must be <= {f_info.le}", "type": "value_error"})
                if f_info.pattern is not None and isinstance(val, str) and not re.search(f_info.pattern, val):
                    errors.append({"loc": (key,), "msg": f"String does not match pattern {f_info.pattern}", "type": "value_error"})

            setattr(self, key, val)

        if errors:
            raise ValidationError(errors)

    def _coerce_type(self, val: Any, expected_type: Any) -> Any:
        origin = get_origin(expected_type)
        args = get_args(expected_type)

        # Optional[T] / Union[T, None]
        if origin is not None and origin is type(None):
            return val
        if origin is not None and hasattr(origin, "__name__") and origin.__name__ == "Union":
            non_none = [a for a in args if a is not type(None)]
            if len(non_none) == 1:
                if val is None:
                    return None
                return self._coerce_type(val, non_none[0])

        if isinstance(expected_type, type):
            if issubclass(expected_type, Enum) and not isinstance(val, Enum):
                return expected_type(val)
            if issubclass(expected_type, BaseModel) and isinstance(val, dict):
                return expected_type(**val)

        if origin is list and args:
            item_type = args[0]
            if isinstance(val, list):
                return [self._coerce_type(item, item_type) for item in val]

        return val

    def model_dump(self, mode: str = "python") -> dict[str, Any]:
        result = {}
        for k, v in self.__dict__.items():
            if not k.startswith("_"):
                result[k] = _dump_value(v)
        return result

    def model_dump_json(self, **kwargs: Any) -> str:
        return json.dumps(self.model_dump(), default=str)

    @classmethod
    def model_validate(cls, obj: Any) -> Any:
        if isinstance(obj, cls):
            return obj
        if isinstance(obj, dict):
            return cls(**obj)
        raise ValueError(f"Cannot validate object of type {type(obj)} into {cls.__name__}")

    @classmethod
    def model_validate_json(cls, json_str: str) -> Any:
        data = json.loads(json_str)
        return cls.model_validate(data)

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.model_dump().items())
        return f"{self.__class__.__name__}({attrs})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, BaseModel):
            return self.model_dump() == other.model_dump()
        return False
