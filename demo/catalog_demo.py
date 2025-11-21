#!/usr/bin/env python3
"""
GGF Catalog Query API Demo

Demonstrates how to query the GGF catalog programmatically.
Useful for LLM query planning and offline GGF discovery.
"""

from SPARQLLM.catalog import (
    find_ggfs_by_alias,
    find_ggfs_by_source,
    find_ggfs_by_cost,
    find_ggfs_by_network,
    find_ggfs_by_env_requirements,
    get_catalog_summary
)


def main():
    print("=== GGF Catalog Query API Demo ===\n")

    # 1. Get catalog summary
    print("1. Catalog Summary:")
    summary = get_catalog_summary()
    print(f"   Total GGFs: {summary['total_ggfs']}")
    print(f"   Network required: {summary['network_required']}")
    print(f"   Local only: {summary['local_only']}")
    print(f"   By data source:")
    for source, count in summary['by_data_source'].items():
        print(f"     - {source}: {count}")
    print()

    # 2. Find GGF by alias
    print("2. Find by Alias (SLM-READFILE):")
    ggf = find_ggfs_by_alias("SLM-READFILE")
    if ggf:
        print(f"   Description: {ggf['description']}")
        print(f"   Module: {ggf['module_path']}")
        print(f"   Latency: {ggf['latency_ms']}ms")
        print(f"   Deterministic: {ggf['deterministic']}")
    print()

    # 3. Find filesystem GGFs
    print("3. Filesystem GGFs:")
    fs_ggfs = find_ggfs_by_source("filesystem")
    for ggf in fs_ggfs[:5]:  # Show first 5
        print(f"   - {ggf['name']}: {ggf['latency_ms']}ms")
    print(f"   ... {len(fs_ggfs)} total")
    print()

    # 4. Find LLM-based GGFs
    print("4. LLM GGFs:")
    llm_ggfs = find_ggfs_by_source("llm")
    for ggf in llm_ggfs:
        tokens = f", {ggf['tokens']} tokens" if ggf['tokens'] else ""
        print(f"   - {ggf['name']}: {ggf['latency_ms']}ms{tokens}")
    print()

    # 5. Find fast GGFs (<100ms)
    print("5. Fast GGFs (<100ms latency):")
    fast_ggfs = find_ggfs_by_cost(max_latency_ms=100)
    for ggf in fast_ggfs[:10]:  # Show first 10
        print(f"   - {ggf['name']}: {ggf['latency_ms']}ms")
    print()

    # 6. Find local-only GGFs (no network)
    print("6. Local-only GGFs (no network required):")
    local_ggfs = find_ggfs_by_network(requires_network=False)
    for ggf in local_ggfs[:5]:  # Show first 5
        sources = ', '.join(ggf['data_sources'])
        print(f"   - {ggf['name']}: {sources}")
    print(f"   ... {len(local_ggfs)} total")
    print()

    # 7. Find GGFs by environment requirements
    print("7. GGFs by Environment Variables:")
    env_map = find_ggfs_by_env_requirements()
    for env_var, ggfs in env_map.items():
        print(f"   {env_var}:")
        for ggf in ggfs:
            print(f"     - {ggf}")
    print()

    print("=== Demo Complete ===")


if __name__ == "__main__":
    main()
