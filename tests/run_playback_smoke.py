import asyncio
import pprint
from cache_manager import cache_manager
import crud
from queue_manager import queue_manager
import websocket_manager

pp = pprint.PrettyPrinter(indent=2)


def show_states():
    print('\n--- States ---')
    for estado in ['reproduciendo', 'aprobado', 'pendiente_lazy', 'cantada']:
        songs = cache_manager.get_songs_by_estado(estado)
        print(f"{estado}: {[s.get('id') for s in songs]}")


async def main():
    cache_manager.clear_all_songs()

    # Add songs
    id1 = cache_manager.add_song_to_cache(1, {'titulo':'S1','youtube_id':'Y1','duracion_seconds':120,'usuario_id':1,'estado':'reproduciendo'})
    id2 = cache_manager.add_song_to_cache(2, {'titulo':'S2','youtube_id':'Y2','duracion_seconds':150,'usuario_id':2,'estado':'aprobado'})
    id3 = cache_manager.add_song_to_cache(3, {'titulo':'S3','youtube_id':'Y3','duracion_seconds':180,'usuario_id':3,'estado':'aprobado'})

    show_states()

    print('\nCalling avanzar_cola_automaticamente()')
    siguiente = await crud.avanzar_cola_automaticamente(None)
    print('Returned siguiente:', siguiente.get('id') if siguiente else None)
    show_states()

    print('\nCalling play specific song (id3)')
    await crud.play_song_now(id3, None)
    show_states()

    print('\nCalling broadcast pause/resume/restart (no websockets connected)')
    await websocket_manager.manager.broadcast_pause()
    await websocket_manager.manager.broadcast_resume()
    await websocket_manager.manager.broadcast_restart_song()
    print('Broadcasts sent (if no exceptions).')


if __name__ == '__main__':
    asyncio.run(main())
