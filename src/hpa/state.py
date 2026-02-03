from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class AgentState:
    category: Optional[str] = None
    subtype: Optional[str] = None
    slots: Dict[str, str] = field(default_factory=dict)

    # which slot the agent asked last turn (for simple extractor)
    last_asked_slot: Optional[str] = None

    history: List[Tuple[str, str]] = field(default_factory=list)  # (role, content)
    turn: int = 0

    def mode_key(self) -> Optional[str]:
        if not self.category or not self.subtype:
            return None
        return f"{self.category}/{self.subtype}"
