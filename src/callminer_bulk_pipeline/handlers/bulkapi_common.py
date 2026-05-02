from typing import Optional


class ValidationError(ValueError):
    pass


class ApiError(RuntimeError):
    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class DuplicateJobMatchError(RuntimeError):
    pass
