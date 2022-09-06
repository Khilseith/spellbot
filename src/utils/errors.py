class BadRoll(Exception):
    def __init__(self, message, offendingAtribute: dict):
        self.message = message
        self.offendingAtribute = offendingAtribute
        super().__init__(message)
