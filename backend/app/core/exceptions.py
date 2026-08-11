class RepositoryCloneError(Exception):
    """
    Raised when repository cloning fails.
    """

    def __init__(self, message: str):
        self.message = message

        super().__init__(self.message)


class RepositoryIndexError(Exception):
    """
    Raised when a repository cannot be indexed or reindexed.
    """

    def __init__(self, message: str):
        self.message = message

        super().__init__(self.message)