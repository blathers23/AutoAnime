import asyncio 

from sqlmodel import Session, select, and_ 

from model import AnimeUpdate 
from database import engine, AnimeDB 
from utils import request_xml_async 


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


async def update_anime() -> dict[str, str | list[dict[str, str]]]: 
    with Session(engine) as session: 
        anime_db_list = session.exec(select(AnimeDB).where( 
            and_(AnimeDB.auto_update == True, AnimeDB.under_management == False) 
        ).with_for_update()).all() 

        for anime_db in anime_db_list: 
            anime_db.under_management = True 
        
        session.add_all(anime_db_list) 
        session.commit() 

    anime_update_list = await asyncio.gather(*(
        asyncio.create_task(_get_anime_update_async(anime_db)) for anime_db in anime_db_list
    )) 

    

