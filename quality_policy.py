"""Small, dependency-free reference implementation of the product's row policy.

Fabric enforcement uses equivalent vectorized PySpark expressions in notebook 02.
This module makes policy behavior testable in GitHub Actions without Fabric access.
"""
from __future__ import annotations

from typing import Any, Mapping

MAX_TRIP_DISTANCE_MILES = 100.0
VALID_PAYMENT_TYPES = {0, 1, 2, 3, 4, 5, 6}
REQUIRED_FIELDS = (
    "pickup_datetime",
    "dropoff_datetime",
    "pickup_location_id",
    "dropoff_location_id",
    "trip_distance",
    "fare_amount",
    "total_amount",
)


def quality_reasons(row: Mapping[str, Any]) -> list[str]:
    """Return policy violations for a row-like mapping; empty means publishable.

    Expected timestamp values can be Python datetime objects or comparable values.
    Null timestamps are reported before ordering is tested.
    """
    reasons: list[str] = []

    missing = [name for name in REQUIRED_FIELDS if row.get(name) is None]
    if missing:
        reasons.append("MISSING_REQUIRED_FIELDS:" + ",".join(missing))

    pickup = row.get("pickup_datetime")
    dropoff = row.get("dropoff_datetime")
    if pickup is not None and dropoff is not None and dropoff <= pickup:
        reasons.append("INVALID_TRIP_TIME_ORDER")

    distance = row.get("trip_distance")
    if distance is not None:
        try:
            if float(distance) <= 0 or float(distance) > MAX_TRIP_DISTANCE_MILES:
                reasons.append("TRIP_DISTANCE_OUT_OF_POLICY_RANGE")
        except (TypeError, ValueError):
            reasons.append("TRIP_DISTANCE_NOT_NUMERIC")

    for name in ("fare_amount", "total_amount"):
        value = row.get(name)
        if value is not None:
            try:
                if float(value) < 0:
                    reasons.append(f"{name.upper()}_NEGATIVE")
            except (TypeError, ValueError):
                reasons.append(f"{name.upper()}_NOT_NUMERIC")

    payment_type = row.get("payment_type")
    if payment_type is not None:
        try:
            if int(payment_type) not in VALID_PAYMENT_TYPES:
                reasons.append("PAYMENT_TYPE_OUTSIDE_DOMAIN")
        except (TypeError, ValueError):
            reasons.append("PAYMENT_TYPE_NOT_INTEGER")

    return reasons
