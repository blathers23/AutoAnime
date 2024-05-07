import os 
import asyncio 

from sqlmodel import Session, select, and_  

from settings import AnimeSourcesParsed, user_settings 
from model import AnimeChange, AnimeAdd, AnimeInquire, AnimeDelete, EpisodeAdd   
from database import engine, AnimeDB, EpisodeUpdateTaskDB   
from utils import anime, episode 


def add_anime(anime_add: AnimeAdd) -> dict[str, str | list[dict[str, str]]]: 
    uuid = anime.get_uuid(anime_add.name, anime_add.season)     
    dir_path = anime.get_dir_path(anime_add.name, anime_add.season) 

    if anime_add.search_text is None and anime_add.http_url is None: 
        return {'code': 0, 'msg': 'Search text and http url cannot be empty at the same time', 'detail': []} 

    elif anime_add.search_text is not None and anime_add.http_url is not None: 
        return {'code': 0, 'msg': 'Search text and http url cannot have values at the same time', 'detail': []} 

    elif anime_add.search_text is None: 
        if anime_add.source in AnimeSourcesParsed: 
            return {'code': 0, 'msg': f'The selected source {anime_add.source.value} must be passed the search text', 'detail': []} 
        else: 
            search_text = None  
            http_url = anime_add.http_url.unicode_string() 

    else: 
        if anime_add.source not in AnimeSourcesParsed: 
            return {'code': 0, 'msg': f'The selected source {anime_add.source.value} must be passed the http url', 'detail': []} 
        else: 
            search_text = anime_add.search_text 
            http_url = anime.get_http_url(anime_add.source, anime_add.search_text) 

    anime_db = AnimeDB( 
        uuid=uuid, 
        name=anime_add.name, 
        season=anime_add.season, 
        dir_path=dir_path, 
        source=anime_add.source, 
        search_text=search_text, 
        http_url=http_url, 
        episodes_str='', 
        newest_pub_date=0., 
        auto_update=anime_add.auto_update, 
        under_management=False, 
    ) 

    with Session(engine) as session: 
        if session.exec(select(AnimeDB).where(AnimeDB.uuid == anime_db.uuid)).first() is not None: 
            return {'code': 0, 'msg': 'Anime is already in the library', 'detail': []} 
        
        session.add(anime_db) 
        session.commit() 

    return {'code': 1, 'msg': 'Anime added successfully', 'detail': []} 


def change_anime(anime_change: AnimeChange) -> dict[str, str | list[dict[str, str]]]: 
    with Session(engine) as session: 
        anime_db = session.exec(select(AnimeDB).where(AnimeDB.uuid == anime_change.uuid).with_for_update()).first() 
        if anime_db is None: 
            return {'code': 0, 'msg': 'Anime dose not exist', 'detail': []} 
        
        if anime_db.under_management: 
            return {'code': 0, 'msg': 'Anime is under management', 'detail': []} 
        
        anime_db.under_management = True 

        session.add(anime_db) 
        session.commit() 

    with Session(engine) as session: 
        anime_db = session.exec(select(AnimeDB).where(AnimeDB.uuid == anime_change.uuid)).first() 
        
        if anime_change.search_text is not None and anime_change.http_url is not None: 
            return {'code': 0, 'msg': 'Search text and http url cannot have values at the same time', 'detail': []} 

        if anime_change.source is not None: 
            anime_db.source = anime_change.source 

            if anime_change.source in AnimeSourcesParsed: 

                if anime_change.http_url is not None: 
                    return { 
                        'code': 0, 'detail': [], 
                        'msg': f'The selected source {anime_change.source.value} cannot be passed the http url', 
                    } 

                elif anime_change.search_text is not None: 
                    anime_db.search_text = anime_change.search_text 

                elif anime_db.search_text is None: 
                    return { 
                        'code': 0, 'detail': [],
                        'msg': f'The selected source {anime_change.source.value} must be passed the search text', 
                    } 

                anime_db.http_url = anime.get_http_url(anime_db.source, anime_db.search_text) 

            else: 
                
                if anime_change.search_text is not None: 
                    return {
                        'code': 0, 'detail': [], 
                        'msg': f'The selected source {anime_change.source.value} cannot be passed the search text', 
                    } 
                
                elif anime_change.http_url is not None: 
                    anime_db.http_url = anime_change.search_text 

                elif anime_db.http_url is None: 
                    return { 
                        'code': 0, 'detail': [], 
                        'msg': f'The selected source {anime_change.source.value} must be passed the http url', 
                    } 
                
                anime_db.search_text = None 

        else: 

            if anime_change.search_text is not None: 
                if anime_db.source not in AnimeSourcesParsed: 
                    return { 
                        'code': 0, 'detail': [], 
                        'msg': f'The selected source {anime_db.source} cannot be passed the search text', 
                    } 
                
                anime_db.search_text = anime_change.search_text 
                anime_db.http_url = anime.get_http_url(anime_db.source, anime_db.search_text) 

            if anime_change.http_url is not None: 
                if anime_db.source in AnimeSourcesParsed: 
                    return { 
                        'code': 0, 'detail': [], 
                        'msg': f'The selected source {anime_db.source} cannot be passed the http url', 
                    } 
                
                anime_db.http_url = anime_change.http_url 

        if anime_change.auto_update is not None: 
            anime_db.auto_update = anime_change.auto_update 

        session.add(anime_db) 
        session.commit() 

    return {'code': 1, 'msg': 'Anime changed successfully', 'detail': ''} 


def inquire_anime_update_ready() -> list[AnimeDB]: 
    with Session(engine) as session: 
        anime_db_list = session.exec(select(AnimeDB).where( 
            and_(AnimeDB.auto_update == True, AnimeDB.under_management == False) 
        ).with_for_update()).all() 

        for anime_db in anime_db_list: 
            anime_db.under_management = True 
        
        session.add_all(anime_db_list) 
        session.commit() 

    return anime_db_list 


def inquire_anime(anime_inquire: AnimeInquire) -> dict[str, str | list[dict[str, str]]]: 
    with Session(engine) as session: 
        if anime_inquire.uuid is not None: 
            list_anime_db = session.exec(select(AnimeDB).where(AnimeDB.uuid == anime_inquire.uuid)).all() 
        
        elif anime_inquire.name is not None: 
            list_anime_db = session.exec(select(AnimeDB).where(AnimeDB.name.contains(anime_inquire.name))).all() 

        else: 
            list_anime_db = session.exec(select(AnimeDB)).all() 

        if len(list_anime_db) == 0: 
            return {'code': 0, 'msg': 'Anime dose not exist', 'detail': []} 
        
        list_anime_db = [anime_db.model_dump() for anime_db in list_anime_db] 
        
        return {'code': 1, 'msg': 'Anime inquire successful', 'detail': list_anime_db} 
    

def delete_anime(anime_delete: AnimeDelete) -> dict[str, str | list[str, str]]: 
    with Session(engine) as session: 
        anime_db = session.exec(select(AnimeDB).where(AnimeDB.uuid == anime_delete.uuid).with_for_update()).first() 

        if anime_db is None: 
            return {'code': 0, 'msg': 'Anime dose not exist', 'detail': []} 
        
        if anime_db.under_management: 
            return {'code': 0, 'msg': 'Anime is under management', 'detail': []} 
        
        anime_db.under_management = True 

        session.add(anime_db) 
        session.commit() 

    with Session(engine) as session: 
        anime_db = session.exec(select(AnimeDB).where(AnimeDB.uuid == anime_delete.uuid)).first() 
        
        session.delete(anime_db) 
        session.commit() 


async def _get_episode_db_async(episode_add: EpisodeAdd) -> EpisodeUpdateTaskDB: 
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


async def add_episode_list(episode_add_list: list[EpisodeAdd]) -> None: 
    
    episode_update_task_list: list[EpisodeUpdateTaskDB] = await asyncio.gather(*( 
        asyncio.create_task(_get_episode_db_async(episode_add)) for episode_add in episode_add_list 
    )) 
    episode_update_task_list = [episode_db for episode_db in episode_update_task_list if episode_db] 

    with Session(engine) as session: 
        session.add_all(episode_update_task_list) 
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

        episode_update_task_list=list(uuid_add_num_episode_dict.values()) 

        for episode_update_task in episode_update_task_list: 
            episode_update_task.under_management = True 

        session.add_all(episode_list) 
        session.commit() 

    return episode_update_task_list 

