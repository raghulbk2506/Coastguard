"""Tests for Azure Pricing Engine and filtering logic."""

from unittest.mock import MagicMock, patch
import httpx
import pytest

from costguard.core.cache import PricingCache
from costguard.core.models import PricingSource
from costguard.core.pricing import AzurePricingEngine


@pytest.fixture
def mock_cache(tmp_path):
    db_file = str(tmp_path / "test_pricing.db")
    return PricingCache(db_path=db_file)


def test_spot_and_low_priority_filtered_out(mock_cache):
    """Verify that Spot and Low Priority meters are strictly excluded."""
    engine = AzurePricingEngine(cache=mock_cache)

    mock_response_data = {
        "BillingCurrency": "USD",
        "Items": [
            {
                "currencyCode": "USD",
                "retailPrice": 0.008,
                "unitOfMeasure": "1 Hour",
                "armRegionName": "eastus",
                "armSkuName": "Standard_B2s",
                "meterName": "B2s Spot",
                "productName": "Virtual Machines BS Series",
            },
            {
                "currencyCode": "USD",
                "retailPrice": 0.009,
                "unitOfMeasure": "1 Hour",
                "armRegionName": "eastus",
                "armSkuName": "Standard_B2s",
                "meterName": "B2s Low Priority",
                "productName": "Virtual Machines BS Series",
            },
            {
                "currencyCode": "USD",
                "retailPrice": 0.0416,
                "unitOfMeasure": "1 Hour",
                "armRegionName": "eastus",
                "armSkuName": "Standard_B2s",
                "meterName": "B2s",
                "productName": "Virtual Machines BS Series",
            },
        ],
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response_data

    with patch("httpx.Client.get", return_value=mock_resp):
        rate, warn = engine.get_price(sku="Standard_B2s", region="eastus", os_type="Linux")
        assert warn is None
        assert rate.hourly_rate == 0.0416
        assert "spot" not in rate.meter_name.lower()
        assert "low priority" not in rate.meter_name.lower()


def test_windows_vs_linux_filtering(mock_cache):
    """Verify that Linux requests filter out Windows meters and vice versa."""
    engine = AzurePricingEngine(cache=mock_cache)

    mock_response_data = {
        "BillingCurrency": "USD",
        "Items": [
            {
                "currencyCode": "USD",
                "retailPrice": 0.0416,
                "unitOfMeasure": "1 Hour",
                "armRegionName": "eastus",
                "armSkuName": "Standard_B2s",
                "meterName": "B2s",
                "productName": "Virtual Machines BS Series",
            },
            {
                "currencyCode": "USD",
                "retailPrice": 0.0832,
                "unitOfMeasure": "1 Hour",
                "armRegionName": "eastus",
                "armSkuName": "Standard_B2s",
                "meterName": "B2s",
                "productName": "Virtual Machines BS Series Windows",
            },
        ],
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response_data

    with patch("httpx.Client.get", return_value=mock_resp):
        # Linux VM should get 0.0416
        rate_linux, _ = engine.get_price(sku="Standard_B2s", region="eastus", os_type="Linux")
        assert rate_linux.hourly_rate == 0.0416

        # Windows VM should get 0.0832
        rate_win, _ = engine.get_price(sku="Standard_B2s", region="eastus", os_type="Windows", use_cache=False)
        assert rate_win.hourly_rate == 0.0832


def test_unknown_sku_handling(mock_cache):
    """Verify that unknown SKUs return 0.0 rate and warning without crashing."""
    engine = AzurePricingEngine(cache=mock_cache)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"Items": []}

    with patch("httpx.Client.get", return_value=mock_resp):
        rate, warn = engine.get_price(sku="Custom_Unknown_SKU", region="eastus")
        assert rate.hourly_rate == 0.0
        assert warn is not None
        assert "not found in Azure Retail API" in warn


def test_network_failure_fallback(mock_cache):
    """Verify graceful handling when network times out."""
    engine = AzurePricingEngine(cache=mock_cache)

    with patch("httpx.Client.get", side_effect=httpx.ConnectTimeout("Connection timed out")):
        rate, warn = engine.get_price(sku="Standard_B1s", region="eastus", use_cache=False)
        assert rate.hourly_rate == 0.0
        assert rate.source == PricingSource.FALLBACK
        assert "Network unavailable" in warn
