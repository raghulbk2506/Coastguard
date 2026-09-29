"""Tests for SQLite write-through caching layer."""

import pytest
from costguard.core.cache import PricingCache
from costguard.core.models import PriceRate, PricingSource


@pytest.fixture
def temp_cache(tmp_path):
    db_file = str(tmp_path / "test_cache.db")
    return PricingCache(db_path=db_file)


def test_cache_miss_and_set(temp_cache):
    # Initial lookup is a miss
    rate = temp_cache.get("Standard_B1s", "eastus", "USD")
    assert rate is None
    assert temp_cache.misses == 1

    # Store rate
    item = PriceRate(
        sku="Standard_B1s",
        region="eastus",
        currency="USD",
        hourly_rate=0.0104,
        monthly_rate=7.592,
        meter_name="B1s",
        product_name="Virtual Machines",
    )
    temp_cache.set(item)

    # Subsequent lookup is a hit
    cached = temp_cache.get("Standard_B1s", "eastus", "USD")
    assert cached is not None
    assert cached.hourly_rate == 0.0104
    assert cached.source == PricingSource.CACHE
    assert temp_cache.hits == 1


def test_cache_clear(temp_cache):
    item = PriceRate(
        sku="Standard_B2s",
        region="eastus",
        currency="USD",
        hourly_rate=0.0416,
        monthly_rate=30.368,
    )
    temp_cache.set(item)
    assert temp_cache.count() == 1

    cleared = temp_cache.clear()
    assert cleared == 1
    assert temp_cache.count() == 0


def test_cache_stats(temp_cache):
    temp_cache.get("Standard_NonExistent", "eastus", "USD")  # miss
    item = PriceRate(
        sku="Standard_D2s_v3",
        region="eastus",
        currency="USD",
        hourly_rate=0.096,
        monthly_rate=70.08,
    )
    temp_cache.set(item)
    temp_cache.get("Standard_D2s_v3", "eastus", "USD")  # hit

    stats = temp_cache.get_stats()
    assert stats.total_entries == 1
    assert stats.cache_hits == 1
    assert stats.cache_misses == 1
    assert stats.hit_rate_pct == 50.0
