from flask import jsonify

def success_response(data=None, message=None, status_code=200):
    payload = {
        "ok": True,
        "data": data or {},
    }
    if message:
        payload["message"] = message
    return jsonify(payload), status_code

def error_response(error, message, status_code=400, details=None):
    payload = {
        "ok": False,
        "error": error,
        "message": message,
    }
    if details is not None:
        payload["details"] = details
    return jsonify(payload), status_code
