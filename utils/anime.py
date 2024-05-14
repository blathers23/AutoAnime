import os 
import re 
from hashlib import sha1 
from urllib.parse import quote 
from typing import Callable 
from xml.etree import ElementTree 
from datetime import datetime, timezone 

from settings import AnimeSources, user_settings 


def get_uuid(name: str, season: int) -> str: 
    return sha1((name+str(season)).encode()).hexdigest() 


def get_dir_path(name: str, season: str) -> str: 
    return os.path.join(user_settings.base_path, name, f'Season{str(season)}') 


def _acgrip_http_url_constructor(text: str) -> str: 
    http_url = 'https://acg.rip/.xml?term=' + quote(text) 
    return http_url 


def _dmhy_http_url_constructor(text: str) -> str: 
    http_url = f'http://www.dmhy.org/topics/rss/rss.xml?keyword={quote(text)}&sort_id=2&team_id=0&order=date-desc' 
    return http_url 


def _bangumi_http_url_constructor(text: str) -> str: 
    http_url = 'https://bangumi.moe/rss/search/' + quote(text) 
    return http_url 


anime_http_url_constructor = {
    'acgrip': _acgrip_http_url_constructor, 
    'dmhy': _dmhy_http_url_constructor, 
    'bangumi': _bangumi_http_url_constructor,  
}


def get_http_url(source: AnimeSources, search_text: str) -> str: 
    return anime_http_url_constructor[source.value](search_text) 


def _xml_parser_generator(time_format: str) -> Callable[[str], list[tuple[str, int, float, str]]]: 

    def _parse_episode(name: str) -> int: 
        res = -1
        matched_episode_block = re.search(r' - \d+ | - \d+v\d+ |\[\d+\]|第\d+集|第\d+話', name) 
        if matched_episode_block:
            matched_episode = re.search(r'\d+', matched_episode_block.group())
            if matched_episode:
                res = matched_episode.group() 

        return int(res) 

    def _xml_parser(xml: str) -> list[tuple[str, int, float, str]]: 
        episode_info_list: list[tuple[str, int, float, str]] = list() 

        try: 
            root = ElementTree.fromstring(xml).find('channel') 
        except: 
            print(xml) 
            return list() 

        for item in root.iter(tag='item'): 
            title: str = item.find('title').text 
            episode_num: int = _parse_episode(title) 
            
            pub_date = datetime.strptime(
                item.find('pubDate').text, time_format
            ).astimezone(timezone.utc).timestamp() 
            torrent_url = item.find('enclosure').attrib['url'] 

            episode_info_list.append((
                title, episode_num, 
                pub_date, torrent_url, 
            ))

        return episode_info_list 

    return _xml_parser 


anime_xml_parser = {
    'acgrip': _xml_parser_generator(time_format='%a, %d %b %Y %H:%M:%S %z') , 
    'dmhy': _xml_parser_generator(time_format='%a, %d %b %Y %H:%M:%S %z'), 
    'bangumi': _xml_parser_generator(time_format='%a, %d %b %Y %H:%M:%S %Z') 
} 


def get_episode_info(source: AnimeSources, xml: str) -> list[tuple[str, int, float, str]]: 
    return anime_xml_parser[source.value](xml) 

