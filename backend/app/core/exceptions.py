class RepositoryCloneError(Exception):
    """
    Raised when repository cloning fails.
    """

    def __init__(self, message: str):
        self.message = message

        super().__init__(self.message)