from datetime import datetime, timedelta

from src.quality_policy import quality_reasons


def good_trip(**overrides):
    row = {
        "pickup_datetime": datetime(2024, 1, 1, 9, 0),
        "dropoff_datetime": datetime(2024, 1, 1, 9, 18),
        "pickup_location_id": 161,
        "dropoff_location_id": 236,
        "trip_distance": 2.6,
        "fare_amount": 14.0,
        "total_amount": 18.5,
        "payment_type": 1,
    }
    row.update(overrides)
    return row


def test_valid_trip_has_no_reasons():
    assert quality_reasons(good_trip()) == []


def test_missing_required_field_is_rejected():
    reasons = quality_reasons(good_trip(pickup_location_id=None))
    assert any(r.startswith("MISSING_REQUIRED_FIELDS:") for r in reasons)


def test_dropoff_must_be_after_pickup():
    pickup = datetime(2024, 1, 1, 9, 0)
    assert "INVALID_TRIP_TIME_ORDER" in quality_reasons(
        good_trip(pickup_datetime=pickup, dropoff_datetime=pickup)
    )


def test_trip_distance_is_positive_and_bounded():
    assert "TRIP_DISTANCE_OUT_OF_POLICY_RANGE" in quality_reasons(good_trip(trip_distance=0))
    assert "TRIP_DISTANCE_OUT_OF_POLICY_RANGE" in quality_reasons(good_trip(trip_distance=100.1))


def test_negative_amounts_are_rejected():
    reasons = quality_reasons(good_trip(fare_amount=-1, total_amount=-1))
    assert "FARE_AMOUNT_NEGATIVE" in reasons
    assert "TOTAL_AMOUNT_NEGATIVE" in reasons


def test_unknown_payment_type_is_rejected():
    assert "PAYMENT_TYPE_OUTSIDE_DOMAIN" in quality_reasons(good_trip(payment_type=9))


def test_null_optional_payment_type_is_allowed():
    assert quality_reasons(good_trip(payment_type=None)) == []
