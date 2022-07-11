class CommandError(Exception):
    def __init__(self, message, error_code):
        super().__init__(self, message)
        self.error_code = error_code
