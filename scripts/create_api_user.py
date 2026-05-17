import asyncio
import argparse
import os
from uuid import uuid4

from dotenv import load_dotenv
import requests
import resend

from runner.dependencies import get_dependencies, register_dependencies
from users.db.repository import UsersRepository
from users.model import User
from webhooks.client import WebhookClient

load_dotenv(override=True)

_OTS_URL = "https://onetimesecret.com"
_TTL= 172800 # 48 hours

async def _create_api_user(email: str):
    user_id = User.hash_api_key(email) # TODO Move hashing to a common place to avoid domain inconsitencies.    
    api_key = str(uuid4())

    users_repository: UsersRepository = get_dependencies().resolve(UsersRepository)
    users_repository.add_user(user_id, User.hash_api_key(api_key))

    # Create webhook application for the user
    webhook_client: WebhookClient = get_dependencies().resolve(WebhookClient)
    webhook_client.create_application(user_id)

    # Create a link with the secret
    res = requests.post(
        f"{_OTS_URL}/api/v2/secret/conceal",
        json={
            "secret": {
                "kind": "conceal",
                "secret": api_key,
                "ttl": str(_TTL)
            }
        }
    )
    if res.status_code != 200 :
        raise ValueError(f"Unable to create secret! Reason: {res.text}")

    secret_creation_result = res.json()

    api_key_link = f"https://onetimesecret.com/secret/{secret_creation_result['record']['secret']['identifier']}"

    html_email = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to XXXXXXX</title>
            <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600&family=Syne:wght@700&display=swap" rel="stylesheet">
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    background-color: #F5F0E8;
                    font-family: 'DM Sans', Arial, sans-serif;
                    font-size: 1rem;
                    font-weight: 400;
                    line-height: 1.6;
                    color: #2C2825;
                }}

                .email-container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #F5F0E8;
                }}

                .email-header {{
                    background-color: #7B2D3E;
                    padding: 1.5rem 2rem;
                    /* Reemplazo seguro para flexbox simple */
                    text-align: left; 
                }}

                .email-header__logo {{
                    width: 48px;
                    height: auto;
                    vertical-align: middle;
                }}

                .email-header__brand {{
                    font-family: 'Syne', Arial, sans-serif;
                    font-size: 1.35rem;
                    font-weight: 700;
                    color: #F5F0E8;
                    letter-spacing: 0.03em;
                    vertical-align: middle;
                    margin-left: 15px;
                }}

                .email-body {{
                    padding: 2.5rem 2rem;
                }}

                .email-body p {{
                    margin: 0 0 1.25rem;
                    color: #2C2825;
                }}

                .email-body a {{
                    color: #7B2D3E;
                    text-decoration: underline;
                    text-underline-offset: 2px;
                }}

                .email-body a:hover {{
                    color: #9B3D52;
                }}

                .email-link {{
                    display: inline-block;
                    margin: 0.5rem 0 1.5rem;
                    padding: 0.75rem 1.5rem;
                    background-color: #7B2D3E;
                    color: #F5F0E8 !important;
                    border-radius: 4px;
                    text-decoration: none;
                    font-weight: 600;
                }}

                .email-link:hover {{
                    background-color: #9B3D52;
                }}

                .email-disclaimer {{
                    margin-top: 2rem;
                    padding-top: 1.5rem;
                    border-top: 1px solid #C8C3BB;
                    font-size: 0.9rem;
                    color: #6B6560;
                }}

                .email-disclaimer strong {{
                    color: #7B2D3E;
                }}

                .email-footer {{
                    text-align: center;
                    padding: 1.5rem;
                    font-size: 0.85rem;
                    color: #8A8480;
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="email-header">
                    <img class="email-header__logo" src="https://xxxxxxx.com/assets/images/logo.svg" alt="XXXXXXX Logo">
                    <span class="email-header__brand">XXXXXXX</span>
                </div>
                <div class="email-body">
                    <p>Hello!</p>
                    <p>Thank you for your interest in the XXXXXXXXX API!</p>
                    <p>You have been granted access to our signals.</p>
                    <p>
                        You can find your private API key here:<br>
                        <a class="email-link" href="{api_key_link}">Retrieve Your API Key</a>
                    </p>

                    <p>
                        Use it by including the header <strong>X-API-Key</strong> in your requests. API documentation is available at <a href="https://xxxxxxx.com/api/v1/docs">https://xxxxxxx.com/api/v1/docs</a>
                    </p>
                    <p>
                        By using our API, you acknowledge that you have read and agree to our Terms of Service, which can be found at <a href="https://xxxxxxx.com/legal.html">https://xxxxxxx.com/legal.html</a>.
                    </p>
                    <p>You can unsubscribe by deleting your user account through API.</p>
                    <div class="email-disclaimer">
                        <strong>IMPORTANT:</strong> Please keep in mind that crypto trading carries inherent risks. Any use of our signals is at your own risk. We are not liable for any losses you may incur.
                    </div>
                    <p style="margin-top: 1.5rem;">Looking forward to hearing from you!</p>
                    <p>The XXXXXXXXX Team</p>
                </div>
                <div class="email-footer">
                    &copy; 2026 XXXXXXX. All rights reserved.
                </div>
            </div>
        </body>
        </html>
    """

    resend.api_key = os.getenv("RESEND_API_KEY")
    send_params: resend.Emails.SendParams = {
        "from": "XXXXXXXXX <hello@xxxxxxx.com>",
        "to": [email],
        "subject": "Welcome to XXXXXXXXX! Your access to premium API is ready!",
        "html": html_email,
    }

    resend.Emails.send(send_params)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a new API user.")
    parser.add_argument("-e", "--email", required=True, help="The email address of the user.")
    args = parser.parse_args()
    
    register_dependencies()
    asyncio.run(_create_api_user(args.email))