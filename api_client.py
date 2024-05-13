from typing import Iterable 

from qbittorrentapi import Client as QbittorrentClient 
from jellyfin_apiclient_python import JellyfinClient 

from settings import autoanime_settings, user_settings 


def login_jellyfin() -> JellyfinClient: 
    jellyfin_client: JellyfinClient = JellyfinClient() 
    jellyfin_client.config.app( 
        name=autoanime_settings.name, 
        version=autoanime_settings.version, 
        device_name=user_settings.host_name, 
        device_id=user_settings.host_name + user_settings.jellyfin_username 
    ) 
    jellyfin_client.config.data['auth.ssl'] = True 
    jellyfin_client.auth.connect_to_address(user_settings.jellyfin_addr.unicode_string()[:-1]) 
    jellyfin_client.auth.login(
        server_url=user_settings.jellyfin_addr.unicode_string()[:-1], 
        username=user_settings.jellyfin_username, 
        password=user_settings.jellyfin_password.get_secret_value(), 
    ) 

    return jellyfin_client 


def refresh_jellyfin(client: JellyfinClient) -> None: 
        client.jellyfin._post("Library/Refresh") 


def login_qbittorrent() -> QbittorrentClient: 
    qbittorrent_client: QbittorrentClient = QbittorrentClient(
        host=user_settings.qbittorrent_addr.host, 
        port=user_settings.qbittorrent_addr.port, 
        username=user_settings.qbittorrent_username, 
        password=user_settings.qbittorrent_password.get_secret_value(), 
    )

    return qbittorrent_client 


def add_qbittorrent(
        client: QbittorrentClient, 
        torrent_urls: Iterable[str] | None = None, 
        torrent_files: Iterable[str] | None = None
    ) -> str: 

    return client.torrents_add(urls=torrent_urls, torrent_files=torrent_files) 


def delete_qbittorrent(client: QbittorrentClient, torrent_hashes: Iterable[str]) -> None: 
    return client.torrents_delete(delete_files=False, torrent_hashes=torrent_hashes)


def info_qbittorrent(
        client: QbittorrentClient, 
        torrent_hashes: Iterable[str]
) -> Iterable[dict[str, str | float]]: 
    return client.torrents_info(torrent_hashes=torrent_hashes) 


class MediaClient:  
    def __init__(self, login_method, refresh_method): 
        self.login_method = login_method  
        self.refresh_method = refresh_method 
        self.client = None  
        self.re_login = False 

    def login(self): 
        self.client = self.login_method() 

    def refresh(self): 
        if not self.client or self.re_login: 
            self.login() 
        
        self.refresh_method(self.client) 


class TorrentClient: 
    def __init__(self, login_method, add_method, delete_methode, info_method): 
        self.login_method = login_method 
        self.add_method = add_method 
        self.delete_method = delete_methode 
        self.info_method = info_method 
        self.client = None 
        self.re_login = False 

    def login(self) -> None: 
        self.client = self.login_method() 

    def add( 
        self, torrent_urls: Iterable[str] | None = None, 
        torrent_files: Iterable[str] | None = None 
    ) -> str: 
        if not self.client or self.re_login: 
            self.login() 
        
        return self.add_method(self.client, torrent_urls, torrent_files) 
    
    def delete(self, torrent_hashes: Iterable[str]) -> None: 
        if not self.client or self.re_login: 
            self.login() 

        return self.delete_method(self.client, torrent_hashes) 
    
    def info(self, torrent_hashes: Iterable[str]) -> Iterable[dict[str, str | float]]:
        if not self.client or self.re_login: 
            self.login() 

        return self.info_method(self.client, torrent_hashes) 


jellyfin_client = MediaClient(login_jellyfin, refresh_jellyfin) 
qbittorrent_client = TorrentClient(login_qbittorrent, add_qbittorrent, delete_qbittorrent, info_qbittorrent) 
