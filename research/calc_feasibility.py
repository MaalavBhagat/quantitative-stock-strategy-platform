"""Step 0.4 — break-even calculator. Re-run: python3 calc_feasibility.py
All inputs at the top. Sources/labels in SMALL_ACCOUNT_FEASIBILITY.md."""

CAPITAL_AUD = 10_000
AUDUSD = 0.69          # ASSUMPTION: rate used in Stake's own FX example (not a live rate)
SHARE_PRICE = 250.0    # ASSUMPTION: illustrative US share price for per-share fees / idle cash

# spread + slippage per side (ASSUMPTION — no free historical spread data)
SPREAD = {"tight": 0.0002, "normal": 0.0005, "wide": 0.0010}

def stake(trade_usd):      # US$3 or 0.01% above US$30k  [Stake AU pricing page]
    return 3.0 if trade_usd <= 30_000 else 0.0001 * trade_usd

def ibkr_fixed(trade_usd): # US$0.005/share, min US$1, max 1%  [IBKR AU commissions]
    shares = trade_usd / SHARE_PRICE
    return min(max(0.005 * shares, 1.0), 0.01 * trade_usd)

def commsec(trade_usd):    # US$5 or 0.12%, greater  [CommSec rates & fees]
    return max(5.0, 0.0012 * trade_usd)

# one-off FX into USD at start (and assume same again at exit)
FX_ONEOFF = {"IBKR (LOW)": 0.00002, "Stake (MID)": 0.0055, "CommSec (HIGH)": 0.0055}
# FX charged on every trade? (CommSec standard auto-converts each trade)
FX_PER_TRADE = {"IBKR (LOW)": 0.0, "Stake (MID)": 0.0, "CommSec (HIGH)": 0.0055}
BROKERAGE = {"IBKR (LOW)": ibkr_fixed, "Stake (MID)": stake, "CommSec (HIGH)": commsec}

usd = CAPITAL_AUD * AUDUSD
print(f"Capital AUD {CAPITAL_AUD:,} @ {AUDUSD} = US${usd:,.2f} before FX\n")

print("A) One round trip (sell + rebuy) as % of position, by spread level")
print(f"{'Broker':16}{'brokerage':>11}{'FX':>8}" + "".join(f"{k:>10}" for k in SPREAD))
rows = {}
for b, fee_fn in BROKERAGE.items():
    start_usd = usd * (1 - FX_ONEOFF[b])
    brk = 2 * fee_fn(start_usd) / start_usd
    fx = 2 * FX_PER_TRADE[b]
    tot = {k: brk + fx + 2 * v for k, v in SPREAD.items()}
    rows[b] = tot
    print(f"{b:16}{brk*100:>10.3f}%{fx*100:>7.2f}%" + "".join(f"{t*100:>9.3f}%" for t in tot.values()))

print("\nB) Break-even: the dip (Y) must be bigger than the round-trip cost just to gain ANY shares")
print("   Net gain per successful round trip ≈ Y − cost   (normal spread)")
for b, tot in rows.items():
    c = tot["normal"]
    print(f"   {b:16} cost {c*100:.2f}%  →  Y=2%: {(0.02-c)*100:+.2f}%   Y=3%: {(0.03-c)*100:+.2f}%   Y=5%: {(0.05-c)*100:+.2f}%")

print("\nC) Yearly cost drag by number of round trips (normal spread)")
print(f"{'Broker':16}" + "".join(f"{n:>9}/yr" for n in (5, 10, 20, 50)))
for b, tot in rows.items():
    print(f"{b:16}" + "".join(f"{tot['normal']*n*100:>11.2f}%" for n in (5, 10, 20, 50)))

print("\nD) One-off FX in + out (hits buy-and-hold too)")
for b, f in FX_ONEOFF.items():
    print(f"   {b:16} ~{2*f*100:.2f}% total (in + out)")

print("\nE) Whole shares only (no fractional): idle cash")
print(f"   At share price US${SHARE_PRICE:.0f}: max idle = {SHARE_PRICE/usd*100:.1f}% of capital, average ≈ {SHARE_PRICE/2/usd*100:.1f}%")
