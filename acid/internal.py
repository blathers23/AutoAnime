import os 
import asyncio 
from datetime import datetime, timezone 

from sqlmodel import Session, select, and_  

from settings import AnimeSourcesParsed, user_settings 
from model import AnimeChange, AnimeAdd, AnimeInquire, AnimeDelete, EpisodeAdd, EpisodeUpdate 
from database import engine, AnimeDB, EpisodeUpdateTaskDB 
from utils import anime, episode 


def change_anime_db_update_result(
        uuid_episode_num_list_dict: dict[str, list[int]], uuid_episode_newest_pub_date: dict[str, float]
    ) -> None: 
    with Session(engine) as session: 
        anime_db_list = session.exec( 
            select(AnimeDB).where(AnimeDB.under_management == True).with_for_update() 
        ).all() 
        
        for anime_db in anime_db_list: 
            if len(uuid_episode_num_list_dict[anime_db.uuid] > 0) and anime_db.episodes_str: 
                anime_db.episodes_str += ',' 
            
                anime_db.episodes_str += ','.join(map(str, uuid_episode_num_list_dict[anime_db.uuid])) 
                anime_db.newest_pub_date = max(anime_db.newest_pub_date, uuid_episode_newest_pub_date[anime_db.uuid]) 
                
            anime_db.under_management = False 

        session.add_all(anime_db_list) 
        session.commit() 


def inquire_anime_update_ready(auto_update: bool) -> list[AnimeDB]: 
    with Session(engine) as session: 
        if not auto_update: 
            anime_db_list = session.exec(select(AnimeDB).where( 
                and_(AnimeDB.under_management == False) 
            ).with_for_update()).all() 
        else: 
            timestamp = datetime.now(timezone.utc).timestamp() 

            anime_db_list = session.exec(select(AnimeDB).where( 
                and_(
                    AnimeDB.auto_update == True, AnimeDB.under_management == False, 
                    AnimeDB.newest_pub_date - timestamp > user_settings.auto_update_online_interval 
                ) 
            ).with_for_update()).all() 

        for anime_db in anime_db_list: 
            anime_db.under_management = True 
        
        session.add_all(anime_db_list) 
        session.commit() 

    return anime_db_list 


async def _episode_add_to_episode_update_task_db(episode_add: EpisodeAdd) -> EpisodeUpdateTaskDB: 
    try:
        torrent_hash, torrent_file_path, torrent_magnet = await episode.parse_torrent_url_async(episode_add.torrent_url) 
    except AssertionError as e: 
        print(e) 
        return None 
    else: 
        return EpisodeUpdateTaskDB( 
            torrent_hash=torrent_hash, 
            torrent_file_path=torrent_file_path, 
            torrent_magnet=torrent_magnet, 
            name=episode_add.name, 
            season=episode_add.season, 
            episode_num=episode_add.episode_num, 
            file_path=os.path.join(
                episode_add.dir_path, 
                f'S{str(episode_add.season)}E{str(episode_add.episode_num)}', 
            ), 
            pub_date=episode_add.pub_date, 
            under_management=False, 
            done=False, 
            success=False, 
        ) 


async def add_episode_add_list(episode_add_list: list[EpisodeAdd]) -> None: 
    
    episode_update_task_db_list: list[EpisodeUpdateTaskDB] = await asyncio.gather(*( 
        asyncio.create_task(_episode_add_to_episode_update_task_db(episode_add)) 
        for episode_add in episode_add_list 
    )) 
    episode_update_task_db_list = [ 
        episode_update_task_db for episode_update_task_db in episode_update_task_db_list 
        if episode_update_task_db 
    ] 

    with Session(engine) as session: 
        session.add_all(episode_update_task_db_list) 
        session.commit() 


def change_episode_update_task_db_update_result(id_set_success: set[int], id_set_fail: set[int]) -> None: 
    with Session(engine) as session: 
        episode_update_task_db_list = session.exec(
            select(EpisodeUpdateTaskDB).where(EpisodeUpdateTaskDB.under_management == True).with_for_update()
        ).all() 

        for episode_update_task_db in episode_update_task_db_list: 
            if episode_update_task_db.id_ in id_set_success: 
                episode_update_task_db.under_management = False 
                episode_update_task_db.done = True 
                episode_update_task_db.success = True 
            
            elif episode_update_task_db.id_ in id_set_fail: 
                episode_update_task_db.under_management = False 
                episode_update_task_db.done = True 

        session.add_all(episode_update_task_db_list) 
        session.commit() 


def inquire_episode_update_ready() -> list[EpisodeUpdateTaskDB]: 
    with Session(engine) as session: 
        episode_list = session.exec(
            select(EpisodeUpdateTaskDB).where(
                EpisodeUpdateTaskDB.done == False
            ).order_by(EpisodeUpdateTaskDB.id_).with_for_update() 
        ).all() 
        
        """
        从未完成的任务中, 按照放入任务队列的顺序, 将任务取出 

        1. 如果相同的下载地址, 有任务正在进行, 则搁置之后所有的同地址任务 
        2. 如果相同的下载地址, 没有正在进行的任务, 但是有更新的任务, 则覆盖旧的任务, 并删除旧任务的种子文件 

        相同地址的确定方法为: uuid 和 episode_num, 不能采用 torrent hash 
        """
        uuid_add_num_episode_dict: dict[str, EpisodeUpdateTaskDB] = dict()
        suspend_uuid_add_num_set: set[str] = set() 
        for episode in episode_list: 
            uuid_add_num = episode.uuid + str(episode.episode_num) 

            if episode.under_management: 
                suspend_uuid_add_num_set.add(uuid_add_num) 

            elif uuid_add_num in suspend_uuid_add_num_set: 
                continue 

            elif uuid_add_num in uuid_add_num_episode_dict: 
                uuid_add_num_episode_dict[uuid_add_num].done = True 

                if os.path.isfile(uuid_add_num_episode_dict[uuid_add_num].torrent_file_path): 
                    os.remove(uuid_add_num_episode_dict[uuid_add_num].torrent_file_path) 

                uuid_add_num_episode_dict[uuid_add_num] = episode 

            else: 
                uuid_add_num_episode_dict[uuid_add_num] = episode 

        episode_update_task_db_list=list(uuid_add_num_episode_dict.values()) 

        for episode_update_task_db in episode_update_task_db_list: 
            episode_update_task_db.under_management = True 

        session.add_all(episode_list) 
        session.commit() 

    return episode_update_task_db_list 

