"""Tests for Terraform Plan JSON parsing."""

import pytest
from costguard.core.models import ActionType
from costguard.core.parser import ParserError, TerraformPlanParser


def test_parse_valid_json():
    data = TerraformPlanParser.parse_json('{"resource_changes": []}')
    assert "resource_changes" in data


def test_parse_invalid_json():
    with pytest.raises(ParserError):
        TerraformPlanParser.parse_json("invalid json {")


def test_parse_empty_input():
    with pytest.raises(ParserError):
        TerraformPlanParser.parse_json("")


def test_parse_create_action():
    plan = {
        "resource_changes": [
            {
                "address": "azurerm_linux_virtual_machine.vm1",
                "type": "azurerm_linux_virtual_machine",
                "change": {
                    "actions": ["create"],
                    "before": None,
                    "after": {"size": "Standard_B1s", "location": "eastus"}
                }
            }
        ]
    }
    billable, skipped = TerraformPlanParser.parse_plan(plan)
    assert len(billable) == 1
    assert billable[0].action == ActionType.CREATE
    assert billable[0].sku == "Standard_B1s"
    assert billable[0].region == "eastus"


def test_parse_delete_action():
    plan = {
        "resource_changes": [
            {
                "address": "azurerm_linux_virtual_machine.old_vm",
                "type": "azurerm_linux_virtual_machine",
                "change": {
                    "actions": ["delete"],
                    "before": {"size": "Standard_B2s", "location": "eastus"},
                    "after": None
                }
            }
        ]
    }
    billable, skipped = TerraformPlanParser.parse_plan(plan)
    assert len(billable) == 1
    assert billable[0].action == ActionType.DELETE
    assert billable[0].old_sku == "Standard_B2s"


def test_parse_update_action():
    plan = {
        "resource_changes": [
            {
                "address": "azurerm_linux_virtual_machine.app",
                "type": "azurerm_linux_virtual_machine",
                "change": {
                    "actions": ["update"],
                    "before": {"size": "Standard_B1s", "location": "eastus"},
                    "after": {"size": "Standard_B2s", "location": "eastus"}
                }
            }
        ]
    }
    billable, skipped = TerraformPlanParser.parse_plan(plan)
    assert len(billable) == 1
    assert billable[0].action == ActionType.UPDATE
    assert billable[0].old_sku == "Standard_B1s"
    assert billable[0].sku == "Standard_B2s"


def test_parse_replacement_action():
    plan = {
        "resource_changes": [
            {
                "address": "azurerm_linux_virtual_machine.app",
                "type": "azurerm_linux_virtual_machine",
                "change": {
                    "actions": ["delete", "create"],
                    "before": {"size": "Standard_B1s", "location": "eastus"},
                    "after": {"size": "Standard_D2s_v3", "location": "eastus"}
                }
            }
        ]
    }
    billable, skipped = TerraformPlanParser.parse_plan(plan)
    assert len(billable) == 1
    assert billable[0].action == ActionType.REPLACE
