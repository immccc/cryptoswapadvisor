from datetime import datetime, timezone
import os
from typing import  Optional

import jwt
from svix import ApplicationIn, ListResponseMessageOut, MessageIn, Svix, SvixOptions
from svix.api import AppPortalAccessIn, EndpointIn, ListResponseEndpointOut, MessageCreateOptions, MessageListOptions

from webhooks.model import MessageSent

class WebhookClient:
    _jwt_secret: str = os.getenv("SVIX_JWT_SECRET")
    _server_url: str = os.getenv("SVIX_SERVER_URL")
    _svix: Svix

    def __init__(self):

        jwt_token = jwt.encode(
            {
                "iss": "svix-server",
                "sub": "org_23rb8YdGqMT0qIzpgGwdXfHirMu" # As stated in https://github.com/svix/svix-webhooks?tab=readme-ov-file#authentication
            },
            self._jwt_secret,
            algorithm="HS256",
        )

        self._svix = Svix(
            jwt_token,
            SvixOptions(
                server_url=self._server_url,
            )
        )


    def send(self, sender: str, event_type: str,payload: dict, idempotency_key: str = None):
        self._svix.message.create(
            app_id=sender,
            message_in=MessageIn(
                event_type=event_type,
                payload=payload
            ),
            options=MessageCreateOptions(
                idempotency_key=idempotency_key
            )
        )

    def create_endpoint(self, app_id: str, url: str):
        self._svix.endpoint.create(
            app_id=app_id,
            endpoint_in=EndpointIn(
                url=url
            )
        )

    def clear_endpoints(self, app_id: str):
        endpoints: ListResponseEndpointOut = self._svix.endpoint.list(app_id=app_id)
        for endpoint in endpoints.data:
            self._svix.endpoint.delete(app_id=app_id, endpoint_id=endpoint.id)


    def get_messages(self, app_id: str, before: Optional[int] = None, after: Optional[int] = None) -> list[MessageSent]:
        messages: ListResponseMessageOut = self._svix.message.list(
            app_id=app_id,
            options=MessageListOptions(
                after=datetime.fromtimestamp(after, timezone.utc) if after else None,
                before=datetime.fromtimestamp(before, timezone.utc) if before else None
            )
        )

        return [
            MessageSent(
                id=message.id,
                msg_type=message.event_type,
                content=message.payload,
                timestamp=int(message.timestamp.timestamp())
            )
            for message in messages.data]

    def create_application(self, app_id: str):
        app_in = ApplicationIn(
            name=app_id,
            uid=app_id,
        )
        self._svix.application.create(
            application_in=app_in
        )

        self._svix.authentication.app_portal_access(
            app_id=app_id,
            app_portal_access_in=AppPortalAccessIn(
                application=app_in
            )
        )

    def delete_application(self, app_id: str):
        self._svix.application.delete(app_id)
