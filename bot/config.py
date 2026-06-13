import re
import os
import time
import warnings
warnings.simplefilter("ignore", category=UserWarning)
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
model_path_color = os.path.join(options_resolver.BUNDLE_DIR, 'oracle_v2_color.h5')
model_path_gray = os.path.join(options_resolver.BUNDLE_DIR, 'oracle_v2_gray.h5')
classes_path = os.path.join(options_resolver.BUNDLE_DIR, 'classes.txt')

import sys
import traceback

captcha_model_color = None
captcha_model_gray = None

try:
    captcha_model_color = tf.keras.models.load_model(model_path_color)
except Exception as e:
    print(f"\033[1;31m🚨 AVISO: Falha ao carregar modelo de captcha COLOR:\033[0m {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)

try:
    captcha_model_gray = tf.keras.models.load_model(model_path_gray)
except Exception as e:
    print(f"\033[1;31m🚨 AVISO: Falha ao carregar modelo de captcha GRAY:\033[0m {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)

if captcha_model_color is None and captcha_model_gray is None:
    print("\n\033[1;31m" + "="*80 + "\033[0m", file=sys.stderr)
    print("\033[1;31m🚨 ERRO CRÍTICO: NENHUM MODELO DE CAPTCHA FOI CARREGADO! 🚨\033[0m", file=sys.stderr)
    print("O Oráculo não conseguirá resolver os captchas do Epic RPG automaticamente.", file=sys.stderr)
    print("Por favor, verifique se a versão do TensorFlow e Keras é compatível com os modelos (.h5).", file=sys.stderr)
    print(f"Interpretador Python ativo: {sys.executable}", file=sys.stderr)
    print("Tente atualizar as dependências executando: pip install --upgrade tensorflow", file=sys.stderr)
    print("\033[1;31m" + "="*80 + "\033[0m\n", file=sys.stderr)
    sys.exit(1)

if os.path.exists(classes_path):
    with open(classes_path, 'r', encoding='utf-8') as f:
        captcha_class_names = [line.strip() for line in f.readlines()]
else:
    dataset_cropped_path = os.path.join(options_resolver.BUNDLE_DIR, 'dataset_cropped')
    if os.path.exists(dataset_cropped_path):
        captcha_class_names = sorted([
            d for d in os.listdir(dataset_cropped_path)
            if os.path.isdir(os.path.join(dataset_cropped_path, d))
        ])
    else:
        captcha_class_names = []

if not captcha_class_names:
    print("\n\033[1;31m" + "="*80 + "\033[0m", file=sys.stderr)
    print("\033[1;31m🚨 ERRO CRÍTICO: ARQUIVO DE CLASSIFICAÇÃO DE CLASSES DO CAPTCHA AUSENTE! 🚨\033[0m", file=sys.stderr)
    print(f"O arquivo de mapeamento de classes '{classes_path}' não foi encontrado ou está vazio.", file=sys.stderr)
    print("Sem este arquivo, o bot não pode traduzir as predições do modelo de imagem em texto.", file=sys.stderr)
    print("\033[1;31m" + "="*80 + "\033[0m\n", file=sys.stderr)
    sys.exit(1)

def normalize_pet_adventure_command(val: str | None) -> str:
    if not val:
        return "rpg pet adv learn a"
    val = val.strip()
    val_lower = val.lower()
    if not val_lower or val_lower == "none":
        return "rpg pet adv learn a"
    
    prefixes = [
        ("rpg pet adventure ", "rpg pet adventure"),
        ("rpg pet adv ", "rpg pet adv"),
        ("rpg adv ", "rpg adv"),
        ("pet adventure ", "pet adventure"),
        ("pet adv ", "pet adv"),
        ("rpg pet ", "rpg pet"),
    ]
    
    action = ""
    matched_prefix = False
    for prefix_w_space, prefix_no_space in prefixes:
        if val_lower.startswith(prefix_w_space):
            action = val[len(prefix_w_space):].strip()
            matched_prefix = True
            break
        elif val_lower == prefix_no_space:
            return "rpg pet adv learn a"
            
    if not matched_prefix:
        if val_lower.startswith("adventure "):
            action = val[10:].strip()
        elif val_lower == "adventure":
            return "rpg pet adv learn a"
        elif val_lower.startswith("adv "):
            action = val[4:].strip()
        elif val_lower == "adv":
            return "rpg pet adv learn a"
        else:
            action = val
            
    if not action:
        return "rpg pet adv learn a"
        
    action_lower = action.lower()
    if action_lower.startswith("adventure "):
        action = action[10:].strip()
    elif action_lower.startswith("adv "):
        action = action[4:].strip()
        
    if not action:
        return "rpg pet adv learn a"
        
    return f"rpg pet adv {action}"

# ─── User Options ───
try:
    userOptions = options_resolver.importData()
except Exception as e:
    print("\n\033[1;31m" + "="*80 + "\033[0m", file=sys.stderr)
    print(f"\033[1;31m🚨 ERRO CRÍTICO: FALHA AO LER ARQUIVO DE CONFIGURAÇÃO! 🚨\033[0m", file=sys.stderr)
    print(f"Não foi possível carregar o arquivo de configuração: {e}", file=sys.stderr)
    print("Verifique se o arquivo existe e possui permissões de leitura.", file=sys.stderr)
    print("\033[1;31m" + "="*80 + "\033[0m\n", file=sys.stderr)
    sys.exit(1)

userToken = userOptions.get("user_token", "")

# Removed user_mention_text parsing as it is now determined dynamically in on_ready
userID = 0
userMentionText = ""

active_profile_path = options_resolver.optionsFilePath

try:
    channelID = int(userOptions.get("channel_id", "0"))
except ValueError:
    channelID = 0

randomIntervals = userOptions.get("random_interval", "false").lower() == "true"
is_married = userOptions.get("is_married", "false").lower() == "true"
partner_name = userOptions.get("partner_name", "").lower() if is_married else None
is_ascended = userOptions.get("is_ascended", "false").lower() == "true"
farm_seed = userOptions.get("seed", "carrot").lower()
max_area = userOptions.get("max_area", "1")
user_name_lower = userOptions.get("username", "").lower() # Fallback only, on_ready overwrites this
TelegramBotToken = userOptions.get("telegram_bot_token", "")
TelegramChatID = userOptions.get("telegram_chat_id", "")
try:
    typo_chance = float(userOptions.get("typo_chance", "0.05"))
except ValueError:
    typo_chance = 0.05

try:
    GUILD_ID = int(userOptions.get("guild_id", "0"))
except ValueError:
    GUILD_ID = 0

startTime = time.time()
tc_stop_conditions = [x.strip().lower() for x in userOptions.get("tc_stop_on", "dungeon,miniboss").split(",") if x.strip()]
sleep_at = userOptions.get("sleep_at", "")
wake_up_at = userOptions.get("wake_up_at", "")
theme = userOptions.get("theme", "cathedral")
pet_adventure_command = normalize_pet_adventure_command(userOptions.get("pet_adventure_command", "rpg pet adv learn a"))

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
do_duel      = userOptions.get("do_duel", "false").lower() == "true"
duel_partner_id = userOptions.get("duel_partner_id", "").strip()

# ─── ULTR / Training ───
do_ultr = userOptions.get("do_ultr", "false").lower() == "true"

# ─── Card Hand Action ───
card_hand_action = userOptions.get("card_hand_action", "auto").lower()

# ─── TC Quantity ───
tc_quantity = int(userOptions.get("tc_quantity", "1"))

# ─── Dungeon ───
is_eternal = userOptions.get("is_eternal", "false").lower() == "true"
eternal_tier = userOptions.get("eternal_tier", "t1").lower()

# ─── ULTR overrides training. If ultr active, training is ignored. ───
if do_ultr:
    if is_eternal:
        training_command_sequence = ["rpg ultr"]
    else:
        training_command_sequence = ["rpg ultr", "double", "attack"]
elif do_training:
    training_command_sequence = ["rpg tr"]
else:
    training_command_sequence = []

# ─── Adventure Optimization ───
life_boost_before_adv = userOptions.get("life_boost_before_adv", "none").lower()
adventure_area = userOptions.get("adventure_area", "none").lower()
current_area = userOptions.get("current_area", "none").lower()

# Parse extra authorized admins
admin_ids_str = userOptions.get("admin_ids", "")
ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip().isdigit()]
# userID is 0 at module load; on_ready dynamically appends the real ID

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


def reload_config(profile_path=None):
    global userOptions, userToken, channelID, randomIntervals, is_married, partner_name
    global is_ascended, farm_seed, user_name_lower, TelegramBotToken, TelegramChatID
    global typo_chance, GUILD_ID, tc_stop_conditions, sleep_at, wake_up_at, theme
    global do_hunt, do_adv, do_farm, do_work, do_training, do_daily, do_weekly, do_quest
    global do_lootbox, do_dungeon, do_card_hand, do_ultr, card_hand_action, tc_quantity
    global training_command_sequence, is_eternal, life_boost_before_adv, adventure_area
    global current_area, ADMIN_IDS, ALLOWED_IDS, eternal_tier, pet_adventure_command
    global max_area, active_profile_path, do_duel, duel_partner_id

    if profile_path is not None:
        active_profile_path = profile_path

    userOptions = options_resolver.importData(filePath=active_profile_path)

    userToken = userOptions.get("user_token", "")
    try:
        channelID = int(userOptions.get("channel_id", "0"))
    except ValueError:
        channelID = 0
    randomIntervals = userOptions.get("random_interval", "false").lower() == "true"
    is_married = userOptions.get("is_married", "false").lower() == "true"
    partner_name = userOptions.get("partner_name", "").lower() if is_married else None
    is_ascended = userOptions.get("is_ascended", "false").lower() == "true"
    farm_seed = userOptions.get("seed", "carrot").lower()
    user_name_lower = userOptions.get("username", "").lower()
    TelegramBotToken = userOptions.get("telegram_bot_token", "")
    TelegramChatID = userOptions.get("telegram_chat_id", "")
    try:
        typo_chance = float(userOptions.get("typo_chance", "0.05"))
    except ValueError:
        typo_chance = 0.05
    try:
        GUILD_ID = int(userOptions.get("guild_id", "0"))
    except ValueError:
        GUILD_ID = 0
    tc_stop_conditions = [x.strip().lower() for x in userOptions.get("tc_stop_on", "dungeon,miniboss").split(",") if x.strip()]
    sleep_at = userOptions.get("sleep_at", "")
    wake_up_at = userOptions.get("wake_up_at", "")
    theme = userOptions.get("theme", "cathedral")
    pet_adventure_command = normalize_pet_adventure_command(userOptions.get("pet_adventure_command", "rpg pet adv learn a"))

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
    do_duel      = userOptions.get("do_duel", "false").lower() == "true"
    duel_partner_id = userOptions.get("duel_partner_id", "").strip()

    do_ultr = userOptions.get("do_ultr", "false").lower() == "true"
    card_hand_action = userOptions.get("card_hand_action", "auto").lower()
    try:
        tc_quantity = int(userOptions.get("tc_quantity", "1"))
    except ValueError:
        tc_quantity = 1

    is_eternal = userOptions.get("is_eternal", "false").lower() == "true"
    eternal_tier = userOptions.get("eternal_tier", "t1").lower()

    if do_ultr:
        if is_eternal:
            training_command_sequence = ["rpg ultr"]
        else:
            training_command_sequence = ["rpg ultr", "double", "attack"]
    elif do_training:
        training_command_sequence = ["rpg tr"]
    else:
        training_command_sequence = []

    life_boost_before_adv = userOptions.get("life_boost_before_adv", "none").lower()
    adventure_area = userOptions.get("adventure_area", "none").lower()
    current_area = userOptions.get("current_area", "none").lower()

    admin_ids_str = userOptions.get("admin_ids", "")
    ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip().isdigit()]
    ALLOWED_IDS = [EPIC_RPG_ID, NAVI_LITE_ID] + ADMIN_IDS
    max_area = userOptions.get("max_area", "1")


def update_max_area(new_val):
    global max_area
    max_area = str(new_val)
    userOptions["max_area"] = str(new_val)
    try:
        options_resolver.editData("max_area", str(new_val), filePath=active_profile_path)
    except Exception as e:
        logger.error(f"Erro ao salvar max_area no options.ini: {e}")

