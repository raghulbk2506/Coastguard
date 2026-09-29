"""Tests for monthly cost and financial delta calculation engine."""

from unittest.mock import MagicMock
import pytest

from costguard.core.calculator import HOURS_PER_MONTH, CostCalculator
from costguard.core.models import ActionType, ExtractedResource, PriceRate
from costguard.core.pricing import AzurePricingEngine


@pytest.fixture
def mock_pricing_engine():
    engine = MagicMock(spec=AzurePricingEngine)
    engine.cache = MagicMock()
    engine.cache.hits = 0
    engine.cache.api_calls = 0

    def mock_get_price(sku, region, currency="USD", os_type="Linux", resource_type="virtual_machine", use_cache=True):
        rates = {
            "Standard_B1s": 0.0104,
            "Standard_B2s": 0.0416,
            "Standard_D2s_v3": 0.0960,
            "Premium_SSD_Managed_Disk_P10": 19.71 / 730.0,
        }
        hourly = rates.get(sku, 0.0)
        return PriceRate(
            sku=sku,
            region=region,
            currency=currency,
            hourly_rate=hourly,
            monthly_rate=hourly * 730.0,
            meter_name=sku,
        ), None

    engine.get_price.side_effect = mock_get_price
    return engine


def test_hours_per_month_is_730():
    assert HOURS_PER_MONTH == 730.0


def test_positive_delta_create(mock_pricing_engine):
    calculator = CostCalculator(pricing_engine=mock_pricing_engine)
    res = ExtractedResource(
        address="azurerm_linux_virtual_machine.new_vm",
        resource_type="azurerm_linux_virtual_machine",
        action=ActionType.CREATE,
        sku="Standard_B1s",
        region="eastus",
    )
    item, _ = calculator.calculate_resource_cost(res)
    assert item.old_monthly == 0.0
    assert item.new_monthly == round(0.0104 * 730, 2)
    assert item.delta_monthly == item.new_monthly
    assert item.delta_monthly > 0


def test_negative_delta_delete(mock_pricing_engine):
    calculator = CostCalculator(pricing_engine=mock_pricing_engine)
    res = ExtractedResource(
        address="azurerm_linux_virtual_machine.old_vm",
        resource_type="azurerm_linux_virtual_machine",
        action=ActionType.DELETE,
        sku=None,
        old_sku="Standard_B1s",
        region="eastus",
        old_region="eastus",
    )
    item, _ = calculator.calculate_resource_cost(res)
    assert item.old_monthly == round(0.0104 * 730, 2)
    assert item.new_monthly == 0.0
    assert item.delta_monthly == -item.old_monthly
    assert item.delta_monthly < 0


def test_update_delta(mock_pricing_engine):
    calculator = CostCalculator(pricing_engine=mock_pricing_engine)
    res = ExtractedResource(
        address="azurerm_linux_virtual_machine.app",
        resource_type="azurerm_linux_virtual_machine",
        action=ActionType.UPDATE,
        old_sku="Standard_B1s",
        sku="Standard_B2s",
        region="eastus",
        old_region="eastus",
    )
    item, _ = calculator.calculate_resource_cost(res)
    assert item.old_monthly == round(0.0104 * 730, 2)  # 7.59
    assert item.new_monthly == round(0.0416 * 730, 2)  # 30.37
    assert item.delta_monthly == round(item.new_monthly - item.old_monthly, 2)  # +22.78


def test_zero_delta_metadata_only(mock_pricing_engine):
    calculator = CostCalculator(pricing_engine=mock_pricing_engine)
    res = ExtractedResource(
        address="azurerm_linux_virtual_machine.tags_only",
        resource_type="azurerm_linux_virtual_machine",
        action=ActionType.UPDATE,
        old_sku="Standard_B2s",
        sku="Standard_B2s",
        region="eastus",
        old_region="eastus",
        tags={"env": "prod"},
    )
    item, _ = calculator.calculate_resource_cost(res)
    assert item.delta_monthly == 0.0
    assert item.old_monthly == item.new_monthly


def test_full_plan_totals(mock_pricing_engine):
    calculator = CostCalculator(pricing_engine=mock_pricing_engine)
    resources = [
        ExtractedResource(
            address="azurerm_linux_virtual_machine.app",
            resource_type="azurerm_linux_virtual_machine",
            action=ActionType.UPDATE,
            old_sku="Standard_B1s",
            sku="Standard_B2s",
            region="eastus",
            old_region="eastus",
        ),
        ExtractedResource(
            address="azurerm_managed_disk.data",
            resource_type="azurerm_managed_disk",
            action=ActionType.CREATE,
            sku="Premium_SSD_Managed_Disk_P10",
            region="eastus",
            storage_account_type="Premium_LRS",
            disk_size_gb=128,
        ),
        ExtractedResource(
            address="azurerm_linux_virtual_machine.old",
            resource_type="azurerm_linux_virtual_machine",
            action=ActionType.DELETE,
            old_sku="Standard_B1s",
            region="eastus",
            old_region="eastus",
        ),
    ]
    result = calculator.analyze_plan(resources, skipped_resources=[], max_increase=50.0)
    assert result.prior_total == 15.18
    assert result.projected_total == 50.08
    assert result.net_delta == 34.90
    assert result.verdict.passed is True
    assert result.verdict.exit_code == 0
