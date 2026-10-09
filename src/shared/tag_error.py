class TagError(Exception):
    """携带可安全展示的标签业务错误。"""

    def __init__(self, code, message, status=409, **detail):
        super().__init__(message)
        self.status = status
        self.detail = {"code": code, "message": message, **detail}
