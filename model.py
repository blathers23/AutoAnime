from pydantic import BaseModel, DirectoryPath, HttpUrl, AnyUrl  

from settings import AnimeSources


class AnimeAdd(BaseModel, validate_assignment=True): 
    name: str 
    season: int 
    source: AnimeSources 
    search_text: str | None 
    http_url: HttpUrl | None 
    auto_update: bool 


class AnimeChange(BaseModel, validate_assignment=True): 
    uuid: str 
    source: AnimeSources | None = None 
    search_text: str | None = None 
    http_url: HttpUrl | None = None 
    auto_update: bool | None = None 


class AnimeInquire(BaseModel, validate_assignment=True): 
    uuid: str | None 
    name: str | None 


class AnimeDelete(BaseModel, validate_assignment=True): 
    uuid: str | None 


class AnimeUpdate(BaseModel, validate_assignment=True): 
    uuid: str 
    name: str 
    season: int  
    dir_path: DirectoryPath 
    source: AnimeSources 
    http_url: HttpUrl 
    episodes_list: list[int] 
    xml: str 


class EpisodeAdd(BaseModel, validate_assignment=True): 
    torrent_url: AnyUrl 
    uuid: str 
    name: str 
    season: int 
    dir_path: str 
    episode_num: int  
    pub_date: float 


class EpisodeUpdate(BaseModel, validate_assignment=True): 
    id_: int 
    torrent_hash: str 
    uuid: str 
    file_path: str 
    episode_num: int  
    pub_date: float 
    downloaded: bool  
    copied: bool  

