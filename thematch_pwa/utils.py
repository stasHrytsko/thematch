import logging
from flask import make_response

logging.basicConfig(level=logging.INFO)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def add_cors(response, methods: str = "GET, POST, OPTIONS"):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = methods
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


def cors_preflight(methods: str = "GET, POST, OPTIONS"):
    return add_cors(make_response("", 200), methods)
