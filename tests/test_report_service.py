import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

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

    def test_pdf_export_creates_pdf(self):
        engine = SimulationEngine()
        engine.advance(Decision(hires=0))
        with TemporaryDirectory() as directory:
            path = Path(directory) / "board-report.pdf"
            export_pdf(path, engine.state)
            self.assertGreater(path.stat().st_size, 1_000)
            self.assertEqual(path.read_bytes()[:4], b"%PDF")


if __name__ == "__main__":
    unittest.main()
