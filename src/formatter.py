from tabulate import tabulate
from typing import List, Literal
from decimal import Decimal, getcontext
from helpers import convert_by_decimals, convert_sqrtPriceX96_to_price

Style = Literal["plain", "table", "markdown", "slider"]

class LPFormatter:
    def __init__(self, style: Style = "plain"):
        self.style = style

    def convert_token_amount(self, raw_balance: int, decimals: int, precision: int = 4) -> str:
        value = convert_by_decimals(raw_balance=raw_balance, decimals=decimals, precision=precision)
        return f"{value:,.{precision}f}"

    def sqrtPriceX96_to_price(self, sqrtPriceX96: int, precision: int = 8) -> str:
        price = convert_sqrtPriceX96_to_price(sqrtPriceX96=sqrtPriceX96, precision=precision)
        return f"{price:,.{precision}f}"

    def render_price_slider(self, lower: float, current: float, upper: float, bar_length: int = 40) -> str:
        percent = (current - lower) / (upper - lower)
        pos = int(percent * bar_length)

        bar = ["─"] * bar_length

        if percent < 0:
            pointer = "⏳" + "─" * (bar_length - 2) + "●"
        elif percent > 1:
            pointer = "●" + "─" * (bar_length - 2) + "⏳"
        else:
            pos = max(1, min(bar_length - 2, pos))
            bar[0] = "●"
            bar[-1] = "●"
            bar[pos] = "⏳"
            pointer = ''.join(bar)

        return (
            f"[{pointer}]\n"
            f"{lower:.8f}{' ' * (bar_length - 16)}{upper:.8f}\n"
            f"Current: {current:.8f}"
        )

    def format_position(self, pos, lp, token0, token1, is_staked: bool = True) -> str:
        t0_amt = self.convert_token_amount(pos.staked0 if is_staked else pos.amount0, token0.decimals)
        t1_amt = self.convert_token_amount(pos.staked1 if is_staked else pos.amount1, token1.decimals)

        price_now = self.sqrtPriceX96_to_price(lp.sqrt_ratio, precision=8)
        price_upper = self.sqrtPriceX96_to_price(pos.sqrt_ratio_upper, precision=8)
        price_lower = self.sqrtPriceX96_to_price(pos.sqrt_ratio_lower, precision=8)

        in_range = price_lower <= price_now <= price_upper
        range_status = "✅ In Range" if in_range else "⚠️ Out of Range"
        range_status_table = "In" if in_range else "Out"

        if self.style == "plain":
            msg = (
                f"────────────────────────────────────\n"
                f"📊 LP Position Summary\n"
                f"────────────────────────────────────\n"
                f"🔗 Pair              : {token0.symbol}/{token1.symbol}\n"
                f"💰 {token0.symbol:<18}: {t0_amt}\n"
                f"💰 {token1.symbol:<18}: {t1_amt}\n"
                f"\n"
                f"📈 Tick Range        : {pos.tick_lower} ⟶ {lp.tick} ⟶ {pos.tick_upper}\n"
                f"🔍 Status            : {range_status}\n"
                f"\n"
                f"💹 Price Now         : {price_now}\n"
                f"🔼 Price Upper       : {price_upper}\n"
                f"🔽 Price Lower       : {price_lower}\n"
                f"────────────────────────────────────"
            )
            return msg + "\n"

        elif self.style == "telegram":
            return (
                f"📊 *LP Summary*: {token0.symbol}/{token1.symbol}\n"
                f"💰 {token0.symbol}: `{t0_amt}`\n"
                f"💰 {token1.symbol}: `{t1_amt}`\n"
                f"🔒 Staked: *{'✅ Yes' if is_staked else '❌ No'}*\n"
                f"📈 Tick Range: `{pos.tick_lower} → {lp.tick} → {pos.tick_upper}`\n"
                f"🔍 Status: *{range_status}*\n"
                f"💹 Price Now: `{price_now}`\n"
                f"🔼 Upper Price: `{price_upper}`\n"
                f"🔽 Lower Price: `{price_lower}`"
            )
        
        elif self.style == "ntfy":
            return (
                f"📊 LP Summary: {token0.symbol}/{token1.symbol}\n"
                f"💰 {token0.symbol}: {t0_amt}\n"
                f"💰 {token1.symbol}: {t1_amt}\n"
                f"🔒 Staked: {'✅ Yes' if is_staked else '❌ No'}\n"
                f"📈 Tick Range: {pos.tick_lower} → {lp.tick} → {pos.tick_upper}\n"
                f"🔍 Status: {range_status}\n"
                f"💹 Price Now: {price_now}\n"
                f"🔼 Upper Price: {price_upper}\n"
                f"🔽 Lower Price: {price_lower}"
            )

        elif self.style == "table":
            headers = ["Pair", token0.symbol, token1.symbol, "Ticks", "Status", "Now", "Upper", "Lower"]
            data = [[
                f"{token0.symbol}/{token1.symbol}",
                t0_amt,
                t1_amt,
                f"{pos.tick_lower}→{lp.tick}→{pos.tick_upper}",
                range_status_table,
                price_now,
                price_upper,
                price_lower
            ]]
            return tabulate(data, headers=headers, tablefmt="grid") + "\n"

        elif self.style == "slider":
            lower = float(price_lower)
            current = float(price_now)
            upper = float(price_upper)
            slider = self.render_price_slider(lower, current, upper)
            return (
                f"📊 LP Summary: {token0.symbol}/{token1.symbol}\n"
                f"{slider}\n"
                f"Token0: {t0_amt} {token0.symbol}\n"
                f"Token1: {t1_amt} {token1.symbol}\n"
                f"Tick: {pos.tick_lower} ⟶ {lp.tick} ⟶ {pos.tick_upper}\n"
                f"Status: {range_status}\n"
            )

        else:
            return "❌ Unsupported format style"

    def format_all(self, positions, lps, get_token_info_func) -> List[str]:
        return [
            self.format_position(pos, lps[idx], *get_token_info_func(lps[idx])) + "\n"
            for idx, pos in enumerate(positions)
        ]
