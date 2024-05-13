from acid.internal import (
    change_anime_db_clean_up, 
    change_episode_update_task_db_cleanup, 
    delete_episode_update_task_db_out_of_capacity, 
)


async def cleanup_database() -> None: 
    change_anime_db_clean_up() 
    delete_episode_update_task_db_out_of_capacity() 
    change_episode_update_task_db_cleanup() 

