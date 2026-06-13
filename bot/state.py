import time
import random
import asyncio
from random import randint
from bot.hud import logger
import bot.config as config


class CoinFlipFibonacci:
    def __init__(self, bankroll, max_losses, initial_step=1):
        self.bankroll = bankroll
        self.max_losses = max_losses
        self.step = initial_step
        self.fib_sequence = self.generate_fib_sequence(max_losses)
        self.update_base_unit()
        self.profit = 0
        self.consecutive_losses = 0

    def generate_fib_sequence(self, n):
        if n <= 0:
            return []
        fib = [1, 1]
        if n <= 2:
            return fib[:n]
        for i in range(2, n):
            fib.append(fib[i - 1] + fib[i - 2])
        return fib

    def update_base_unit(self):
        sum_fib = sum(self.fib_sequence)
        self.base_unit = self.bankroll // sum_fib if sum_fib > 0 else 0
        self.current_bet = (
            self.fib_sequence[self.step - 1] * self.base_unit
            if self.fib_sequence
            else 0
        )

    def win(self):
        current_bet = self.current_bet
        if self.step <= 2:
            self.step = 1
        else:
            self.step -= 2
        self.consecutive_losses = 0
        self.update_base_unit()
        self.profit += current_bet

    def loss(self):
        current_bet = self.current_bet
        if self.step < len(self.fib_sequence):
            self.step += 1
        self.consecutive_losses += 1
        self.update_base_unit()
        self.profit -= current_bet

    def get_bet_command(self):
        if self.current_bet >= 1_000_000:
            return f"rpg cf h {self.current_bet // 1_000_000}m"
        return f"rpg cf h {self.current_bet}"

    def handle_insufficient_funds(self, current_balance):
        if current_balance > 0:
            self.bankroll = current_balance
            self.update_base_unit()
            return True
        return False

    def reset_state(self):
        self.step = 1
        self.profit = 0
        self.consecutive_losses = 0
        self.update_base_unit()
        logger.info("Gambling state reset: step, profit, and consecutive losses cleared.")


class BotState:
    def __init__(self):
        self._paused = False
        self._gambling_paused = True
        self.coinflip_pending = False
        self.jailed = False
        self.captcha_pending = False
        self.last_message_id = None
        self.coinflip_step = 1
        self.coinflip_sequence = [1, 1]
        self.coinflip_base_unit = 0
        self.coinflip_profit = 0
        self.awaiting_withdraw = False
        self.captcha_task = None
        self.no_response_count = 0
        self.watchdog_paused_until = 0
        self.is_on_coffee_break = False
        self.next_break_time = time.time() + randint(3600, 7200)
        self.coffee_break_end_time = 0
        self.last_curiosity_time = 0
        self.lootbox_cooldown_until = 0
        self.has_bank_account = True
        self.quest_active = False
        self.gamble_quest_goal = 0
        self.gamble_quest_current = 0
        self.pending_trade_letter = None
        self.time_cookie_mode = False
        self.tc_end_time = 0
        self.last_tc_use_time = 0
        self.minigame_pending_until = 0
        self.cardhand_in_progress = False
        self.cardhand_first_pass_done = False
        self.cardhand_start_time = 0
        self.cardhand_turn_count = 1
        self.last_sent_command = ""
        self.last_cardhand_notification_time = 0
        self.last_sent_time = 0
        self.last_sent_cardhand_image = None
        self.cardhand_user_choice = None
        # Pet Adventure
        self.pet_adventure_return_time = 0
        self.last_save_time = time.time()
        # Dungeon State
        self.dungeon_waiting_confirmation = False
        self.dungeon_in_progress = False
        self.dragon_alive = False
        self.last_dungeon_time = 0
        # TC Quantity (runtime override via sb tc start Xc)
        self.tc_quantity = config.tc_quantity
        # Sleepet Mode
        self.sleepet_mode = False
        self.sleepet_state = None  # None, "init", "waiting_summary", "waiting_claim", "waiting_adventure", "waiting_potion"
        self.last_sleepet_cmd_time = 0
        self.latest_neon_recommendation = None  # Tuple of (rec, formatted, timestamp)
        # Cooldown override/Dungeon
        self.ruby_dragon_state = None
        self.ruby_dragon_time = 0
        # Duel State
        self.duel_in_progress = False
        self.duel_step = None  # None, "waiting_confirmation", "waiting_weapon", "finished"
        self.last_duel_time = 0

    @property
    def neon_updated_event(self):
        if not hasattr(self, '_neon_updated_event') or self._neon_updated_event is None:
            self._neon_updated_event = asyncio.Event()
        return self._neon_updated_event

    @property
    def paused(self):
        return self._paused and not (self._gambling_paused == False)

    @paused.setter
    def paused(self, value):
        self._paused = value

    @property
    def gambling_paused(self):
        return self._gambling_paused

    @gambling_paused.setter
    def gambling_paused(self, value):
        self._gambling_paused = value
        if value == True and coinflip_strategy is not None:
            coinflip_strategy.reset_state()
            bot_state.coinflip_step = coinflip_strategy.step
            bot_state.coinflip_sequence = coinflip_strategy.fib_sequence[
                : bot_state.coinflip_step
            ]
            bot_state.coinflip_base_unit = coinflip_strategy.base_unit
            bot_state.coinflip_profit = coinflip_strategy.profit
            bot_state.coinflip_pending = False
            logger.info(
                "Gambling paused. All game state metrics (wins/losses/profit) reset."
            )
        elif value == False:
            self._paused = False
            if coinflip_strategy is not None:
                first_bet = coinflip_strategy.get_bet_command()
                add_to_high_priority_queue(first_bet)
                bot_state.coinflip_pending = True
                logger.info(f"Gambling activated. First bet queued: {first_bet}")


# ─── Queues ───
lowPriorityQueue = []
highPriorityQueue = []
lowPriorityQueueSet = set()
highPriorityQueueSet = set()

# ─── Session Tracking ───
DEFAULT_SESSION_DATA = {
    "start_time": 0.0,
    "command_data": {
        "hunt": 0, "adventure": 0, "farm": 0, "training": 0,
        "work": 0, "quest": 0, "daily": 0, "weekly": 0, "lootbox": 0,
    },
    "progress_data": {"coins": 0, "xp": 0, "levels": 0},
    "loot_data": {
        "mob_drops": {
            "wolf skin": 0, "zombie eye": 0, "unicorn horn": 0,
            "mermaid hair": 0, "chip": 0, "dragon scale": 0, "dark energy": 0,
        },
        "lootbox_drops": {
            "common": 0, "uncommon": 0, "rare": 0, "epic": 0, "edgy": 0,
            "void": 0, "eternal": 0, "galaxy": 0,
        },
        "work_drops": {
            "banana": 0, "apple": 0, "ruby": 0, "normie fish": 0,
            "golden fish": 0, "epic fish": 0, "super fish": 0,
            "wooden log": 0, "epic log": 0, "super log": 0,
            "mega log": 0, "hyper log": 0, "ultra log": 0, "ultimate log": 0,
        },
        "farm_drops": {"carrot": 0, "potato": 0, "bread": 0},
    },
    "misc": {
        "cards": {
            "common": 0, "uncommon": 0, "epic": 0,
            "omega": 0, "godly": 0, "eternal": 0,
        },
        "coolness": 0,
        "arena_cookies": 0,
        "guard_events": 0,
        "personal_events": 0,
        "pets": 0,
        "misc": {},
    },
    "partner_loot_data": {
        "mob_drops": {
            "wolf skin": 0, "zombie eye": 0, "unicorn horn": 0,
            "mermaid hair": 0, "chip": 0, "dragon scale": 0, "dark energy": 0,
        },
        "lootbox_drops": {
            "common": 0, "uncommon": 0, "rare": 0, "epic": 0, "edgy": 0,
            "void": 0, "eternal": 0, "galaxy": 0,
        },
        "work_drops": {
            "banana": 0, "apple": 0, "ruby": 0, "normie fish": 0,
            "golden fish": 0, "epic fish": 0, "super fish": 0,
            "wooden log": 0, "epic log": 0, "super log": 0,
            "mega log": 0, "hyper log": 0, "ultra log": 0, "ultimate log": 0,
        },
        "farm_drops": {"carrot": 0, "potato": 0, "bread": 0},
        "misc": {
            "cards": {
                "common": 0, "uncommon": 0, "epic": 0,
                "omega": 0, "godly": 0, "eternal": 0,
            },
            "coolness": 0,
            "arena_cookies": 0,
            "guard_events": 0,
            "personal_events": 0,
            "pets": 0,
            "misc": {},
        },
        "progress_data": {"coins": 0, "xp": 0, "levels": 0},
    }
    if config.is_married
    else {},
}

import copy
import time
from bot.persistence import load_session_data, save_session_data, save_session_baseline
sessionData = load_session_data(DEFAULT_SESSION_DATA)
if not sessionData.get("start_time") or sessionData["start_time"] == 0.0:
    sessionData["start_time"] = time.time()
    save_session_data(sessionData)
initialSessionData = copy.deepcopy(sessionData)
# Save baseline snapshot so the dashboard can compute session-only stats
save_session_baseline(initialSessionData)

runtimeErrors = []


def is_sleepet_command(command: str) -> bool:
    if bot_state.captcha_pending or bot_state.jailed:
        return True
    cmd_clean = command.strip().lower()
    # Emergency and jail/protest commands
    if cmd_clean in ["protest", "rpg jail", "fight", "move", "cry"] or any(x in cmd_clean for x in ["jail", "protest"]):
        return True
    # Captcha answers (usually short non-rpg text)
    if len(cmd_clean) <= 8 and not cmd_clean.startswith("rpg"):
        return True
    return cmd_clean.startswith("rpg pet") or "sleepet" in cmd_clean or "rpg use sleepet" in cmd_clean


def is_action_queued(command):
    cmd = command.lower().strip()
    if cmd.startswith("rpg "):
        cmd = cmd[4:].strip()
    parts = cmd.split()
    if not parts:
        return False
    base_action = parts[0]
    
    # Check HPQ
    for q_cmd in highPriorityQueue:
        q_cmd_clean = q_cmd.lower().strip()
        if q_cmd_clean.startswith("rpg "):
            q_cmd_clean = q_cmd_clean[4:].strip()
        q_parts = q_cmd_clean.split()
        if q_parts and q_parts[0] == base_action:
            return True
            
    # Check LPQ
    for q_cmd in lowPriorityQueue:
        q_cmd_clean = q_cmd.lower().strip()
        if q_cmd_clean.startswith("rpg "):
            q_cmd_clean = q_cmd_clean[4:].strip()
        q_parts = q_cmd_clean.split()
        if q_parts and q_parts[0] == base_action:
            return True
            
    return False


def remove_base_action_from_queue(base_action, queue, queue_set):
    to_remove = []
    for cmd in queue:
        cmd_clean = cmd.lower().strip()
        if cmd_clean.startswith("rpg "):
            cmd_clean = cmd_clean[4:].strip()
        parts = cmd_clean.split()
        if parts and parts[0] == base_action:
            to_remove.append(cmd)
    for cmd in to_remove:
        if cmd in queue:
            queue.remove(cmd)
        queue_set.discard(cmd)


def add_to_low_priority_queue(command, suppress_log=False):
    if bot_state.sleepet_mode and not is_sleepet_command(command):
        return
    # Block low-priority rpg commands if duel is active
    if bot_state.duel_in_progress and command.lower().strip().startswith("rpg"):
        return
    # Check if this action is already queued in either queue
    cmd_clean = command.lower().strip()
    if cmd_clean.startswith("rpg "):
        cmd_clean = cmd_clean[4:].strip()
    parts = cmd_clean.split()
    if parts:
        base_action = parts[0]
        match_actions = {"hunt", "adv", "adventure", "fish", "chop", "mine", "pickup", "farm", "daily", "weekly", "lootbox", "quest", "training", "tr"}
        if base_action in match_actions:
            if is_action_queued(command):
                return

    if command not in lowPriorityQueueSet:
        lowPriorityQueue.append(command)
        lowPriorityQueueSet.add(command)
        if not suppress_log:
            logger.info(f"Command {command} added to LPQ.")


def add_to_high_priority_queue(command):
    if bot_state.sleepet_mode and not is_sleepet_command(command):
        return
    # Check if this action is already in HPQ
    cmd_clean = command.lower().strip()
    if cmd_clean.startswith("rpg "):
        cmd_clean = cmd_clean[4:].strip()
    parts = cmd_clean.split()
    if parts:
        base_action = parts[0]
        match_actions = {"hunt", "adv", "adventure", "fish", "chop", "mine", "pickup", "farm", "daily", "weekly", "lootbox", "quest", "training", "tr"}
        if base_action in match_actions:
            # Check if it's already in HPQ
            for q_cmd in highPriorityQueue:
                q_cmd_clean = q_cmd.lower().strip()
                if q_cmd_clean.startswith("rpg "):
                    q_cmd_clean = q_cmd_clean[4:].strip()
                q_parts = q_cmd_clean.split()
                if q_parts and q_parts[0] == base_action:
                    return # already in HPQ, skip
            
            # If it's in LPQ, remove it from LPQ to promote it to HPQ
            remove_base_action_from_queue(base_action, lowPriorityQueue, lowPriorityQueueSet)

    if command not in highPriorityQueueSet:
        highPriorityQueue.append(command)
        highPriorityQueueSet.add(command)
        logger.info(f"Command {command} added to HPQ.")


# ─── Singleton Instances ───
bot_state = BotState()

try:
    bankroll = int(config.userOptions.get("bankroll", "1000000000000"))
    max_losses = int(config.userOptions.get("max_losses", "20"))
    initial_step = int(config.userOptions.get("initial_step", "1"))
    coinflip_strategy = CoinFlipFibonacci(bankroll, max_losses, initial_step)
    bot_state.coinflip_base_unit = coinflip_strategy.base_unit
    bot_state.coinflip_sequence = coinflip_strategy.fib_sequence[:initial_step]
    logger.info(
        f"Coinflip strategy initialized: bankroll={bankroll}, "
        f"max_losses={max_losses}, initial_step={initial_step}"
    )
except Exception as e:
    logger.error(
        f"Error initializing coinflip strategy: {e}. "
        f"Check userOptions: {config.userOptions}"
    )
    coinflip_strategy = None


def reset_bot_state():
    bot_state.paused = False
    bot_state.gambling_paused = True
    bot_state.jailed = False
    bot_state.captcha_pending = False
    bot_state.coinflip_pending = False
    bot_state.awaiting_withdraw = False
    if getattr(bot_state, "captcha_task", None) and not bot_state.captcha_task.done():
        bot_state.captcha_task.cancel()
    bot_state.captcha_task = None
    bot_state.cardhand_in_progress = False
    bot_state.cardhand_first_pass_done = False
    bot_state.cardhand_turn_count = 1
    bot_state.last_sent_cardhand_image = None
    bot_state.cardhand_user_choice = None
    bot_state.dungeon_waiting_confirmation = False
    bot_state.dungeon_in_progress = False
    bot_state.dragon_alive = False
    bot_state.last_dungeon_time = 0
    bot_state.tc_quantity = config.tc_quantity
    bot_state.watchdog_paused_until = 0
    bot_state.no_response_count = 0
    bot_state.coffee_break_end_time = 0
    bot_state.sleepet_mode = False
    bot_state.sleepet_state = None
    bot_state.last_sleepet_cmd_time = 0
    bot_state.ruby_dragon_state = None
    bot_state.ruby_dragon_time = 0
    bot_state.duel_in_progress = False
    bot_state.duel_step = None
    bot_state.last_duel_time = 0
    logger.info("Bot state reset to initial values.")


async def queue_tc_commands():
    """Enfileira comandos iniciais ao ativar TC mode para nao desperdicar cooldowns."""
    bot_state.last_tc_use_time = time.time()
    tc_qty = bot_state.tc_quantity
    add_to_high_priority_queue(f"rpg use tc {tc_qty}")
    add_to_low_priority_queue("rpg rd", suppress_log=True)


async def human_delay(base=1.5, variance=2.5):
    """Simulates human reaction time. Returns after a random delay.
    Default range: 1.5-4.0s. For longer 'thinking' actions, increase base."""
    delay = base + random.random() * variance
    await asyncio.sleep(delay)
