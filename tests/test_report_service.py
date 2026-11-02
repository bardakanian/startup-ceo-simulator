import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from startup_ceo.dilemmas import DILEMMAS
from startup_ceo.engine import Decision, SimulationEngine
from startup_ceo.report_service import build_board_report, export_pdf, report_html


class ReportServiceTests(unittest.TestCase):
    def test_report_contains_required_board_results(self):
        engine = SimulationEngine(seed=12, company_name="Boardroom Cloud")
        engine.advance(Decision(hires=0))
        report = build_board_report(engine.state)
        html = report_html(engine.state)
        self.assertIn("Q1", report.best_quarter)
        self.assertIn("CEO Score", html)
        self.assertIn("Board objectives", html)
        self.assertIn("Major strategic decisions", html)
        self.assertIn("Quarter-by-quarter results", html)
        self.assertIn("Score breakdown", html)
        self.assertIn("Founder stake value", html)
        self.assertIn(engine.state.history[0].event.name, html)

    def test_report_notes_support_overload(self):
        engine = SimulationEngine(seed=12)
        engine.state.customers = 4_000
        engine.advance(Decision(hires=0))
        self.assertTrue(any("Support peaked" in item for item in build_board_report(engine.state).decisions))

    def test_pdf_export_creates_pdf(self):
        engine = SimulationEngine()
        engine.advance(Decision(hires=0))
        with TemporaryDirectory() as directory:
            path = Path(directory) / "board-report.pdf"
            export_pdf(path, engine.state)
            self.assertGreater(path.stat().st_size, 1_000)
            self.assertEqual(path.read_bytes()[:4], b"%PDF")

    def test_report_lists_board_dilemmas(self):
        engine = SimulationEngine(seed=2027)
        for _ in range(4):
            pending = engine.upcoming_dilemma()
            engine.advance(Decision(hires=0, dilemma_choice=pending.options[0].key if pending else ""))
        report = build_board_report(engine.state)
        self.assertEqual(len(report.board_decisions), 1)
        self.assertIn("Q4", report.board_decisions[0])
        self.assertIn("Board dilemmas", report_html(engine.state))

    def test_report_counts_employees_added_by_acquisition(self):
        engine = SimulationEngine(seed=12)
        acquihire = next(item for item in DILEMMAS if item.key == "acquihire")
        engine.upcoming_dilemma = lambda: acquihire
        engine.advance(Decision(hires=0, dilemma_choice="stock"))
        report = build_board_report(engine.state)
        self.assertIn("added 4 through acquisitions", report.decisions[1])
        self.assertIn("+4", report_html(engine.state))


if __name__ == "__main__":
    unittest.main()
