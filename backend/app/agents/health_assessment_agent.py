import logging
import json
from typing import Optional, Callable, Awaitable
from openai import AsyncOpenAI
from enum import Enum

from app.config import get_settings
from app.models.schemas import Language, CallSession, HealthRating, LimitationLevel
from app.services.session_manager import session_manager

logger = logging.getLogger(__name__)


class ConversationState(str, Enum):
    GREETING = "greeting"
    AUTHENTICATION = "authentication"
    INTRO_ASSESSMENT = "intro_assessment"
    QUESTION_GENERAL_HEALTH = "question_general_health"
    QUESTION_MODERATE_ACTIVITIES = "question_moderate_activities"
    QUESTION_CLIMBING_STAIRS = "question_climbing_stairs"
    SMS_OPT_IN = "sms_opt_in"
    PHONE_NUMBER_COLLECTION = "phone_number_collection"
    FAREWELL = "farewell"
    COMPLETED = "completed"


class HealthAssessmentAgent:
    """
    Conversational AI agent for health assessment calls.
    Handles the full conversation flow from authentication to SMS opt-in.
    """

    SYSTEM_PROMPT_EN = """You are Aldea, a friendly and professional AI health assessment assistant calling on behalf of Zappix. 
You are conducting an annual health assessment survey.

Your personality:
- Warm, empathetic, and patient
- Professional but conversational
- Clear and concise in your explanations
- Helpful and accommodating

Important guidelines:
- Keep responses brief and natural for voice conversation
- Wait for the user to respond before moving to the next question
- Be understanding if users need clarification
- Acknowledge their responses before asking the next question

Current conversation state: {state}
User's first name: {first_name}
Authentication status: {auth_status}
Collected answers: {answers}

Based on the current state and user's last response, provide your next spoken response.
Keep it conversational and appropriate for a phone call."""

    SYSTEM_PROMPT_ES = """Eres Aldea, un asistente de IA amigable y profesional para evaluaciones de salud, llamando en nombre de Zappix.
Estás realizando una encuesta de evaluación de salud anual.

Tu personalidad:
- Cálida, empática y paciente
- Profesional pero conversacional
- Clara y concisa en tus explicaciones
- Servicial y complaciente

Pautas importantes:
- Mantén las respuestas breves y naturales para una conversación telefónica
- Espera a que el usuario responda antes de pasar a la siguiente pregunta
- Sé comprensiva si los usuarios necesitan aclaraciones
- Reconoce sus respuestas antes de hacer la siguiente pregunta

Estado actual de la conversación: {state}
Nombre del usuario: {first_name}
Estado de autenticación: {auth_status}
Respuestas recopiladas: {answers}

Basándote en el estado actual y la última respuesta del usuario, proporciona tu siguiente respuesta hablada.
Mantenlo conversacional y apropiado para una llamada telefónica."""

    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        self.state = ConversationState.GREETING
        self.session: Optional[CallSession] = None
        self.detected_language: Optional[Language] = None
        self.conversation_history = []

    async def initialize(self, session: CallSession):
        """Initialize the agent with a session."""
        self.session = session
        self.detected_language = session.language
        self.state = ConversationState.GREETING

    def _get_system_prompt(self) -> str:
        """Get the appropriate system prompt based on language."""
        template = (
            self.SYSTEM_PROMPT_ES
            if self.detected_language == Language.SPANISH
            else self.SYSTEM_PROMPT_EN
        )

        auth_status = "Not authenticated"
        if self.session and self.session.authentication.authenticated:
            auth_status = "Authenticated"

        answers_summary = "None collected yet"
        if self.session:
            answers = []
            if self.session.answers.general_health:
                answers.append(f"General health: {self.session.answers.general_health}")
            if self.session.answers.moderate_activities_limitation:
                answers.append(f"Moderate activities: {self.session.answers.moderate_activities_limitation}")
            if self.session.answers.climbing_stairs_limitation:
                answers.append(f"Climbing stairs: {self.session.answers.climbing_stairs_limitation}")
            if answers:
                answers_summary = ", ".join(answers)

        return template.format(
            state=self.state.value,
            first_name=self.session.first_name if self.session else "User",
            auth_status=auth_status,
            answers=answers_summary
        )

    def _get_state_prompt(self) -> str:
        """Get specific instructions for the current conversation state."""
        is_spanish = self.detected_language == Language.SPANISH

        prompts = {
            ConversationState.GREETING: (
                f"Greet {self.session.first_name} and explain this is Zappix calling for their annual health assessment. "
                "Ask them to say 'Continue' or press 1 to continue."
                if not is_spanish else
                f"Saluda a {self.session.first_name} y explica que Zappix está llamando para su evaluación de salud anual. "
                "Pídele que diga 'Continuar' o presione 1 para continuar."
            ),
            ConversationState.AUTHENTICATION: (
                "Ask for their date of birth and zip code for verification. "
                "You need 2 out of 3: date of birth, zip code, or last 4 digits of SSN."
                if not is_spanish else
                "Pide su fecha de nacimiento y código postal para verificación. "
                "Necesitas 2 de 3: fecha de nacimiento, código postal, o últimos 4 dígitos del SSN."
            ),
            ConversationState.INTRO_ASSESSMENT: (
                "Explain that this assessment asks questions about their health to help them access the right benefits. "
                "Assure them their answers won't affect their benefits."
                if not is_spanish else
                "Explica que esta evaluación hace preguntas sobre su salud para ayudarles a acceder a los beneficios correctos. "
                "Asegúrales que sus respuestas no afectarán sus beneficios."
            ),
            ConversationState.QUESTION_GENERAL_HEALTH: (
                "Ask: Generally, how would you say your health is? Options are: "
                "Excellent (1), Very Good (2), Good (3), Fair (4), or Poor (5)."
                if not is_spanish else
                "Pregunta: En general, ¿cómo diría que está su salud? Las opciones son: "
                "Excelente (1), Muy Buena (2), Buena (3), Regular (4), o Mala (5)."
            ),
            ConversationState.QUESTION_MODERATE_ACTIVITIES: (
                "Ask: Does your health now limit you in doing moderate activities such as moving a table or bowling? "
                "Options: Limited a Lot (1), Limited a Little (2), or Not Limited at All (3)."
                if not is_spanish else
                "Pregunta: ¿Su salud ahora le limita en actividades moderadas como mover una mesa o jugar boliche? "
                "Opciones: Muy Limitado (1), Poco Limitado (2), o Sin Limitación (3)."
            ),
            ConversationState.QUESTION_CLIMBING_STAIRS: (
                "Ask: Does your health now limit you in climbing several flights of stairs? "
                "Options: Limited a Lot (1), Limited a Little (2), or Not Limited at All (3)."
                if not is_spanish else
                "Pregunta: ¿Su salud ahora le limita al subir varios tramos de escaleras? "
                "Opciones: Muy Limitado (1), Poco Limitado (2), o Sin Limitación (3)."
            ),
            ConversationState.SMS_OPT_IN: (
                "Explain they need to review and sign the form. Ask if they'd like to receive "
                "a text message with a link. Tell them to press 1 or say yes to opt in."
                if not is_spanish else
                "Explica que necesitan revisar y firmar el formulario. Pregunta si les gustaría recibir "
                "un mensaje de texto con un enlace. Diles que presionen 1 o digan sí para aceptar."
            ),
            ConversationState.PHONE_NUMBER_COLLECTION: (
                "Ask them to enter their cell phone number followed by the pound key."
                if not is_spanish else
                "Pídeles que ingresen su número de celular seguido de la tecla numeral."
            ),
            ConversationState.FAREWELL: (
                "Thank them for completing the assessment. Let them know they'll receive "
                "a text message shortly with a link to review and sign the form. Say goodbye warmly."
                if not is_spanish else
                "Agradéceles por completar la evaluación. Hazles saber que recibirán "
                "un mensaje de texto pronto con un enlace para revisar y firmar el formulario. Despídete cálidamente."
            ),
            ConversationState.COMPLETED: (
                "The conversation is complete. Say a brief goodbye if the user says anything else."
                if not is_spanish else
                "La conversación ha terminado. Di un breve adiós si el usuario dice algo más."
            )
        }

        return prompts.get(self.state, "Continue the conversation naturally.")

    async def process_user_input(
        self,
        user_input: str,
        detected_language: Optional[str] = None
    ) -> tuple[str, bool]:
        """
        Process user input and generate agent response.

        Args:
            user_input: The user's spoken/typed input
            detected_language: Language detected from STT (if any)

        Returns:
            Tuple of (response_text, is_call_complete)
        """
        # Update language if detected
        if detected_language and detected_language.startswith("es"):
            self.detected_language = Language.SPANISH
            if self.session:
                self.session.language = Language.SPANISH
                await session_manager.update_session(self.session)

        # Add user input to history
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })

        # Process based on state and input
        await self._process_state_transition(user_input)

        # Generate response
        response = await self._generate_response(user_input)

        # Add response to history
        self.conversation_history.append({
            "role": "assistant",
            "content": response
        })

        is_complete = self.state == ConversationState.COMPLETED

        return response, is_complete

    async def _process_state_transition(self, user_input: str):
        """Process state transitions based on user input."""
        input_lower = user_input.lower()

        if self.state == ConversationState.GREETING:
            if any(word in input_lower for word in ["continue", "continuar", "yes", "sí", "1", "one"]):
                self.state = ConversationState.AUTHENTICATION

        elif self.state == ConversationState.AUTHENTICATION:
            # Extract authentication info using LLM
            auth_info = await self._extract_auth_info(user_input)
            if auth_info:
                await session_manager.update_authentication(
                    self.session.session_id,
                    date_of_birth=auth_info.get("dob"),
                    zip_code=auth_info.get("zip"),
                    last_four_ssn=auth_info.get("ssn4")
                )
                # Refresh session
                self.session = await session_manager.get_session(self.session.session_id)

                if self.session.authentication.authenticated:
                    self.state = ConversationState.INTRO_ASSESSMENT

        elif self.state == ConversationState.INTRO_ASSESSMENT:
            if any(word in input_lower for word in ["continue", "continuar", "yes", "sí", "1", "one", "ok", "okay"]):
                self.state = ConversationState.QUESTION_GENERAL_HEALTH

        elif self.state == ConversationState.QUESTION_GENERAL_HEALTH:
            health = self._parse_health_response(input_lower)
            if health:
                await session_manager.update_answers(
                    self.session.session_id,
                    general_health=health
                )
                self.session = await session_manager.get_session(self.session.session_id)
                self.state = ConversationState.QUESTION_MODERATE_ACTIVITIES

        elif self.state == ConversationState.QUESTION_MODERATE_ACTIVITIES:
            limitation = self._parse_limitation_response(input_lower)
            if limitation:
                await session_manager.update_answers(
                    self.session.session_id,
                    moderate_activities=limitation
                )
                self.session = await session_manager.get_session(self.session.session_id)
                self.state = ConversationState.QUESTION_CLIMBING_STAIRS

        elif self.state == ConversationState.QUESTION_CLIMBING_STAIRS:
            limitation = self._parse_limitation_response(input_lower)
            if limitation:
                await session_manager.update_answers(
                    self.session.session_id,
                    climbing_stairs=limitation
                )
                self.session = await session_manager.get_session(self.session.session_id)
                self.state = ConversationState.SMS_OPT_IN

        elif self.state == ConversationState.SMS_OPT_IN:
            if any(word in input_lower for word in ["yes", "sí", "1", "one", "okay", "ok", "sure"]):
                self.state = ConversationState.PHONE_NUMBER_COLLECTION

        elif self.state == ConversationState.PHONE_NUMBER_COLLECTION:
            phone = self._extract_phone_number(user_input)
            if phone:
                await session_manager.set_sms_opt_in(self.session.session_id, phone)
                self.session = await session_manager.get_session(self.session.session_id)
                self.state = ConversationState.FAREWELL

        elif self.state == ConversationState.FAREWELL:
            self.state = ConversationState.COMPLETED
            await session_manager.mark_call_completed(self.session.session_id)

    def _parse_health_response(self, input_lower: str) -> Optional[str]:
        """Parse health rating from user response."""
        if any(word in input_lower for word in ["excellent", "excelente", "1", "one"]):
            return HealthRating.EXCELLENT.value
        elif any(word in input_lower for word in ["very good", "muy buena", "muy bien", "2", "two"]):
            return HealthRating.VERY_GOOD.value
        elif any(word in input_lower for word in ["good", "buena", "bien", "3", "three"]):
            return HealthRating.GOOD.value
        elif any(word in input_lower for word in ["fair", "regular", "4", "four"]):
            return HealthRating.FAIR.value
        elif any(word in input_lower for word in ["poor", "mala", "mal", "5", "five"]):
            return HealthRating.POOR.value
        return None

    def _parse_limitation_response(self, input_lower: str) -> Optional[str]:
        """Parse limitation level from user response."""
        if any(phrase in input_lower for phrase in ["limited a lot", "muy limitado", "1", "one", "a lot"]):
            return LimitationLevel.LIMITED_A_LOT.value
        elif any(phrase in input_lower for phrase in ["limited a little", "poco limitado", "2", "two", "a little"]):
            return LimitationLevel.LIMITED_A_LITTLE.value
        elif any(phrase in input_lower for phrase in ["not limited", "sin limitación", "no", "3", "three", "not at all"]):
            return LimitationLevel.NOT_LIMITED.value
        return None

    def _extract_phone_number(self, input_text: str) -> Optional[str]:
        """Extract phone number from user input."""
        import re
        # Remove non-numeric characters except +
        digits = re.sub(r'[^\d+]', '', input_text)
        # Check if it looks like a valid phone number (at least 10 digits)
        if len(digits) >= 10:
            return digits
        return None

    async def _extract_auth_info(self, user_input: str) -> Optional[dict]:
        """Use LLM to extract authentication information from natural language."""
        extraction_prompt = """Extract any authentication information from the user's response.
Return a JSON object with the following fields (use null for any not provided):
- dob: Date of birth in MM/DD/YYYY format
- zip: 5-digit zip code
- ssn4: Last 4 digits of social security number

User said: "{input}"

Return ONLY the JSON object, no other text."""

        try:
            response = await self.client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[{
                    "role": "user",
                    "content": extraction_prompt.format(input=user_input)
                }],
                temperature=0,
                max_tokens=100
            )

            result = response.choices[0].message.content.strip()
            # Parse JSON
            if result.startswith("```"):
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
            return json.loads(result)
        except Exception as e:
            logger.error(f"Failed to extract auth info: {e}")
            return None

    async def _generate_response(self, user_input: str) -> str:
        """Generate agent response using OpenAI."""
        system_prompt = self._get_system_prompt()
        state_prompt = self._get_state_prompt()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": f"Current task: {state_prompt}"}
        ]

        # Add conversation history (last 10 exchanges)
        messages.extend(self.conversation_history[-20:])

        try:
            response = await self.client.chat.completions.create(
                model=self.settings.openai_model,
                messages=messages,
                temperature=0.7,
                max_tokens=200
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            # Fallback responses
            if self.detected_language == Language.SPANISH:
                return "Lo siento, tuve un problema. ¿Podría repetir eso?"
            return "I'm sorry, I had a moment. Could you please repeat that?"

    async def get_initial_greeting(self) -> str:
        """Return the initial greeting for the call (pre-canned for fast response)."""
        if not self.session:
            raise ValueError("Session not initialized")

        # Use pre-canned greeting for fast response (avoids LLM latency)
        first_name = self.session.first_name
        
        if self.detected_language == Language.SPANISH:
            greeting = f"Hola {first_name}, soy Aldea llamando de parte de Zappix para su evaluación de salud anual. ¿Puede decir continuar para comenzar?"
        else:
            greeting = f"Hi {first_name}, this is Aldea calling from Zappix for your annual health assessment. Please say continue to get started."
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "assistant",
            "content": greeting
        })
        
        return greeting


# Factory function
def create_health_assessment_agent() -> HealthAssessmentAgent:
    return HealthAssessmentAgent()

