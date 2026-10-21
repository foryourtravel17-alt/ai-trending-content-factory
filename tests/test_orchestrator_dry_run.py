from pathlib import Path

from src import orchestrator


def test_save_state_is_noop_during_dry_run(tmp_path, monkeypatch):
    state_path = tmp_path / "state.json"
    monkeypatch.setattr(orchestrator, "STATE_PATH", state_path)
    monkeypatch.setattr(orchestrator, "DRY_RUN", True)

    orchestrator.save_state({"signals": {"example": {"status": "dry_run"}}})

    assert not state_path.exists()


def test_save_state_persists_during_live_run(tmp_path, monkeypatch):
    state_path = tmp_path / "state.json"
    monkeypatch.setattr(orchestrator, "STATE_PATH", state_path)
    monkeypatch.setattr(orchestrator, "DRY_RUN", False)

    orchestrator.save_state({"signals": {"example": {"status": "approved"}}})

    assert state_path.exists()
    assert '"approved"' in state_path.read_text(encoding="utf-8")
