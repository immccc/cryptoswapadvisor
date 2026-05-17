from fastapi import APIRouter, HTTPException, Query, Request, status

from runner.dependencies import get_dependencies
from simulation.db.repository import SimulationsRepository
from users.db.repository import UsersRepository
from webhooks.client import WebhookClient

router = APIRouter(prefix="/users", tags=["Users"])

@router.delete(
    "", 
    status_code=status.HTTP_204_NO_CONTENT,

    summary="Delete user and so its running simulation, if any. This action cannot be undone!",
    responses={
        400: {"description": "Confirmation is required"},
        401: {"description": "Invalid API Key"}
    }
)
async def delete_user(
    request: Request,
    confirm: bool = Query(False, description="Set to true to confirm account deletion, verifying you know what you are doing.")
):
    """
    Permanently deletes a simulation from the system. This action cannot be undone.
    """
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation is required")

    sims_repository: SimulationsRepository = get_dependencies().resolve(SimulationsRepository)
    users_repository: UsersRepository = get_dependencies().resolve(UsersRepository)
    webhook_client: WebhookClient = get_dependencies().resolve(WebhookClient)

    sims_repository.remove_simulation(request.state.user.id)
    users_repository.remove_user(request.state.user.id)

    webhook_client.delete_application(request.state.user.id)
