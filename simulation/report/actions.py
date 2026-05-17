from datetime import datetime, timezone
from math import floor
import textwrap
from coins.actions import get_evaluations, get_uptrend_coins
from coins.db.repository import CoinsRepository
from coins.model import Evaluation
from simulation.actions import get_market_recover_signs_over_total
from simulation.db.repository import SimulationsRepository
from simulation.model import Simulation, SimulationParams
from users.db.repository import UsersRepository


async def generate_general_bot_stats(
    users_repository: UsersRepository, sims_repository: SimulationsRepository
) -> str:
    users = users_repository.get_all_users()
    sims = [sims_repository.get_simulation(user.id) for user in users]
    sims = [sim for sim in sims if sim]

    if not sims:
        return "🤖 Bot is not running any simulation at this time. He's a bit bored."

    sims_in_panic = [sim for sim in sims if sim.panic_mode]
    ratio_sims_in_panic = len(sims_in_panic) / len(sims)

    return textwrap.dedent(
        f"<strong>🤖 Bot STATS</strong>"
        "\n\n\n"
        f"- Bot is taking care of {len(sims)} simulations at this time.\n\n"
        f"- {_print_semaphore(1 - ratio_sims_in_panic)} {len(sims_in_panic)} out of {len(sims)} are shielded, attempting to recover funds: {_print_bar(ratio_sims_in_panic)}\n"
        f"- {_print_semaphore(ratio_sims_in_panic)} {len(sims) - len(sims_in_panic)} out of {len(sims)} are running normally: {_print_bar(1 - ratio_sims_in_panic)}\n"
        "\n\n"
        f"- Avg. % revenue per day for normally running sims, in fiat: {_get_avg_percent_revenue(sims_repository, *[sim for sim in sims if not sim.panic_mode])}%\n"
        f"- Avg. % revenue per day for currently shielded sims, in fiat: {_get_avg_percent_revenue(sims_repository, *[sim for sim in sims if sim.panic_mode])}%\n"
        "\n\n"
        f"<strong>- Avg. % revenue for ALL currently running sims, in fiat: {_get_avg_percent_revenue(sims_repository, *sims)}</strong>\n"
    )


async def generate_market_status_report(
    coins_repository: CoinsRepository,
    sim_params: SimulationParams,
    timespan_in_hours: int,
) -> str:
    current_timestamp = int(datetime.timestamp(datetime.now(timezone.utc)))

    evaluations = await get_evaluations(
        coins_repository, current_timestamp, timespan_in_hours * 3600
    )
    uptrend_coins = await get_uptrend_coins(
        coins_repository,
        timespan_in_hours,
        current_timestamp,
        filter_by_confidence=False,
        evaluations=evaluations,
    )

    if not evaluations:
        return "⌛Bot doesn't have enough information to know market status. Give it some time"

    recovery_signs = (
        await get_market_recover_signs_over_total(
            coins_repository, sim_params, timespan_in_hours, *uptrend_coins
        )
        if uptrend_coins
        else (0, 3)
    )

    coins = await coins_repository.get_coins(*(coin for coin, _ in evaluations.items()))
    positive_confidence_coins = [
        coin
        for coin in coins
        if coin.get_confidence_for_closest_timespan(timespan_in_hours) > 0
        and coin.name in uptrend_coins
    ]

    ratio_uptrends = len(uptrend_coins) / max(1, len(evaluations))
    ratio_downtrends = len(
        [
            _
            for _, ev in evaluations.items()
            if ev[0] in (Evaluation.BEARISH, Evaluation.PEAK)
        ]
    ) / len(evaluations)
    ratio_neutral = len(
        [_ for _, ev in evaluations.items() if ev[0] == Evaluation.NEUTRAL]
    ) / len(evaluations)

    ratio_positive_confidences = len(positive_confidence_coins) / max(1, len(uptrend_coins))
    ratio_positive_confidences_strong = len(
        [
            coin
            for coin in positive_confidence_coins
            if coin.get_confidence_for_closest_timespan(timespan_in_hours)
            > sim_params.min_confidence_to_recover / 10
        ]
    ) / len(uptrend_coins)
    ratio_positive_confidences_for_panic_mode = len(
        [
            coin
            for coin in positive_confidence_coins
            if coin.get_confidence_for_closest_timespan(timespan_in_hours)
            > sim_params.min_confidence_to_recover
        ]
    ) / len(uptrend_coins)
    ratio_recovery_signs = recovery_signs[0] / recovery_signs[1]

    return textwrap.dedent(
        f"<strong>📝 Current market status for last {timespan_in_hours} hrs.</strong>"
        "\n\n\n"
        "Here you can check some metrics, the bot takes into account for "
        "handling your funds:"
        "\n\n\n"
        f"- {_print_semaphore(ratio_uptrends)} Uptrend coins: {_print_bar(ratio_uptrends)}\n"
        f"- {_print_semaphore(1 - ratio_downtrends)} Downtrend coins: {_print_bar(ratio_downtrends)}\n"
        f"- {_print_semaphore(min(ratio_neutral, 0.5))} Neutral coins: {_print_bar(ratio_neutral)}\n"
        "\n\n"
        f"- {_print_semaphore(ratio_positive_confidences)} Coins with confidence enough for full invest on them over total of uptrends: {_print_bar(ratio_positive_confidences_strong)}\n"
        f"- {_print_semaphore(ratio_positive_confidences)} Coins with confidence enough to attempt recovery from safe mode over total of uptrends: {_print_bar(ratio_positive_confidences_for_panic_mode)}\n"
        f"- {_print_semaphore(ratio_recovery_signs)} 🤖 Bot optimism percentage: {_print_bar(ratio_recovery_signs)}"
    )


def _print_bar(ratio_completed: float, length: int = 10) -> str:
    filled_chunk = "▓"
    unfilled_chunk = "░"

    proportion = ratio_completed * length
    filled_amount = floor(proportion)
    unfilled_amount = length - filled_amount

    return (
        filled_chunk * filled_amount
        + unfilled_chunk * unfilled_amount
        + f" - {round(ratio_completed * 100.0, 2)} %"
    )


def _print_semaphore(ratio: float) -> str:
    semaphore_colors = ["🔴", "🟡", "🟢"]
    return semaphore_colors[round((len(semaphore_colors) - 1) * ratio)]


def _get_avg_percent_revenue(
    sims_repository: SimulationsRepository, *sims: Simulation
) -> float:
    current_time = datetime.now(timezone.utc)

    revenue_percent_avg_per_day = 0

    for sim in sims:
        history = sims_repository.get_history(sim.user_id)
        first_time = datetime.fromtimestamp(min(history.keys()), timezone.utc)
        total_sim_days = (current_time - first_time).days

        revenue_percent_avg_per_day += (
            sim.updated_fiat_amount - sim.initial_fiat_amount
        ) / (sim.initial_fiat_amount * max(1, total_sim_days))

    return round(revenue_percent_avg_per_day / max(1, len(sims)), 2) * 100.0
