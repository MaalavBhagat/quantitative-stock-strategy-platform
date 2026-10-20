You are working on the Quantitative Stock Strategy Research Platform.
Read first: CLAUDE.md, PROJECT_GUIDE.md (esp. §4 units, D1–D3, §5 testing), PROJECT_STATUS.md,
research/EXPERIMENT_PLAN.md §1, research/BROKER_FEES.md §4, and Phase 3 in the roadmap .txt.

STEP 0 (docs → main): commit PROJECT_STATUS.md, research/BROKER_FEES.md, prompts/08_*.md —
"Phase 2 verified by chat Claude; Stake fractional rules". Push.

CONTEXT: Phase 3 is the most important phase. "Incorrect accounting can make an unprofitable strategy appear
profitable." Correctness beats speed and beats features. Phase 3 is split into 3 prompts:
08 = cash + whole + fractional positions (this one) · 09 = costs, dividends, splits · 10 = valuation + full accounting tests.

TASK: Phase 3, Steps 3.1 (cash), 3.2 (whole shares), 3.3 (fractional shares). Branch: `phase3-ledger-core`.

FIRST: show Goggy a short plan (classes, functions, what each test proves) in plain words and WAIT for OK.

DESIGN RULES:
- Module `src/quant_research/portfolio/`. Decimal for all money and share quantities (D1). No float may enter the
  ledger: reject float inputs with a clear error (strings/ints/Decimal OK) — conversion from float prices happens at
  ONE tested function `to_decimal_price(x: float) -> Decimal` (used later by execution).
- Rounding (D2): cash to cents, against us — amounts we pay round UP, amounts we receive round DOWN.
  Shares (D3): fractional to 6 dp [ASSUMPTION], shares bought round DOWN.
- The ledger only RECORDS trades it is told about. It does not decide prices, fees or timing. Fees arrive as an
  explicit Decimal argument (fee_usd) — the cost model is prompt 09.
- Average-cost basis for realised/unrealised P&L [ASSUMPTION — no tax modelling; log it in PROJECT_GUIDE §4].
- Every change writes an immutable ledger entry (date, type, ticker, quantity, price, fee, cash_before, cash_after).
  The entry list is the audit trail.

BUILD:
1. Cash (3.1): `Portfolio(initial_cash_usd)`. Track initial capital, cash spent, cash received, fees paid, current cash.
   Refuse any trade that would make cash < 0 (raise InsufficientCashError with numbers in the message).
   Deposits/withdrawals not needed yet (FX at start/end comes in prompt 09).
2. Whole shares (3.2): `buy(date, ticker, quantity, price_usd, fee_usd)` / `sell(...)`. Validate: quantity > 0,
   price > 0, fee ≥ 0, whole-number quantity when share_mode="whole", can't sell more than held
   (InsufficientSharesError), dates never go backwards.
3. Fractional (3.3): share_mode="fractional". Helper `shares_affordable(cash_usd, price_usd, fee_usd, share_mode)`
   → max quantity so price×qty + fee ≤ cash (whole: floor to int; fractional: floor to 6 dp).
   Stake minimum order US$10 as a config value `min_order_usd` (BROKER_FEES §4) — orders below it raise.
4. Realised P&L on sells (average cost), position quantity, average cost per share, trade log.

TESTS (tests/accounting/ — create the folder now since it gets real tests):
- Every test has its hand calculation written as a comment ABOVE the assert, and asserts EXACT Decimal equality.
- At minimum: start cash; buy whole shares (cash = start − qty×price − fee); buy then sell → realised P&L;
  two buys at different prices → average cost; partial sell; too little cash → error and NOTHING changed;
  selling more than held → error and nothing changed; fractional buy rounds shares down to 6 dp; cash rounding
  against us (craft a case where qty×price has more than 2 dp); whole mode rejects 1.5 shares;
  shares_affordable whole vs fractional; min order US$10; float input rejected; dates backwards rejected;
  ledger entries are complete and can't be edited.
- One "invariant" test: after a random-but-seeded sequence of valid trades,
  initial_cash − total_spent − total_fees + total_received == current cash (exactly).

FINISH: pytest / ruff check / ruff format --check (real output) · safety checks · commit on branch → merge → push →
delete branch · PROJECT_GUIDE.md: `portfolio/` marked created + average-cost assumption · PROJECT_STATUS.md
(Steps 3.1–3.3, next = prompt 09) · CHANGELOG.md.

COMPLETION REPORT: files · plain-words explanation of how the ledger works · each test's purpose (one line each) ·
tests + real output · assumptions made · open questions.
Do not claim anything is done unless the evidence supports it.
