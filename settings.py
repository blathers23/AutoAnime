import os 
import yaml 
from enum import Enum 

from pydantic import (
    BaseModel, Field, field_serializer, HttpUrl, DirectoryPath, FilePath, Secret, ValidationError 
) 


class AutoAnimeSettings(BaseModel): 
    name: str = Field('AutoAnime', frozen=True) 
    version: str = Field('3.0.0-beta4-1', frozen=True) 


class AnimeSources(str, Enum): 
    acgrip = 'acgrip' 
    dmhy = 'dmhy' 
    bangumi = 'bangumi' 


class AnimeSourcesParsed(str, Enum): 
    acgrip = 'acgrip' 
    dmhy = 'dmhy' 
    bangumi = 'bangumi' 


class AnimeSourcesSubscribed(str, Enum): 
    pass 


class UserSettings(BaseModel, validate_assignment=True): 
    # Base Settings 
    host_name: str 
    base_path: DirectoryPath 
    work_path: DirectoryPath 
    settings_file_path: FilePath 
    # API Client Settings 
    jellyfin_addr: HttpUrl 
    jellyfin_username: str 
    jellyfin_password: Secret[str] 
    qbittorrent_addr: HttpUrl 
    qbittorrent_username: str 
    qbittorrent_password: Secret[str] 
    # Update Settings 
    refresh_time: int 
    auto_update_offline_interval: int 
    auto_update_online_interval: int 
    default_source: AnimeSources 
    download: bool 
    timeout: int 
    http_proxy: HttpUrl | None 


    @field_serializer('jellyfin_addr', when_used='json')
    def jellyfin_addr_serializer(self, jellyfin_addr: HttpUrl) -> str: 
        return str(jellyfin_addr)  
    

    @field_serializer('qbittorrent_addr', when_used='json') 
    def qbittorrent_addr_serializer(self, qbittorrent_addr: HttpUrl) -> str: 
        return str(qbittorrent_addr) 
    

    @field_serializer('default_source', when_used='json') 
    def default_source(self, default_source: AnimeSources) -> str: 
        return default_source.value 
    
    
    @field_serializer('http_proxy', when_used='json') 
    def http_proxy_serializer(self, http_proxy: HttpUrl | None) -> str | None: 
        if http_proxy is None: 
            return None 
        else: 
            return str(http_proxy) 


def read_user_settings_file(user_settings: UserSettings) -> dict[str, str | dict[str, str]]: 
    settings_file_path: str = user_settings.settings_file_path 
    if not os.path.isfile(settings_file_path): 
        return {'code': 0, 'msg': 'User settings file does not exist', 'detail': []} 
     
    with open(settings_file_path, mode='r') as f: 
        user_settings_dict: dict = yaml.safe_load(f) 

    try: 
        UserSettings.model_validate(user_settings_dict) 
    except ValidationError as e: 
        error_list = e.errors(include_url=False, include_input=False, include_context=False) 
        for err in error_list: 
            if err['loc']: 
                err['loc'] = err['loc'][0] 
            else: 
                err['loc'] = 'null' 
        return {'code': 0, 'msg': 'User settings file loading failed', 'detail': error_list} 
    else: 
        for k, v in user_settings_dict.items(): 
            setattr(user_settings, k, v) 
        
        return {'code': 1, 'msg': 'User settings file loaded successfully', 'detail': []} 


def save_user_settings_file(user_settings: UserSettings) -> None: 
    settings_file_path: str = user_settings.settings_file_path 
    user_settings_dict = user_settings.model_dump(mode='json') 

    with open(settings_file_path, mode='w') as f: 
        yaml.dump(user_settings_dict, f) 


user_settings = UserSettings(
    host_name = 'AutoAnime', 
    base_path = os.path.dirname(__file__), 
    work_path = os.path.dirname(__file__),  
    settings_file_path = os.path.join(os.path.dirname(__file__), 'user_settings.yaml'), 
    jellyfin_addr = 'http://127.0.0.1:8096/', 
    jellyfin_username = 'root', 
    jellyfin_password = '', 
    qbittorrent_addr = 'http://127.0.0.1:8080/', 
    qbittorrent_username = 'admin', 
    qbittorrent_password = '', 
    refresh_time = 2, 
    auto_update_offline_interval = 7200, 
    auto_update_online_interval = 604800, 
    default_source = list(AnimeSources)[0].value, 
    download = True, 
    timeout = 20, 
    http_proxy = None, 
) 

# user_settings_default = user_settings.model_copy() 


if __name__ == '__main__': 
    print(read_user_settings_file(user_settings)) 
    print(user_settings) 
    # save_user_settings_file(user_settings) 
