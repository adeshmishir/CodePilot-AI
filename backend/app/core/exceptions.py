class RepositoryCloneError(Exception):
    """
    Raised when repository cloning fails.
    """

    def __init__(self, message: str, detail: str | None = None):
        self.message = message
        self.detail = detail

        super().__init__(self.message)


class RepositoryIndexError(Exception):
    """
    Raised when a repository cannot be indexed or reindexed.
    """

    def __init__(self, message: str, detail: str | None = None):
        self.message = message
        self.detail = detail

        super().__init__(self.message)


class RepositoryPathError(Exception):
    """
    Raised when a repository file cannot be read from the local checkout.
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)