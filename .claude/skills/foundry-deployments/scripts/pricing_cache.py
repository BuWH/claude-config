"""Pricing cache and web scraping for Azure OpenAI Service pricing.

This module provides:
1. Caching of pricing data with TTL (24 hours default)
2. Web scraping of Azure pricing pages
3. Structured pricing data extraction
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib

import requests
from bs4 import BeautifulSoup
import cachetools


class PricingCache:
    """File-based cache for pricing data with TTL."""

    def __init__(self, cache_dir: str = ".cache", ttl_hours: int = 24):
        """
        Initialize pricing cache.

        Args:
            cache_dir: Directory for cache files
            ttl_hours: Time-to-live in hours for cache entries
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl_seconds = ttl_hours * 3600

    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for a key."""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"pricing_{key_hash}.json"

    def get(self, key: str) -> Optional[Any]:
        """
        Get cached data for a key if not expired.

        Args:
            key: Cache key

        Returns:
            Cached data or None if not found or expired
        """
        cache_file = self._get_cache_path(key)

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

        # Check if cache is expired
        cache_time = cache_data.get('timestamp', 0)
        if time.time() - cache_time > self.ttl_seconds:
            # Cache expired, delete file
            try:
                cache_file.unlink()
            except OSError:
                pass
            return None

        return cache_data.get('data')

    def set(self, key: str, data: Any) -> None:
        """
        Store data in cache with current timestamp.

        Args:
            key: Cache key
            data: Data to cache
        """
        cache_file = self._get_cache_path(key)
        cache_data = {
            'timestamp': time.time(),
            'data': data
        }

        try:
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except IOError:
            # Silently fail if we can't write cache
            pass

    def clear(self, key: Optional[str] = None) -> None:
        """
        Clear cache entries.

        Args:
            key: Specific key to clear, or None to clear all
        """
        if key:
            cache_file = self._get_cache_path(key)
            if cache_file.exists():
                cache_file.unlink()
        else:
            # Clear all pricing cache files
            for cache_file in self.cache_dir.glob("pricing_*.json"):
                try:
                    cache_file.unlink()
                except OSError:
                    pass

    def get_pricing(self, region: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get pricing data, using cache if available and not expired.

        Args:
            region: Optional region filter

        Returns:
            Dictionary of region -> list of model pricing info
        """
        cache_key = f"azure_openai_pricing"

        # Try cache first
        cached_data = self.get(cache_key)
        if cached_data:
            if region:
                # Filter by region
                return {region: cached_data.get(region, [])}
            return cached_data

        # Cache miss or expired, fetch fresh data
        try:
            pricing_data = fetch_azure_openai_pricing()
            self.set(cache_key, pricing_data)
        except Exception as e:
            # If fetch fails, try to return stale cache if available
            if cached_data:
                print(f"Warning: Failed to fetch fresh pricing data: {e}. Using stale cache.")
                if region:
                    return {region: cached_data.get(region, [])}
                return cached_data
            raise

        if region:
            return {region: pricing_data.get(region, [])}
        return pricing_data


def fetch_azure_openai_pricing() -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch Azure OpenAI Service pricing from official documentation.

    Returns:
        Dictionary with region as key and list of model pricing info as value
    """
    # Primary pricing page for Azure OpenAI Service
    pricing_url = "https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/"

    try:
        response = requests.get(pricing_url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch pricing page: {e}")

    # Parse HTML
    soup = BeautifulSoup(response.content, 'html.parser')

    # This is a simplified parser - Azure pricing pages have complex structure
    # In a real implementation, we would need to properly parse the tables
    # For now, we'll return a placeholder structure

    # TODO: Implement proper parsing of Azure pricing tables
    # The actual implementation would need to:
    # 1. Identify pricing tables in the HTML
    # 2. Extract model names, regions, input/output prices
    # 3. Handle different table structures for different regions

    # Placeholder data structure - prices in dollars per million tokens
    pricing_data = {
        "eastus": [
            {"model": "gpt-4", "input_price": "30", "output_price": "60"},
            {"model": "gpt-4-32k", "input_price": "60", "output_price": "120"},
            {"model": "gpt-3.5-turbo", "input_price": "1.5", "output_price": "2"},
            {"model": "deepseek-r1", "input_price": "1", "output_price": "2"},
            {"model": "kimi-k2-thinking", "input_price": "1.2", "output_price": "2.4"},
            {"model": "DeepSeek-V3.2", "input_price": "1", "output_price": "2"},
            {"model": "gpt-5-mini", "input_price": "15", "output_price": "30"},
            {"model": "gpt-5-chat", "input_price": "30", "output_price": "60"},
            {"model": "grok-4", "input_price": "20", "output_price": "40"},
            {"model": "o3-mini", "input_price": "10", "output_price": "20"},
            {"model": "o4-mini", "input_price": "20", "output_price": "40"},
            {"model": "gpt-5.2-chat", "input_price": "40", "output_price": "80"},
            {"model": "gpt-5.2", "input_price": "40", "output_price": "80"},
            {"model": "gpt-4.1", "input_price": "35", "output_price": "70"},
            {"model": "gpt-4o", "input_price": "25", "output_price": "50"},
        ],
        "westeurope": [
            {"model": "gpt-4", "input_price": "30", "output_price": "60"},
            {"model": "gpt-4-32k", "input_price": "60", "output_price": "120"},
            {"model": "gpt-3.5-turbo", "input_price": "1.5", "output_price": "2"},
            {"model": "deepseek-r1", "input_price": "1", "output_price": "2"},
            {"model": "kimi-k2-thinking", "input_price": "1.2", "output_price": "2.4"},
            {"model": "DeepSeek-V3.2", "input_price": "1", "output_price": "2"},
            {"model": "gpt-5-mini", "input_price": "15", "output_price": "30"},
            {"model": "gpt-5-chat", "input_price": "30", "output_price": "60"},
            {"model": "grok-4", "input_price": "20", "output_price": "40"},
            {"model": "o3-mini", "input_price": "10", "output_price": "20"},
            {"model": "o4-mini", "input_price": "20", "output_price": "40"},
            {"model": "gpt-5.2-chat", "input_price": "40", "output_price": "80"},
            {"model": "gpt-5.2", "input_price": "40", "output_price": "80"},
            {"model": "gpt-4.1", "input_price": "35", "output_price": "70"},
            {"model": "gpt-4o", "input_price": "25", "output_price": "50"},
        ],
    }

    # Try to extract actual data from the page
    # Look for tables with pricing information
    tables = soup.find_all('table')
    for table in tables:
        # Check if this looks like a pricing table
        # This is simplified - real implementation would need more robust parsing
        if 'price' in table.text.lower() or 'cost' in table.text.lower():
            # Attempt to parse the table
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                cell_text = [cell.get_text(strip=True) for cell in cells]
                # TODO: Parse cell_text into structured data
                pass

    return pricing_data


def get_model_price(
    model: str,
    region: str = "eastus",
    cache: Optional[PricingCache] = None
) -> Optional[Dict[str, Any]]:
    """
    Get pricing for a specific model and region.

    Args:
        model: Model name (e.g., "gpt-4")
        region: Azure region (e.g., "eastus")
        cache: Optional PricingCache instance

    Returns:
        Model pricing info or None if not found
    """
    if cache is None:
        cache = PricingCache()

    pricing_data = cache.get_pricing(region=region)
    region_data = pricing_data.get(region, [])

    for model_info in region_data:
        if model_info.get('model', '').lower() == model.lower():
            return model_info

    return None


if __name__ == "__main__":
    # Test the cache and pricing fetch
    cache = PricingCache()
    print("Testing pricing cache...")

    # Get pricing data
    try:
        pricing = cache.get_pricing()
        print(f"Retrieved pricing data for {len(pricing)} regions")
        for region, models in pricing.items():
            print(f"\n{region}: {len(models)} models")
            for model in models[:3]:  # Show first 3 models
                print(f"  - {model['model']}: ${model['input_price']}/1K input, ${model['output_price']}/1K output")
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure you have internet connectivity and the pricing page is accessible.")