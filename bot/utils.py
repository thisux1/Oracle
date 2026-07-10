import datetime
import bot.config as config

def is_sleep_time():
    if not config.sleep_at or not config.wake_up_at:
        return False
    
    try:
        now = datetime.datetime.now().time()
        sleep_time = datetime.datetime.strptime(config.sleep_at, "%H:%M").time()
        wake_time = datetime.datetime.strptime(config.wake_up_at, "%H:%M").time()
        
        if sleep_time < wake_time:
            # Case 1: Sleep during the same day (e.g., 01:00 to 05:00)
            return sleep_time <= now < wake_time
        else: 
            # Case 2: Sleep over midnight (e.g., 23:00 to 07:00)
            return now >= sleep_time or now < wake_time
    except Exception as e:
        # If format is wrong, disable sleep mode to avoid crash
        return False
