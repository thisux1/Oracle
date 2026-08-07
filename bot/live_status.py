import time
import bot.config as config
from bot.state import bot_state
from bot.persistence import save_live_status


def update_live_status() -> None:
    """Build the shared live status payload from bot_state + config and write
    the atomic live_<profile>.json consumed by the dashboard. Never raises."""
    try:
        now = time.time()
        if bot_state.jailed and bot_state.jail_started_at:
            jail_elapsed = max(0.0, now - bot_state.jail_started_at)
        else:
            jail_elapsed = 0.0

        payload = {
            "jailed": bool(bot_state.jailed),
            "jail_started_at": bot_state.jail_started_at,
            "jail_elapsed": jail_elapsed,
        }

        # Summer payload (expanded later in Fase B, already present to keep
        # the shared JSON single-source-of-truth for the dashboard).
        try:
            payload["summer"] = {
                "active": bool(config.do_summer),
                "strategy": config.summer_surf_strategy,
                "color_team": bot_state.summer_color_team,
                "drink_choice": config.summer_drink_choice,
                "surf_rounds": bot_state.summer_surf_rounds,
                "surf_cooldown_remaining": max(
                    0.0, bot_state.summer_surf_cooldown_until - now
                ),
                "tasks_claimed": sorted(bot_state.summer_tasks_claimed),
                "pending_tasks": sorted(bot_state.summer_pending_tasks),
                "quest_completed": bool(bot_state.summer_quest_completed),
                "daily_date": bot_state.summer_daily_date,
                "drink_this_week": bool(bot_state.summer_drink_this_week),
                "beach_party_active": bool(bot_state.summer_beach_party_active),
                "arena_in_progress": bool(bot_state.arena_in_progress),
                "boost_exhausted": bool(bot_state.summer_boost_exhausted),
                "inventory": {
                    "coconut": bot_state.summer_coconut_count,
                    "chopped_coconut": bot_state.inventory_chopped_coconut,
                    "normiefish": bot_state.inventory_normiefish,
                    "epic_fish": bot_state.inventory_epic_fish,
                    "edgy_lootbox": bot_state.inventory_edgy_lootbox,
                    "chip": bot_state.inventory_chip,
                    "epic_seed": bot_state.inventory_epic_seed,
                    "banana": bot_state.inventory_banana,
                    "lottery_ticket": bot_state.inventory_lottery_ticket,
                    "ruby": bot_state.inventory_ruby,
                    "mermaid_hair": bot_state.inventory_mermaid_hair,
                    "palm_log": bot_state.summer_palm_log_count,
                    "mega_palm_log": bot_state.summer_mega_palm_log_count,
                },
                "drinks": {
                    "blue": bot_state.inventory_blue_drink,
                    "pink": bot_state.inventory_pink_drink,
                    "green": bot_state.inventory_green_drink,
                    "yellow": bot_state.inventory_yellow_drink,
                },
                "boosts_active": dict(bot_state.summer_boosts_active),
                "boost_count": len(bot_state.summer_boosts_active),
            }
        except Exception:
            payload["summer"] = None

        save_live_status(payload)
    except Exception as e:
        from bot.hud import logger
        logger.error(f"Error updating live status: {e}")
