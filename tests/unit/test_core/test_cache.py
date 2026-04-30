"""
Unit tests for HexStrikeCache

Tests cover:
- Cache initialization
- Key generation
- Cache get/set operations
- Expiration handling
- LRU eviction
- Statistics tracking
- Cache size limits

Target: 90%+ code coverage
"""

import pytest
import sys
import os
import time
from unittest.mock import patch

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from hexstrike_server import HexStrikeCache


class TestCacheInitialization:
    """Test cache initialization and configuration"""

    def test_cache_initializes_with_defaults(self):
        """Test cache initializes with default parameters"""
        cache = HexStrikeCache()
        assert cache.max_size > 0
        assert cache.ttl > 0
        assert isinstance(cache.cache, dict)
        assert isinstance(cache.stats, dict)

    def test_cache_initializes_with_custom_size(self):
        """Test cache initialization with custom max size"""
        cache = HexStrikeCache(max_size=50)
        assert cache.max_size == 50

    def test_cache_initializes_with_custom_ttl(self):
        """Test cache initialization with custom TTL"""
        cache = HexStrikeCache(ttl=600)
        assert cache.ttl == 600

    def test_cache_stats_initialized(self):
        """Test cache statistics are initialized to zero"""
        cache = HexStrikeCache()
        assert cache.stats["hits"] == 0
        assert cache.stats["misses"] == 0
        assert cache.stats["evictions"] == 0

    def test_cache_is_empty_on_init(self):
        """Test cache is empty when initialized"""
        cache = HexStrikeCache()
        assert len(cache.cache) == 0


class TestKeyGeneration:
    """Test cache key generation"""

    def test_generate_key_returns_string(self):
        """Test that key generation returns a string"""
        cache = HexStrikeCache()
        key = cache._generate_key("command", {"param": "value"})
        assert isinstance(key, str)
        assert len(key) > 0

    def test_generate_key_consistent(self):
        """Test that same inputs generate same key"""
        cache = HexStrikeCache()
        key1 = cache._generate_key("nmap", {"target": "example.com"})
        key2 = cache._generate_key("nmap", {"target": "example.com"})
        assert key1 == key2

    def test_generate_key_different_for_different_commands(self):
        """Test that different commands generate different keys"""
        cache = HexStrikeCache()
        key1 = cache._generate_key("nmap", {"target": "example.com"})
        key2 = cache._generate_key("gobuster", {"target": "example.com"})
        assert key1 != key2

    def test_generate_key_different_for_different_params(self):
        """Test that different parameters generate different keys"""
        cache = HexStrikeCache()
        key1 = cache._generate_key("nmap", {"target": "example.com"})
        key2 = cache._generate_key("nmap", {"target": "other.com"})
        assert key1 != key2

    def test_generate_key_handles_empty_params(self):
        """Test key generation with empty parameters"""
        cache = HexStrikeCache()
        key = cache._generate_key("command", {})
        assert isinstance(key, str)
        assert len(key) > 0

    def test_generate_key_handles_complex_params(self):
        """Test key generation with complex nested parameters"""
        cache = HexStrikeCache()
        params = {
            "target": "example.com",
            "options": {
                "timeout": 30,
                "threads": 10
            },
            "flags": ["verbose", "aggressive"]
        }
        key = cache._generate_key("nmap", params)
        assert isinstance(key, str)

    def test_generate_key_param_order_doesnt_matter(self):
        """Test that parameter order doesn't affect key generation"""
        cache = HexStrikeCache()
        params1 = {"a": 1, "b": 2, "c": 3}
        params2 = {"c": 3, "a": 1, "b": 2}
        key1 = cache._generate_key("cmd", params1)
        key2 = cache._generate_key("cmd", params2)
        # Should be same because json.dumps uses sort_keys=True
        assert key1 == key2


class TestCacheGetSet:
    """Test cache get and set operations"""

    def test_set_and_get_basic(self):
        """Test basic set and get operations"""
        cache = HexStrikeCache()
        command = "nmap"
        params = {"target": "example.com"}
        result = {"status": "success", "data": "test"}

        cache.set(command, params, result)
        retrieved = cache.get(command, params)

        assert retrieved == result

    def test_get_nonexistent_returns_none(self):
        """Test that getting non-existent key returns None"""
        cache = HexStrikeCache()
        result = cache.get("nonexistent", {})
        assert result is None

    def test_get_increments_hit_stat(self):
        """Test that successful get increments hit counter"""
        cache = HexStrikeCache()
        cache.set("cmd", {"p": "v"}, {"result": "data"})

        initial_hits = cache.stats["hits"]
        cache.get("cmd", {"p": "v"})

        assert cache.stats["hits"] == initial_hits + 1

    def test_get_increments_miss_stat(self):
        """Test that failed get increments miss counter"""
        cache = HexStrikeCache()
        initial_misses = cache.stats["misses"]

        cache.get("nonexistent", {})

        assert cache.stats["misses"] == initial_misses + 1

    def test_set_overwrites_existing(self):
        """Test that set overwrites existing cached value"""
        cache = HexStrikeCache()
        command = "test"
        params = {"key": "value"}

        cache.set(command, params, {"result": "old"})
        cache.set(command, params, {"result": "new"})

        retrieved = cache.get(command, params)
        assert retrieved == {"result": "new"}

    def test_cache_stores_different_commands_separately(self):
        """Test that different commands are cached separately"""
        cache = HexStrikeCache()

        cache.set("cmd1", {"p": "v"}, {"result": "cmd1_result"})
        cache.set("cmd2", {"p": "v"}, {"result": "cmd2_result"})

        result1 = cache.get("cmd1", {"p": "v"})
        result2 = cache.get("cmd2", {"p": "v"})

        assert result1 == {"result": "cmd1_result"}
        assert result2 == {"result": "cmd2_result"}


class TestCacheExpiration:
    """Test cache expiration functionality"""

    def test_is_expired_fresh_entry(self):
        """Test that fresh entries are not expired"""
        cache = HexStrikeCache(ttl=3600)  # 1 hour TTL
        current_time = time.time()
        assert not cache._is_expired(current_time)

    def test_is_expired_old_entry(self):
        """Test that old entries are expired"""
        cache = HexStrikeCache(ttl=10)  # 10 second TTL
        old_time = time.time() - 20  # 20 seconds ago
        assert cache._is_expired(old_time)

    @patch('time.time')
    def test_get_returns_none_for_expired_entry(self, mock_time):
        """Test that get returns None for expired entries"""
        cache = HexStrikeCache(ttl=10)

        # Set time to now
        mock_time.return_value = 1000.0
        cache.set("cmd", {"p": "v"}, {"result": "data"})

        # Advance time past TTL
        mock_time.return_value = 1020.0  # 20 seconds later
        result = cache.get("cmd", {"p": "v"})

        assert result is None

    @patch('time.time')
    def test_expired_entry_removed_on_get(self, mock_time):
        """Test that expired entries are removed when accessed"""
        cache = HexStrikeCache(ttl=10)

        # Set time to now
        mock_time.return_value = 1000.0
        cache.set("cmd", {"p": "v"}, {"result": "data"})
        initial_size = len(cache.cache)

        # Advance time past TTL
        mock_time.return_value = 1020.0
        cache.get("cmd", {"p": "v"})

        # Cache should be smaller
        assert len(cache.cache) < initial_size

    @patch('time.time')
    def test_non_expired_entry_accessible(self, mock_time):
        """Test that non-expired entries remain accessible"""
        cache = HexStrikeCache(ttl=60)

        # Set time to now
        mock_time.return_value = 1000.0
        cache.set("cmd", {"p": "v"}, {"result": "data"})

        # Advance time but stay within TTL
        mock_time.return_value = 1030.0  # 30 seconds later
        result = cache.get("cmd", {"p": "v"})

        assert result is not None
        assert result == {"result": "data"}


class TestLRUEviction:
    """Test LRU (Least Recently Used) eviction"""

    def test_cache_evicts_when_full(self):
        """Test that cache evicts entries when max size reached"""
        cache = HexStrikeCache(max_size=3, ttl=3600)

        # Fill cache to max
        cache.set("cmd1", {}, {"result": "1"})
        cache.set("cmd2", {}, {"result": "2"})
        cache.set("cmd3", {}, {"result": "3"})

        # Add one more - should trigger eviction
        cache.set("cmd4", {}, {"result": "4"})

        # Cache should not exceed max size
        assert len(cache.cache) <= cache.max_size

    def test_eviction_removes_oldest_entry(self):
        """Test that eviction removes the least recently used entry"""
        cache = HexStrikeCache(max_size=2, ttl=3600)

        cache.set("cmd1", {}, {"result": "1"})
        cache.set("cmd2", {}, {"result": "2"})

        # Add third entry - should evict cmd1
        cache.set("cmd3", {}, {"result": "3"})

        # cmd1 should be evicted
        assert cache.get("cmd1", {}) is None
        # cmd2 and cmd3 should still exist
        assert cache.get("cmd2", {}) is not None
        assert cache.get("cmd3", {}) is not None

    def test_eviction_increments_stat(self):
        """Test that eviction increments eviction counter"""
        cache = HexStrikeCache(max_size=2, ttl=3600)

        cache.set("cmd1", {}, {"result": "1"})
        cache.set("cmd2", {}, {"result": "2"})

        initial_evictions = cache.stats["evictions"]

        # Trigger eviction
        cache.set("cmd3", {}, {"result": "3"})

        assert cache.stats["evictions"] > initial_evictions

    def test_lru_get_updates_access_time(self):
        """Test that accessing an entry updates its position in LRU"""
        cache = HexStrikeCache(max_size=2, ttl=3600)

        cache.set("cmd1", {}, {"result": "1"})
        cache.set("cmd2", {}, {"result": "2"})

        # Access cmd1 to make it recently used
        cache.get("cmd1", {})

        # Add cmd3 - should evict cmd2 (least recently used)
        cache.set("cmd3", {}, {"result": "3"})

        # cmd1 should still exist (was accessed recently)
        assert cache.get("cmd1", {}) is not None
        # cmd2 should be evicted
        assert cache.get("cmd2", {}) is None


class TestCacheStatistics:
    """Test cache statistics tracking"""

    def test_get_stats_returns_dict(self):
        """Test that get_stats returns a dictionary"""
        cache = HexStrikeCache()
        stats = cache.get_stats()
        assert isinstance(stats, dict)

    def test_get_stats_includes_size(self):
        """Test that stats include current cache size"""
        cache = HexStrikeCache()
        cache.set("cmd1", {}, {"result": "1"})
        cache.set("cmd2", {}, {"result": "2"})

        stats = cache.get_stats()
        assert "size" in stats
        assert stats["size"] == 2

    def test_get_stats_includes_max_size(self):
        """Test that stats include max cache size"""
        cache = HexStrikeCache(max_size=100)
        stats = cache.get_stats()
        assert "max_size" in stats
        assert stats["max_size"] == 100

    def test_get_stats_includes_hit_rate(self):
        """Test that stats include hit rate calculation"""
        cache = HexStrikeCache()
        cache.set("cmd", {}, {"result": "data"})

        # Generate some hits and misses
        cache.get("cmd", {})  # hit
        cache.get("cmd", {})  # hit
        cache.get("nonexistent", {})  # miss

        stats = cache.get_stats()
        assert "hit_rate" in stats
        # Should be formatted as percentage string
        assert "%" in stats["hit_rate"]

    def test_get_stats_hit_rate_calculation(self):
        """Test that hit rate is calculated correctly"""
        cache = HexStrikeCache()
        cache.set("cmd", {}, {"result": "data"})

        # 2 hits, 1 miss = 66.7% hit rate
        cache.get("cmd", {})  # hit
        cache.get("cmd", {})  # hit
        cache.get("miss", {})  # miss

        stats = cache.get_stats()
        hit_rate_str = stats["hit_rate"]
        hit_rate = float(hit_rate_str.rstrip('%'))

        # Should be approximately 66.7%
        assert 66.0 <= hit_rate <= 67.0

    def test_get_stats_zero_requests(self):
        """Test stats with zero requests (no division by zero)"""
        cache = HexStrikeCache()
        stats = cache.get_stats()

        # Should handle zero requests gracefully
        assert "hit_rate" in stats
        # Hit rate should be 0% or handle it gracefully
        assert isinstance(stats["hit_rate"], str)

    def test_get_stats_includes_all_counters(self):
        """Test that stats include all counter values"""
        cache = HexStrikeCache(max_size=2)
        cache.set("cmd1", {}, {"result": "1"})
        cache.get("cmd1", {})  # hit
        cache.get("miss", {})  # miss
        cache.set("cmd2", {}, {"result": "2"})
        cache.set("cmd3", {}, {"result": "3"})  # eviction

        stats = cache.get_stats()
        assert "hits" in stats
        assert "misses" in stats
        assert "evictions" in stats
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1
        assert stats["evictions"] >= 1


class TestCacheEdgeCases:
    """Test edge cases and error conditions"""

    def test_cache_handles_none_result(self):
        """Test that cache can store None as a result"""
        cache = HexStrikeCache()
        cache.set("cmd", {}, None)
        result = cache.get("cmd", {})
        assert result is None  # But should be a hit, not a miss

    def test_cache_handles_empty_dict_result(self):
        """Test that cache can store empty dict"""
        cache = HexStrikeCache()
        cache.set("cmd", {}, {})
        result = cache.get("cmd", {})
        assert result == {}

    def test_cache_handles_large_result(self):
        """Test that cache can handle large result objects"""
        cache = HexStrikeCache()
        large_result = {"data": "x" * 10000}  # Large string
        cache.set("cmd", {}, large_result)
        result = cache.get("cmd", {})
        assert result == large_result

    def test_cache_with_zero_max_size(self):
        """Test cache behavior with max_size=0"""
        cache = HexStrikeCache(max_size=0)
        cache.set("cmd", {}, {"result": "data"})
        # Cache should handle this gracefully (might not store anything)
        # This tests that it doesn't crash

    def test_cache_with_negative_ttl(self):
        """Test cache behavior with negative TTL"""
        cache = HexStrikeCache(ttl=-1)
        cache.set("cmd", {}, {"result": "data"})
        # All entries would be immediately expired
        # This tests that it doesn't crash

    def test_multiple_sets_same_key(self):
        """Test multiple sets to the same key"""
        cache = HexStrikeCache()
        for i in range(10):
            cache.set("cmd", {}, {"iteration": i})

        result = cache.get("cmd", {})
        assert result == {"iteration": 9}  # Should have latest value

    def test_cache_size_never_exceeds_max(self):
        """Test that cache size never exceeds max_size"""
        max_size = 5
        cache = HexStrikeCache(max_size=max_size)

        # Add more entries than max_size
        for i in range(max_size * 2):
            cache.set(f"cmd{i}", {}, {"result": i})
            # Check size after each insertion
            assert len(cache.cache) <= max_size


class TestCacheIntegration:
    """Integration tests for cache behavior"""

    def test_realistic_usage_pattern(self):
        """Test cache with realistic usage pattern"""
        cache = HexStrikeCache(max_size=10, ttl=3600)

        # Simulate scanning multiple targets
        targets = ["target1.com", "target2.com", "target3.com"]
        tools = ["nmap", "gobuster", "sqlmap"]

        for target in targets:
            for tool in tools:
                params = {"target": target}
                result = {"tool": tool, "findings": []}

                # First access - miss
                assert cache.get(tool, params) is None

                # Set result
                cache.set(tool, params, result)

                # Second access - hit
                assert cache.get(tool, params) == result

        # Verify statistics
        stats = cache.get_stats()
        assert stats["hits"] > 0
        assert stats["misses"] > 0

    def test_cache_performance_with_many_entries(self):
        """Test cache performance with many entries"""
        cache = HexStrikeCache(max_size=100, ttl=3600)

        # Add many entries
        for i in range(100):
            cache.set(f"cmd{i}", {"param": i}, {"result": f"data{i}"})

        # Verify all can be retrieved
        for i in range(100):
            result = cache.get(f"cmd{i}", {"param": i})
            assert result is not None

    @patch('time.time')
    def test_mixed_expired_and_valid_entries(self, mock_time):
        """Test cache with mix of expired and valid entries"""
        cache = HexStrikeCache(max_size=10, ttl=60)

        # Add entries at different times
        mock_time.return_value = 1000.0
        cache.set("old1", {}, {"result": "old1"})
        cache.set("old2", {}, {"result": "old2"})

        mock_time.return_value = 1050.0  # 50 seconds later
        cache.set("fresh1", {}, {"result": "fresh1"})
        cache.set("fresh2", {}, {"result": "fresh2"})

        # Check at 1080 (old entries expired, fresh still valid)
        mock_time.return_value = 1080.0

        # Old entries should be expired
        assert cache.get("old1", {}) is None
        assert cache.get("old2", {}) is None

        # Fresh entries should still be valid
        assert cache.get("fresh1", {}) is not None
        assert cache.get("fresh2", {}) is not None
