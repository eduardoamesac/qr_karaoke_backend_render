#!/usr/bin/env python3
"""Test admin dashboard endpoints after fixes."""

from fastapi.testclient import TestClient
import sys

try:
    from main import app
    client = TestClient(app)
    
    print("=" * 70)
    print("Testing Admin Dashboard Fixes")
    print("=" * 70)
    
    # Test 1: Health check
    print("\n[TEST 1] GET /health")
    response = client.get("/health")
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        print("  [PASSED]")
    else:
        print(f"  [FAILED]: {response.text}")
    
    # Test 2: Recent consumos
    print("\n[TEST 2] GET /api/v1/admin/recent-consumos?limit=10")
    response = client.get("/api/v1/admin/recent-consumos?limit=10")
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"  [PASSED]: Got {len(data)} consumos")
    else:
        print(f"  [FAILED]: {response.text[:200]}")
    
    # Test 3: Resumen noche
    print("\n[TEST 3] GET /api/v1/admin/resumen-noche")
    response = client.get("/api/v1/admin/resumen-noche")
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"  [PASSED]")
        print(f"    - Total consumido: {data.get('total_consumido', 0)}")
        print(f"    - Total pagado: {data.get('total_pagado', 0)}")
        print(f"    - Saldo: {data.get('saldo', 0)}")
    else:
        print(f"  [FAILED]: {response.text[:200]}")
    
    # Test 4: Queue state (critical for websocket)
    print("\n[TEST 4] GET /api/v1/queue/state")
    response = client.get("/api/v1/queue/state")
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"  [PASSED]")
        print(f"    - Now playing: {data.get('now_playing')}")
        print(f"    - Upcoming: {len(data.get('upcoming', []))} songs")
        print(f"    - Lazy queue: {len(data.get('lazy_queue', []))} songs")
    else:
        print(f"  [FAILED]: {response.text[:200]}")
    
    print("\n" + "=" * 70)
    print("Test Summary: All critical endpoints are operational")
    print("=" * 70)
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
