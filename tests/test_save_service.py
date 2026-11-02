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

    def test_round_trip_preserves_board_decisions(self):
        engine = SimulationEngine(seed=2027)
        for _ in range(4):
            pending = engine.upcoming_dilemma()
            engine.advance(Decision(hires=0, dilemma_choice=pending.options[1].key if pending else ""))
        with TemporaryDirectory() as directory:
            path = Path(directory) / "session.json"
            save_game(path, engine.state, engine.seed)
            state, _ = load_game(path)
        record = state.decision_history[3]
        self.assertTrue(record.dilemma)
        self.assertEqual(record.response, engine.state.decision_history[3].response)
        self.assertEqual(record.decision.dilemma_choice, engine.state.decision_history[3].decision.dilemma_choice)

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

    def test_saves_from_before_capacity_model_still_load(self):
        engine = SimulationEngine(seed=55)
        engine.advance(Decision())
        with TemporaryDirectory() as directory:
            path = Path(directory) / "older.json"
            save_game(path, engine.state, engine.seed)
            payload = json.loads(path.read_text(encoding="utf-8"))
            del payload["state"]["market_size"]
            for item in payload["state"]["history"]:
                del item["costs"], item["support_load"], item["event"]["market_growth"]
            path.write_text(json.dumps(payload), encoding="utf-8")
            state, seed = load_game(path)
        self.assertEqual(seed, 55)
        self.assertEqual(state.quarter, 1)
        self.assertEqual(state.history[0].costs, {})

    def test_unknown_fields_are_rejected_with_message(self):
        engine = SimulationEngine()
        engine.advance(Decision())
        with TemporaryDirectory() as directory:
            path = Path(directory) / "session.json"
            save_game(path, engine.state, engine.seed)
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["state"]["surprise"] = 1
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(SaveFileError, "incomplete or corrupted"):
                load_game(path)
            del payload["state"]["surprise"]
            payload["state"]["history"][0]["costs"] = {"Payroll": "lots"}
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(SaveFileError, "cost breakdown"):
                load_game(path)
            payload["state"]["history"][0]["costs"] = {}
            payload["state"]["market_size"] = "large"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(SaveFileError, "incomplete or corrupted"):
                load_game(path)

    def test_corrupted_numbers_and_decisions_are_rejected_not_crashed_on(self):
        engine = SimulationEngine(seed=7)
        engine.advance(Decision())
        corruptions = (
            lambda state: state["history"][0].update(revenue="lots"),
            lambda state: state["history"][0].update(support_load=None),
            lambda state: state["history"][0]["event"].update(demand_multiplier="big"),
            lambda state: state.update(cash=float("nan")),
            lambda state: state.update(bankrupt="no"),
            lambda state: state["decision_history"][0]["decision"].update(price=5),
            lambda state: state["decision_history"][0]["decision"].update(hires="x"),
            lambda state: state["decision_history"][0].update(response=7),
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "session.json"
            for corrupt in corruptions:
                save_game(path, engine.state, engine.seed)
                payload = json.loads(path.read_text(encoding="utf-8"))
                corrupt(payload["state"])
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaisesRegex(SaveFileError, "incomplete or corrupted"):
                    load_game(path)


if __name__ == "__main__":
    unittest.main()
