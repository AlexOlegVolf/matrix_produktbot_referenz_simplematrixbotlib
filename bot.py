"""Produktbot: private, unverschluesselte Matrix-Nachrichten an n8n weiterleiten."""

import argparse
import logging
from pathlib import Path

import aiohttp
import simplematrixbotlib as botlib
from nio import InviteMemberEvent


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EEApp-Produktbot")
    parser.add_argument("--homeserver", required=True)
    parser.add_argument("--bot-user", required=True)
    parser.add_argument("--allowed-server", required=True)
    parser.add_argument("--webhook-url", required=True)
    parser.add_argument("--matrix-token-file", required=True)
    parser.add_argument("--webhook-key-file", required=True)
    return parser.parse_args()


def read_secret(file_name: str) -> str:
    value = Path(file_name).read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError(f"Leere Geheimnisdatei: {file_name}")
    return value


def is_allowed_user(user_id: str, allowed_server: str) -> bool:
    """Erlaubt nur reguläre Matrix-IDs des Firmen-Matrix-Servers."""
    return user_id.startswith("@") and user_id.rsplit(":", 1)[-1].lower() == allowed_server.lower()


async def call_n8n(webhook_url: str, webhook_key: str, payload: dict) -> str:
    timeout = aiohttp.ClientTimeout(total=45)
    headers = {"X-Bot-Key": webhook_key}
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(webhook_url, headers=headers, json=payload) as response:
            response.raise_for_status()
            result = await response.json()

    if result.get("room_id") != payload["room_id"] or result.get("request_id") != payload["request_id"]:
        raise ValueError("n8n-Antwort gehoert nicht zur aktuellen Anfrage")
    answer = result.get("antwort")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("n8n hat keine Antwort im Feld 'antwort' geliefert")
    return answer.strip()


def main() -> None:
    args = arguments()
    matrix_token = read_secret(args.matrix_token_file)
    webhook_key = read_secret(args.webhook_key_file)

    config = botlib.Config()
    config.encryption_enabled = False
    config.join_on_invite = False  # Einladungen werden unten gezielt behandelt.

    creds = botlib.Creds(
        args.homeserver,
        args.bot_user,
        access_token=matrix_token,
        session_stored_file=None,
        device_name="EEApp Produktbot",
    )
    bot = botlib.Bot(creds, config)

    @bot.listener.on_custom_event(InviteMemberEvent)
    async def accept_employee_invite(room, event) -> None:
        if event.membership != "invite" or not is_allowed_user(event.sender, args.allowed_server):
            logging.warning("Einladung von nicht zugelassenem Konto ignoriert.")
            return
        await bot.async_client.join(room.room_id)
        logging.info("Private Einladung angenommen: %s", room.room_id)

    @bot.listener.on_message_event
    async def product_search(room, message) -> None:
        if message.sender == args.bot_user or not is_allowed_user(message.sender, args.allowed_server):
            return
        if room.encrypted or room.member_count != 2:
            logging.warning("Nachricht ausserhalb eines privaten, unverschluesselten Chats ignoriert: %s", room.room_id)
            return

        query = message.body.strip()
        if not query:
            return
        if len(query) > 500:
            await bot.api.send_text_message(room.room_id, "Der Suchbegriff ist zu lang. Bitte sende maximal 500 Zeichen.")
            return

        logging.info("Produktsuche angefordert: Raum %s", room.room_id)
        try:
            answer = await call_n8n(
                args.webhook_url,
                webhook_key,
                {
                    "suchbegriff": query,
                    "room_id": room.room_id,
                    "sender": message.sender,
                    "request_id": message.event_id,
                },
            )
        except Exception:
            logging.exception("Produktsuche fehlgeschlagen: Raum %s", room.room_id)
            answer = "Die Produktsuche ist gerade nicht verfuegbar. Bitte versuche es erneut."

        await bot.api.send_text_message(room.room_id, answer)

    bot.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
