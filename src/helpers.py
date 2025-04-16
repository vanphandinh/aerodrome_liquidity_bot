import os
import requests
import asyncio

from decimal import Decimal, ROUND_DOWN, getcontext
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from typing import List, Union, List
from contract import sugar_lp, web3, erc20_abi, price_oracle
from data_models import Lp, Position, Token
import matplotlib.pyplot as plt
from io import BytesIO
from matplotlib.patches import FancyBboxPatch
from matplotlib.pyplot import subplots
import matplotlib


account_address = os.getenv("ACCOUNT_ADDRESS")
ntfy_topic = os.getenv("NTFY_TOPIC")
telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
usdc = os.getenv("USDC_ADDRESS")
aero = os.getenv("AERO_ADDRESS")

def get_all_lp(limit: int, offset: int) -> List[Lp]:
    result = sugar_lp.functions.all(limit, offset).call()
    return [Lp(*item) for item in result]


def get_all_lp_batch(limit: int = 300, batch_size: int = 3, start_offset: int = 0) -> List[Lp]:
    all_lps = []
    offsets = [start_offset + i * limit for i in range(batch_size)]

    with web3.batch_requests() as batch:
        for offset in offsets:
            batch.add(sugar_lp.functions.all(limit, offset))
        batch_responses = batch.execute()
    batch.clear()

    for result in batch_responses:
        all_lps.extend([Lp(*item) for item in result])

    return all_lps


def get_lp_by_address(pool_address: str) -> Lp:
    result = sugar_lp.functions.byAddress(web3.to_checksum_address(pool_address)).call()
    return Lp(*result)


def get_positions(limit: int, offset: int, account: str) -> List[Position]:
    result = sugar_lp.functions.positions(limit, offset, web3.to_checksum_address(account)).call()
    return [Position(*item) for item in result]


def get_positions_batch(
    limit: int = 100,
    batch_size: int = 3,
    start_offset: int = 0,
    account: str = account_address
) -> List[Position]:
    positions = []
    offsets = [start_offset + i * limit for i in range(batch_size)]

    with web3.batch_requests() as batch:
        for offset in offsets:
            batch.add(sugar_lp.functions.positions(limit, offset, web3.to_checksum_address(account)))
        batch_responses = batch.execute()
    batch.clear()

    for result in batch_responses:
        positions.extend([Position(*item) for item in result])

    return positions


def get_positions_unstaked_concentrated_batch(
    limit: int = 100,
    batch_size: int = 3,
    start_offset: int = 0,
    account: str = account_address
) -> List[Position]:
    positions = []
    offsets = [start_offset + i * limit for i in range(batch_size)]

    with web3.batch_requests() as batch:
        for offset in offsets:
            batch.add(sugar_lp.functions.positionsUnstakedConcentrated(limit, offset, web3.to_checksum_address(account)))
        batch_responses = batch.execute()
    batch.clear()

    for result in batch_responses:
        positions.extend([Position(*item) for item in result])

    return positions


def get_positions_unstaked_concentrated(limit: int, offset: int, account: str) -> List[Position]:
    result = sugar_lp.functions.positionsUnstakedConcentrated(limit, offset, web3.to_checksum_address(account)).call()
    return [Position(*item) for item in result]


def get_all_positions() -> tuple[List[Position], List[Position]]:
    offset = 7000
    limit = 100
    batch_size = 1
    last_non_empty_offset = None

    while True:
        print(f"[INFO] Fetching from offset {offset}...")
        lps = get_all_lp_batch(limit=limit, batch_size=batch_size, start_offset=offset)
        if not lps:
            print(f"[DONE] No more results at offset {offset}. Last non-empty offset: {last_non_empty_offset}")
            break
        last_non_empty_offset = offset
        offset += limit * batch_size

    offset = 0
    all_positions = []
    all_unstaked_positions = []

    while offset <= last_non_empty_offset:
        limit = 100
        if offset < 6000:
            batch_size = 20
        elif offset < 7000:
            batch_size = 10
        else:
            batch_size = 1

        print(f"[INFO] Fetching positions from offset {offset} with batch_size {batch_size}...")
        pos_batch = get_positions_batch(limit=limit, batch_size=batch_size, start_offset=offset, account=account_address)
        all_positions.extend(pos_batch)

        print(f"[INFO] Fetching unstaked positions from offset {offset} with batch_size {batch_size}...")
        unstaked_batch = get_positions_unstaked_concentrated_batch(limit=limit, batch_size=batch_size, start_offset=offset, account=account_address)
        all_unstaked_positions.extend(unstaked_batch)

        offset += limit * batch_size


    return (all_positions, all_unstaked_positions)


def get_lps_from_positions(positions: List[Position]) -> List[Lp]:
    lps = []
    if len(positions) == 0:
        return lps

    with web3.batch_requests() as batch:
        for pos in positions:
            batch.add(sugar_lp.functions.byAddress(web3.to_checksum_address(pos.lp)))
        batch_responses = batch.execute()
    batch.clear()

    for result in batch_responses:
        lps.append(Lp(*result))

    return lps
    

def get_lp_token_info(lp: Lp) -> tuple[Token, Token]:
    token0 = web3.eth.contract(address=web3.to_checksum_address(lp.token0), abi=erc20_abi)
    token1 = web3.eth.contract(address=web3.to_checksum_address(lp.token1), abi=erc20_abi)

    with web3.batch_requests() as batch:
        batch.add(token0.functions.symbol())
        batch.add(token0.functions.decimals())
        batch.add(token1.functions.symbol())
        batch.add(token1.functions.decimals())
        batch_responses = batch.execute()
    batch.clear()

    return (Token(batch_responses[0], batch_responses[1]), Token(batch_responses[2], batch_responses[3]))


def send_ntfy_notification(
    message: str,
    title: str = "Alert",
    priority: str = "high",
    tags: Union[str, List[str]] = "rotating_light",
    click: str = None,
    attach: str = None,
    actions: List[dict] = None,
    topic: str = ntfy_topic,
):
    """
    Send a rich notification via ntfy.sh

    :param message: Message body (required)
    :param title: Optional title of the notification
    :param priority: Notification priority: min, low, default, high, max
    :param tags: Emoji tags like ['warning', 'fire'] or a single string
    :param click: URL to open when clicking the notification
    :param attach: URL to attach media (image/file)
    :param actions: List of action dicts for interactive buttons
    :param topic: Topic name subscribed in ntfy app
    """
    url = f"https://ntfy.sh/{topic}"
    headers = {
        "Priority": priority
    }

    if title:
        headers["Title"] = title
    if tags:
        headers["Tags"] = ",".join(tags) if isinstance(tags, list) else tags
    if click:
        headers["Click"] = click
    if attach:
        headers["Attach"] = attach
    if actions:
        import json
        headers["Actions"] = json.dumps(actions)

    response = requests.post(url, headers=headers, data=message.encode("utf-8"))

    if response.status_code == 200:
        print("✅ Notification sent successfully!")
    else:
        raise Exception(f"❌ Failed to send notification: {response.status_code} - {response.text}")


def handle_telegram_commands(get_messages_func, parse_mode="MarkdownV2", bot_ready_hook=False):
    async def liquidity_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_message = update.message
            asyncio.create_task(delete_after_delay(
                context=context,
                chat_id=user_message.chat_id,
                message_id=user_message.message_id,
                delay=300
            ))
        except Exception as e:
            print(f"⚠️ Failed to schedule user message deletion: {e}")

        # 👇 Lấy danh sách (message, image)
        message_tuples = await get_messages_func(update, context)

        # 📤 Gửi từng ảnh + caption
        for msg, image in message_tuples:
            try:
                sent_msg = await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=image,
                    caption=msg,
                    parse_mode=parse_mode
                )

                asyncio.create_task(delete_after_delay(
                    context=context,
                    chat_id=sent_msg.chat_id,
                    message_id=sent_msg.message_id,
                    delay=300
                ))
            except Exception as e:
                print(f"⚠️ Error sending photo message: {e}")

    # 🧹 Hàm xóa sau delay
    async def delete_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int):
        await asyncio.sleep(delay)
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception as e:
            print(f"❌ Failed to delete message {message_id}: {e}")

    # 🚀 Khởi tạo bot
    app = ApplicationBuilder().token(telegram_bot_token).build()
    app.add_handler(CommandHandler("liquidity", liquidity_command))

    if bot_ready_hook:
        async def set_commands(app):
            await app.bot.set_my_commands([
                BotCommand("liquidity", "Show all current liquidity positions")
            ])
        app.post_init = set_commands

    print("🤖 Telegram bot is running and listening for /liquidity ...")
    app.run_polling()


def convert_by_decimals(raw_balance: int, decimals: int, precision: int = 4) -> Decimal:
    getcontext().prec = precision + 10
    return Decimal(raw_balance) / Decimal(10 ** decimals)


def convert_sqrtPriceX96_to_price(sqrtPriceX96: int, precision: int = 8) -> Decimal:
    getcontext().prec = precision + 10
    return (Decimal(sqrtPriceX96) ** 2) / Decimal(2 ** 192)


def create_price_slider(lower_price, price_now, upper_price, precision=8):
    def fmt(val):
        d = Decimal(str(val)).quantize(Decimal(f"1e-{precision}"), rounding=ROUND_DOWN)
        return format(d.normalize(), 'f')

    lower, current, upper = map(lambda v: Decimal(str(v)), (lower_price, price_now, upper_price))
    min_range, max_range = min(lower, current, upper), max(lower, current, upper)
    margin = (max_range - min_range) * Decimal("0.3")
    view_min, view_max = float(min_range - margin), float(max_range + margin)
    lower_f, current_f, upper_f = map(float, (lower, current, upper))

    fig, ax = subplots(figsize=(9, 3.6), facecolor='#101615')
    ax.set(xlim=(view_min, view_max), ylim=(0, 1.8))
    ax.axis('off')

    # Layout constants
    bar_y = 0.9
    bar_height = 0.06
    arrow_offset = 0.10
    label_offset = 0.45  # đã kéo xuống thêm để tránh đè
    symmetric_offset = 0.18

    active_color = '#00e6b8'
    bg_color = '#5f6d67'
    tick_color = '#f6c744'

    # Bar backgrounds
    ax.add_patch(FancyBboxPatch((view_min, bar_y - bar_height / 2),
                                view_max - view_min, bar_height,
                                boxstyle="round,pad=0.01", linewidth=0, facecolor=bg_color))
    ax.add_patch(matplotlib.patches.Rectangle((lower_f, bar_y - bar_height / 2),
                                              upper_f - lower_f, bar_height,
                                              linewidth=0, facecolor=active_color, zorder=1))

    # Endpoint circles
    for x in (lower_f, upper_f):
        ax.plot(x, bar_y, marker='o', markersize=13, color=active_color, zorder=2)

    # Vertical tick
    ax.plot([current_f]*2, [bar_y - arrow_offset, bar_y + arrow_offset],
            color=tick_color, linewidth=2, zorder=3)
    ax.annotate('', xy=(current_f, bar_y), xytext=(current_f, bar_y + arrow_offset),
                arrowprops=dict(arrowstyle='-|>', color=tick_color, linewidth=2), zorder=4)
    ax.annotate('', xy=(current_f, bar_y - arrow_offset), xytext=(current_f, bar_y),
                arrowprops=dict(arrowstyle='<|-', color=tick_color, linewidth=2), zorder=4)

    # Zone labels (kéo thấp hơn)
    ax.text((view_min + lower_f) / 2, bar_y - label_offset, "OUT",
            ha='center', va='center', fontsize=9, color='gray')
    ax.text((lower_f + upper_f) / 2, bar_y - label_offset, "ACTIVE RANGE",
            ha='center', va='center', fontsize=9, color=active_color)
    ax.text((upper_f + view_max) / 2, bar_y - label_offset, "OUT",
            ha='center', va='center', fontsize=9, color='gray')

    # Price values (upper/lower)
    ax.text(lower_f, bar_y + symmetric_offset, fmt(lower),
            ha='center', va='bottom', fontsize=10, color=active_color, fontweight='bold')
    ax.text(upper_f, bar_y + symmetric_offset, fmt(upper),
            ha='center', va='bottom', fontsize=10, color=active_color, fontweight='bold')

    # Boxed current price (cách thanh giá một khoảng bằng upper/lower)
    ax.text(current_f, bar_y - symmetric_offset, fmt(current),
            ha='center', va='top', fontsize=10, fontweight='bold',
            color=tick_color,
            bbox=dict(boxstyle="round,pad=0.25", fc="#101615", ec=tick_color, lw=1.5))

    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    buf.seek(0)
    return buf


def get_token_price_batch(token_list: List[str]) -> List[str]:
    prices = []

    with web3.batch_requests() as batch:
        for token in token_list:
            batch.add(price_oracle.functions.getRate(token, usdc, False))
        batch_responses = batch.execute()
    batch.clear()

    for result in batch_responses:
        prices.append(result)

    return prices    


def cal_lp_apr(lp: Lp, precision: int = 3) -> Decimal:
    getcontext().prec = precision + 10
    token0, token1 = get_lp_token_info(lp)
    apr = 0
    emissions = lp.emissions
    staked_token0 = lp.staked0
    staked_token1 = lp.staked1
    token_prices = get_token_price_batch([lp.token0, lp.token1, aero])
    apr = 100 * convert_by_decimals(31_556_926 * emissions, 18) * Decimal(token_prices[2]) / (Decimal(token_prices[0]) * convert_by_decimals(staked_token0, token0.decimals) 
       + Decimal(token_prices[1]) * convert_by_decimals(staked_token1, token1.decimals))
    return apr