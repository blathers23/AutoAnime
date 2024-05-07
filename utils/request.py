from tempfile import NamedTemporaryFile 

from aiohttp import ClientSession, ClientTimeout 

from settings import user_settings 


async def request_tmp_file_async(url: str) -> str:
    proxy = user_settings.http_proxy 
    if proxy: 
        proxy = user_settings.http_proxy.unicode_string() 
    
    async with ClientSession(timeout=ClientTimeout(total=user_settings.timeout)) as session: 
        async with session.get(url, proxy=proxy) as resp: 
            content = await resp.content.read() 
            with NamedTemporaryFile(delete=False) as fp: 
                fp.write(content) 

                return fp.name 
            

async def request_xml_async(url: str) -> str: 
    proxy = user_settings.http_proxy 
    if proxy: 
        proxy = user_settings.http_proxy.unicode_string() 

    async with ClientSession(timeout=ClientTimeout(total=user_settings.timeout)) as session: 
        async with session.get(url, proxy=proxy) as resp: 

            return await resp.text() 
        
