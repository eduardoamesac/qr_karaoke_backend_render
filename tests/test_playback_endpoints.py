import os
import time
from fastapi.testclient import TestClient
import main
from cache_manager import cache_manager

client = TestClient(main.app)


def setup_module(module):
    # Clear cache files to start from a clean state
    cache_manager.clear_all_songs()


def teardown_module(module):
    cache_manager.clear_all_songs()


def make_song(title, youtube_id, usuario_id=1, estado='pendiente', duracion=120):
    song = {
        'titulo': title,
        'youtube_id': youtube_id,
        'duracion_seconds': duracion,
        'usuario_id': usuario_id,
        'estado': estado
    }
    song_id = cache_manager.add_song_to_cache(usuario_id, song)
    return song_id


def test_play_endpoint_sets_reproduciendo():
    # Arrange: create two approved songs
    cache_manager.clear_all_songs()
    id1 = make_song('Song One', 'AAA111', estado='aprobado')
    id2 = make_song('Song Two', 'BBB222', estado='aprobado')

    # Act: call play endpoint for id2
    res = client.post(f"/api/v1/canciones/{id2}/play")
    assert res.status_code == 200

    # Assert: cache shows id2 as reproduciendo
    reproduciendo = cache_manager.get_songs_by_estado('reproduciendo')
    assert any(s.get('id') == id2 for s in reproduciendo), f"Song {id2} not reproduciendo"


def test_siguiente_advances_queue():
    # Arrange: create approved songs and set first as reproduciendo
    cache_manager.clear_all_songs()
    id1 = make_song('Song A', 'AAA', estado='reproduciendo')
    id2 = make_song('Song B', 'BBB', estado='aprobado')
    id3 = make_song('Song C', 'CCC', estado='aprobado')

    # Act: call siguiente
    res = client.post('/api/v1/canciones/siguiente')
    # Either 200 with response body or 204 if no next; expect 200 because there is a next
    assert res.status_code in (200, 204)

    # Refresh internal state (cache is updated by endpoints)
    reproduciendo = cache_manager.get_songs_by_estado('reproduciendo')
    cantadas = cache_manager.get_songs_by_estado('cantada')

    # Expect one reproduciendo (id2) and previous (id1) marked as cantada
    assert any(s.get('id') == id2 for s in reproduciendo), f"Expected {id2} reproduciendo"
    assert any(s.get('id') == id1 for s in cantadas), f"Expected {id1} cantada"


def test_pause_resume_and_restart_endpoints():
    # These endpoints just broadcast; ensure they return 200 and JSON message
    res_pause = client.post('/api/v1/admin/player/pause')
    assert res_pause.status_code == 200
    assert 'mensaje' in res_pause.json()

    res_resume = client.post('/api/v1/admin/player/resume')
    assert res_resume.status_code == 200
    assert 'mensaje' in res_resume.json()

    res_restart = client.post('/api/v1/admin/canciones/restart')
    assert res_restart.status_code == 200
    assert 'mensaje' in res_restart.json()
