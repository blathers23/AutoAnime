from settings import AnimeSourcesParsed 
from model import AnimeSearch 
from utils.request import request_xml_async 
from utils.anime import get_http_url, get_episode_info 


async def search_anime(anime_search: AnimeSearch) -> dict[str, str | list[dict[str, str | float]]]: 
    if anime_search.search_text is not None and anime_search.http_url is not None: 
        return {'code': 0, 'msg': 'Search text and http url cannot have values at the same time', 'detail': []} 
    
    elif anime_search.search_text is None and anime_search.http_url is None: 
        return {'code': 0, 'msg': 'Search text and http url cannot be empty at the same time', 'detail': []} 
    
    elif anime_search.source in AnimeSourcesParsed:

        if anime_search.search_text is not None: 
            http_url = get_http_url(anime_search.source, anime_search.search_text) 

        else: 
            return {'code': 0, 'msg': f'The selected source {anime_search.source.value} must be passed the search text', 'detail': []} 
        
    else: 

        if anime_search.http_url is not None: 
            http_url = anime_search.http_url.unicode_string() 

        else:
            return {'code': 0, 'msg': f'The selected source {anime_search.source.value} must be passed the http url', 'detail': []} 
        
    xml = await request_xml_async(http_url) 
    episode_info_list = get_episode_info(anime_search.source, xml) 

    return { 
        'code': 1, 'msg': 'success', 
        'detail': [
            {
                'title': episode_info[0], 'episode_num': str(episode_info[1]), 'pub_date': episode_info[2]
            } for episode_info in episode_info_list
        ] 
    } 

