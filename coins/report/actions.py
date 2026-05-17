# TODO Move to simulations/report/actions.py!

from datetime import datetime, timezone
import io
import textwrap
import threading
from typing import Iterable

import numpy as np
from coins.model import RESERVE_DEFAULT_FIAT_CURRENCY
from simulation.db.repository import SimulationsRepository
from simulation.model import UPDATED_SIMULATION_FIAT_KEY, Simulation

import matplotlib

matplotlib.use("Agg")

from matplotlib.cm import get_cmap
import matplotlib.pyplot as plt


matplotlib_lock = threading.Lock()


def generate_coin_distribution_generic_report(sim: Simulation) -> str:
    distribution = "\n\n".join(
        [
            f" - {coin}: {amount}"
            for coin, amount in sim.amount_per_coins.items()
            if amount > 0 and coin != RESERVE_DEFAULT_FIAT_CURRENCY
        ]
        + [
            f" - Hold money in FIAT: {sim.amount_per_coins.get(RESERVE_DEFAULT_FIAT_CURRENCY, 0.0)}"
        ]
    )

    return textwrap.dedent(distribution)


def generate_simulation_historical_graph(
    repository: SimulationsRepository, sim: Simulation
) -> io.BytesIO:
    with matplotlib_lock:
        history = repository.get_history(sim.user_id)
        timestamps = sorted(history.keys())
        coins = sorted(
            {
                coin
                for coins_per_timestamp in history.values()
                for coin in coins_per_timestamp.keys()
            }
        )

        dates = [datetime.fromtimestamp(ts, timezone.utc) for ts in timestamps]

        coin_ratios_sorted_per_timestamp: dict[str, list[float]] = {
            coin: [history[timestamp].get(coin, 0.0) for timestamp in timestamps]
            for coin in coins
        }

        fig, (ax_balance, ax_dist) = plt.subplots(
            2,
            1,
            sharex=True,
            figsize=(8, 6),
        )

        _draw_balance_evolution(dates, coin_ratios_sorted_per_timestamp, ax_balance)
        _draw_portfolio_evolution(coins, dates, coin_ratios_sorted_per_timestamp, ax_dist)

        plt.title("Personal portfolio evolution over time")
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png")

        plt.close(fig)

        buf.seek(0)
        return buf

def _draw_portfolio_evolution(coins: Iterable[str], dates: Iterable[datetime], coin_ratios_sorted_per_timestamp: dict[str, list[float]], ax_dist):
    ax_dist.stackplot(
            dates,
            np.array(
                [
                    coin_ratios_sorted_per_timestamp[coin]
                    for coin in coins
                    if coin != UPDATED_SIMULATION_FIAT_KEY
                ]
            ),
            labels=[
                coin
                for coin in coins
                if coin != UPDATED_SIMULATION_FIAT_KEY
                and len(
                    [
                        coin
                        for coin in coin_ratios_sorted_per_timestamp[coin]
                        if coin > 0
                    ]
                )
            ],
            colors=get_cmap("tab20b")(np.linspace(0.3, 1, len(coins) - 1)),
        )
    ax_dist.set_ylabel("Ratio per coin")
    ax_dist.legend(loc="upper right", bbox_to_anchor=(0.5, 1.15), ncol=3)
    ax_dist.set_title("Coin distribution over time")

def _draw_balance_evolution(dates: Iterable[datetime], coin_ratios_sorted_per_timestamp: dict[str, list[float]], ax_balance):
    balances = coin_ratios_sorted_per_timestamp.get(UPDATED_SIMULATION_FIAT_KEY, [0 for _ in dates])

    # Remove redundant balance entries for clearer visualization
    dates_with_updated_balance = [dates[0]]
    balance_changed = [balances[0]]

    for i in range(1, len(dates)):
        balance = balances[i]
        if abs(balance - balances[i - 1]) >= 1e-8:
            dates_with_updated_balance.append(dates[i])
            balance_changed.append(balance)

    if len(balance_changed) == 1:
        dates_with_updated_balance.append(dates[-1])
        balance_changed.append(balances[-1])

    ax_balance.plot(
            dates_with_updated_balance,
            balance_changed,
            color="orange",
            linewidth=2,
        )
    ax_balance.set_title("Total balance in fiat over time")
    ax_balance.set_ylabel("FIAT Balance")
    ax_balance.grid(True, linestyle="--", alpha=0.3)
