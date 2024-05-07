import os 
from base64 import b32decode 

from pydantic import AnyUrl 
from torf import Torrent 

from model import EpisodeAdd 
from database import EpisodeUpdateTaskDB 
from settings import user_settings 
from request import request_tmp_file_async 


async def parse_torrent_url_async(torrent_url: AnyUrl) -> tuple[str, str, str]: 

    torrent_hash = None 
    torrent_file_path = None 
    torrent_magnet = None 

    if torrent_url.scheme == 'http' or torrent_url.scheme == 'https': 
        torrent_magnet = '' 
        torrent_file_path = await request_tmp_file_async(torrent_url.unicode_string()) 
        torrent_hash = Torrent.read(torrent_file_path).infohash 

    elif torrent_url.scheme == 'magnet': 
        torrent_file_path = '' 
        torrent_magnet = torrent_url.unicode_string() 

        xt = torrent_url.query[3:torrent_url.query.find('&')] 
        assert xt[:9] == 'urn:btih:', 'xt not support yet'

        infohash = xt[9:] 
        if len(infohash) == 32:
            torrent_hash = b32decode(infohash).hex() 
        elif len(infohash) == 40: 
            torrent_hash = infohash 
        else: 
            raise AssertionError('length not correct') 

    else: 
        raise AssertionError('scheme not support yet') 
    
    return torrent_hash, torrent_file_path, torrent_magnet 

    

def parse_xml():
    pass 