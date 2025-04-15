import time

from threading import Thread
from formatter import LPFormatter
from helpers import (
    get_all_positions,
    get_lps_from_positions,
    get_lp_token_info,
    send_ntfy_notification,
    handle_telegram_commands,
    convert_sqrtPriceX96_to_price
)
from alert_db import init_db, load_alerted_positions, add_alerted_position, remove_alerted_position


formatter_ntfy = LPFormatter(style="ntfy")
formatter_telegram = LPFormatter(style="markdown")

async def get_all_liquidity_messages(update=None, context=None) -> list[str]:
    if update is not None:
        waiting_message = await update.message.reply_text("⏳ Fetching liquidity data, please wait...", parse_mode=None)

    messages = []
    all_positions, all_unstaked_positions = get_all_positions()
    lps = get_lps_from_positions(all_positions)
    unstaked_lps = get_lps_from_positions(all_unstaked_positions)

    for idx, pos in enumerate(all_positions):
        lp = lps[idx]
        token0, token1 = get_lp_token_info(lp)
        msg = formatter_telegram.format_position(pos, lp, token0, token1, staked=True)
        messages.append(msg)

    for idx, pos in enumerate(all_unstaked_positions):
        lp = unstaked_lps[idx]
        token0, token1 = get_lp_token_info(lp)
        msg = formatter_telegram.format_position(pos, lp, token0, token1, staked=False)
        messages.append(msg)

    if update is not None:
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=waiting_message.message_id)
        except Exception:
            pass

    return messages


def run_alert_loop(interval_minutes=3):
    init_db()
    alerted_positions = load_alerted_positions()

    while True:
        print("🔄 Scanning LP positions for alert...")
        all_positions, all_unstaked_positions = get_all_positions()
        lps = get_lps_from_positions(all_positions)
        unstaked_lps = get_lps_from_positions(all_unstaked_positions)

        def check_and_alert(positions, lps, staked=True):
            for idx, pos in enumerate(positions):
                lp = lps[idx]
                token0, token1 = get_lp_token_info(lp)

                price_now = convert_sqrtPriceX96_to_price(lp.sqrt_ratio, precision=8)
                price_upper = convert_sqrtPriceX96_to_price(pos.sqrt_ratio_upper, precision=8)
                price_lower = convert_sqrtPriceX96_to_price(pos.sqrt_ratio_lower, precision=8)

                in_range = price_lower <= price_now <= price_upper
                pos_key = f"position_{pos.id}"

                if not in_range and pos_key not in alerted_positions:
                    msg = formatter_ntfy.format_position(pos, lp, token0, token1, staked=staked)
                    send_ntfy_notification(msg)
                    add_alerted_position(pos_key)
                    alerted_positions.add(pos_key)
                elif in_range and pos_key in alerted_positions:
                    remove_alerted_position(pos_key)
                    alerted_positions.remove(pos_key)

        check_and_alert(all_positions, lps, staked=True)
        check_and_alert(all_unstaked_positions, unstaked_lps, staked=False)

        print(f"✅ Done. Sleeping {interval_minutes} minutes...\n")
        time.sleep(interval_minutes * 60)


if __name__ == "__main__":
    Thread(target=run_alert_loop, daemon=True).start()
    handle_telegram_commands(get_all_liquidity_messages, parse_mode="MarkdownV2", bot_ready_hook=True)
