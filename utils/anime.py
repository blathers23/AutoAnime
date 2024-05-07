import os 
from hashlib import sha1 
from urllib.parse import quote 

from settings import AnimeSources, user_settings 


def get_uuid(name: str, season: int) -> str: 
    return sha1((name+str(season)).encode()).hexdigest() 


def get_dir_path(name: str, season: str) -> str: 
    return os.path.join(user_settings.base_path, name, f'Season{str(season)}') 


def acgrip_http_url_constructor(text: str) -> str: 
    http_url = 'https://acg.rip/.xml?term=' + quote(text) 
    return http_url 


def dmhy_http_url_constructor(text: str) -> str: 
    http_url = f'http://www.dmhy.org/topics/rss/rss.xml?keyword={quote(text)}&sort_id=2&team_id=0&order=date-desc' 
    return http_url 


def bangumi_http_url_constructor(text: str) -> str: 
    http_url = 'https://bangumi.moe/rss/search/' + quote(text) 
    return http_url 


anime_http_url_constructor = {
    'acgrip': acgrip_http_url_constructor, 
    'dmhy': dmhy_http_url_constructor, 
    'bangumi': bangumi_http_url_constructor 
}


def get_http_url(source: AnimeSources, search_text: str) -> str: 
    return anime_http_url_constructor[source.value](search_text) 

