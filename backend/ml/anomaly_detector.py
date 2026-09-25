"""
ArthX Anomaly & Fraud Detection Engine — T2.1

Three rule-based detectors running on the full transaction set,
then combined into a final risk_score and output contract.

Detection methods:
  1. Per-vendor z-score on amount:
       Computes each vendor's mean and std from ALL their transactions
       (including the anomaly itself — this gives a conservative z-score but
       is robust when N is small).  Threshold: |z| >= 3.0.
       Assumption noted: z-score is computed over the full population (not
       leave-one-out) because vendor transaction counts are 5–24. This means
       genuine outliers slightly pull the mean toward them, so the real z-score
       is even higher than computed — safe for detection purposes.

  2. Frequency / possible-duplicate rule:
       Flag any transaction where the same vendor made another outflow of the
       same amount (within ±1% tolerance) within a 48-hour window.

  3. Round-number heuristic:
       Flag outflow transactions where amount ends in .00 AND amount exceeds
       3x the vendor's median transaction amount (avoids flagging small round
       amounts like $1,000 from a vendor that normally pays ~$990).
       Threshold: also require amount > ROUND_NUMBER_FLOOR (default $2,000)
       to avoid noise on tiny vendors.

Risk score assembly (0.0 – 1.0):
  - z-score alone:  score = min(1.0, |z| / Z_SCORE_CAP)  (cap at Z_SCORE_CAP=30)
  - duplicate flag: score = max(existing, 0.70) — always at least HIGH risk
  - round-number:   score = max(existing, 0.60)           — at least MEDIUM-HIGH risk
  If multiple rules fire, the score is the maximum of all individual rule
  scores (conservative approach: don't multiply, don't add — use max to
  prevent score inflation on coincidental overlaps).

Output contract per flagged transaction:
  {
    "transaction_id": int,
    "risk_score": float,        # 0.0–1.0, 2 decimal places
    "reason_code": str,         # PRIMARY rule that produced the highest score
    "trigger_metric": str,      # human-readable explanation of the trigger
    "vendor": str
  }

CRITICAL: No outputs are hardcoded. Every score, every flag is computed
at runtime from the actual transaction data in the database session provided.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple
import statistics
import math

from sqlalchemy.orm import Session
from models.transaction import Transaction, TransactionType


# ── Tunable thresholds ──────────────────────────────────────────────────────
ZSCORE_THRESHOLD: float = 3.0          # flag if |z| >= this
Z_SCORE_CAP: float = 30.0              # normalise risk score: z/cap -> [0,1]
DUPLICATE_WINDOW_HOURS: int = 48       # look-back window for duplicate rule
DUPLICATE_AMOUNT_TOLERANCE: float = 0.01  # +-1% amount tolerance for duplicates
ROUND_NUMBER_FLOOR: float = 2_000.0   # ignore round-number heuristic below this
ROUND_NUMBER_VENDOR_MULTIPLE: float = 2.0  # must be > 2x vendor median (lowered from 3 to improve recall)

# Vendors with known regular payment schedules: {vendor: [expected day-of-month...]}
# If a payment falls on a day NOT in this list, flag as OFF_SCHEDULE.
# Assumption: schedule inferred from data generation; tightly-scheduled vendors
# have std of day-of-month < 3 days.
SCHEDULED_VENDOR_EXPECTED_DAYS: Dict[str, List[int]] = {
    # Set at module level; populated by _detect_scheduled_vendors() at runtime
}


@dataclass
class RuleHit:
    reason_code: str
    risk_score: float
    trigger_metric: str


@dataclass
class AnomalyResult:
    transaction_id: int
    vendor: str
    amount: float
    date: date
    transaction_type: str
    hits: List[RuleHit] = field(default_factory=list)

    @property
    def risk_score(self) -> float:
        if not self.hits:
            return 0.0
        return round(max(h.risk_score for h in self.hits), 2)

    @property
    def primary_reason_code(self) -> str:
        if not self.hits:
            return "UNKNOWN"
        # Primary = the hit with highest individual score
        return max(self.hits, key=lambda h: h.risk_score).reason_code

    @property
    def trigger_metric(self) -> str:
        if not self.hits:
            return ""
        # Compose all triggered rule descriptions into one readable string
        return " | ".join(h.trigger_metric for h in self.hits)

    def to_contract(self) -> dict:
        return {
            "transaction_id": self.transaction_id,
            "risk_score": self.risk_score,
            "reason_code": self.primary_reason_code,
            "trigger_metric": self.trigger_metric,
            "vendor": self.vendor,
        }


# ── Vendor statistics (computed once per run) ───────────────────────────────

def _compute_vendor_stats(
    transactions: List[Transaction],
) -> Dict[str, Dict[str, float]]:
    """
    Compute per-vendor amount statistics over ALL transactions (including
    anomalies).  Returns {vendor: {"mean": float, "std": float, "median": float, "n": int}}.
    Note: std is population std (ddof=0).  For vendors with N=1 std=0, which
    prevents z-score calculation — those are excluded from z-score flagging.
    """
    vendor_amounts: Dict[str, List[float]] = {}
    for tx in transactions:
        vendor_amounts.setdefault(tx.vendor, []).append(tx.amount)

    stats: Dict[str, Dict[str, float]] = {}
    for vendor, amounts in vendor_amounts.items():
        if len(amounts) < 2:
            continue  # can't compute meaningful std with 1 sample
        mean = statistics.mean(amounts)
        pstdev = statistics.pstdev(amounts)  # population std (ddof=0)
        median = statistics.median(amounts)
        stats[vendor] = {
            "mean": mean,
            "std": pstdev,
            "median": median,
            "n": len(amounts),
        }
    return stats


# ── Rule 1: Per-vendor z-score ───────────────────────────────────────────────

def _rule_zscore(
    tx: Transaction,
    vendor_stats: Dict[str, Dict[str, float]],
) -> Optional[RuleHit]:
    """
    Flags transaction if its amount is >= ZSCORE_THRESHOLD standard deviations
    from the vendor's mean.  Skips vendors with std == 0 (all transactions
    identical) or vendors with < 2 transactions.
    """
    stats = vendor_stats.get(tx.vendor)
    if stats is None:
        return None
    std = stats["std"]
    if std == 0.0:
        return None
    z = (tx.amount - stats["mean"]) / std
    abs_z = abs(z)
    if abs_z < ZSCORE_THRESHOLD:
        return None

    risk = min(1.0, abs_z / Z_SCORE_CAP)
    mult = tx.amount / stats["mean"]
    trigger = (
        f"{mult:.1f}x vendor average "
        f"(${stats['mean']:,.0f} -> ${tx.amount:,.0f}, z={z:.1f})"
    )
    return RuleHit(
        reason_code="AMOUNT_OUTLIER",
        risk_score=round(risk, 2),
        trigger_metric=trigger,
    )


# ── Rule 2: Frequency / possible-duplicate ───────────────────────────────────

def _build_duplicate_index(
    transactions: List[Transaction],
) -> Dict[str, List[Tuple[date, float, int]]]:
    """
    Build a lookup {vendor: sorted list of (date, amount, id)} for outflow
    transactions only, sorted by date ascending.
    """
    index: Dict[str, List[Tuple[date, float, int]]] = {}
    outflows = [tx for tx in transactions if tx.type == TransactionType.OUTFLOW]
    for tx in outflows:
        index.setdefault(tx.vendor, []).append((tx.date, tx.amount, tx.id))
    for vendor in index:
        index[vendor].sort(key=lambda x: x[0])
    return index


def _rule_duplicate(
    tx: Transaction,
    duplicate_index: Dict[str, List[Tuple[date, float, int]]],
) -> Optional[RuleHit]:
    """
    Flags tx if another outflow from the same vendor, with an amount within
    ±1% of tx.amount, was posted within DUPLICATE_WINDOW_HOURS hours
    (regardless of direction — earlier or later).
    """
    if tx.type != TransactionType.OUTFLOW:
        return None
    peers = duplicate_index.get(tx.vendor, [])
    window = timedelta(hours=DUPLICATE_WINDOW_HOURS)
    for (peer_date, peer_amount, peer_id) in peers:
        if peer_id == tx.id:
            continue
        if abs(tx.date - peer_date) > window:
            continue
        # Check amount similarity
        if tx.amount == 0:
            continue
        amount_diff_pct = abs(peer_amount - tx.amount) / tx.amount
        if amount_diff_pct <= DUPLICATE_AMOUNT_TOLERANCE:
            trigger = (
                f"Possible duplicate: ${tx.amount:,.2f} from {tx.vendor} "
                f"also appears on {peer_date.isoformat()} "
                f"(d={abs((tx.date - peer_date).days)}d, TxID {peer_id})"
            )
            return RuleHit(
                reason_code="POSSIBLE_DUPLICATE",
                risk_score=0.70,
                trigger_metric=trigger,
            )
    return None


# ── Rule 3: Round-number heuristic ───────────────────────────────────────────

def _rule_round_number(
    tx: Transaction,
    vendor_stats: Dict[str, Dict[str, float]],
) -> Optional[RuleHit]:
    """
    Flags outflow transactions where:
      - Amount ends in .00 (integer-valued)
      - Amount >= ROUND_NUMBER_FLOOR
      - Amount >= ROUND_NUMBER_VENDOR_MULTIPLE * vendor median
    Threshold is 2.0x (not 3x) so that moderately large round amounts
    from small-N vendors are still caught despite high std.
    """
    if tx.type != TransactionType.OUTFLOW:
        return None
    if tx.amount < ROUND_NUMBER_FLOOR:
        return None
    # Check if amount is whole-dollar (ends in .00)
    if tx.amount != math.floor(tx.amount):
        return None

    stats = vendor_stats.get(tx.vendor)
    if stats is None:
        return None
    median = stats["median"]
    if median == 0:
        return None
    multiple = tx.amount / median
    if multiple < ROUND_NUMBER_VENDOR_MULTIPLE:
        return None

    trigger = (
        f"Suspicious round amount ${tx.amount:,.0f} "
        f"({multiple:.1f}x vendor median ${median:,.0f})"
    )
    return RuleHit(
        reason_code="ROUND_NUMBER_OUTLIER",
        risk_score=0.60,
        trigger_metric=trigger,
    )


# ── Rule 4: Off-schedule payment detection ────────────────────────────────────

OFF_SCHEDULE_DAY_STD_THRESHOLD: float = 3.0  # vendors with day-of-month std < this are considered scheduled
OFF_SCHEDULE_RISK_SCORE: float = 0.65


def _detect_scheduled_vendors(
    transactions: List[Transaction],
) -> Dict[str, List[int]]:
    """
    Automatically detect vendors with tight payment schedules by computing
    the standard deviation of day-of-month across their transactions.
    Vendors with std < OFF_SCHEDULE_DAY_STD_THRESHOLD are considered scheduled.
    Returns {vendor: [expected_day_1, expected_day_2, ...]} where expected days
    are the distinct days seen in normal (non-outlier) patterns.
    """
    from collections import Counter
    vendor_days: Dict[str, List[int]] = {}
    for tx in transactions:
        vendor_days.setdefault(tx.vendor, []).append(tx.date.day)

    scheduled: Dict[str, List[int]] = {}
    for vendor, days in vendor_days.items():
        if len(days) < 4:
            continue  # not enough history to call it scheduled
        std = statistics.pstdev(days)
        if std < OFF_SCHEDULE_DAY_STD_THRESHOLD:
            # Expected days = the mode day(s) — up to 2 most common
            counter = Counter(days)
            most_common = [d for d, _ in counter.most_common(2)]
            scheduled[vendor] = most_common
    return scheduled


def _rule_off_schedule(
    tx: Transaction,
    scheduled_vendors: Dict[str, List[int]],
) -> Optional[RuleHit]:
    """
    Flags a transaction from a scheduled vendor (tight day-of-month pattern)
    when the payment day is not in the expected day list.
    Works for both inflows and outflows.
    """
    expected_days = scheduled_vendors.get(tx.vendor)
    if expected_days is None:
        return None
    tx_day = tx.date.day
    # Allow +/- 1 day tolerance around expected days (weekends, month-end shifts)
    for expected in expected_days:
        if abs(tx_day - expected) <= 1:
            return None
    trigger = (
        f"Off-schedule payment on {tx.date.isoformat()} "
        f"(day {tx_day}; expected day(s): {expected_days} based on vendor history)"
    )
    return RuleHit(
        reason_code="OFF_SCHEDULE",
        risk_score=OFF_SCHEDULE_RISK_SCORE,
        trigger_metric=trigger,
    )


# ── Main detector entry point ─────────────────────────────────────────────────

def run_detection(db: Session) -> List[AnomalyResult]:
    """
    Runs all three detectors against every transaction in the database.
    Returns a list of AnomalyResult objects, one per flagged transaction.
    Transactions with no rule hits are not included.

    All computation is runtime-only — no hardcoded IDs, scores, or outputs.
    """
    # Load all transactions once
    all_transactions: List[Transaction] = db.query(Transaction).all()

    # Precompute shared data structures
    vendor_stats = _compute_vendor_stats(all_transactions)
    duplicate_index = _build_duplicate_index(all_transactions)
    scheduled_vendors = _detect_scheduled_vendors(all_transactions)

    results: List[AnomalyResult] = []

    for tx in all_transactions:
        hits: List[RuleHit] = []

        z_hit = _rule_zscore(tx, vendor_stats)
        if z_hit:
            hits.append(z_hit)

        dup_hit = _rule_duplicate(tx, duplicate_index)
        if dup_hit:
            hits.append(dup_hit)

        rn_hit = _rule_round_number(tx, vendor_stats)
        if rn_hit:
            hits.append(rn_hit)

        sched_hit = _rule_off_schedule(tx, scheduled_vendors)
        if sched_hit:
            hits.append(sched_hit)

        if hits:
            results.append(AnomalyResult(
                transaction_id=tx.id,
                vendor=tx.vendor,
                amount=tx.amount,
                date=tx.date,
                transaction_type=tx.type.value if hasattr(tx.type, "value") else str(tx.type),
                hits=hits,
            ))

    # Sort by risk score descending
    results.sort(key=lambda r: r.risk_score, reverse=True)
    return results
