# CLAUDE.md — rules for Claude Code in this repo (read automatically every session)

Project: Quantitative Stock Strategy Research Platform (Goggy, Macquarie Uni).
Question: does "sell after a small rise, rebuy after a dip" beat buy-and-hold after real costs,
on AUD 10,000, US stocks, Stake as main broker? A "no" answer is a valid result.

## Read before doing anything
1. PROJECT_BRIEF.md — one-page summary
2. PROJECT_STATUS.md — current phase, task, decisions
3. The research/ file(s) relevant to the task (esp. research/EXPERIMENT_PLAN.md for any strategy/backtest work)
4. "Quantitative Stock Strategy Research Platform.txt" — master roadmap (phase steps + acceptance criteria)

## How to work
- Do ONE task at a time — the one named in PROJECT_STATUS.md "NEXT ACTION" or given by Goggy.
- Inspect existing files before changing anything. Don't rewrite unrelated files.
- Explain the plan in plain, simple language BEFORE editing. Goggy has no coding background.
- Ask before installing anything system-wide (Homebrew, Python versions, global packages).
- Write tests for any logic. Run them. Report the REAL output — never claim tests pass without running them.
- Finish every task by updating PROJECT_STATUS.md (completed, decisions, next action, tests run + results).

## Hard rules (anti-hallucination)
- Never invent data, fees, prices, or results. Any number needs a source link or the label UNVERIFIED / ASSUMPTION.
- Never claim a strategy is profitable. Results are "simulated, historical".
- No look-ahead: decide on day T close → trade at day T+1 open (see EXPERIMENT_PLAN.md).
- Never trade at adjusted prices. Adjusted prices are for analysis only.
- If high and low are both hit in one daily bar, assume the WORSE order.
- Never change the experiment plan, stock list or test dates silently — log changes in the file's change log.
- Never open the final test period (2021+) until Goggy says so.

## Security / licence
- API keys go in .env (git-ignored). Never print, commit or hard-code keys.
- Downloaded market data (data/) is personal-use licence → NEVER commit it to Git.

## Status words
Not started / In progress / Blocked / Verified. "Verified" = deliverables exist + tests pass + limits documented.
