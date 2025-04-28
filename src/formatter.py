from typing import List, Literal
from decimal import Decimal
from helpers import convert_by_decimals, convert_sqrtPriceX96_to_price, cal_lp_apr, cal_real_price

Style = Literal["ntfy", "telegram"]

class LPFormatter:
    def __init__(self, style: Style = "telegram"):
        self.style = style

    def convert_token_amount(self, raw_balance: int, decimals: int, precision: int = 4) -> str:
        value = convert_by_decimals(raw_balance=raw_balance, decimals=decimals, precision=precision)
        return f"{value:,.{precision}f}"

    def format_price(self, price, precision: int = 8) -> Decimal:
        return f"{price:,.{precision}f}"
    
    def calculate_lp_apr(self, lp, pos, precision: int = 3) -> str:
        max_arp = cal_lp_apr(lp=lp, precision=precision)
        div = abs(pos.tick_upper - pos.tick_lower)
        real_apr = max_arp / div
        return f"{real_apr:,.{precision}f}"

    def format_position(self, pos, lp, token0, token1, is_staked: bool = True) -> str:
        t0_amt = self.convert_token_amount(pos.staked0 if is_staked else pos.amount0, token0.decimals)
        t1_amt = self.convert_token_amount(pos.staked1 if is_staked else pos.amount1, token1.decimals)

        rewards = self.convert_token_amount(pos.emissions_earned, decimals=18)
        lp_apr = self.calculate_lp_apr(lp, pos, precision=3)

        price_now = convert_sqrtPriceX96_to_price(lp.sqrt_ratio, precision=8)
        price_upper = convert_sqrtPriceX96_to_price(pos.sqrt_ratio_upper, precision=8)
        price_lower = convert_sqrtPriceX96_to_price(pos.sqrt_ratio_lower, precision=8)
        (price_upper, price_now, price_lower) = cal_real_price(token0, token1, price_upper, price_now, price_lower)

        in_range = price_lower <= price_now <= price_upper

        price_now = self.format_price(price_now)
        price_upper = self.format_price(price_upper)
        price_lower = self.format_price(price_lower)
        range_status = "✅ In Range" if in_range else "⚠️ Out of Range"

        if self.style == "telegram":
            return (
                f"📊 *LP Summary*: {token0.symbol}/{token1.symbol}\n\n"

                f"💰 {token0.symbol}: `{t0_amt}`\n"
                f"💰 {token1.symbol}: `{t1_amt}`\n"
                f"🏆 Rewards: `{rewards} AERO`\n"
                f"💹 APR: `{lp_apr}%`\n\n"

                f"🔒 Staked: *{'✅ Yes' if is_staked else '❌ No'}*\n"
                f"🔍 Status: *{range_status}*\n\n"

                f"📈 Tick Range: `{pos.tick_lower} → {lp.tick} → {pos.tick_upper}`\n"
                f"🟢 Price Now: `{price_now}`\n"
                f"🔼 Upper Price: `{price_upper}`\n"
                f"🔽 Lower Price: `{price_lower}`"
            )
        
        elif self.style == "ntfy":
            return (
                f"📊 LP Summary: {token0.symbol}/{token1.symbol}\n\n"

                f"💰 {token0.symbol}: {t0_amt}\n"
                f"💰 {token1.symbol}: {t1_amt}\n"
                f"🏆 Rewards: {rewards} AERO\n"
                f"💹 APR: {lp_apr}%\n\n"

                f"🔒 Staked: {'✅ Yes' if is_staked else '❌ No'}\n"
                f"🔍 Status: {range_status}\n\n"

                f"📈 Tick Range: {pos.tick_lower} → {lp.tick} → {pos.tick_upper}\n"
                f"🟢 Price Now: {price_now}\n"
                f"🔼 Upper Price: {price_upper}\n"
                f"🔽 Lower Price: {price_lower}"
            )

        else:
            return "❌ Unsupported format style"

    def format_all(self, positions, lps, get_token_info_func) -> List[str]:
        return [
            self.format_position(pos, lps[idx], *get_token_info_func(lps[idx])) + "\n"
            for idx, pos in enumerate(positions)
        ]
