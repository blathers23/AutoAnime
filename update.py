import asyncio 

from sqlmodel import Session, select, and_ 

from model import AnimeUpdate, EpisodeAdd 
from database import engine, AnimeDB, EpisodeUpdateTaskDB  
from utils import request_xml_async, anime 
from acid import add_episode_list, inquire_anime_update_ready, inquire_episode_update_ready


async def _get_anime_update_async(anime_db: AnimeDB) -> AnimeUpdate:
    return AnimeUpdate(
        uuid=anime_db.uuid, 
        season=anime_db.season, 
        dir_path=anime_db.dir_path, 
        source=anime_db.source, 
        http_url=anime_db.http_url, 
        episodes_list=list(map(int, anime_db.episodes_str.split(','))), 
        xml=await request_xml_async(anime_db.http_url),  
    ) 


async def update_anime_add_task() -> dict[str, str | list[dict[str, str]]]: 
    anime_db_list = inquire_anime_update_ready() 

    anime_update_list = await asyncio.gather(*(
        asyncio.create_task(_get_anime_update_async(anime_db)) for anime_db in anime_db_list
    )) 
    
    episode_add_list = [] 
    for anime_update in anime_update_list: 
        for _, episode_num, pub_date, torrent_url in anime.get_episode_info(anime_update.source, anime_update.xml): 
            episode_add_list.append(EpisodeAdd( 
                torrent_url=torrent_url, 
                uuid=anime_update.uuid, 
                season=anime_update.season, 
                dir_path=anime_update.dir_path, 
                episode_num=episode_num, 
                pub_date=pub_date, 
            )) 

    await add_episode_list(episode_add_list) 

    return {'code': 1, 'msg': 'Anime update task added successfully', 'detail': []} 


async def update_anime_run_task() -> None: 
    episode_update_task_list = inquire_episode_update_ready() 
    
