import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional
import io

from app.config import get_settings
from app.models.schemas import CallSession, Language

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email notifications."""

    def __init__(self):
        self.settings = get_settings()

    def _create_form_html(self, session: CallSession) -> str:
        """Create HTML content for the completed form email."""
        lang = session.language

        if lang == Language.SPANISH:
            title = "Formulario de Evaluación de Salud Completado"
            labels = {
                "name": "Nombre",
                "date_of_birth": "Fecha de Nacimiento",
                "zip_code": "Código Postal",
                "general_health": "Estado de Salud General",
                "moderate_activities": "Limitación en Actividades Moderadas",
                "climbing_stairs": "Limitación al Subir Escaleras",
                "language": "Idioma Preferido",
                "session_id": "ID de Sesión"
            }
        else:
            title = "Completed Health Assessment Form"
            labels = {
                "name": "Name",
                "date_of_birth": "Date of Birth",
                "zip_code": "Zip Code",
                "general_health": "General Health Status",
                "moderate_activities": "Moderate Activities Limitation",
                "climbing_stairs": "Climbing Stairs Limitation",
                "language": "Preferred Language",
                "session_id": "Session ID"
            }

        # Format answers for display
        health_display = {
            "excellent": "Excellent" if lang == Language.ENGLISH else "Excelente",
            "very_good": "Very Good" if lang == Language.ENGLISH else "Muy Bueno",
            "good": "Good" if lang == Language.ENGLISH else "Bueno",
            "fair": "Fair" if lang == Language.ENGLISH else "Regular",
            "poor": "Poor" if lang == Language.ENGLISH else "Malo"
        }

        limitation_display = {
            "limited_a_lot": "Limited a Lot" if lang == Language.ENGLISH else "Muy Limitado",
            "limited_a_little": "Limited a Little" if lang == Language.ENGLISH else "Poco Limitado",
            "not_limited": "Not Limited at All" if lang == Language.ENGLISH else "Sin Limitación"
        }

        general_health = health_display.get(
            session.answers.general_health, "N/A"
        ) if session.answers.general_health else "N/A"

        moderate_activities = limitation_display.get(
            session.answers.moderate_activities_limitation, "N/A"
        ) if session.answers.moderate_activities_limitation else "N/A"

        climbing_stairs = limitation_display.get(
            session.answers.climbing_stairs_limitation, "N/A"
        ) if session.answers.climbing_stairs_limitation else "N/A"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #1a365d 0%, #2d5a87 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 8px 8px 0 0;
                    text-align: center;
                }}
                .content {{
                    background: #f8f9fa;
                    padding: 20px;
                    border: 1px solid #e9ecef;
                }}
                .field {{
                    margin-bottom: 15px;
                    padding: 10px;
                    background: white;
                    border-radius: 4px;
                    border-left: 4px solid #2d5a87;
                }}
                .label {{
                    font-weight: bold;
                    color: #1a365d;
                    font-size: 12px;
                    text-transform: uppercase;
                }}
                .value {{
                    font-size: 16px;
                    margin-top: 5px;
                }}
                .footer {{
                    background: #1a365d;
                    color: white;
                    padding: 15px;
                    text-align: center;
                    font-size: 12px;
                    border-radius: 0 0 8px 8px;
                }}
                .signature-box {{
                    border: 2px dashed #2d5a87;
                    padding: 20px;
                    text-align: center;
                    background: white;
                    margin-top: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{title}</h1>
                <p>Zappix + Aldea AI Demo</p>
            </div>
            <div class="content">
                <div class="field">
                    <div class="label">{labels['name']}</div>
                    <div class="value">{session.first_name}</div>
                </div>
                <div class="field">
                    <div class="label">{labels['date_of_birth']}</div>
                    <div class="value">{session.authentication.date_of_birth or 'N/A'}</div>
                </div>
                <div class="field">
                    <div class="label">{labels['zip_code']}</div>
                    <div class="value">{session.authentication.zip_code or 'N/A'}</div>
                </div>
                <div class="field">
                    <div class="label">{labels['general_health']}</div>
                    <div class="value">{general_health}</div>
                </div>
                <div class="field">
                    <div class="label">{labels['moderate_activities']}</div>
                    <div class="value">{moderate_activities}</div>
                </div>
                <div class="field">
                    <div class="label">{labels['climbing_stairs']}</div>
                    <div class="value">{climbing_stairs}</div>
                </div>
                <div class="field">
                    <div class="label">{labels['language']}</div>
                    <div class="value">{'Spanish' if lang == Language.SPANISH else 'English'}</div>
                </div>
                <div class="signature-box">
                    <div class="label">✓ Signature Captured</div>
                </div>
                <div class="field" style="margin-top: 20px;">
                    <div class="label">{labels['session_id']}</div>
                    <div class="value" style="font-size: 12px; font-family: monospace;">{session.session_id}</div>
                </div>
            </div>
            <div class="footer">
                <p>This form was completed via the Zappix + Aldea AI Health Assessment Demo</p>
                <p>© 2024 Zappix Inc. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        return html

    async def send_completed_form(
        self,
        session: CallSession,
        signature_image: Optional[bytes] = None
    ) -> bool:
        """Send the completed form to the notification email."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Health Assessment Form Completed - {session.first_name} ({session.session_id[:8]})"
            msg["From"] = f"Zappix Demo <noreply@aldea.ai>"
            msg["To"] = self.settings.notification_email

            # Create HTML content
            html_content = self._create_form_html(session)
            msg.attach(MIMEText(html_content, "html"))

            # Attach signature image if provided
            if signature_image:
                part = MIMEBase("image", "png")
                part.set_payload(signature_image)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename=signature_{session.session_id[:8]}.png"
                )
                msg.attach(part)

            # Send email
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as server:
                server.starttls()
                server.login(self.settings.smtp_user, self.settings.smtp_password)
                server.send_message(msg)

            logger.info(f"Sent completed form email for session {session.session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email for session {session.session_id}: {e}")
            return False


# Singleton instance
email_service = EmailService()

