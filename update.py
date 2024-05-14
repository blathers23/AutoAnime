import os 
import asyncio 
from collections import defaultdict 

from aioshutil import copy 

from settings import user_settings 
from model import AnimeUpdate, EpisodeAdd, EpisodeUpdate  
from database import AnimeDB  
from utils import anime 
from utils.request import request_xml_async  
from acid.internal import (
    add_episode_add_list, inquire_anime_update_ready, 
    inquire_episode_update_ready, change_anime_db_unlock, 
    change_anime_db_update_result, change_episode_update_task_db_update_result, 
) 
from api_client import (
    qbittorrent_client as torrent_client, 
    jellyfin_client as media_client 
)  


id_download_progress_dict: dict[int, float] = dict() 
id_copy_progress_dict: dict[int, float] = dict() 


async def _anime_db_to_anime_update_async(anime_db: AnimeDB) -> AnimeUpdate:
    return AnimeUpdate(
        uuid=anime_db.uuid, 
        name=anime_db.name, 
        season=anime_db.season, 
        dir_path=anime_db.dir_path, 
        source=anime_db.source, 
        http_url=anime_db.http_url, 
        episodes_list=list(map(lambda x: int(x) if len(x) > 0 else -1, anime_db.episodes_str.split(','))), 
        xml=await request_xml_async(anime_db.http_url),  
    ) 


async def update_add_task(auto_update: bool) -> dict[str, str | list[dict[str, str]]]: 
    anime_db_list = inquire_anime_update_ready(auto_update) 

    anime_update_list = await asyncio.gather(*(
        asyncio.create_task(_anime_db_to_anime_update_async(anime_db)) for anime_db in anime_db_list
    )) 

    # print(anime_db_list)
    
    episode_add_list = list() 
    all_uuid_set = set() 
    update_uuid_set = set() 
    for anime_update in anime_update_list: 
        all_uuid_set.add(anime_update.uuid) 
        for _, episode_num, pub_date, torrent_url in anime.get_episode_info(anime_update.source, anime_update.xml): 
            if episode_num == -1: 
                continue 

            elif episode_num in anime_update.episodes_list: 
                continue 
                
            else:
                update_uuid_set.add(anime_update.uuid) 

            episode_add_list.append(EpisodeAdd( 
                torrent_url=torrent_url, 
                uuid=anime_update.uuid, 
                name=anime_update.name, 
                season=anime_update.season, 
                dir_path=str(anime_update.dir_path), 
                episode_num=episode_num, 
                pub_date=pub_date, 
            )) 

    # print(episode_add_list) 
    change_anime_db_unlock(all_uuid_set - update_uuid_set) 

    if len(episode_add_list) == 0: 
        return {'code': 0, 'msg': 'No updates for anime detected', 'detail': []} 
    
    await add_episode_add_list(episode_add_list) 

    return {'code': 1, 'msg': 'Anime update task added successfully', 'detail': []} 


async def _update_download_manager(episode_update_list: list[EpisodeUpdate]) -> None: 
    torrent_hash_set = {episode.torrent_hash for episode in episode_update_list} 
    hash_episode_dict = {episode.torrent_hash: episode for episode in episode_update_list} 

    while len(torrent_hash_set) > 0: 
        torrent_info_list = torrent_client.info(torrent_hashes=torrent_hash_set) 

        for torrent_info in torrent_info_list: 
            download_progress = float(torrent_info['progress']) 

            id_download_progress_dict[hash_episode_dict[torrent_info['infohash_v1']].id_] = download_progress 
            if download_progress >= 1.: 
                torrent_hash_set.remove(torrent_info['infohash_v1']) 
                hash_episode_dict[torrent_info['infohash_v1']].downloaded = True 

        await asyncio.sleep(user_settings.refresh_time) 


async def _update_copy_worker(episode_update: EpisodeUpdate) -> None: 
    while not episode_update.downloaded: 
        await asyncio.sleep(user_settings.refresh_time) 

    id_copy_progress_dict[episode_update.id_] = .5 

    src_path: str = torrent_client.info(torrent_hashes=[episode_update.torrent_hash])[0]['content_path'] 
    if os.path.isfile(src_path): 
        dest_path = episode_update.file_path + src_path[src_path.rfind('.'):] 

        await copy(src_path, dest_path) 

    episode_update.copied = True 
    id_copy_progress_dict[episode_update.id_] = 1. 


async def update_run_task() -> None: 
    episode_update_task_db_list = inquire_episode_update_ready() 

    episode_update_list: list[EpisodeUpdate] = list() 
    torrent_file_path_list: list[str] = list() 
    torrent_magnet_list: list[str] = list() 
    torrent_hash_list: list[str] = list()

    for episode_update_task_db in episode_update_task_db_list: 
        if episode_update_task_db.torrent_file_path: 
            torrent_file_path_list.append(episode_update_task_db.torrent_file_path) 
            torrent_hash_list.append(episode_update_task_db.torrent_hash) 
        elif episode_update_task_db.torrent_magnet: 
            torrent_magnet_list.append(episode_update_task_db.torrent_magnet) 
            torrent_hash_list.append(episode_update_task_db.torrent_hash) 
        else: 
            continue 
        
        episode_update_list.append( 
            EpisodeUpdate( 
                id_=episode_update_task_db.id_, 
                torrent_hash=episode_update_task_db.torrent_hash, 
                uuid=episode_update_task_db.uuid, 
                file_path=episode_update_task_db.file_path, 
                episode_num=episode_update_task_db.episode_num, 
                pub_date=episode_update_task_db.pub_date, 
                downloaded=False, 
                copied=False, 
            ) 
        ) 

    if len(episode_update_list) == 0: 
        return 

    id_set_success: set[str] = set() 
    id_set_fail: set[str] = set() 
    uuid_episode_num_list_dict: dict[str, list[int]] = defaultdict(list) 
    uuid_newest_pub_date: dict[str, float] = defaultdict(float) 

    torrent_client.delete(torrent_hashes=torrent_hash_list) 

    if torrent_client.add(torrent_urls=torrent_magnet_list, torrent_files=torrent_file_path_list) != 'Ok.': 
        print("can't connect to the torrent server") 
        for episode_update in episode_update_list: 
            id_set_fail.add(episode_update.id_) 
            uuid_episode_num_list_dict[episode_update.uuid] 
            uuid_newest_pub_date[episode_update.uuid] 

        change_episode_update_task_db_update_result(id_set_success, id_set_fail) 
        change_anime_db_update_result(uuid_episode_num_list_dict, uuid_newest_pub_date) 
        return 
    
    try: 
        async with asyncio.timeout(user_settings.timeout_update): 
            await asyncio.gather( 
                asyncio.create_task(_update_download_manager(episode_update_list)), 
                *(asyncio.create_task(_update_copy_worker(episode)) for episode in episode_update_list) 
            ) 
    
    except asyncio.TimeoutError: 
        print('the update task timed out') 
        for episode_update in episode_update_list: 
            print('episode uuid: ', episode_update.uuid) 
            print('episode download progress: ', id_download_progress_dict[episode_update.id_]) 
            print('episode copy progress: ', id_copy_progress_dict[episode_update.id_]) 
            print() 

    for episode_update in episode_update_list: 
        if episode_update.copied: 
            id_set_success.add(episode_update.id_) 
            uuid_episode_num_list_dict[episode_update.uuid].append(episode_update.episode_num) 
            uuid_newest_pub_date[episode_update.uuid] = max(uuid_newest_pub_date[episode_update.uuid], episode_update.pub_date) 
        else: 
            id_set_fail.add(episode_update.id_) 

    change_episode_update_task_db_update_result(id_set_success, id_set_fail) 
    change_anime_db_update_result(uuid_episode_num_list_dict, uuid_newest_pub_date) 

    media_client.refresh() 


async def update_auto_update() -> None: 
    _ = await update_add_task(auto_update=True) 
    await update_run_task() 

