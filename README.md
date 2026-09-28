# Startup CEO Simulator

Startup CEO Simulator is an offline strategic-management game built for MBA presentations. The player leads a fictional SaaS company through 12 quarters, balancing growth, profitability, product strength, people, liquidity, valuation, and founder control.

The experience is deliberately approachable: decisions are connected to visible business effects through a transparent rules engine, making the application useful as an interactive case study for professors, recruiters, and potential employers.

![Startup CEO Simulator strategy canvas](docs/screenshots/strategy-canvas.png)

## Why I built this project

I built Startup CEO Simulator to turn MBA concepts into an interactive decision-making experience. Instead of presenting strategy, finance, and operations as separate topics, the simulator shows how a CEO's choices affect one another over time: aggressive growth can reduce runway, hiring can expand capacity while increasing fixed costs, and outside funding can protect the business while diluting founder ownership.

The project also gave me a practical way to connect business analysis with software development. My goal was to create a portfolio piece that demonstrates how I approach ambiguous problems, translate business ideas into clear rules, and communicate tradeoffs through an accessible product. It is designed to encourage discussion rather than produce a single “correct” strategy.

## Strategy Canvas

The primary screen places controllable management choices beside estimated business effects:

- Set monthly subscription price, marketing and product investment.
- Hire or lay off employees; the interface prevents both in one quarter.
- Raise funding when additional runway justifies founder dilution.
- Review directional estimates for growth, margin, quality, runway, and control.
- Respond to seeded market events such as economic slowdowns, supplier increases, competitor outages, privacy concerns, and market expansion.
- Commit the strategy and immediately see the resulting revenue, profit, customers, cash, valuation, quality, and morale.

Directional previews are explicitly estimates. Actual results reflect the selected strategy, company health, and the quarter's market condition.

## Board objectives

Every simulation tracks three goals from the opening briefing through the final report:

1. Finish with positive cash.
2. Reach at least 3,000 customers.
3. Retain at least 80% founder ownership.

## Save, resume, and reporting

Sessions can be saved to a local JSON file and reopened later. Saves include current company metrics, the random seed, decision history, market-event history, and board-objective progress. Unsupported, incomplete, and corrupted files are rejected with a helpful message.

At the end of the simulation, the final board report summarizes:

- CEO score, valuation, cash, customers, and founder ownership
- Best-performing quarter
- Board-objective results
- Major hiring, layoff, funding, and product-investment decisions
- A concise assessment of what worked and what could improve

The report can be exported as a professionally formatted PDF.

## MBA concepts demonstrated

| Concept | Simulation application |
|---|---|
| Unit economics | Price, variable cost, acquisition investment, and churn jointly affect profit |
| Capital allocation | Cash is distributed among product, marketing, talent, and runway protection |
| Price elasticity | Premium pricing raises revenue per customer while pressuring demand and retention |
| Diminishing returns | Marketing generates leads through a square-root response curve |
| Operating leverage | Headcount expands capacity while adding recurring payroll and onboarding cost |
| Growth versus profitability | Growth can increase valuation while shortening runway |
| Venture finance | Funding adds cash while progressively diluting founder ownership |
| Stakeholder management | Layoffs lower cost but damage morale and retention |
| Risk management | Repeatable external events test whether a strategy is resilient |

The model is educational and explainable rather than predictive or investment advice.

## Install and launch

Python 3.11 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python main.py
```

After editable installation, the console command is also available:

```bash
startup-ceo-simulator
```

On Windows, activate the environment with `.venv\Scripts\activate`.

## Test and visual QA

Run the full engine, persistence, report, and GUI test suite:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

Generate a deterministic local dashboard preview:

```bash
QT_QPA_PLATFORM=offscreen python scripts/capture_screenshot.py
```

The generated image is written to `work/dashboard-preview.png` and is intentionally ignored by Git.

## Project structure

```text
.
├── main.py                         # Application entry point
├── scripts/
│   └── capture_screenshot.py       # Deterministic visual-QA helper
├── src/startup_ceo/
│   ├── app.py                      # Strategy Canvas and interaction flow
│   ├── engine.py                   # PySide6-independent simulation rules
│   ├── models.py                   # Typed business and history models
│   ├── report_service.py           # Board summary and PDF export
│   ├── save_service.py             # Validated local JSON persistence
│   └── widgets.py                  # Reusable PySide6 presentation widgets
└── tests/
    ├── test_engine.py              # Financial and deterministic behavior
    ├── test_gui.py                 # Offscreen interface smoke test
    ├── test_report_service.py      # Report content and PDF verification
    └── test_save_service.py        # Round-trip and corruption handling
```

## Simulation model

Each quarter applies the upcoming seeded market event, estimates marketing leads with diminishing returns, converts demand according to price, brand, and quality, calculates churn, recognizes quarterly subscription revenue, deducts variable and operating costs, updates company health and cash, and estimates valuation from annualized revenue, growth, margin, quality, and liquidity.

Using the same seed and decisions produces the same results, enabling fair classroom comparisons between growth-first, capital-efficient, and product-led strategies.

## Privacy and offline operation

All calculations, saves, screenshots, and PDF reports remain on the user's computer. The application has no accounts, uploads, telemetry, analytics, advertising, API integrations, or runtime network calls.

## AI-assisted development

I used AI-assisted tools during development to help explore implementation approaches, draft and refine code, troubleshoot issues, develop test cases, and improve documentation. I directed the product concept, requirements, business assumptions, and design decisions, then reviewed, tested, and refined the resulting work.

AI is not part of the running simulation. The application does not call an AI model or send player data to an external service; outcomes come from the deterministic, locally executed rules described above.

## License

Released under the [MIT License](LICENSE).
