class ToolError(Exception):
    pass


class AgentTool:
    """Base class for repository inspection tools."""

    name: str = ""
    description: str = ""

    def execute(self, **kwargs) -> dict:
        raise NotImplementedError

    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
        }
