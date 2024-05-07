from pydantic import BaseModel, DirectoryPath, HttpUrl 

from settings import AnimeSources


class AnimeChange(BaseModel, validate_assignment=True): 
    uuid: str 
    source: AnimeSources | None = None 
    search_text: str | None = None 
    http_url: HttpUrl | None = None 
    auto_update: bool | None = None 


class AnimeAdd(BaseModel, validate_assignment=True): 
    name: str 
    season: int 
    source: AnimeSources 
    search_text: str | None 
    http_url: HttpUrl | None 
    auto_update: bool 


class AnimeInquire(BaseModel, validate_assignment=True): 
    uuid: str | None 
    name: str | None 


class AnimeDelete(BaseModel, validate_assignment=True): 
    uuid: str | None 


class Anime(BaseModel, validate_assignment=True): 
    uuid: str 
    season: int  
    dir_path: DirectoryPath 
    source: AnimeSources 
    http_url: HttpUrl 
    episodes_list: list[int] 
    xml: str 
