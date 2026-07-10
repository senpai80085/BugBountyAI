from dataclasses import dataclass
from datetime import datetime
from typing import Union


@dataclass(frozen=True)
class Artifact:
    """
    Structured reference to a file artifact generated during tool execution.
    Tracks remote and local paths, file size, integrity checksum, and creation time.
    """
    id: str
    type: str
    filename: str
    remote_path: str
    local_path: str = ""
    checksum: str = ""
    size: int = 0
    created_at: Union[datetime, str] = ""
