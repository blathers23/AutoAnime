from contextlib import asynccontextmanager 
from datetime import datetime, timedelta  

from fastapi import FastAPI, APIRouter, BackgroundTasks, Depends, Request 
from fastapi.responses import JSONResponse   
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.job import Job 
from apscheduler.schedulers.asyncio import AsyncIOScheduler 
from starlette.staticfiles import StaticFiles 
from starlette.templating import Jinja2Templates  

from settings import autoanime_settings, user_settings, read_user_settings_file  
from model import AnimeAdd, AnimeChange, AnimeInquire, AnimeDelete, AnimeSearch, EpisodeInquire 
from start_up import cleanup_database, load_and_test_settings 
from acid.external import add_anime, change_anime, inquire_anime, delete_anime, inquire_episode 
from update import update_add_task, update_run_task, update_auto_update 
from search import search_anime 


asyncio_scheduler = AsyncIOScheduler() 
# tamplates = Jinja2Templates(directory='static') 
settings_checked = False 


def put_off_auto_update(func): 
    async def warp_func(): 
        job: Job = asyncio_scheduler.get_job(job_id='auto_update') 
        job.modify(next_run_time = None) 

        res = await func() 

        job.modify(next_run_time = datetime.now() + timedelta(seconds=user_settings.auto_update_online_interval)) 
        return res 
    
    return warp_func 


# lifespan 
@asynccontextmanager 
async def lifespan(app: FastAPI): 
    response = read_user_settings_file(user_settings) 
    if response['code'] == 1: 
        print(response['msg']) 

        response = load_and_test_settings() 
        if response['code'] == 1: 
            global settings_checked 
            settings_checked = True 
        
        print(response['msg']) 
    
    else:     
        print(response['msg']) 
    
    cleanup_database() 
    print('Cleaning database completed') 

    asyncio_scheduler.add_job( 
        func=update_auto_update, 
        trigger='interval', 
        id='auto_update', 
        replace_existing=True, 
        seconds=user_settings.auto_update_offline_interval) 
    asyncio_scheduler.start() 

    job: Job = asyncio_scheduler.get_job(job_id='auto_update') 
    print('The automatic update task is created') 
    print(f'Next automatic update time: {job.next_run_time}') 

    yield 


app = FastAPI(
    debug=True, 
    title='Auto Anime', 
    version=autoanime_settings.version, 
    summary='I am a cat; but as yet I have no name.', 
    lifespan=lifespan, 
) 


app.add_middleware( 
    CORSMiddleware, 
    allow_origins=['http://127.0.0.1:8000', 'http://localhost:8000'], 
    allow_credentials=True, allow_methods=['*'], allow_headers=['*'], 
) 


# app.mount('/static', StaticFiles(directory='static'), name='static') 

 
# @app.get('/', include_in_schema=False) 
# async def vue(request: Request): 
#     return tamplates.TemplateResponse('index.html', {'request': request}) 


class UncheckedException(Exception): 
    pass 


@app.exception_handler(UncheckedException)
async def unicorn_exception_handler(request: Request, exc: UncheckedException):
    return JSONResponse(
        status_code=403,
        content={'code': 0, 'msg': 'Settings file has not passed testing', 'detail': []},
    )


async def is_config_loaded_and_checked() -> dict[str, str | list]: 
    if not settings_checked: 
        raise UncheckedException() 
    

# 与配置有关的接口 
settings_router = APIRouter(prefix='/settings') 


@settings_router.get('/check/') 
async def check_settings(): 
    global settings_checked 

    response = load_and_test_settings() 
    if response['code'] == 1: 
        settings_checked = True 
    else: 
        settings_checked = False 

    return response 


# 与新建有关的接口 
add_router = APIRouter(prefix='/add') 


@add_router.post('/')
async def add_anime_api(anime_add: AnimeAdd): 
    response = add_anime(anime_add) 
    return response 


# 与修改有关的接口 
change_router = APIRouter(prefix='/change')


@change_router.post('/')
async def change_anime_api(anime_change: AnimeChange): 
    response = change_anime(anime_change) 
    return response 


# 与查找有关的接口 
inquire_router = APIRouter(prefix='/inquire') 


@inquire_router.post('/anime')
async def inquire_anime_api(anime_inquire: AnimeInquire): 
    response = inquire_anime(anime_inquire) 
    return response 


@inquire_router.post('/episode') 
async def inquire_episode_api(episode_inquire: EpisodeInquire): 
    response = inquire_episode(episode_inquire) 
    return response 


# 与删除有关的接口 
delete_router = APIRouter(prefix='/delete')


@delete_router.delete('/') 
async def delete_anime_api(anime_delete: AnimeDelete): 
    response = delete_anime(anime_delete) 
    return response 


# 与搜索有关的接口
search_router = APIRouter(prefix='/search') 


@search_router.post('/') 
async def search_anime_api(anime_search: AnimeSearch): 
    response = await search_anime(anime_search) 
    return response 


# 与更新有关的接口 
update_router = APIRouter(prefix='/update') 


@update_router.get('/') 
async def update_add_task_and_run_task_api(background_tasks: BackgroundTasks): 
    response = await update_add_task(auto_update=False)
    background_tasks.add_task(put_off_auto_update(update_run_task)) 
    return response  


app.include_router(router=settings_router) 
app.include_router(router=add_router, dependencies=[Depends(is_config_loaded_and_checked)]) 
app.include_router(router=change_router, dependencies=[Depends(is_config_loaded_and_checked)]) 
app.include_router(router=inquire_router, dependencies=[Depends(is_config_loaded_and_checked)]) 
app.include_router(router=delete_router, dependencies=[Depends(is_config_loaded_and_checked)]) 
app.include_router(router=search_router, dependencies=[Depends(is_config_loaded_and_checked)]) 
app.include_router(router=update_router, dependencies=[Depends(is_config_loaded_and_checked)]) 


def main(): 
    import uvicorn 
    uvicorn.run(app='autoanime:app', host='127.0.0.1', port=8000, reload=True) 


if __name__ == '__main__': 
    main() 
