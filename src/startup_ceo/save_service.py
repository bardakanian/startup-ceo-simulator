"""Validated, local-only JSON persistence for simulation sessions."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from .models import Decision, DecisionRecord, GameState, MarketEvent, QuarterResult


SAVE_VERSION = 1


class SaveFileError(ValueError):
    """Raised when a save cannot be read or does not match the expected schema."""


def save_game(path: str | Path, state: GameState, seed: int) -> None:
    destination = Path(path)
    payload = {
        "version": SAVE_VERSION,
        "seed": seed,
        "state": asdict(state),
        "board_objectives": state.objective_progress,
    }
    try:
        destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        raise SaveFileError(f"The simulation could not be saved: {exc}") from exc


def load_game(path: str | Path) -> tuple[GameState, int]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SaveFileError("The selected save file does not exist.") from exc
    except (OSError, UnicodeError) as exc:
        raise SaveFileError(f"The save file could not be read: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SaveFileError("The selected file is not valid JSON.") from exc

    if not isinstance(payload, dict) or payload.get("version") != SAVE_VERSION:
        raise SaveFileError("This save file version is missing or unsupported.")
    state_data = payload.get("state")
    if not isinstance(state_data, dict):
        raise SaveFileError("The save file does not contain valid company data.")
    try:
        state = _state_from_dict(state_data)
        seed = _integer(payload.get("seed"), "seed")
        _validate_state(state)
        objectives = _mapping(payload.get("board_objectives"), "board objectives")
        if objectives != state.objective_progress:
            raise ValueError("board-objective progress does not match company data")
    except (KeyError, TypeError, ValueError) as exc:
        raise SaveFileError(f"The save file is incomplete or corrupted: {exc}") from exc
    return state, seed


def _state_from_dict(data: dict[str, Any]) -> GameState:
    history = []
    for item in _list(data.get("history"), "history"):
        event_data = _mapping(item.get("event"), "market event")
        event = MarketEvent(**event_data)
        history.append(QuarterResult(event=event, **{key: value for key, value in item.items() if key != "event"}))

    decisions = []
    for item in _list(data.get("decision_history"), "decision history"):
        decision_data = _mapping(item.get("decision"), "decision")
        decisions.append(
            DecisionRecord(
                quarter=_integer(item.get("quarter"), "decision quarter"),
                decision=Decision(**decision_data),
                event_name=str(item.get("event_name", "")),
            )
        )
    scalar_data = {key: value for key, value in data.items() if key not in {"history", "decision_history"}}
    return GameState(history=history, decision_history=decisions, **scalar_data)


def _validate_state(state: GameState) -> None:
    if not state.company_name.strip() or len(state.company_name) > 80:
        raise ValueError("invalid company name")
    if not 0 <= state.quarter <= state.max_quarters <= 40:
        raise ValueError("invalid quarter")
    if len(state.history) != state.quarter or len(state.decision_history) != state.quarter:
        raise ValueError("history does not match the current quarter")
    if state.customers < 0 or state.employees < 1:
        raise ValueError("invalid company totals")
    if not 0 <= state.product_quality <= 100 or not 0 <= state.morale <= 100:
        raise ValueError("invalid quality or morale")
    if not 0 <= state.founder_ownership <= 100:
        raise ValueError("invalid founder ownership")
    if any(record.quarter != index for index, record in enumerate(state.decision_history, 1)):
        raise ValueError("decision history is out of order")


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object")
    return value


def _list(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise TypeError(f"{label} must be a list")
    return value


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer")
    return value
