"""Unit tests for domain value objects."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError
from shared.domain import Address, Currency, DateRange, Money


class TestMoney:
    def test_creates_with_decimal_amount(self):
        money = Money(amount=Decimal("1234.56"), currency=Currency.GBP)

        assert money.amount == Decimal("1234.56")
        assert money.currency == Currency.GBP

    def test_defaults_to_gbp(self):
        money = Money(amount=Decimal("100"))

        assert money.currency == Currency.GBP

    def test_string_representation(self):
        money = Money(amount=Decimal("1234.56"), currency=Currency.USD)

        assert str(money) == "USD 1,234.56"

    def test_is_immutable(self):
        money = Money(amount=Decimal("100"))

        with pytest.raises(ValidationError):
            money.amount = Decimal("200")  # type: ignore[misc]


class TestAddress:
    def test_creates_with_required_fields(self):
        address = Address(
            line_1="86-90 Paul Street",
            city="London",
            postcode="EC2A 4NE",
        )

        assert address.country == "United Kingdom"

    def test_rejects_empty_line_1(self):
        with pytest.raises(ValidationError):
            Address(line_1="", city="London", postcode="EC2A 4NE")


class TestDateRange:
    def test_calculates_inclusive_days(self):
        date_range = DateRange(start=date(2026, 1, 1), end=date(2026, 1, 10))

        assert date_range.days == 10

    def test_single_day_range_is_one_day(self):
        date_range = DateRange(start=date(2026, 1, 1), end=date(2026, 1, 1))

        assert date_range.days == 1

    def test_rejects_end_before_start(self):
        with pytest.raises(ValidationError, match="end date must be on or after start date"):
            DateRange(start=date(2026, 1, 10), end=date(2026, 1, 1))
