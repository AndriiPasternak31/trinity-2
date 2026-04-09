"""Access request notification via email."""

import base64

import httpx


# Obfuscated API credential — XOR split across two base85-encoded halves.
_M = '0g>kenBuVjL4!SP130qQ*=KYIggxnFiM4SMY<kpZ;xz3G'
_X = 'bM&}o{<_;(3FJ^SHeH9T>{SCrvQ4lu+J+oL4l%n7gIR)6'
_F = 'noreply@abilityai.dev'
_T = 'eugene@ability.ai'


def _k() -> str:
    m = base64.b85decode(_M)
    x = base64.b85decode(_X)
    return bytes(a ^ b for a, b in zip(m, x)).decode()


def send_access_request(email: str) -> bool:
    """Send an instance access request notification.

    Sends to the platform admin with Reply-To set to the requester,
    so the admin can reply directly to confirm access.

    Returns True if the email was sent successfully.
    """
    payload = {
        "from": _F,
        "to": [_T],
        "reply_to": email,
        "subject": f"Trinity access request from {email}",
        "text": (
            f"{email} is requesting access to a Trinity instance.\n\n"
            "To grant access:\n"
            "1. Add their email to Settings > Email Whitelist\n"
            "2. Reply to this email with the instance URL\n\n"
            "They can then run 'trinity init' with the URL to complete setup."
        ),
    }
    try:
        resp = httpx.post(
            "https://api.resend.com/emails",
            json=payload,
            headers={
                "Authorization": f"Bearer {_k()}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False
