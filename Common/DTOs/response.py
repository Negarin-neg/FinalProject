class Response:
    def __init__(self, is_success: bool, message: str, data=None, error_code=None):
        self.success = is_success
        self.message = message
        self.data = data
        # Optional machine-readable marker so the UI can react to a specific
        # failure (e.g. "account does not exist" -> go to the register page)
        # instead of matching on a human-readable message.
        self.error_code = error_code
