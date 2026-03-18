from __future__ import annotations

from typing import Dict, Optional

from actions.models import ActionProposal
from .fsm import TacticalMode


class BaseModeHandler:
    def propose(self, ctx) -> ActionProposal:
        raise NotImplementedError


# -------------------------
# MODE IMPLEMENTATIONS
# -------------------------

class SeekWeaponMode(BaseModeHandler):
    def propose(self, ctx):
        return ActionProposal.move_to_weapon(ctx)


class AggressiveAttackMode(BaseModeHandler):
    def propose(self, ctx):
        return ActionProposal.attack(ctx)


class RetreatMode(BaseModeHandler):
    def propose(self, ctx):
        return ActionProposal.retreat(ctx)


class SafeFallbackMode(BaseModeHandler):
    def propose(self, ctx):
        return ActionProposal.idle()


# -------------------------
# REGISTRY
# -------------------------

class ModeRegistry:
    def __init__(self):
        self._handlers: Dict[TacticalMode, BaseModeHandler] = {
            TacticalMode.SEEK_WEAPON: SeekWeaponMode(),
            TacticalMode.AGGRESSIVE_ATTACK: AggressiveAttackMode(),
            TacticalMode.RETREAT: RetreatMode(),
            TacticalMode.SAFE_FALLBACK: SafeFallbackMode(),
        }

    def get(self, mode: TacticalMode) -> Optional[BaseModeHandler]:
        return self._handlers.get(mode)
