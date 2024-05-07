from sqlmodel import Session, select 

from model import AnimeChange, AnimeAdd, AnimeInquire, AnimeDelete  
from database import engine, AnimeDB, EpisodeUpdateTaskDB   
from settings import AnimeSourcesParsed, user_settings 
from utils import anime_get_uuid, anime_get_dir_path, anime_get_http_url


def add_anime(anime_add: AnimeAdd) -> dict[str, str | list[dict[str, str]]]: 
    uuid = anime_get_uuid(anime_add.name, anime_add.season)     
    dir_path = anime_get_dir_path(anime_add.name, anime_add.season) 

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
            http_url = anime_get_http_url(anime_add.source, anime_add.search_text) 

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

                anime_db.http_url = anime_get_http_url(anime_db.source, anime_db.search_text) 

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
                anime_db.http_url = anime_get_http_url(anime_db.source, anime_db.search_text) 

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
        
