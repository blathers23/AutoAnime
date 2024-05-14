import requests 

from settings import user_settings, read_user_settings_file  
from api_client import jellyfin_client as media_client 
from api_client import qbittorrent_client as torrent_client 


from acid.internal import (
    change_anime_db_clean_up, 
    change_episode_update_task_db_cleanup, 
    delete_episode_update_task_db_out_of_capacity, 
)


def cleanup_database() -> None: 
    change_anime_db_clean_up() 
    delete_episode_update_task_db_out_of_capacity() 
    change_episode_update_task_db_cleanup() 


def load_and_test_settings() -> dict[str, str | list]: 
    response = read_user_settings_file(user_settings) 
    if response['code'] == 0: 
        return response 
    
    # 测试 media_client 
    print('测试媒体客户端....', end='') 
    try: 
        media_client.login() 
        media_client.refresh() 
        print('ok.') 
    except: 
        print('fails.') 
        return {'code': 0, 'msg': '媒体客户端测试不通过', 'detail': []} 

    # 测试 torrent_client 
    print('测试 Torrent 客户端....', end='') 
    try:
        torrent_client.login() 
        torrent_client.info(torrent_hashes=[]) 
        print('ok.') 
    except:
        print('fails.')
        return {'code': 0, 'msg': 'Torrent 客户端测试不通过', 'detail': []} 

    # 测试代理 
    if user_settings.http_proxy: 
        try:
            print('测试代理服务器....', end='') 
            r = requests.get('http://www.google.com/', proxies={'http': user_settings.http_proxy.unicode_string()}) 
            assert r.status_code == 200 
            print('ok.') 
        except: 
            print('fails.')
            return {'code': 0, 'msg': '代理服务器测试不通过', 'detail': []} 
        
    return {'code': 1, 'msg': '全部测试通过!', 'detail': []} 

