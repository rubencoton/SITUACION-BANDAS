from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage
import logging
from pathlib import Path
import smtplib

from src.config import Settings


@dataclass(slots=True)
class EmailSendResult:
    sent: bool
    dry_run: bool
    reason: str
    total_recipients: int


class BaseEmailProvider:
    def send(
        self,
        settings: Settings,
        recipients: list[str],
        subject: str,
        body: str,
        attachments: list[Path] | None = None,
    ) -> None:
        raise NotImplementedError


class DryRunEmailProvider(BaseEmailProvider):
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def send(
        self,
        settings: Settings,
        recipients: list[str],
        subject: str,
        body: str,
        attachments: list[Path] | None = None,
    ) -> None:
        self.logger.info(
            "DRY-RUN correo | from=%s | to=%s | subject=%s | attachments=%s",
            settings.email_from,
            recipients,
            subject,
            [str(p) for p in attachments or []],
        )
        self.logger.info("Body preview (first 200): %s", body[:200])


class SmtpEmailProvider(BaseEmailProvider):
    def send(
        self,
        settings: Settings,
        recipients: list[str],
        subject: str,
        body: str,
        attachments: list[Path] | None = None,
    ) -> None:
        if not settings.email_smtp_host:
            raise RuntimeError("EMAIL_SMTP_HOST no configurado.")

        msg = EmailMessage()
        msg["From"] = settings.email_from
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
        msg.set_content(body)

        for attachment in attachments or []:
            data = attachment.read_bytes()
            msg.add_attachment(
                data,
                maintype="application",
                subtype="pdf",
                filename=attachment.name,
            )

        with smtplib.SMTP(settings.email_smtp_host, settings.email_smtp_port, timeout=30) as smtp:
            if settings.email_use_tls:
                smtp.starttls()
            if settings.email_smtp_user and settings.email_smtp_password:
                smtp.login(settings.email_smtp_user, settings.email_smtp_password)
            smtp.send_message(msg)


class EmailService:
    def __init__(self, settings: Settings, logger: logging.Logger):
        self.settings = settings
        self.logger = logger
        self.dry_provider = DryRunEmailProvider(logger)
        self.smtp_provider = SmtpEmailProvider()

    def send_manual(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        attachments: list[Path] | None = None,
        dry_run: bool = True,
        confirm_live: bool = False,
    ) -> EmailSendResult:
        if not recipients:
            return EmailSendResult(
                sent=False,
                dry_run=True,
                reason="No hay destinatarios.",
                total_recipients=0,
            )

        if dry_run:
            self.dry_provider.send(
                self.settings, recipients, subject, body, attachments=attachments
            )
            return EmailSendResult(
                sent=False,
                dry_run=True,
                reason="Dry-run ejecutado. No se envio correo real.",
                total_recipients=len(recipients),
            )

        if not self.settings.email_enabled:
            return EmailSendResult(
                sent=False,
                dry_run=False,
                reason="EMAIL_ENABLED=false. Envio real bloqueado por seguridad.",
                total_recipients=len(recipients),
            )

        if self.settings.email_require_confirmation and not confirm_live:
            return EmailSendResult(
                sent=False,
                dry_run=False,
                reason="Falta confirmacion explicita (--confirm-live).",
                total_recipients=len(recipients),
            )

        if self.settings.email_provider != "smtp":
            return EmailSendResult(
                sent=False,
                dry_run=False,
                reason=f"Proveedor no soportado: {self.settings.email_provider}",
                total_recipients=len(recipients),
            )

        self.smtp_provider.send(
            self.settings, recipients, subject, body, attachments=attachments
        )
        return EmailSendResult(
            sent=True,
            dry_run=False,
            reason="Correo enviado correctamente.",
            total_recipients=len(recipients),
        )
