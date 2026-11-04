from dataclasses import replace
import unittest

from startup_ceo.dilemmas import DILEMMAS, dilemma_schedule
from startup_ceo.engine import Decision, SimulationEngine
from startup_ceo.formatting import money


def respond(engine, decision, option=0):
    """Answer any pending board dilemma (the first option by default; -1 is always the status quo)."""
    dilemma = engine.upcoming_dilemma()
    return replace(decision, dilemma_choice=dilemma.options[option].key) if dilemma else decision


def dilemma(key):
    return next(item for item in DILEMMAS if item.key == key)


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
            engine.advance(respond(engine, Decision(marketing=20_000, product=20_000)))
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
        self.assertEqual(
            set(preview),
            {"Customer growth", "Operating margin", "Product quality", "Service capacity", "Runway resilience", "Founder control"},
        )

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

    def test_cost_breakdown_reconciles_with_operating_profit(self):
        engine = SimulationEngine(seed=21)
        result = engine.advance(Decision(price=95, marketing=140_000, product=60_000, hires=2))
        self.assertAlmostEqual(result.revenue - sum(result.costs.values()), result.operating_profit)
        self.assertEqual(result.costs["Hiring and severance"], 16_000)

    def test_customers_beyond_support_capacity_raise_churn(self):
        staffed = SimulationEngine(seed=8)
        stretched = SimulationEngine(seed=8)
        for engine, employees in ((staffed, 14), (stretched, 6)):
            engine.state.customers = 3_000
            engine.state.employees = employees
        staffed_result = staffed.advance(Decision(hires=0))
        stretched_result = stretched.advance(Decision(hires=0))
        self.assertGreater(stretched_result.support_load, 1)
        self.assertGreater(stretched_result.churned_customers, staffed_result.churned_customers)
        self.assertLess(stretched.state.morale, staffed.state.morale)

    def test_market_saturation_reduces_acquisition(self):
        early = SimulationEngine(seed=4)
        mature = SimulationEngine(seed=4)
        for engine, customers in ((early, 1_000), (mature, 15_000)):
            engine.state.customers = customers
            engine.state.employees = 80
        decision = Decision(marketing=150_000, hires=0)
        self.assertGreater(early.advance(decision).new_customers, mature.advance(decision).new_customers)

    def test_product_quality_softens_price_sensitivity(self):
        strong = SimulationEngine(seed=6)
        weak = SimulationEngine(seed=6)
        strong.state.product_quality = 90
        weak.state.product_quality = 40
        decision = Decision(price=129, hires=0)
        strong_result = strong.advance(decision)
        weak_result = weak.advance(decision)
        self.assertGreater(strong_result.new_customers, weak_result.new_customers)
        self.assertLess(strong_result.churned_customers, weak_result.churned_customers)

    def test_repeated_funding_lowers_score_through_founder_stake(self):
        disciplined = SimulationEngine(seed=11)
        serial_raiser = SimulationEngine(seed=11)
        for _ in range(12):
            disciplined.advance(respond(disciplined, Decision(price=99, marketing=150_000, product=60_000, hires=1)))
            serial_raiser.advance(respond(serial_raiser, Decision(price=99, marketing=150_000, product=60_000, hires=1, raise_funding=True)))
        self.assertGreater(serial_raiser.state.cash, disciplined.state.cash)
        self.assertLess(serial_raiser.state.founder_stake, disciplined.state.founder_stake)
        self.assertLess(serial_raiser.state.score(), disciplined.state.score())

    def test_score_breakdown_sums_to_score(self):
        engine = SimulationEngine(seed=13)
        engine.advance(Decision())
        breakdown = engine.state.score_breakdown()
        self.assertEqual(round(sum(breakdown.values())), engine.state.score())
        self.assertIn("Founder stake value", breakdown)

    def test_runway_is_unlimited_when_plan_generates_cash(self):
        engine = SimulationEngine()
        engine.state.customers = 4_000
        lean = Decision(marketing=0, product=0, hires=0)
        self.assertLess(engine.preview_net_burn(lean), 0)
        self.assertEqual(engine.preview_runway_months(lean), float("inf"))

    def test_reset_can_change_scenario_seed(self):
        engine = SimulationEngine(seed=1)
        engine.advance(Decision())
        engine.reset("Second Team", seed=99)
        self.assertEqual(engine.seed, 99)
        self.assertEqual(engine.state.quarter, 0)
        self.assertEqual(engine.state.company_name, "Second Team")

    def test_dilemma_schedule_is_seeded_and_spread_across_the_game(self):
        schedule = dilemma_schedule(2027)
        self.assertEqual(schedule, dilemma_schedule(2027))
        self.assertEqual(len(schedule), 4)
        self.assertTrue(all(2 <= quarter <= 12 for quarter in schedule))
        self.assertEqual(len({item.key for item in schedule.values()}), 4)
        self.assertNotEqual(schedule, dilemma_schedule(2028))

    def test_dilemmas_do_not_change_market_events(self):
        engine = SimulationEngine(seed=2027)
        events = []
        for _ in range(12):
            events.append(engine.upcoming_event().name)
            engine.advance(respond(engine, Decision(hires=0)))
        self.assertEqual([result.event.name for result in engine.state.history], events)

    def test_pending_dilemma_requires_a_response(self):
        engine = SimulationEngine()
        engine.upcoming_dilemma = lambda: dilemma("acquihire")
        with self.assertRaisesRegex(ValueError, "Acqui-hire"):
            engine.advance(Decision())
        with self.assertRaisesRegex(ValueError, "Acqui-hire"):
            engine.advance(Decision(dilemma_choice="not-an-option"))
        self.assertEqual(engine.state.quarter, 0)
        self.assertEqual(engine.state.cash, 1_200_000)

    def test_acquisition_adds_team_and_customers(self):
        by_cash = SimulationEngine(seed=3)
        by_stock = SimulationEngine(seed=3)
        for engine in (by_cash, by_stock):
            engine.upcoming_dilemma = lambda: dilemma("acquihire")
        by_cash.advance(Decision(hires=0, dilemma_choice="cash"))
        by_stock.advance(Decision(hires=0, dilemma_choice="stock"))
        self.assertEqual(by_cash.state.employees, 12)
        self.assertEqual(by_cash.state.founder_ownership, 100)
        self.assertAlmostEqual(by_stock.state.founder_ownership, 94)
        self.assertGreater(by_stock.state.cash, by_cash.state.cash)
        record = by_cash.state.decision_history[0]
        self.assertEqual((record.dilemma, record.response), ("Acqui-hire opportunity", "Acquire it for $450K cash"))

    def test_unaffordable_option_is_rejected(self):
        engine = SimulationEngine()
        engine.state.cash = 200_000
        engine.upcoming_dilemma = lambda: dilemma("acquihire")
        cash_option = dilemma("acquihire").option("cash")
        self.assertIn("Not enough cash", engine.check_dilemma_option(cash_option))
        with self.assertRaisesRegex(ValueError, "Not enough cash"):
            engine.advance(Decision(dilemma_choice="cash"))

    def test_dilemma_expense_reconciles_and_shapes_outcome(self):
        honest = SimulationEngine(seed=5)
        quiet = SimulationEngine(seed=5)
        for engine in (honest, quiet):
            engine.upcoming_dilemma = lambda: dilemma("security_flaw")
        honest_result = honest.advance(Decision(hires=0, dilemma_choice="disclose"))
        quiet_result = quiet.advance(Decision(hires=0, dilemma_choice="quiet"))
        self.assertEqual(honest_result.costs["Board decision"], 90_000)
        self.assertAlmostEqual(honest_result.revenue - sum(honest_result.costs.values()), honest_result.operating_profit)
        self.assertGreater(quiet_result.churned_customers, honest_result.churned_customers)
        self.assertGreater(honest.state.brand, quiet.state.brand)
        self.assertIn("Security vulnerability reported", honest_result.narrative)

    def test_preview_reflects_chosen_response(self):
        engine = SimulationEngine()
        engine.upcoming_dilemma = lambda: dilemma("key_engineer")
        self.assertEqual(engine.preview_effects(Decision(dilemma_choice="equity"))["Founder control"], "Under pressure")
        self.assertEqual(engine.preview_effects(Decision(dilemma_choice="let_go"))["Founder control"], "Stable")
        self.assertGreater(
            engine.preview_net_burn(Decision(dilemma_choice="team_bonus")),
            engine.preview_net_burn(Decision(dilemma_choice="let_go")),
        )

    def test_layoffs_cannot_go_below_minimum_team(self):
        engine = SimulationEngine(seed=1)
        engine.advance(Decision(hires=0, layoffs=5))
        self.assertEqual(engine.state.employees, 3)
        cash, morale = engine.state.cash, engine.state.morale
        with self.assertRaisesRegex(ValueError, "At least 3 employees"):
            engine.advance(Decision(hires=0, layoffs=2))
        self.assertEqual((engine.state.quarter, engine.state.cash, engine.state.morale), (1, cash, morale))

    def test_runway_preview_counts_the_funding_round(self):
        engine = SimulationEngine()
        engine.state.cash = 300_000
        raised, _ = engine.funding_offer()
        without = engine.preview_runway_months(Decision(hires=0))
        with_round = engine.preview_runway_months(Decision(hires=0, raise_funding=True))
        self.assertAlmostEqual(with_round / without, (300_000 + raised) / 300_000)
        self.assertEqual(engine.preview_effects(Decision(hires=0))["Runway resilience"], "Under pressure")
        self.assertNotEqual(engine.preview_effects(Decision(hires=0, raise_funding=True))["Runway resilience"], "Under pressure")

    def test_funding_round_can_pay_for_a_cash_acquisition(self):
        engine = SimulationEngine()
        engine.state.cash = 300_000
        engine.upcoming_dilemma = lambda: dilemma("acquihire")
        option = dilemma("acquihire").option("cash")
        self.assertIsNotNone(engine.check_dilemma_option(option))
        self.assertIsNone(engine.check_dilemma_option(option, raising_funding=True))
        engine.advance(Decision(hires=0, raise_funding=True, dilemma_choice="cash"))
        self.assertEqual(engine.state.employees, 12)
        self.assertEqual(engine.state.decision_history[0].acquired_employees, 4)

    def test_money_switches_units_after_rounding(self):
        self.assertEqual(money(999_600), "$1.00M")
        self.assertEqual(money(-999_700), "-$1.00M")
        self.assertEqual(money(999_400), "$999K")
        self.assertEqual(money(999.7), "$1K")
        self.assertEqual(money(950), "$950")

    def test_dilemma_schedule_is_cached(self):
        self.assertIs(dilemma_schedule(31), dilemma_schedule(31))

    def test_projection_matches_the_engine_except_for_demand_variation(self):
        for seed in range(1, 40):
            engine = SimulationEngine(seed=seed)
            engine.state.customers = 2_500
            decision = Decision(price=99, marketing=150_000, product=60_000, hires=1)
            projected_burn = engine.preview_net_burn(decision)
            result = engine.advance(decision)
            # Only the +/-6% demand variation separates the estimate from the result.
            self.assertAlmostEqual(-projected_burn, result.operating_profit, delta=result.revenue * 0.02)

    def test_preview_uses_announced_market_event(self):
        seeds = {SimulationEngine(seed=seed).upcoming_event().name: seed for seed in range(1, 200)}
        slowdown = SimulationEngine(seed=seeds["Economic slowdown"])
        boom = SimulationEngine(seed=seeds["Enterprise spotlight"])
        decision = Decision(marketing=150_000, hires=0)
        self.assertLess(slowdown._project(decision)[0].new_customers, boom._project(decision)[0].new_customers)

    def test_preview_leaves_state_untouched(self):
        engine = SimulationEngine(seed=21)
        engine.advance(Decision())
        before = (engine.state.cash, engine.state.customers, engine.state.market_size, engine.state.product_quality,
                  len(engine.state.history), engine.state.quarter)
        engine.preview_effects(Decision(price=129, marketing=250_000, hires=3, raise_funding=True))
        engine.preview_runway_months(Decision(raise_funding=True))
        after = (engine.state.cash, engine.state.customers, engine.state.market_size, engine.state.product_quality,
                 len(engine.state.history), engine.state.quarter)
        self.assertEqual(before, after)

    def test_growth_estimate_matches_actual_growth_band(self):
        import random
        rnd = random.Random(3)
        hits = total = 0
        for _ in range(300):
            engine = SimulationEngine(seed=rnd.randrange(1, 10**6))
            engine.state.customers = rnd.randrange(500, 9_000)
            engine.state.employees = rnd.randrange(3, 30)
            decision = Decision(rnd.randrange(39, 150), rnd.randrange(0, 251) * 1000, rnd.randrange(0, 201) * 1000, 0)
            label = engine.preview_effects(decision)["Customer growth"]
            opening = engine.state.customers
            engine.advance(decision)
            growth = (engine.state.customers - opening) / opening
            actual = "Low" if growth < 0.03 else "High" if growth > 0.10 else "Moderate"
            hits += label == actual
            total += 1
        self.assertGreater(hits / total, 0.95)

    def test_acquired_customers_are_reported_separately(self):
        engine = SimulationEngine(seed=3)
        engine.upcoming_dilemma = lambda: dilemma("acquihire")
        result = engine.advance(Decision(hires=0, dilemma_choice="stock"))
        self.assertEqual(result.acquired_customers, 300)
        self.assertEqual(800 + result.growth, engine.state.customers)

    def _play_to_final_quarter(self, seed):
        engine = SimulationEngine(seed=seed)
        for _ in range(11):
            decision = respond(engine, Decision(price=99, marketing=150_000, product=60_000, hires=1), -1)
            decision.raise_funding = engine.preview_runway_months(decision) < 6 and not engine.state.funding_rounds
            engine.advance(decision)
        self.assertFalse(engine.state.complete)
        return engine

    def test_final_quarter_price_hike_does_not_pay(self):
        from copy import deepcopy
        gains = []
        for seed in range(30, 40):
            steady = self._play_to_final_quarter(seed)
            hiked = deepcopy(steady)
            steady.advance(respond(steady, Decision(price=99, marketing=150_000, product=60_000, hires=1), -1))
            hiked.advance(respond(hiked, Decision(price=149, marketing=150_000, product=60_000, hires=1), -1))
            gains.append(hiked.state.score() - steady.state.score())
        self.assertLess(sum(gains) / len(gains), 0)

    def test_price_increase_drives_existing_customers_away(self):
        held = SimulationEngine(seed=2)
        raised = SimulationEngine(seed=2)
        for engine in (held, raised):
            engine.state.current_price = 99
            engine.state.product_quality = 70
        held_result = held.advance(Decision(price=99, hires=0))
        raised_result = raised.advance(Decision(price=119, hires=0))
        self.assertGreater(raised_result.churned_customers, held_result.churned_customers * 1.5)

    def test_acquired_customers_do_not_count_as_organic_growth_in_valuation(self):
        from copy import deepcopy
        engine = self._play_to_final_quarter(41)
        bought = deepcopy(engine)
        passed = deepcopy(engine)
        for copy_, choice in ((bought, "stock"), (passed, "pass")):
            copy_.upcoming_dilemma = lambda: dilemma("acquihire")
            copy_.advance(Decision(price=99, marketing=150_000, product=60_000, hires=1, dilemma_choice=choice))
        revenue_gain = bought.state.revenue / passed.state.revenue - 1
        valuation_gain = bought.state.valuation / passed.state.valuation - 1
        self.assertLess(valuation_gain, revenue_gain + 0.03)

    def test_results_record_non_operating_cash(self):
        engine = SimulationEngine()
        engine.upcoming_dilemma = lambda: dilemma("research_grant")
        raised, _ = engine.funding_offer()
        start = engine.state.cash
        result = engine.advance(Decision(hires=0, raise_funding=True, dilemma_choice="apply"))
        self.assertEqual((result.funding_raised, result.board_cash), (raised, 250_000))
        self.assertAlmostEqual(engine.state.cash - start, result.operating_profit + raised + 250_000)


if __name__ == "__main__":
    unittest.main()
