import datetime
import logging

import pytest

from custom_components.greenchoice.api import GreenchoiceApi
from custom_components.greenchoice.model import Consumptions, MeterReadings, Rates


@pytest.mark.asyncio
async def test_update_request(
    mock_api,
):
    mock_api(has_gas=True, has_rates=True)

    async with GreenchoiceApi("fake_user", "fake_password") as greenchoice_api:
        result = await greenchoice_api.update()

    assert result.model_dump() == {
        "electricity_consumption_off_peak": 60000.0,
        "electricity_consumption_normal": 50000.0,
        "electricity_consumption_total": 110000.0,
        "electricity_feed_in_off_peak": 6000.0,
        "electricity_feed_in_normal": 5000.0,
        "electricity_feed_in_total": 11000.0,
        "electricity_reading_date": datetime.datetime(2022, 5, 6, 0, 0),
        "electricity_price_single": 0.25,
        "electricity_price_off_peak": 0.2,
        "electricity_price_normal": 0.3,
        "electricity_feed_in_compensation": 0.08,
        "electricity_feed_in_cost": 0.01,
        "gas_consumption": 10000.0,
        "gas_reading_date": datetime.datetime(2022, 5, 6, 0, 0),
        "gas_price": 0.8,
    }


@pytest.mark.asyncio
async def test_update_request_without_gas(mock_api):
    mock_api(has_gas=False)

    async with GreenchoiceApi("fake_user", "fake_password") as greenchoice_api:
        result = await greenchoice_api.update()

    assert result.model_dump() == {
        "electricity_consumption_off_peak": 60000.0,
        "electricity_consumption_normal": 50000.0,
        "electricity_consumption_total": 110000.0,
        "electricity_feed_in_off_peak": 6000.0,
        "electricity_feed_in_normal": 5000.0,
        "electricity_feed_in_total": 11000.0,
        "electricity_reading_date": datetime.datetime(2022, 5, 6, 0, 0),
        "electricity_price_single": 0.25,
        "electricity_price_off_peak": 0.2,
        "electricity_price_normal": 0.3,
        "electricity_feed_in_compensation": 0.08,
        "electricity_feed_in_cost": 0.01,
        "gas_consumption": None,
        "gas_reading_date": None,
        "gas_price": None,
    }


@pytest.mark.asyncio
async def test_update_request_without_rates(mock_api):
    mock_api(has_rates=False)

    async with GreenchoiceApi("fake_user", "fake_password") as greenchoice_api:
        result = await greenchoice_api.update()

    assert result.model_dump() == {
        "electricity_consumption_off_peak": 60000.0,
        "electricity_consumption_normal": 50000.0,
        "electricity_consumption_total": 110000.0,
        "electricity_feed_in_off_peak": 6000.0,
        "electricity_feed_in_normal": 5000.0,
        "electricity_feed_in_total": 11000.0,
        "electricity_reading_date": datetime.datetime(2022, 5, 6, 0, 0),
        "electricity_price_single": None,
        "electricity_price_off_peak": None,
        "electricity_price_normal": None,
        "electricity_feed_in_compensation": None,
        "electricity_feed_in_cost": None,
        "gas_consumption": 10000.0,
        "gas_reading_date": datetime.datetime(2022, 5, 6, 0, 0),
        "gas_price": None,
    }


@pytest.mark.asyncio
async def test_update_request_with_agreement_id(
    mock_api,
):
    mock_api()

    async with GreenchoiceApi(
        "fake_user", "fake_password", customer_number=2222, agreement_id=1111
    ) as greenchoice_api:
        result = await greenchoice_api.update()

    assert result.model_dump() == {
        "electricity_consumption_off_peak": 60000.0,
        "electricity_consumption_normal": 50000.0,
        "electricity_consumption_total": 110000.0,
        "electricity_feed_in_off_peak": 6000.0,
        "electricity_feed_in_normal": 5000.0,
        "electricity_feed_in_total": 11000.0,
        "electricity_reading_date": datetime.datetime(2022, 5, 6, 0, 0),
        "electricity_price_single": 0.25,
        "electricity_price_off_peak": 0.2,
        "electricity_price_normal": 0.3,
        "electricity_feed_in_compensation": 0.08,
        "electricity_feed_in_cost": 0.01,
        "gas_consumption": 10000.0,
        "gas_reading_date": datetime.datetime(2022, 5, 6, 0, 0),
        "gas_price": 0.8,
    }


@pytest.mark.asyncio
async def test_update_request_gas_only(mock_api):
    """A gas-only agreement still reports a gas price.

    Regression test: Greenchoice moved the rates to
    ``/api/v3/.../rate-details``. The retired v2 ``contracts/current`` answered
    404, which the client turned into ``{}``, and the resulting ValidationError
    was swallowed — leaving gas_price silently ``unknown``.
    """
    mock_api(has_gas=True, has_rates=True, has_electricity=False)

    async with GreenchoiceApi("fake_user", "fake_password") as greenchoice_api:
        result = await greenchoice_api.update()

    assert result.gas_price == 0.8
    assert result.gas_consumption == 10000.0
    assert result.electricity_price_single is None
    assert result.electricity_price_normal is None
    assert result.electricity_price_off_peak is None
    assert result.electricity_feed_in_compensation is None
    assert result.electricity_feed_in_cost is None


@pytest.mark.asyncio
async def test_update_request_rates_without_any_rates_warns(mock_api, caplog):
    """A rate response with no gas and no electricity must be logged, not dropped."""
    mock_api(has_gas=True, has_rates=True, empty_rates=True)

    async with GreenchoiceApi("fake_user", "fake_password") as greenchoice_api:
        result = await greenchoice_api.update()

    assert result.gas_price is None
    assert result.electricity_price_single is None
    assert "contain no gas and no electricity rates" in caplog.text


@pytest.mark.asyncio
async def test_rate_details_404_on_ended_supply_is_not_a_warning(mock_api, caplog):
    """An ended agreement has no current rates — that is normal, not an anomaly.

    Greenchoice serves rate-details for any date inside a contract period and
    404s outside one, so a terminated agreement 404s forever. Reporting that as
    a shape anomaly hides the real one: an endpoint retirement.
    """
    caplog.set_level(logging.INFO)
    mock_api(has_rates=False, supply_ended=True)

    async with GreenchoiceApi("fake_user", "fake_password") as greenchoice_api:
        result = await greenchoice_api.update()

    assert result.gas_price is None
    assert result.electricity_price_single is None
    assert "1111" in caplog.text
    assert "2026-03-08" in caplog.text
    assert "contain no gas and no electricity rates" not in caplog.text
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


@pytest.mark.asyncio
async def test_rate_details_404_on_undated_ended_supply_is_not_a_warning(
    mock_api, caplog
):
    """A "Past" supply with no end date is still an ended supply, not an anomaly."""
    caplog.set_level(logging.INFO)
    mock_api(has_rates=False, supply_ended=True, supply_ended_dated=False)

    async with GreenchoiceApi("fake_user", "fake_password") as greenchoice_api:
        result = await greenchoice_api.update()

    assert result.gas_price is None
    assert "reports its energy supply as ended" in caplog.text
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


@pytest.mark.asyncio
async def test_rate_details_404_on_active_supply_still_warns(mock_api, caplog):
    """A 404 for an agreement the account still supplies is an API problem."""
    caplog.set_level(logging.INFO)
    mock_api(has_rates=False)

    async with GreenchoiceApi("fake_user", "fake_password") as greenchoice_api:
        result = await greenchoice_api.update()

    assert result.gas_price is None
    assert [r.levelno for r in caplog.records if r.levelno >= logging.WARNING] == [
        logging.WARNING
    ]
    assert "energy supply is active" in caplog.text


def test_live_rate_details_response_parses_electricity_and_gas_rates(
    rate_details_live_response,
):
    """Lock the electricity field names against a real Greenchoice response.

    The electricity mapping was originally guessed from the portal's frontend
    because the development account had no electricity contract. This fixture
    is an actual in-contract response; the expected numbers below are read off
    it by hand, so a renamed or re-nested field fails here.
    """

    rates = Rates.model_validate(rate_details_live_response)

    assert rates.start == datetime.date(2025, 9, 11)
    electricity = rates.electricity
    assert electricity is not None
    assert electricity.delivery_single is not None
    assert electricity.delivery_single.all_in_rate_including_vat == 0.19326
    assert electricity.delivery_normal is not None
    assert electricity.delivery_normal.all_in_rate_including_vat == 0.20445
    assert electricity.delivery_low is not None
    assert electricity.delivery_low.all_in_rate_including_vat == 0.17955
    # A bare number, not a nested rate object — the other original guess.
    assert electricity.feed_in_compensation == 0.08
    assert electricity.feed_in_costs is None
    assert rates.gas is not None
    assert rates.gas.delivery is not None
    assert rates.gas.delivery.all_in_rate_including_vat == 0.93097


@pytest.mark.asyncio
async def test_unparseable_electricity_still_reports_gas(mock_api, caplog):
    """A wrong electricity shape must not blank the gas price.

    Gas and electricity are independent sections of one response; validating
    them together would let an unexpected electricity shape discard a valid
    gas rate. Relevant because the electricity mapping is inferred from the
    portal frontend rather than an observed response.
    """
    mock_api(has_gas=True, has_rates=True, bad_electricity=True)

    async with GreenchoiceApi("fake_user", "fake_password") as greenchoice_api:
        result = await greenchoice_api.update()

    assert result.gas_price == 0.8
    assert result.electricity_price_single is None
    assert result.electricity_feed_in_compensation is None
    assert "Ignoring unparseable electricity_rates" in caplog.text


@pytest.mark.asyncio
async def test_unparseable_period_still_reports_rates(mock_api, rate_details_response):
    """start/end only label log lines, so a bad one must not cost us a rate."""
    payload = dict(rate_details_response, start="not-a-date")
    rates = Rates.model_validate(payload)

    assert rates.start is None
    assert rates.gas is not None
    assert rates.gas.delivery is not None
    assert rates.gas.delivery.all_in_rate_including_vat == 0.8


def test_meter_row_carrying_both_fuels_reports_both():
    """One row per date, both fuels: the shape Greenchoice sends now.

    Readings used to arrive one fuel at a time, so ``gas is not None`` was
    enough to tell the two apart. A dual-fuel row makes that test true for
    every row, which left the electricity sensors at ``unknown``.
    """
    readings = MeterReadings.model_validate(
        {
            "year": 2026,
            "hasElectricity": True,
            "hasGas": True,
            "months": [
                {
                    "month": 9,
                    "readings": [
                        {
                            "readingDate": "2026-09-20T00:00:00",
                            "normalConsumption": 18863,
                            "offPeakConsumption": 20168,
                            "normalFeedIn": 19049,
                            "offPeakFeedIn": 7866,
                            "gas": 13941,
                        }
                    ],
                }
            ],
        }
    )

    electricity = readings.last_electricity_reading
    gas = readings.last_gas_reading

    assert electricity is not None
    assert electricity.normal_consumption == 18863
    assert gas is not None
    assert gas.gas == 13941


def test_gas_only_rows_report_no_electricity_reading():
    """A gas-only agreement leaves the electricity registers null."""
    readings = MeterReadings.model_validate(
        {
            "year": 2026,
            "hasElectricity": False,
            "hasGas": True,
            "months": [
                {
                    "month": 9,
                    "readings": [
                        {
                            "readingDate": "2026-09-20T00:00:00",
                            "normalConsumption": None,
                            "offPeakConsumption": None,
                            "normalFeedIn": None,
                            "offPeakFeedIn": None,
                            "gas": 13941,
                        }
                    ],
                }
            ],
        }
    )

    assert readings.last_electricity_reading is None
    assert readings.last_gas_reading is not None


def test_consumptions_maps_v3_products_onto_per_fuel_items(
    consumptions_hour_with_gas_response,
):
    """The v3 ``periods``/``products`` shape feeds the statistics unchanged."""
    consumptions = Consumptions.model_validate(consumptions_hour_with_gas_response)

    item = consumptions.consumption_costs[0]

    assert item.electricity is not None
    assert item.electricity.total_delivery_consumption == 0.422
    assert item.electricity.total_delivery_costs == 0.11276
    assert item.electricity.total_feed_in_consumption == 0
    assert item.electricity.total_fixed_costs == -0.00379
    assert item.gas is not None
    assert item.gas.total_delivery_consumption == 0.005
    assert item.gas.total_delivery_costs == 0.00653
    assert item.gas.total_fixed_costs == 0.04199


def test_consumptions_without_gas_product_leaves_gas_unset(
    consumptions_hour_response,
):
    """An electricity-only day carries no Gas product, so no gas item."""
    consumptions = Consumptions.model_validate(consumptions_hour_response)

    item = consumptions.consumption_costs[0]

    assert item.electricity is not None
    assert item.gas is None


def test_consumptions_request_targets_v3():
    """The v2 path 404s; the query parameters are unchanged."""
    url = Consumptions.Request(
        customer_number=2222,
        agreement_id=1111,
        interval="Hour",
        start=datetime.date(2026, 9, 20),
        end=datetime.date(2026, 9, 21),
    ).build_url()

    assert url == (
        "/api/v3/customers/2222/agreements/1111/consumptions"
        "?interval=Hour&start=2026-09-20&end=2026-09-21"
    )


def test_consumptions_total_block_has_no_timestamp(
    consumptions_hour_with_gas_response,
):
    """The range-level ``total`` repeats the products shape without ``consumedOn``.

    Typing it as a period made the whole response unparseable, which is how
    the v2 -> v3 migration failed the first time round.
    """
    consumptions = Consumptions.model_validate(consumptions_hour_with_gas_response)

    assert consumptions.total is not None
    electricity = consumptions.total.totals("electricity")
    assert electricity is not None
    assert electricity.consumption_quantity is not None
    assert len(consumptions.periods) == 24
