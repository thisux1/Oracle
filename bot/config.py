import re
import os
import time
import tensorflow as tf
import numpy as np
from PIL import Image
import options_resolver
from bot.hud import logger

# ─── Discord IDs ───
EPIC_RPG_ID = 555955826880413696
NAVI_LITE_ID = 1213487623688167494
NEON_BOT_IDS = [754276211302088704, 787861783143637032, 851436490415931422]
# ─── Oracle Model ───
img_height, img_width = 128, 128
model_path_color = 'oracle_v2_color.h5'
model_path_gray = 'oracle_v2_gray.h5'
classes_path = 'classes.txt'

try:
    captcha_model_color = tf.keras.models.load_model(model_path_color)
except:
    captcha_model_color = None

try:
    captcha_model_gray = tf.keras.models.load_model(model_path_gray)
except:
    captcha_model_gray = None

if os.path.exists(classes_path):
    with open(classes_path, 'r') as f:
        captcha_class_names = [line.strip() for line in f.readlines()]
else:
    captcha_class_names = sorted([
        d for d in os.listdir('dataset_cropped')
        if os.path.isdir(os.path.join('dataset_cropped', d))
    ])

# ─── User Options ───
userOptions = options_resolver.importData()

userToken = userOptions.get("user_token", "")

# Supports cleaner `user_id` but falls back to `user_mention_text` for backwards compatibility
raw_id = userOptions.get("user_id", "")
if not raw_id:
    mention = userOptions.get("user_mention_text", "")
    raw_id = mention.replace("<", "").replace(">", "").replace("@", "").replace("!", "")

userID = int(raw_id) if raw_id.isdigit() else 0
userMentionText = f"<@{userID}>"

channelID = int(userOptions.get("channel_id", "0"))
randomIntervals = userOptions.get("random_interval", "false").lower() == "true"
is_married = userOptions.get("is_married", "false").lower() == "true"
partner_name = userOptions.get("partner_name", "").lower() if is_married else None
is_ascended = userOptions.get("is_ascended", "false").lower() == "true"
farm_seed = userOptions.get("seed", "carrot").lower()
user_name_lower = userOptions.get("username", "").lower() # Fallback only, on_ready overwrites this
TelegramBotToken = userOptions.get("telegram_bot_token", "")
TelegramChatID = userOptions.get("telegram_chat_id", "")
try:
    typo_chance = float(userOptions.get("typo_chance", "0.05"))
except ValueError:
    typo_chance = 0.05
GUILD_ID = int(userOptions.get("guild_id", "0"))
startTime = time.time()
tc_stop_conditions = [x.strip().lower() for x in userOptions.get("tc_stop_on", "dungeon,miniboss").split(",") if x.strip()]

# ─── Togglable Command Flags ───
do_hunt     = userOptions.get("do_hunt", "true").lower() == "true"
do_adv      = userOptions.get("do_adv", "true").lower() == "true"
do_farm     = userOptions.get("do_farm", "true").lower() == "true"
do_work     = userOptions.get("do_work", "true").lower() == "true"
do_training = userOptions.get("do_training", "true").lower() == "true"
do_daily    = userOptions.get("do_daily", "true").lower() == "true"
do_weekly   = userOptions.get("do_weekly", "true").lower() == "true"
do_quest    = userOptions.get("do_quest", "true").lower() == "true"
do_lootbox  = userOptions.get("do_lootbox", "true").lower() == "true"
do_dungeon  = userOptions.get("do_dungeon", "true").lower() == "true"
do_card_hand = userOptions.get("do_card_hand", "true").lower() == "true"

# ─── ULTR / Training ───
do_ultr = userOptions.get("do_ultr", "false").lower() == "true"

# ─── Card Hand Action ───
card_hand_action = userOptions.get("card_hand_action", "auto").lower()

# ─── TC Quantity ───
tc_quantity = int(userOptions.get("tc_quantity", "1"))

# ─── ULTR overrides training. If ultr active, training is ignored. ───
if do_ultr:
    training_command_sequence = ["rpg ultr", "double", "attack", f"rpg use tc {tc_quantity}"]
elif do_training:
    training_command_sequence = ["rpg tr"]
else:
    training_command_sequence = []

# ─── Dungeon ───
is_eternal = userOptions.get("is_eternal", "false").lower() == "true"

# ─── Adventure Optimization ───
life_boost_before_adv = userOptions.get("life_boost_before_adv", "none").lower()
adventure_area = userOptions.get("adventure_area", "none").lower()
current_area = userOptions.get("current_area", "none").lower()

# Parse extra authorized admins
admin_ids_str = userOptions.get("admin_ids", "")
ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip().isdigit()]
if userID not in ADMIN_IDS:
    ADMIN_IDS.append(userID)

ALLOWED_IDS = [EPIC_RPG_ID, NAVI_LITE_ID] + ADMIN_IDS

# ─── Regex Patterns ───
farm_drop_regex = re.compile(
    r"(\d+) <:[^:]+:\d+> ([a-z]+) have grown from the seed", re.IGNORECASE
)
drop_regex = re.compile(
    r"got (\d+) \**`*<:[^:]+:\d+>`*\**\s*([`*_]*([a-zA-Z0-9 -_]+)[`*_]*(?:\s*[^a-zA-Z0-9\s].*?)?)",
    re.IGNORECASE,
)
special_banana_regex = re.compile(
    r"carrying (\d+) \**`*<:[^:]+:\d+>`*\**\s*([`*_]*([a-z0-9 -_]+)[`*_]*(?:\s*[^a-zA-Z0-9\s].*?)?)",
    re.IGNORECASE,
)
special_tree_regex = re.compile(
    r"tree had ([\d,]+) \**`*<:[^:]+:\d+>`*\**\s*([`*_]*([a-z0-9 -_]+)[`*_]*(?:\s*[^a-zA-Z0-9\s].*?)?)",
    re.IGNORECASE,
)
coins_xp_regex_new = re.compile(
    r"\+([\d,]+) \**`*<:[^:]+:\d+>`*\**, \+([\d,]+) XP", re.IGNORECASE
)
coins_xp_regex_old = re.compile(
    r"earned ([\d,]+) coins and ([\d,]+) XP", re.IGNORECASE
)
lootbox_drop_regex = re.compile(
    r"\+([\d,]+) \**`*<:[^:]+:\d+>`*\**\s*([`*_]*([a-zA-Z0-9 -_]+)[`*_]*(?:\s*[^a-zA-Z0-9\s].*?)?)",
    re.IGNORECASE,
)
