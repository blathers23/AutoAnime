from sqlmodel import SQLModel, Field, create_engine 

from settings import user_settings 


class AnimeDB(SQLModel, table=True): 
    uuid: str = Field(primary_key=True) 
    name: str 
    season: int 
    dir_path: str 
    source: str 
    search_text: str | None 
    http_url: str 
    episodes_str: str 
    newest_pub_date: float 
    auto_update: bool 
    under_management: bool 


class EpisodeUpdateTaskDB(SQLModel, table=True): 
    id_: int | None = Field(default=None, primary_key=True) 
    torrent_hash: str 
    torrent_file_path: str 
    torrent_magnet: str 
    uuid: str 
    episode_num: int 
    file_path: str 
    pub_date: float 
    under_management: bool 
    done: bool 


# engine = create_engine(url=f'sqlite:///{user_settings.work_path}/autoanime.db') 
engine = create_engine(url=f'sqlite:///{user_settings.work_path}/autoanime.db', echo=True) 
SQLModel.metadata.create_all(engine) 


if __name__ == '__main__': 
    import os 

    from sqlmodel import Session, select, update 

    anime = AnimeDB(
        uuid='1', name='test', season=1, dir_path='', source=user_settings.default_source, 
        search_text=None, http_url='', episodes_str='1', newest_pub_date=0., auto_update=True, 
        under_management=False, 
    ) 

    with Session(engine) as session: 
        session.add(anime) 
        # session.add(episode) 
        session.commit() 

    # anime_change = AnimeDB(
    #     uuid='1', name='test', season=1, dir_path='', source=user_settings.default_source, 
    #     search_text='', http_url='', episodes='1', newest_pub_date=0., auto_update=True, 
    #     under_management=True, 
    # ) 

    with Session(engine) as session: 
        anime = session.exec(select(AnimeDB).where(AnimeDB.name.contains('a'))).first() 
        print(anime)

    # with Session(engine) as session: 
    #     anime = session.exec(select(AnimeDB)).first() 
    #     print(anime) 
    #     anime.name = '2' 
    #     session.add(anime) 
    #     session.commit() 
    #     anime = session.exec(select(AnimeDB)).first() 
    #     print(anime) 

    os.remove(os.path.join(user_settings.work_path, 'autoanime.db')) 
