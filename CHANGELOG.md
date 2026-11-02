# Changelog

All notable changes to Startup CEO Simulator are recorded here. The project follows [semantic versioning](https://semver.org/).

## [0.2.0] - 2026-11-01

### Added

- **Board dilemmas.** In four quarters of every game the board brings a decision, drawn from a pool of nine (enterprise pilot, security vulnerability, poached engineer, acqui-hire, marketplace partnership, viral complaint, price war, R&D grant, workplace strategy). Each has two or three responses with their consequences shown up front, and the quarter cannot be committed until one is chosen. The schedule comes from the scenario code, so teams playing the same code face the same dilemmas.
- **Scenario code** on the new-game screen, so a class can compare results on the same market.
- **Performance trend chart** (cash, revenue, operating profit, customers, valuation) and a **last-quarter income statement**.
- **Live warnings** when runway is short or customers are outgrowing the team, and a preview of the next funding round's size and dilution.
- **"Service capacity"** estimate alongside the other expected business effects.
- **Guide dialog** explaining the levers, board dilemmas and scoring, plus keyboard shortcuts (Ctrl/⌘+Enter to commit, Ctrl/⌘+N/S/O to start, save and open).
- **Board report additions:** score breakdown, founder stake value, quarter-by-quarter results, a full decision log, and every board dilemma with the response chosen.
- A "View Final Board Report" button after the last quarter and a prompt before closing or replacing a game with unsaved quarters.

### Changed

- **Rebalanced simulation.** Marketing now faces market saturation in a growing addressable market; each employee supports about 300 customers, and outgrowing the team raises churn and lowers quality and morale; product quality gives pricing power; product investment has diminishing returns. Previously one fixed plan (maximum marketing and product, no hiring, no funding) won every scenario. Now growth-led, premium product-led and balanced plans are all competitive.
- **New CEO score** built mainly on the founder's stake value (valuation × ownership), so raising money every quarter or late in the game is no longer rewarded.
- Hiring, layoffs and funding are one-off actions that reset after each quarter.
- More compact Strategy Canvas layout so the new panels fit on screen.

### Fixed

- Corrupted or tampered save files with invalid numbers or decisions are now rejected with a message instead of crashing the app or the report.
- Layoffs that would leave fewer than three employees are refused instead of charging severance for people who were not let go.
- The runway estimate now includes cash from a funding round being raised that quarter, and that cash can cover a board dilemma's cost.
- Amounts just under $1M display as "$1.00M" instead of "$1000K".
- PDF report tables are readable (their text was rendering at a tiny size).

## [0.1.0] - 2026-09-28

- Initial release: Strategy Canvas for 12 quarters, seeded market events, board objectives, validated local saves, and PDF board report export.
