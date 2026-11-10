# Model 13 Phase 2 — independent price-availability observations

This optional data source is **not** automatically populated. The Odds API's
recorded prices are NOT proof a bookmaker would accept a wager at that price.

Store only independently checked observations; never fabricate a check, and
never put login details, account numbers, identifying screenshots, or financial
records in this public repo.

Create `data/model13/execution_observations.csv` ONLY if a verified observer
has an actual observation, with these CSV headers:

```csv
event_id,checked_utc,book_key,selected_side,offered_odds_checked,execution_status,max_stake_units,fees_per_unit,evidence_reference,notes
```

Example **illustration only, do not commit as real data**:

```csv
example-event-id,2026-11-10T15:05:00Z,draftkings,HOME,390,PRICE_UNAVAILABLE,,,private-check-001,Illustrative example only
```

Allowed `execution_status` values:

- `PRICE_CONFIRMED`: observer saw the matching book/side/odds; **not a bet
  fill**, and does not prove a stake could be placed.
- `PRICE_UNAVAILABLE`: price was not visible when independently checked.
- `REGION_RESTRICTED`, `LIMITED_LIQUIDITY`, `ACCOUNT_RESTRICTED`:
  observed availability/access restrictions.
- `UNKNOWN`, `UNREVIEWED`: explicitly not confirmed.

Every record should include the **original** frozen `event_id`, `book_key`,
and `selected_side`. `checked_utc` must reflect actual observation time;
do not retroactively claim availability based on an archive.

The Phase 2 audit flags checks outside 15 minutes from the frozen selection
timestamp or with missing evidence references; it does not compute true net EV
from these manually entered details. Live Model 13 selection criteria remain
unchanged.

**Calibration warning:** the Phase 2 Brier and log-loss metrics evaluate a
selected-side *cross-book market reference*; they are not independent model
probabilities, and cannot independently prove positive EV.
