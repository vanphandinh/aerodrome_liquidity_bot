from dataclasses import dataclass

@dataclass
class Lp:
    lp: str
    symbol: str
    decimals: int
    liquidity: int
    type: int
    tick: int
    sqrt_ratio: int
    token0: str
    reserve0: int
    staked0: int
    token1: str
    reserve1: int
    staked1: int
    gauge: str
    gauge_liquidity: int
    gauge_alive: bool
    fee: str
    bribe: str
    factory: str
    emissions: int
    emissions_token: str
    pool_fee: int
    unstaked_fee: int
    token0_fees: int
    token1_fees: int
    nfpm: str
    alm: str
    root: str

@dataclass
class Position:
    id: int
    lp: str
    liquidity: int
    staked: int
    amount0: int
    amount1: int
    staked0: int
    staked1: int
    unstaked_earned0: int
    unstaked_earned1: int
    emissions_earned: int
    tick_lower: int
    tick_upper: int
    sqrt_ratio_lower: int
    sqrt_ratio_upper: int
    alm: str

@dataclass
class Token:
    symbol: str
    decimals: int
