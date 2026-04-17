"""
Tests that _maybe_visit_detail handles timeouts gracefully — a timeout on
a detail page must never crash the crawl.
"""
from unittest.mock import patch, MagicMock
import pytest

from autobeat import _maybe_visit_detail
from models import Car


def _make_car(url: str) -> Car:
    return Car(url=url, brand="test", model="model", price=1000, price_local_currency=3000)


def test_detail_visit_timeout_does_not_raise():
    """A TimeoutError from fetch_html must be caught — not propagated."""
    cars = [_make_car("https://abw.by/cars/detail/geely/galaxy-e5/25833010")]
    with patch("autobeat.random.random", return_value=0.0):  # force visit
        with patch("autobeat.fetch_html", side_effect=Exception("Timeout 60000ms exceeded")):
            # must not raise
            _maybe_visit_detail(cars)


def test_detail_visit_timeout_logs_warning(caplog):
    """A timeout must log a warning so it is visible in logs."""
    import logging
    cars = [_make_car("https://abw.by/cars/detail/geely/galaxy-e5/25833010")]
    with patch("autobeat.random.random", return_value=0.0):
        with patch("autobeat.fetch_html", side_effect=Exception("Timeout 60000ms exceeded")):
            with caplog.at_level(logging.WARNING, logger="root"):
                _maybe_visit_detail(cars)
    assert any("timed out" in r.message for r in caplog.records)


def test_detail_visit_success_does_not_raise():
    """A successful detail visit works normally."""
    cars = [_make_car("https://abw.by/cars/detail/skoda/fabia/123")]
    mock_soup = MagicMock()
    with patch("autobeat.random.random", return_value=0.0):
        with patch("autobeat.fetch_html", return_value=mock_soup) as mock_fetch:
            _maybe_visit_detail(cars)
    mock_fetch.assert_called_once_with(cars[0].url)


def test_detail_visit_skipped_when_chance_not_met():
    """When random.random() returns above DETAIL_VISIT_CHANCE, fetch_html must not be called."""
    cars = [_make_car("https://abw.by/cars/detail/skoda/fabia/123")]
    with patch("autobeat.random.random", return_value=1.0):  # never visit
        with patch("autobeat.fetch_html") as mock_fetch:
            _maybe_visit_detail(cars)
    mock_fetch.assert_not_called()


def test_detail_visit_skipped_when_no_cars():
    """Empty car list must result in no fetch attempt."""
    with patch("autobeat.fetch_html") as mock_fetch:
        _maybe_visit_detail([])
    mock_fetch.assert_not_called()
