import unittest

from startup_ceo.engine import Decision, SimulationEngine


class SimulationEngineTests(unittest.TestCase):
    def test_default_decision_advances_one_quarter(self):
        engine = SimulationEngine(seed=10)
        result = engine.advance(Decision())
        self.assertEqual(result.quarter, 1)
        self.assertEqual(len(engine.state.history), 1)
        self.assertGreater(result.revenue, 0)
        self.assertGreater(engine.state.customers, 0)

    def test_simulation_is_deterministic_for_same_seed(self):
        first = SimulationEngine(seed=42)
        second = SimulationEngine(seed=42)
        decision = Decision(price=89, marketing=110_000, product=95_000, hires=2)
        a = first.advance(decision)
        b = second.advance(decision)
        self.assertEqual(a.event.name, b.event.name)
        self.assertAlmostEqual(a.revenue, b.revenue)
        self.assertEqual(a.customers, b.customers)

    def test_funding_increases_cash_and_dilutes_founder(self):
        baseline = SimulationEngine(seed=5)
        funded = SimulationEngine(seed=5)
        baseline.advance(Decision())
        funded.advance(Decision(raise_funding=True))
        self.assertGreater(funded.state.cash, baseline.state.cash)
        self.assertLess(funded.state.founder_ownership, 100)
        self.assertEqual(funded.state.funding_rounds, 1)

    def test_hiring_increases_headcount(self):
        engine = SimulationEngine()
        engine.advance(Decision(hires=3))
        self.assertEqual(engine.state.employees, 11)

    def test_invalid_decisions_are_rejected(self):
        engine = SimulationEngine()
        with self.assertRaises(ValueError):
            engine.advance(Decision(price=10))
        with self.assertRaises(ValueError):
            engine.advance(Decision(hires=1, layoffs=1))

    def test_game_ends_after_twelve_quarters(self):
        engine = SimulationEngine(seed=100)
        for _ in range(12):
            engine.advance(Decision(marketing=20_000, product=20_000))
            if engine.state.bankrupt:
                break
        self.assertTrue(engine.state.complete)
        with self.assertRaises(RuntimeError):
            engine.advance(Decision())

    def test_score_is_bounded(self):
        engine = SimulationEngine()
        self.assertGreaterEqual(engine.state.score(), 0)
        self.assertLessEqual(engine.state.score(), 100)

    def test_financial_calculation_reconciles_operating_profit(self):
        engine = SimulationEngine(seed=3)
        decision = Decision(price=89, marketing=100_000, product=75_000, hires=0)
        result = engine.advance(decision)
        event_variable_cost = result.revenue * 0.19 * result.event.cost_multiplier
        expected_costs = event_variable_cost + 8 * 27_000 + 75_000 + 100_000 + 75_000
        self.assertAlmostEqual(result.operating_profit, result.revenue - expected_costs)
        self.assertAlmostEqual(result.gross_profit, result.revenue - event_variable_cost)

    def test_preview_does_not_change_state_or_random_event(self):
        engine = SimulationEngine(seed=77)
        event = engine.upcoming_event()
        preview = engine.preview_effects(Decision(hires=0))
        self.assertEqual(engine.state.quarter, 0)
        self.assertEqual(engine.upcoming_event(), event)
        self.assertEqual(set(preview), {"Customer growth", "Operating margin", "Product quality", "Runway resilience", "Founder control"})

    def test_decision_and_event_histories_are_recorded(self):
        engine = SimulationEngine(seed=9)
        result = engine.advance(Decision(price=99, hires=0))
        record = engine.state.decision_history[0]
        self.assertEqual(record.quarter, 1)
        self.assertEqual(record.decision.price, 99)
        self.assertEqual(record.event_name, result.event.name)

    def test_board_objectives_report_current_progress(self):
        engine = SimulationEngine()
        self.assertTrue(engine.state.objective_progress["Finish with positive cash"])
        self.assertFalse(engine.state.objective_progress["Reach at least 3,000 customers"])
        self.assertTrue(engine.state.objective_progress["Retain at least 80% founder ownership"])


if __name__ == "__main__":
    unittest.main()
