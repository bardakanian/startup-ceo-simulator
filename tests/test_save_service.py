import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from startup_ceo.engine import Decision, SimulationEngine
from startup_ceo.save_service import SaveFileError, load_game, save_game


class SaveServiceTests(unittest.TestCase):
    def test_round_trip_preserves_state_histories_and_seed(self):
        engine = SimulationEngine(seed=314, company_name="Signal Works")
        engine.advance(Decision(price=92, marketing=120_000, product=70_000, hires=0, raise_funding=True))
        with TemporaryDirectory() as directory:
            path = Path(directory) / "session.json"
            save_game(path, engine.state, engine.seed)
            state, seed = load_game(path)
        self.assertEqual(seed, 314)
        self.assertEqual(state.company_name, "Signal Works")
        self.assertEqual(state.quarter, 1)
        self.assertEqual(state.history[0].event.name, engine.state.history[0].event.name)
        self.assertEqual(state.decision_history[0].decision.price, 92)
        self.assertEqual(state.objective_progress, engine.state.objective_progress)

    def test_corrupted_json_has_helpful_error(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "broken.json"
            path.write_text("{not-json", encoding="utf-8")
            with self.assertRaisesRegex(SaveFileError, "not valid JSON"):
                load_game(path)

    def test_inconsistent_history_is_rejected(self):
        engine = SimulationEngine()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "session.json"
            save_game(path, engine.state, engine.seed)
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["state"]["quarter"] = 2
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(SaveFileError, "history"):
                load_game(path)


if __name__ == "__main__":
    unittest.main()
