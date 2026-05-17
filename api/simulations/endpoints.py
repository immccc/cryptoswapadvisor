from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, status

from api.simulations.model import SimulationCreate, SimulationMessagesResponse, SimulationResponse
from coins.db.repository import CoinsRepository
from runner.dependencies import get_dependencies
from simulation.actions import get_fiat_balance, start_simulation, swap_cryptos
from simulation.db.config import SimulationConfig
from simulation.db.repository import SimulationsRepository
from webhooks.client import WebhookClient

router = APIRouter(prefix="/simulations", tags=["Simulations"])

@router.post(
    "", 
    response_model=SimulationResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Create a new simulation",
    responses={
        201: {"description": "Simulation created successfully"},
        401: {"description": "Unauthorized"},
        409: {"description": "Already created for this user"}
    },
)
async def create_simulation(request: Request, data: SimulationCreate):
    """
    Creates a new simulation instance with the initial balance and configured parameters.
    
    - **initial_fiat_amount**: Initial amount of money the bot starts with.
    - **timespan_in_hours**: Frequency at which the algorithm recalculates weights.
    - **operational_fee_percentage**: Percentage of commission per operation charged by the exchange.
    - **trader_pro**: If true, disables automatic loss protection mechanisms.
    - **webhook_endpoint**: URL to receive real-time updates about the simulation's performance and panic mode status.
    """

    coins_repository: CoinsRepository = get_dependencies().resolve(CoinsRepository)
    sims_repository: SimulationsRepository = get_dependencies().resolve(SimulationsRepository)
    sim_config: SimulationConfig = get_dependencies().resolve(SimulationConfig)

    webhook_client: WebhookClient = get_dependencies().resolve(WebhookClient)

    if sims_repository.get_simulation(request.state.user.id):
        raise HTTPException(status_code=409, detail="Already created for this user")

    sim = await start_simulation(
        coins_repository,
        sims_repository,
        sim_config.get(),
        request.state.user.id,
        data.initial_fiat_amount,
        data.timespan_in_hours,
        data.operational_fee_percentage,
        trader_pro=data.trader_pro,
        webhook_endpoint=data.webhook_endpoint,
    )

    webhook_client.create_endpoint(sim.user_id, sim.webhook_endpoint)

    return SimulationResponse(
        amount_per_coins=sim.amount_per_coins,
        ratio_per_coins=sim.ratio_per_coins,
        initial_fiat_amount=sim.initial_fiat_amount,
        timespan_in_hours=sim.timespan_in_hours,
        operational_fee_percentage=sim.operational_fee_percentage,
        last_rotated_at=sim.last_rotated_at,
        current_fiat_balance=await get_fiat_balance(
            coins_repository, int(datetime.now(timezone.utc).timestamp()), sim
        )
    )


@router.get(
    "", 
    response_model=SimulationResponse,
    summary="Get simulation status",
    responses={
        404: {"description": "Simulation not found for this user"},
        401: {"description": "Invalid API Key"}
    }
)
async def get_simulation(request: Request) -> SimulationResponse:
    """
    Returns the current state of a specific simulation, including performance and panic mode.
    """
    sims_repository: SimulationsRepository = get_dependencies().resolve(SimulationsRepository)
    coins_repository: CoinsRepository = get_dependencies().resolve(CoinsRepository)

    sim = sims_repository.get_simulation(request.state.user.id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found for this user")

    return SimulationResponse(
        amount_per_coins=sim.amount_per_coins,
        ratio_per_coins=sim.ratio_per_coins,
        last_rotated_at=sim.last_rotated_at,
        current_fiat_balance=await get_fiat_balance(
            coins_repository, int(datetime.now(timezone.utc).timestamp()), sim
        ),
        initial_fiat_amount=sim.initial_fiat_amount,
        timespan_in_hours=sim.timespan_in_hours,
        operational_fee_percentage=sim.operational_fee_percentage,
    )


@router.get(
    "/messages", 
    response_model=SimulationMessagesResponse,
    summary="Get messages sent from a simulation",
    responses={
        404: {"description": "Simulation not found"},
        401: {"description": "Invalid API Key"},
    }
)
async def get_simulation_sent_messages(request: Request, before: Optional[int] = None, after: Optional[int] = None):
    """
    Returns the current state of a specific simulation, including performance and panic mode.
    """
    sims_repository: SimulationsRepository = get_dependencies().resolve(SimulationsRepository)
    webhook_client: WebhookClient = get_dependencies().resolve(WebhookClient)
    
    sim = sims_repository.get_simulation(request.state.user.id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found for this user")

    return SimulationMessagesResponse(
        msgs=webhook_client.get_messages(sim.user_id, before, after)
    )

@router.post(
        "/force",
        response_model=SimulationResponse,
        status_code=status.HTTP_200_OK,
        summary="Force a simulation to rotate its portfolio and recalculate weights right away",
        responses={
            200: {"description": "Simulation updated successfully"},
            401: {"description": "Invalid API Key"},
            404: {"description": "Simulation not found for this user"},
        }
)
async def force_update(request: Request) -> SimulationResponse:
    """
    Forces a simulation to rotate its portfolio and recalculate weights right away, regardless of the configured timespan.
    """

    sims_repository: SimulationsRepository = get_dependencies().resolve(SimulationsRepository)
    coins_repository: CoinsRepository = get_dependencies().resolve(CoinsRepository)
    simulation_config: SimulationConfig = get_dependencies().resolve(SimulationConfig)

    sim = sims_repository.get_simulation(request.state.user.id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found for this user")
    
    
    await swap_cryptos(coins_repository, sims_repository, simulation_config.get(), sim)

    return SimulationResponse(
        amount_per_coins=sim.amount_per_coins,
        ratio_per_coins=sim.ratio_per_coins,
        last_rotated_at=sim.last_rotated_at,
        current_fiat_balance=await get_fiat_balance(
            coins_repository, int(datetime.now(timezone.utc).timestamp()), sim
        ),
        initial_fiat_amount=sim.initial_fiat_amount,
        timespan_in_hours=sim.timespan_in_hours,
        operational_fee_percentage=sim.operational_fee_percentage,
    )


@router.delete(
    "", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user's simulation. This action cannot be undone!",
    responses={
        400: {"description": "Confirmation is required"},
        401: {"description": "Invalid API Key"}
    }
)
async def delete_simulation(
    request: Request,
    confirm: bool = Query(False, description="Set to true to confirm simulation deletion, verifying you know what you are doing.")
):
    """
    Permanently deletes a simulation from the system. This action cannot be undone.
    """
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation is required")

    sims_repository: SimulationsRepository = get_dependencies().resolve(SimulationsRepository)
    webhook_client: WebhookClient = get_dependencies().resolve(WebhookClient)
    sim = sims_repository.get_simulation(request.state.user.id)
    if not sim:
        return

    sims_repository.remove_simulation(sim.user_id)
    webhook_client.clear_endpoints(sim.user_id)
