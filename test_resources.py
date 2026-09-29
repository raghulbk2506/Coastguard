"""Tests for resource extraction, normalization, and categorization."""

from costguard.core.resources import (
    determine_disk_tier,
    extract_resource_details,
    normalize_region,
)


def test_normalize_region():
    assert normalize_region("East US") == "eastus"
    assert normalize_region("eastus") == "eastus"
    assert normalize_region("West Europe") == "westeurope"
    assert normalize_region("Central-US") == "centralus"
    assert normalize_region(None) == "eastus"


def test_disk_tier_determination():
    sku, disp = determine_disk_tier("Premium_LRS", 128)
    assert sku == "Premium_SSD_Managed_Disk_P10"
    assert "P10" in disp

    sku_std, disp_std = determine_disk_tier("Standard_LRS", 128)
    assert sku_std == "Standard_HDD_Managed_Disk_S10"
    assert "S10" in disp_std


def test_extract_linux_vm():
    change = {
        "address": "azurerm_linux_virtual_machine.my_vm",
        "type": "azurerm_linux_virtual_machine",
        "change": {
            "actions": ["create"],
            "before": None,
            "after": {
                "size": "Standard_B1s",
                "location": "East US",
            },
        },
    }
    extracted = extract_resource_details(change)
    assert extracted.is_billable is True
    assert extracted.sku == "Standard_B1s"
    assert extracted.region == "eastus"
    assert extracted.os_type == "Linux"


def test_extract_windows_vm():
    change = {
        "address": "azurerm_windows_virtual_machine.win_vm",
        "type": "azurerm_windows_virtual_machine",
        "change": {
            "actions": ["create"],
            "before": None,
            "after": {
                "size": "Standard_D2s_v3",
                "location": "westeurope",
            },
        },
    }
    extracted = extract_resource_details(change)
    assert extracted.is_billable is True
    assert extracted.sku == "Standard_D2s_v3"
    assert extracted.region == "westeurope"
    assert extracted.os_type == "Windows"


def test_skip_non_billable_resources():
    non_billable_types = [
        "azurerm_resource_group",
        "azurerm_virtual_network",
        "azurerm_subnet",
        "azurerm_network_security_group",
        "azurerm_route_table",
    ]
    for rtype in non_billable_types:
        change = {
            "address": f"{rtype}.test",
            "type": rtype,
            "change": {
                "actions": ["create"],
                "before": None,
                "after": {"name": "test", "location": "eastus"},
            },
        }
        extracted = extract_resource_details(change)
        assert extracted.is_billable is False
        assert "non-billable" in extracted.skip_reason.lower()
