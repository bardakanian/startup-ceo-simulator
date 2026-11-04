# Changelog

All notable changes to Startup CEO Simulator are recorded here. The project follows [semantic versioning](https://semver.org/).

## [Unreleased]

### Fixed

- The "Expected Business Effects" estimates now project the quarter with the engine's own rules and the announced market condition (without the quarter's random demand variation). The customer-growth estimate was right only about 60% of the time and is now right about 99%, and margin and quality estimates now account for market events and support overload.
- Brand is shown in the company health summary, so the brand effects listed on board dilemmas are visible.
- The income statement lists customers gained through an acquisition, so the customer change adds up.
- The low-runway warning stays visible when a funding round is ticked but still leaves less than six months of runway.
- After the final quarter, forward-looking estimates (runway, expected effects and the next funding round) are cleared instead of describing a quarter that will not happen.
- A final-quarter price hike no longer inflates the score (it added about 7 points). Raising the price on existing customers now causes extra churn, and the valuation multiple falls when quarterly churn rises above 3%.
- Customers gained through an acquisition no longer count as organic growth in the valuation multiple.
- The income statement shows cash from funding rounds and board decisions, with a change-in-cash total, so the cash balance can be reconciled.
- At the minimum window size the page no longer scrolls sideways or clips cards, and the sliders stay usable.
- PDF export no longer reports success when an existing report can't be overwritten, and it writes through a temporary file so a failed export can't leave a partial report.
- Suggested save and report file names are safe when the company name contains characters such as `/` or `:`.
- The company name in the header is shown literally instead of being interpreted as formatting, and a long name no longer widens the window.
- Save files with fewer than three employees are rejected, matching the game's minimum team size.

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
