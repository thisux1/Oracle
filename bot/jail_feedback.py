import os
import sys
import time
import asyncio
import subprocess
import bot.config as config
from bot.state import bot_state
from bot.hud import HUD, logger
from bot.live_status import update_live_status
from bot.telegram import send_telegram_raw, delete_telegram_message


# Candidatos de som para o alarme no Linux, em ordem de preferencia
_LINUX_SOUND_CANDIDATES = [
    "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga",
    "/usr/share/sounds/freedesktop/stereo/complete.oga",
    "/usr/share/sounds/alsa/Front_Center.wav",
]


def _play_linux_sound() -> bool:
    """Tenta reproduzir um som de alerta no Linux via subprocess (nao bloqueia)."""
    for sound_file in _LINUX_SOUND_CANDIDATES:
        if not os.path.exists(sound_file):
            continue
        for cmd in (
            ["paplay", sound_file],
            ["aplay", "-q", sound_file],
            ["ffplay", "-nodisp", "-autoexit", sound_file],
        ):
            try:
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return True
            except Exception:
                continue
    return False


def play_jail_alarm() -> None:
    """Reproduz o som de alarme do jail. Windows usa winsound; Linux tenta uma
    cadeia de players de audio e, como ultimo recurso, o bell do terminal."""
    try:
        if sys.platform.startswith("win"):
            try:
                import winsound

                winsound.Beep(1000, 400)
                time.sleep(0.1)
                winsound.Beep(1500, 400)
                return
            except Exception:
                pass

        if not _play_linux_sound():
            try:
                subprocess.Popen(
                    ["printf", "\a"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass
    except Exception:
        pass


def _format_elapsed(seconds: float) -> str:
    seconds = int(max(0, seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    return f"{minutes}m {secs:02d}s"


async def _send_jail_message() -> None:
    """Envia mensagem NOVA de jail e apaga a anterior (1 visivel por vez)."""
    elapsed = _format_elapsed(time.time() - bot_state.jail_started_at)
    interval = getattr(config, "jail_notify_interval_min", 15)
    msg = (
        "🚨 BOT PRESO! Intervenção manual necessária.\n"
        f"⏱️ Preso há {elapsed}\n"
        f"🔄 Reaviso a cada {interval} min."
    )
    try:
        new_id = await send_telegram_raw(msg)
    except Exception as e:
        logger.error(f"Erro ao enviar aviso de jail: {e}")
        return

    old_id = bot_state.jail_message_id
    bot_state.jail_message_id = new_id

    if old_id:
        try:
            await delete_telegram_message(old_id)
        except Exception:
            pass


async def _jail_repeat_loop() -> None:
    """Loop de reaviso periodico enquanto preso. Intervalo re-lido a cada
    iteracao (mudanca de config em runtime vale)."""
    try:
        while bot_state.jailed:
            interval = getattr(config, "jail_notify_interval_min", 15) * 60
            await asyncio.sleep(interval)
            if not bot_state.jailed:
                break
            play_jail_alarm()
            await _send_jail_message()
            update_live_status()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Erro no loop de reaviso de jail: {e}")


def _start_jail_repeat_loop() -> None:
    """Inicia o loop de reaviso como asyncio.Task, se ainda nao ativo."""
    if bot_state.jail_repeat_task and not bot_state.jail_repeat_task.done():
        return
    bot_state.jail_repeat_task = asyncio.ensure_future(_jail_repeat_loop())


def _stop_jail_repeat_loop() -> None:
    """Cancela o loop de reaviso, se ativo."""
    if bot_state.jail_repeat_task and not bot_state.jail_repeat_task.done():
        bot_state.jail_repeat_task.cancel()
        bot_state.jail_repeat_task = None


def on_jail_detected() -> None:
    """Entrada no jail: alarme + persiste status + inicia loop de reaviso."""
    if bot_state.jail_started_at == 0.0:
        bot_state.jail_started_at = time.time()
    play_jail_alarm()
    _start_jail_repeat_loop()
    update_live_status()


async def on_jail_released() -> None:
    """Saida do jail: apaga msg telegram + cancela loop + persiste status."""
    _stop_jail_repeat_loop()
    if bot_state.jail_message_id:
        try:
            await delete_telegram_message(bot_state.jail_message_id)
        except Exception:
            pass
    bot_state.jail_message_id = None
    bot_state.jail_started_at = 0.0
    update_live_status()


def reset_jail_state() -> None:
    """Reset sincrono usado no reset_bot_state (nao faz chamadas async)."""
    _stop_jail_repeat_loop()
    bot_state.jail_message_id = None
    bot_state.jail_started_at = 0.0
    update_live_status()
