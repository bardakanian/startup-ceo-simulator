import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from startup_ceo.app import MainWindow


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
        window.close()


if __name__ == "__main__":
    unittest.main()
