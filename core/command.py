from dataclasses import dataclass, field
import shlex


@dataclass
class Command:
    """
    Structured representation of a command to be executed.
    Avoids raw string concatenation to mitigate shell injection risks.
    """
    executable: str
    args: list[str] = field(default_factory=list)

    def shell_escape(self) -> str:
        """
        Safely formats the executable and its arguments into a shell-escaped string.
        """
        return " ".join(shlex.quote(arg) for arg in [self.executable] + self.args)
