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
        self.is_on_coffee_break = False
        self.next_break_time = time.time() + randint(3600, 7200)
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
        self.last_sent_command = ""
        self.last_sent_time = 0
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
            "omega": 0, "godly": 0, "eternal": 0, "void": 0,
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
            "omega": 0, "godly": 0, "eternal": 0, "void": 0,
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

from bot.persistence import load_session_data
sessionData = load_session_data(DEFAULT_SESSION_DATA)

runtimeErrors = []


def add_to_low_priority_queue(command, suppress_log=False):
    if command not in lowPriorityQueueSet:
        lowPriorityQueue.append(command)
        lowPriorityQueueSet.add(command)
        if not suppress_log:
            logger.info(f"Command {command} added to LPQ.")


def add_to_high_priority_queue(command):
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
    bot_state.dungeon_waiting_confirmation = False
    bot_state.dungeon_in_progress = False
    bot_state.dragon_alive = False
    bot_state.last_dungeon_time = 0
    bot_state.tc_quantity = config.tc_quantity
    logger.info("Bot state reset to initial values.")


async def queue_tc_commands():
    """Enfileira comandos iniciais ao ativar TC mode para nao desperdicar cooldowns."""
    tc_qty = bot_state.tc_quantity
    add_to_high_priority_queue(f"rpg use tc {tc_qty}")

    if config.do_hunt:
        hunt_cmd = "rpg hunt"
        if config.is_ascended:
            hunt_cmd += " h"
        if config.is_married:
            hunt_cmd += " t"
        add_to_low_priority_queue(hunt_cmd, suppress_log=True)

    if config.do_work:
        add_to_low_priority_queue(f"rpg {config.userOptions['work_command']}", suppress_log=True)

    if config.do_farm:
        farm_cmd = f"rpg farm {config.farm_seed}" if config.farm_seed and config.farm_seed != "none" else "rpg farm"
        add_to_low_priority_queue(farm_cmd, suppress_log=True)

    add_to_low_priority_queue("rpg rd", suppress_log=True)


async def human_delay(base=1.5, variance=2.5):
    """Simulates human reaction time. Returns after a random delay.
    Default range: 1.5-4.0s. For longer 'thinking' actions, increase base."""
    delay = base + random.random() * variance
    await asyncio.sleep(delay)
