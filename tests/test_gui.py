import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from startup_ceo.app import MainWindow, WelcomeDialog


class GuiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_strategy_canvas_constructs_and_updates(self):
        window = MainWindow()
        window.show()
        self.app.processEvents()
        self.assertEqual(window.windowTitle(), "Startup CEO Simulator")
        self.assertIn("Q1:", window.event_title.text())
        self.assertTrue(window.advance_button.isEnabled())
        self.assertEqual(len(window.cards), 6)
        window.layoffs.set_value(2)
        self.assertEqual(window.hires.value(), 0)
        window.hires.set_value(3)
        self.assertEqual(window.layoffs.value(), 0)
        self.assertEqual(len(window.effects), 6)
        self.assertFalse(window.grab().isNull())
        window.close()

    def test_committing_a_quarter_updates_history_and_resets_one_off_actions(self):
        window = MainWindow()
        window.hires.set_value(2)
        window.funding.setChecked(True)
        window._advance()
        self.assertEqual(window.engine.state.quarter, 1)
        self.assertEqual(window.engine.state.employees, 10)
        self.assertEqual(window.hires.value(), 0)
        self.assertFalse(window.funding.isChecked())
        self.assertTrue(window.unsaved)
        self.assertIn("Operating profit", window.statement.text())
        self.assertEqual(len(window.chart.values), 2)
        window.show()
        self.assertFalse(window.grab().isNull())
        self.assertIn("Q2:", window.event_title.text())
        window.unsaved = False
        window.close()

    def test_completed_game_offers_report_and_blocks_advance(self):
        window = MainWindow()
        window._show_report = lambda: None
        for _ in range(12):
            if window.dilemma_group.buttons():
                next(button for button in window.dilemma_group.buttons() if button.isEnabled()).setChecked(True)
            window._advance()
        self.assertTrue(window.engine.state.complete)
        self.assertFalse(window.advance_button.isEnabled())
        self.assertFalse(window.report_button.isHidden())
        window._advance()
        self.assertLessEqual(window.engine.state.quarter, 12)
        window.unsaved = False
        window.close()

    def test_low_runway_shows_warning(self):
        window = MainWindow()
        window.engine.state.cash = 150_000
        window._update_dashboard()
        self.assertFalse(window.alert.isHidden())
        self.assertIn("Runway", window.alert.text())
        window.funding.setChecked(True)
        self.assertNotIn("Runway", window.alert.text())
        window.close()

    def test_board_dilemma_blocks_commit_until_answered(self):
        window = MainWindow()
        while window.engine.upcoming_dilemma() is None:
            window._advance()
        quarter = window.engine.state.quarter
        self.assertFalse(window.dilemma_panel.isHidden())
        self.assertFalse(window.advance_button.isEnabled())
        window._advance()
        self.assertEqual(window.engine.state.quarter, quarter)
        window.dilemma_group.buttons()[0].setChecked(True)
        self.assertTrue(window.advance_button.isEnabled())
        window._advance()
        self.assertEqual(window.engine.state.quarter, quarter + 1)
        self.assertTrue(window.engine.state.decision_history[-1].response)
        if window.engine.upcoming_dilemma() is None:
            self.assertTrue(window.dilemma_panel.isHidden())
        while window.engine.upcoming_dilemma() is None:
            window._advance()
        self.assertEqual(window.dilemma_options.count(), len(window.engine.upcoming_dilemma().options))
        window.unsaved = False
        window.close()

    def test_layoff_control_respects_minimum_team(self):
        window = MainWindow()
        window.engine.state.employees = 4
        window._update_dashboard()
        self.assertEqual(window.layoffs.spin.maximum(), 1)
        window.engine.state.employees = 20
        window._update_dashboard()
        self.assertEqual(window.layoffs.spin.maximum(), 5)
        window.close()

    def test_funding_round_unlocks_cash_dilemma_option(self):
        from startup_ceo.dilemmas import DILEMMAS
        window = MainWindow()
        acquihire = next(item for item in DILEMMAS if item.key == "acquihire")
        window.engine.upcoming_dilemma = lambda: acquihire
        window.engine.state.cash = 300_000
        window.shown_dilemma = None
        window._update_dashboard()
        cash_button = window.dilemma_cards[0].button
        self.assertFalse(cash_button.isEnabled())
        window.funding.setChecked(True)
        self.assertTrue(cash_button.isEnabled())
        cash_button.setChecked(True)
        self.assertTrue(window.advance_button.isEnabled())
        window.funding.setChecked(False)
        self.assertFalse(cash_button.isEnabled())
        self.assertFalse(cash_button.isChecked())
        self.assertFalse(window.advance_button.isEnabled())
        window.close()

    def test_welcome_dialog_offers_scenario_code(self):
        dialog = WelcomeDialog(seed=314)
        self.assertEqual(dialog.seed.value(), 314)


if __name__ == "__main__":
    unittest.main()
