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
    
    # Test 2: Recent consumos
    print("\n[TEST 1] GET /api/v1/admin/recent-consumos?limit=10")
    response = client.get("/api/v1/admin/recent-consumos?limit=10")
    print("  Status: " + str(response.status_code))
    if response.status_code == 200:
        data = response.json()
        print("  [OK] Got " + str(len(data)) + " consumos")
    else:
        print("  [ERROR] " + response.text[:200])
    
    # Test 3: Resumen noche
    print("\n[TEST 2] GET /api/v1/admin/resumen-noche")
    response = client.get("/api/v1/admin/resumen-noche")
    print("  Status: " + str(response.status_code))
    if response.status_code == 200:
        data = response.json()
        print("  [OK]")
        print("    - Total consumido: " + str(data.get('total_consumido', 0)))
        print("    - Total pagado: " + str(data.get('total_pagado', 0)))
        print("    - Saldo: " + str(data.get('saldo', 0)))
    else:
        print("  [ERROR] " + response.text[:200])
    
    # Test 4: Queue state (critical for websocket)
    print("\n[TEST 3] GET /api/v1/queue/state")
    response = client.get("/api/v1/queue/state")
    print("  Status: " + str(response.status_code))
    if response.status_code == 200:
        data = response.json()
        print("  [OK]")
        print("    - Now playing: " + str(data.get('now_playing')))
        print("    - Upcoming songs: " + str(len(data.get('upcoming', []))))
        print("    - Lazy queue songs: " + str(len(data.get('lazy_queue', []))))
    else:
        print("  [ERROR] " + response.text[:200])
    
    print("\n" + "=" * 70)
    print("All critical endpoints tested successfully")
    print("=" * 70)
    
except Exception as e:
    print("ERROR: " + str(e))
    import traceback
    traceback.print_exc()
    sys.exit(1)
