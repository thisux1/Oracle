import json
import os
import time
import copy
from bot.hud import logger

STATS_FILE = "stats_totals.json"
HISTORY_FILE = "stats_history.json"

def subtract_dicts(d1, d2):
    result = {}
    for k, v in d1.items():
        if isinstance(v, dict):
            if k in d2 and isinstance(d2[k], dict):
                result[k] = subtract_dicts(v, d2[k])
            else:
                result[k] = copy.deepcopy(v)
        elif isinstance(v, (int, float)):
            result[k] = v - d2.get(k, 0)
        else:
            result[k] = v
    return result

def merge_dicts(default, saved):
    for k, v in saved.items():
        if isinstance(v, dict) and k in default and isinstance(default[k], dict):
            merge_dicts(default[k], v)
        elif k in default:
            default[k] = v

def load_session_data(default_data):
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r") as f:
                saved_data = json.load(f)
                merged = copy.deepcopy(default_data)
                merge_dicts(merged, saved_data)
                return merged
        except Exception as e:
            logger.error(f"Error loading stats_totals.json: {e}")
    return copy.deepcopy(default_data)

def save_session_data(session_data, save_snapshot=False):
    try:
        with open(STATS_FILE, "w") as f:
            json.dump(session_data, f, indent=4)
            
        if save_snapshot:
            history = {}
            if os.path.exists(HISTORY_FILE):
                try:
                    with open(HISTORY_FILE, "r") as f:
                        history = json.load(f)
                except Exception:
                    pass
            
            now = time.time()
            history[str(now)] = copy.deepcopy(session_data)
            
            # keep max 30 days of snapshots
            cutoff = now - (31 * 24 * 3600)
            history = {k: v for k, v in history.items() if float(k) > cutoff}
            
            with open(HISTORY_FILE, "w") as f:
                json.dump(history, f)
    except Exception as e:
        logger.error(f"Error saving session data: {e}")

def get_stats_for_period(current_data, period_str):
    # period_str can be '10h', '10d', '1m', '24h'
    if not os.path.exists(HISTORY_FILE):
        return current_data
        
    try:
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
    except Exception:
        return current_data
        
    now = time.time()
    seconds_to_subtract = 0
    
    if period_str.endswith("h"):
        seconds_to_subtract = int(period_str[:-1]) * 3600
    elif period_str.endswith("d"):
        seconds_to_subtract = int(period_str[:-1]) * 24 * 3600
    elif period_str.endswith("m"):
        seconds_to_subtract = int(period_str[:-1]) * 30 * 24 * 3600
    else:
        return current_data
        
    target_time = now - seconds_to_subtract
    
    # find the closest snapshot before or equal to target_time
    closest_timestamp = None
    min_diff = float('inf')
    
    for ts_str in history.keys():
        ts = float(ts_str)
        # We want the snapshot that is closest to our target_time
        diff = abs(ts - target_time)
        if diff < min_diff:
            min_diff = diff
            closest_timestamp = ts_str
            
    if closest_timestamp:
        snapshot = history[closest_timestamp]
        result = subtract_dicts(current_data, snapshot)
        result["start_time"] = float(closest_timestamp)
        return result
        
    return current_data
