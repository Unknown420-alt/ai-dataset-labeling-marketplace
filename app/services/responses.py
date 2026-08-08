from typing import Any, Optional


def ok(data: Any = None, message: str = "OK") -> dict:
    return {"success": True, "data": data, "message": message}


def fail(message: str, data: Any = None) -> dict:
    return {"success": False, "data": data, "message": message}
