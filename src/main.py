import time
from threading import Thread
from io import BytesIO

from formatter import LPFormatter
from helpers import (
    get_all_positions,
    get_lps_from_positions,
    get_lp_token_info,
    send_ntfy_notification,
    handle_telegram_commands,
    convert_sqrtPriceX96_to_price,
    cal_real_price,
    create_price_slider,
    handle_error
)
from alert_db import (
    init_db, load_alerted_positions, add_alerted_position,
    remove_alerted_position, cleanup_alerted_positions
)


formatter_ntfy = LPFormatter(style="ntfy")
formatter_telegram = LPFormatter(style="telegram")


async def get_all_liquidity_messages(update=None, context=None) -> list[tuple[str, BytesIO]]:
    results = []
    waiting_message = None

    try:
        if update:
            waiting_message = await update.message.reply_text("⏳ Fetching liquidity data, please wait...", parse_mode=None)

        all_positions, all_unstaked_positions = get_all_positions()
        lps = get_lps_from_positions(all_positions)
        unstaked_lps = get_lps_from_positions(all_unstaked_positions)

        def build_entry(pos, lp, is_staked):
            token0, token1 = get_lp_token_info(lp)
            msg = formatter_telegram.format_position(pos, lp, token0, token1, is_staked)

            price_now = convert_sqrtPriceX96_to_price(lp.sqrt_ratio, precision=8)
            price_upper = convert_sqrtPriceX96_to_price(pos.sqrt_ratio_upper, precision=8)
            price_lower = convert_sqrtPriceX96_to_price(pos.sqrt_ratio_lower, precision=8)
            (price_upper, price_now, price_lower) = cal_real_price(token0, token1, price_upper, price_now, price_lower)

            image = create_price_slider(price_lower, price_now, price_upper)
            return (msg, image)

        results += [build_entry(pos, lps[i], True) for i, pos in enumerate(all_positions)]
        results += [build_entry(pos, unstaked_lps[i], False) for i, pos in enumerate(all_unstaked_positions)]

    except Exception as e:
        handle_error(e, "Liquidity Fetch")

    finally:
        if update and waiting_message:
            try:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=waiting_message.message_id)
            except Exception as e:
                print(f"⚠️ Failed to delete waiting message: {e}")

    return results


def run_alert_loop(interval_minutes=3):
    try:
        init_db()

        while True:
            try:
                print("🔄 Scanning LP positions for alert...")
                all_positions, all_unstaked_positions = get_all_positions()
                lps = get_lps_from_positions(all_positions)
                unstaked_lps = get_lps_from_positions(all_unstaked_positions)

                valid_keys = {f"position_{pos.id}" for pos in all_positions + all_unstaked_positions}
                cleanup_alerted_positions(valid_keys)
                alerted = load_alerted_positions()

                def check_and_alert(positions, lps, is_staked):
                    for i, pos in enumerate(positions):
                        lp = lps[i]
                        token0, token1 = get_lp_token_info(lp)

                        price_now = convert_sqrtPriceX96_to_price(lp.sqrt_ratio, precision=8)
                        price_upper = convert_sqrtPriceX96_to_price(pos.sqrt_ratio_upper, precision=8)
                        price_lower = convert_sqrtPriceX96_to_price(pos.sqrt_ratio_lower, precision=8)
                        (price_upper, price_now, price_lower) = cal_real_price(token0, token1, price_upper, price_now, price_lower)

                        in_range = price_lower <= price_now <= price_upper
                        key = f"position_{pos.id}"

                        if not in_range and key not in alerted:
                            msg = formatter_ntfy.format_position(pos, lp, token0, token1, is_staked)
                            send_ntfy_notification(msg)
                            add_alerted_position(key)
                            alerted.add(key)
                        elif in_range and key in alerted:
                            remove_alerted_position(key)
                            alerted.remove(key)

                check_and_alert(all_positions, lps, True)
                check_and_alert(all_unstaked_positions, unstaked_lps, False)

                print(f"✅ Done. Sleeping {interval_minutes} minutes...\n")
                time.sleep(interval_minutes * 60)

            except Exception as e:
                handle_error(e, "Alert Loop")
                time.sleep(10)

    except Exception as e:
        handle_error(e, "Init Alert Loop")


if __name__ == "__main__":
    try:
        Thread(target=run_alert_loop, daemon=True).start()
        handle_telegram_commands(get_all_liquidity_messages, parse_mode="MarkdownV2", bot_ready_hook=True)
    except Exception as e:
        handle_error(e, "Main Thread")
