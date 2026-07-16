import re
import os
import time
import warnings
from typing import Optional
warnings.simplefilter("ignore", category=UserWarning)
import numpy as np
from PIL import Image
import options_resolver
from bot.hud import logger

# ─── Discord IDs ───
EPIC_RPG_ID = 555955826880413696
NAVI_LITE_ID = 1213487623688167494
NEON_BOT_IDS = [754276211302088704, 787861783143637032, 851436490415931422]
ARMY_BOT_ID = 902703931275247637  # Helper army bot (Galaxy Gather) — ID fixo, nunca muda
# ─── Oracle Model ───
img_height, img_width = 128, 128
language = "pt"
model_path_color = os.path.join(options_resolver.BUNDLE_DIR, 'oracle_v2_color.h5')
model_path_gray = os.path.join(options_resolver.BUNDLE_DIR, 'oracle_v2_gray.h5')
tflite_path_color = os.path.join(options_resolver.BUNDLE_DIR, 'oracle_v2_color.tflite')
tflite_path_gray = os.path.join(options_resolver.BUNDLE_DIR, 'oracle_v2_gray.tflite')
classes_path = os.path.join(options_resolver.BUNDLE_DIR, 'classes.txt')

import sys
import traceback

class TFLiteModelWrapper:
    def __init__(self, model_path):
        try:
            import tflite_runtime.interpreter as tflite
        except ImportError:
            from tensorflow import lite as tflite
        self.interpreter = tflite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

    def predict(self, x, verbose=0):
        x_input = x.astype(np.float32)
        self.interpreter.set_tensor(self.input_details[0]['index'], x_input)
        self.interpreter.invoke()
        return self.interpreter.get_tensor(self.output_details[0]['index'])

captcha_model_color = None
captcha_model_gray = None

# Try loading TFLite first to save RAM and avoid loading full TensorFlow
if os.path.exists(tflite_path_color) or os.path.exists(tflite_path_gray):
    try:
        try:
            import tflite_runtime.interpreter
        except ImportError:
            import tensorflow as tf
            
        if os.path.exists(tflite_path_color):
            captcha_model_color = TFLiteModelWrapper(tflite_path_color)
        if os.path.exists(tflite_path_gray):
            captcha_model_gray = TFLiteModelWrapper(tflite_path_gray)
    except Exception as e:
        pass

# Fallback to loading original .h5 models if TFLite models could not be loaded
if captcha_model_color is None and captcha_model_gray is None:
    try:
        import tensorflow as tf
        if os.path.exists(model_path_color):
            captcha_model_color = tf.keras.models.load_model(model_path_color)
        if os.path.exists(model_path_gray):
            captcha_model_gray = tf.keras.models.load_model(model_path_gray)
    except Exception as e:
        print(f"\033[1;31m🚨 AVISO: Falha ao carregar modelos Keras (.h5):\033[0m {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

if captcha_model_color is None and captcha_model_gray is None:
    print("\n\033[1;31m" + "="*80 + "\033[0m", file=sys.stderr)
    print("\033[1;31m🚨 ERRO CRÍTICO: NENHUM MODELO DE CAPTCHA FOI CARREGADO! 🚨\033[0m", file=sys.stderr)
    print("O Oráculo não conseguirá resolver os captchas do Epic RPG automaticamente.", file=sys.stderr)
    print("Por favor, verifique se a versão do TensorFlow/TFLite é compatível com os modelos.", file=sys.stderr)
    print(f"Interpretador Python ativo: {sys.executable}", file=sys.stderr)
    print("Tente instalar o runtime executando: pip install tflite-runtime", file=sys.stderr)
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

def get_full_lootbox_name(lootbox_type: str) -> str:
    if not lootbox_type:
        return "none"
    lootbox_type = lootbox_type.strip().lower()
    mapping = {
        "common lb": "common lootbox",
        "uncommon lb": "uncommon lootbox",
        "rare lb": "rare lootbox",
        "ep lb": "epic lootbox",
        "ed lb": "edgy lootbox",
        "common": "common lootbox",
        "uncommon": "uncommon lootbox",
        "rare": "rare lootbox",
        "epic": "epic lootbox",
        "ep": "epic lootbox",
        "edgy": "edgy lootbox",
        "ed": "edgy lootbox"
    }
    return mapping.get(lootbox_type, lootbox_type)

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

def get_opt(key: str, default: str) -> str:
    val = userOptions.get(key)
    if val is None:
        return default
    val_stripped = val.strip()
    if not val_stripped:
        return default
    return val_stripped

def get_opt_bool(key: str, default: bool) -> bool:
    default_str = "true" if default else "false"
    return get_opt(key, default_str).lower() == "true"

def parse_tc_stop_conditions(options_dict) -> list[str]:
    val = options_dict.get("tc_stop_on", "dungeon,miniboss")
    val_stripped = val.strip().lower()
    if not val_stripped or val_stripped == "none":
        return []
    return [x.strip() for x in val_stripped.split(",") if x.strip()]

userToken = get_opt("user_token", "")
language = get_opt("language", "pt").lower()

# Removed user_mention_text parsing as it is now determined dynamically in on_ready
userID = 0
userMentionText = ""

active_profile_path = options_resolver.optionsFilePath

try:
    channelID = int(get_opt("channel_id", "0"))
except ValueError:
    channelID = 0

randomIntervals = get_opt_bool("random_interval", False)
is_married = get_opt_bool("is_married", False)
partner_name = get_opt("partner_name", "").lower() if is_married else None
is_ascended = get_opt_bool("is_ascended", False)
farm_seed = get_opt("seed", "carrot").lower()
work_command = get_opt("work_command", "chainsaw").lower()
lootbox_type = get_full_lootbox_name(get_opt("lootbox_type", "none"))
max_area = get_opt("max_area", "1")
user_name_lower = get_opt("username", "").lower() # Fallback only, on_ready overwrites this
TelegramBotToken = get_opt("telegram_bot_token", "")
TelegramChatID = get_opt("telegram_chat_id", "")
try:
    typo_chance = float(get_opt("typo_chance", "0.05"))
except ValueError:
    typo_chance = 0.05

try:
    GUILD_ID = int(get_opt("guild_id", "0"))
except ValueError:
    GUILD_ID = 0

startTime = time.time()
tc_stop_conditions = parse_tc_stop_conditions(userOptions)
sleep_at = get_opt("sleep_at", "")
wake_up_at = get_opt("wake_up_at", "")
theme_raw = get_opt("theme", "cathedral").lower()
theme_map = {
    "tokyo night": "tokyonight",
    "rosé pine": "rosepine",
    "rose pine": "rosepine",
    "monokai pro": "monokai",
}
theme = theme_map.get(theme_raw, theme_raw)
pet_adventure_command = normalize_pet_adventure_command(get_opt("pet_adventure_command", "rpg pet adv learn a"))

# ─── Togglable Command Flags ───
do_hunt     = get_opt_bool("do_hunt", True)
do_adv      = get_opt_bool("do_adv", True)
do_farm     = get_opt_bool("do_farm", True)
do_work     = get_opt_bool("do_work", True)
do_training = get_opt_bool("do_training", True)
do_daily    = get_opt_bool("do_daily", True)
do_weekly   = get_opt_bool("do_weekly", True)
do_quest    = get_opt_bool("do_quest", True)
do_lootbox  = get_opt_bool("do_lootbox", True)
do_dungeon  = get_opt_bool("do_dungeon", True)
do_card_hand = get_opt_bool("do_card_hand", True)
do_duel      = get_opt_bool("do_duel", False)
win_duel     = get_opt_bool("win_duel", True)
duel_partner_id = get_opt("duel_partner_id", "")
do_pet       = get_opt_bool("do_pet", False)
do_gather    = get_opt_bool("do_gather", False)

# ─── ULTR / Training ───
do_ultr = get_opt_bool("do_ultr", False)

# ─── Card Hand Action ───
card_hand_action = get_opt("card_hand_action", "auto").lower()

# ─── TC Quantity ───
try:
    tc_quantity = int(get_opt("tc_quantity", "1"))
except ValueError:
    tc_quantity = 1

# ─── Dungeon ───
is_eternal = get_opt_bool("is_eternal", False)
eternal_tier = get_opt("eternal_tier", "t1").lower()

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
life_boost_before_adv = get_opt("life_boost_before_adv", "none").lower()
adventure_area = get_opt("adventure_area", "none").lower()
current_area = get_opt("current_area", "none").lower()

# Parse extra authorized admins
admin_ids_str = get_opt("admin_ids", "")
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


def reload_config(profile_path: Optional[str] = None) -> None:
    global userOptions, userToken, channelID, randomIntervals, is_married, partner_name
    global is_ascended, farm_seed, user_name_lower, TelegramBotToken, TelegramChatID
    global typo_chance, GUILD_ID, tc_stop_conditions, sleep_at, wake_up_at, theme
    global do_hunt, do_adv, do_farm, do_work, do_training, do_daily, do_weekly, do_quest
    global do_lootbox, do_dungeon, do_card_hand, do_ultr, card_hand_action, tc_quantity
    global training_command_sequence, is_eternal, life_boost_before_adv, adventure_area
    global current_area, ADMIN_IDS, ALLOWED_IDS, eternal_tier, pet_adventure_command
    global max_area, active_profile_path, do_duel, win_duel, duel_partner_id, do_pet
    global language, do_gather

    if profile_path is not None:
        active_profile_path = profile_path

    userOptions = options_resolver.importData(filePath=active_profile_path)

    userToken = get_opt("user_token", "")
    language = get_opt("language", "pt").lower()
    try:
        channelID = int(get_opt("channel_id", "0"))
    except ValueError:
        channelID = 0
    randomIntervals = get_opt_bool("random_interval", False)
    is_married = get_opt_bool("is_married", False)
    partner_name = get_opt("partner_name", "").lower() if is_married else None
    is_ascended = get_opt_bool("is_ascended", False)
    farm_seed = get_opt("seed", "carrot").lower()
    work_command = get_opt("work_command", "chainsaw").lower()
    lootbox_type = get_full_lootbox_name(get_opt("lootbox_type", "none"))
    ini_username = get_opt("username", "").lower()
    if ini_username:
        user_name_lower = ini_username
    elif not user_name_lower:
        user_name_lower = ""
    TelegramBotToken = get_opt("telegram_bot_token", "")
    TelegramChatID = get_opt("telegram_chat_id", "")
    try:
        typo_chance = float(get_opt("typo_chance", "0.05"))
    except ValueError:
        typo_chance = 0.05
    try:
        GUILD_ID = int(get_opt("guild_id", "0"))
    except ValueError:
        GUILD_ID = 0
    tc_stop_conditions = parse_tc_stop_conditions(userOptions)
    sleep_at = get_opt("sleep_at", "")
    wake_up_at = get_opt("wake_up_at", "")
    theme_raw = get_opt("theme", "cathedral").lower()
    theme_map = {
        "tokyo night": "tokyonight",
        "rosé pine": "rosepine",
        "rose pine": "rosepine",
        "monokai pro": "monokai",
    }
    theme = theme_map.get(theme_raw, theme_raw)
    pet_adventure_command = normalize_pet_adventure_command(get_opt("pet_adventure_command", "rpg pet adv learn a"))

    do_hunt     = get_opt_bool("do_hunt", True)
    do_adv      = get_opt_bool("do_adv", True)
    do_farm     = get_opt_bool("do_farm", True)
    do_work     = get_opt_bool("do_work", True)
    do_training = get_opt_bool("do_training", True)
    do_daily    = get_opt_bool("do_daily", True)
    do_weekly   = get_opt_bool("do_weekly", True)
    do_quest    = get_opt_bool("do_quest", True)
    do_lootbox  = get_opt_bool("do_lootbox", True)
    do_dungeon  = get_opt_bool("do_dungeon", True)
    do_card_hand = get_opt_bool("do_card_hand", True)
    do_duel      = get_opt_bool("do_duel", False)
    win_duel     = get_opt_bool("win_duel", True)
    duel_partner_id = get_opt("duel_partner_id", "")
    do_pet       = get_opt_bool("do_pet", False)
    do_gather    = get_opt_bool("do_gather", False)

    do_ultr = get_opt_bool("do_ultr", False)
    card_hand_action = get_opt("card_hand_action", "auto").lower()
    try:
        tc_quantity = int(get_opt("tc_quantity", "1"))
    except ValueError:
        tc_quantity = 1

    is_eternal = get_opt_bool("is_eternal", False)
    eternal_tier = get_opt("eternal_tier", "t1").lower()

    if do_ultr:
        if is_eternal:
            training_command_sequence = ["rpg ultr"]
        else:
            training_command_sequence = ["rpg ultr", "double", "attack"]
    elif do_training:
        training_command_sequence = ["rpg tr"]
    else:
        training_command_sequence = []

    life_boost_before_adv = get_opt("life_boost_before_adv", "none").lower()
    adventure_area = get_opt("adventure_area", "none").lower()
    current_area = get_opt("current_area", "none").lower()

    admin_ids_str = get_opt("admin_ids", "")
    ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip().isdigit()]
    ALLOWED_IDS = [EPIC_RPG_ID, NAVI_LITE_ID] + ADMIN_IDS
    max_area = get_opt("max_area", "1")


def update_max_area(new_val):
    global max_area
    max_area = str(new_val)
    userOptions["max_area"] = str(new_val)
    try:
        options_resolver.editData("max_area", str(new_val), filePath=active_profile_path)
    except Exception as e:
        logger.error(f"Erro ao salvar max_area no options.ini: {e}")

