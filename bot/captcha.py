import asyncio
import time
import traceback
import os
import numpy as np
from random import randint
from PIL import Image
import options_resolver
from bot.hud import HUD, logger
import bot.config as config
from bot.state import bot_state, human_delay
from bot.telegram import (
    send_telegram_notification,
    send_telegram_photo,
    get_telegram_override,
)

# Client reference — set by client.py at startup via set_client()
_client = None


def set_client(client):
    global _client
    _client = client


async def save_and_crop_attachment(attachment, out_path='epic_guard.png'):
    """Saves attachment. Crop logic removed for Oracle v2 compatibility."""
    try:
        if not os.path.isabs(out_path):
            out_path = os.path.join(options_resolver.USER_DATA_DIR, out_path)
        await attachment.save(out_path)
        logger.info(f"Attachment saved to {out_path}")
    except Exception as e:
        logger.error(f"Erro ao salvar attachment: {e}\n{traceback.format_exc()}")


def is_grayscale(img):
    """Detect if a captcha image is truly grayscale.
    The icon is tiny (~1-2% of pixels), so mean/median saturation always reads
    near zero. Instead, check if the 99th percentile of max RGB channel
    difference is below a threshold — if even the most colorful pixels have
    no channel divergence, the image is genuinely grayscale."""
    rgb = np.array(img.convert('RGB'))
    r, g, b = rgb[:,:,0].astype(int), rgb[:,:,1].astype(int), rgb[:,:,2].astype(int)
    max_diff = np.maximum(np.abs(r - g), np.abs(r - b))
    return np.percentile(max_diff, 99) < 10


def _prepare_input(img, mode):
    """Prepare image tensor for a given model mode."""
    if mode == 'gray':
        img_proc = img.convert('L').resize((config.img_width, config.img_height))
        x = np.array(img_proc) / 255.0
        x = np.stack([x] * 3, axis=-1)
    else:
        img_proc = img.resize((config.img_width, config.img_height))
        x = np.array(img_proc.convert('RGB')) / 255.0
    return np.expand_dims(x, axis=0)


def _get_model_for(mode):
    """Return the model for the given mode, or fallback to the other."""
    if mode == 'gray':
        return config.captcha_model_gray or config.captcha_model_color, \
               'gray' if config.captcha_model_gray else 'color'
    else:
        return config.captcha_model_color or config.captcha_model_gray, \
               'color' if config.captcha_model_color else 'gray'


def predict_item_from_captcha(img_path):
    try:
        if not os.path.isabs(img_path):
            img_path = os.path.join(options_resolver.USER_DATA_DIR, img_path)
        with Image.open(img_path) as img:
            img = img.convert('RGB')
        # We prefer using the color model directly for all images because the color model has higher accuracy (96.28% vs 95.15%)
        # and higher confidence (97.01% vs 95.55%) even on grayscale/silhouette images, and completely avoids misrouting.
        preferred = 'color'
        model, actual_mode = _get_model_for(preferred)

        if model is None:
            logger.error("No captcha model available!")
            return None

        x = _prepare_input(img, actual_mode)
        preds = model.predict(x, verbose=0)
        class_idx = np.argmax(preds, axis=1)[0]
        return config.captcha_class_names[class_idx]
    except Exception as e:
        logger.error(
            f"Error in predict_item_from_captcha: {e}\n{traceback.format_exc()}"
        )
        return None


async def tentar_resolver_captcha(message):
    """Resolves an Epic Guard captcha using AI predictions or Telegram overrides."""
    img_path = os.path.join(options_resolver.USER_DATA_DIR, 'epic_guard.png')
    captcha_start_time = time.time()

    try:
        if not bot_state.captcha_pending:
            return

        # AI Prediction — with cross-model fallback
        with Image.open(img_path) as img:
            img = img.convert('RGB')
        detected_gray = is_grayscale(img)
        # We prefer using the color model directly for all images because the color model has higher accuracy (96.28% vs 95.15%)
        # and higher confidence (97.01% vs 95.55%) even on grayscale/silhouette images, and completely avoids misrouting.
        preferred = 'color'
        model, actual_mode = _get_model_for(preferred)

        if model is None:
            HUD.alert("NENHUM MODELO DE CAPTCHA DISPONÍVEL! Aguardando apenas override do Telegram.")
            await send_telegram_photo(
                img_path,
                "🚨 CAPTCHA DETECTADO! Nenhum modelo de IA disponível. Digite a resposta aqui para resolver.",
            )
            # Wait extra long for manual input
            for _ in range(90):
                override = await get_telegram_override(captcha_start_time)
                if override and override not in ["/start", "rpg", "sb"]:
                    HUD.alert(f"📲 OVERRIDE DO TELEGRAM: '{override}'")
                    await message.channel.send(override)
                    return
                await asyncio.sleep(1)
            return

        HUD.oracle(f"Rota do Modelo: {actual_mode.upper()} (Imagem Grayscale: {detected_gray})")
        x = _prepare_input(img, actual_mode)
        preds = model.predict(x, verbose=0)[0]
        confidence = np.max(preds)

        primary_mode = actual_mode
        primary_confidence = confidence
        alt_mode = 'gray' if actual_mode == 'color' else 'color'
        alt_model = config.captcha_model_gray if alt_mode == 'gray' else config.captcha_model_color
        
        fallback_triggered = False
        alt_confidence = None

        # Cross-model fallback: if primary model is unsure, ask the other
        if confidence < 0.80 and alt_model is not None:
            fallback_triggered = True
            HUD.oracle(f"Baixa confiança ({confidence:.1%}), tentando modelo {alt_mode.upper()}...")
            x_alt = _prepare_input(img, alt_mode)
            preds_alt = alt_model.predict(x_alt, verbose=0)[0]
            alt_confidence = np.max(preds_alt)
            if alt_confidence > confidence:
                HUD.oracle(f"Modelo alternativo venceu: {alt_confidence:.1%} vs {confidence:.1%}")
                preds = preds_alt
                confidence = alt_confidence

        topk_idx = np.argsort(preds)[-3:][::-1]
        topk_names = [
            config.captcha_class_names[i].replace('_', ' ') for i in topk_idx
        ]
        best_guess = topk_names[0]

        HUD.oracle(f"Melhor palpite da IA: {best_guess} ({confidence:.1%})")

        color_conf = None
        gray_conf = None

        if config.captcha_model_color is not None:
            if actual_mode == 'color':
                color_conf = primary_confidence
            elif fallback_triggered and alt_mode == 'color':
                color_conf = alt_confidence
            else:
                x_color = _prepare_input(img, 'color')
                preds_color = config.captcha_model_color.predict(x_color, verbose=0)[0]
                color_conf = np.max(preds_color)

        if config.captcha_model_gray is not None:
            if actual_mode == 'gray':
                gray_conf = primary_confidence
            elif fallback_triggered and alt_mode == 'gray':
                gray_conf = alt_confidence
            else:
                x_gray = _prepare_input(img, 'gray')
                preds_gray = config.captcha_model_gray.predict(x_gray, verbose=0)[0]
                gray_conf = np.max(preds_gray)

        model_info_lines = []
        if color_conf is not None:
            model_info_lines.append(f"palpite do modelo color: {color_conf:.1%}")
        if gray_conf is not None:
            model_info_lines.append(f"palpite do modelo gray: {gray_conf:.1%}")
        model_info = "\n".join(model_info_lines)

        # INSTANT NOTIFICATION WITH GUESS
        HUD.alert("CAPTCHA! Enviando para o Telegram...")
        await send_telegram_photo(
            img_path,
            f"🚨 CAPTCHA DETECTADO!\nPalpite da IA: {best_guess} ({confidence:.1%})\n{model_info}\nDigite a resposta aqui para sobrescrever a IA.",
        )

        await human_delay(1.5, 2.0)  # 1.5-3.5s human "reading" delay

        # Initial Wait for Human Override (7 seconds)
        for _ in range(7):
            override = await get_telegram_override(captcha_start_time)
            if override and override not in ["/start", "rpg", "sb"]:
                HUD.alert(f"📲 OVERRIDE DO TELEGRAM: '{override}'")
                topk_names = [override]
                break
            await asyncio.sleep(1)

        HUD.oracle(f"Silhuetas Alvo: {topk_names}")

        for tentativa, item_name in enumerate(topk_names, start=1):
            if not bot_state.captcha_pending:
                break

            # Check for Telegram override before every attempt
            override = await get_telegram_override(captcha_start_time)
            if (
                override
                and override not in ["/start", "rpg", "sb"]
                and override != item_name
            ):
                HUD.alert(f"📲 HIJACK DO TELEGRAM: Mudando para '{override}'")
                item_name = override

            await human_delay(1.5, 3.0)  # 1.5-4.5s "reading + typing" delay
            HUD.oracle(f"Tentativa {tentativa}: Enviando '{item_name}'")
            sent = await message.channel.send(item_name)

            try:
                result = await asyncio.wait_for(
                    aguardar_resposta_epic_guard(message.channel), timeout=3.5
                )
                if result == "freed":
                    HUD.system("🎯 Captcha Resolvido!")
                    bot_state.paused = False
                    bot_state.jailed = False
                    return True
                elif result == "jailed":
                    HUD.alert("💀 Captcha FALHOU — Preso.")
                    bot_state.jailed = True
                    bot_state.paused = True
                    await send_telegram_notification(
                        "🚨 CAPTCHA FALHOU! O bot está PRESO. Intervenção manual necessária."
                    )
                    return False
            except asyncio.TimeoutError:
                HUD.alert("❌ Errou. Limpando...")
                try:
                    await sent.delete()
                except Exception:
                    pass
                await asyncio.sleep(randint(2, 4))
                continue

        HUD.system("Ciclo de resolução do Oráculo concluído.")
    except Exception as e:
        logger.error(f"Error resolving captcha: {e}\n{traceback.format_exc()}")
    finally:
        bot_state.captcha_pending = False
        bot_state.captcha_task = None


FREEDOM_KEYWORDS = [
    "fine, i will let you go",
    "you are free",
    "is now free",
    "everything seems fine",
    "everything looks fine",
]
JAIL_KEYWORDS = [
    "is now in the jail",
    "is now in the adventure jail",
    "what?? get in the car",
]


async def aguardar_resposta_epic_guard(channel):
    """Waits for Epic Guard response. Returns 'freed' or 'jailed'."""

    def check(m):
        if m.channel.id != channel.id or m.author.id != config.EPIC_RPG_ID:
            return False
        content = m.content.lower()
        return any(x in content for x in FREEDOM_KEYWORDS + JAIL_KEYWORDS)

    try:
        resp = await _client.wait_for('message', check=check)
        content = resp.content.lower()
        if any(x in content for x in FREEDOM_KEYWORDS):
            return "freed"
        return "jailed"
    except asyncio.CancelledError:
        raise
    except Exception:
        return None
