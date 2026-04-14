import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _normalizar_numero(numero: str) -> str:
    """
    Convierte un número de teléfono ecuatoriano a formato internacional E.164.
    - Elimina espacios, guiones, paréntesis.
    - Si empieza con 0 (ej. 0991234567) → 593991234567
    - Si ya tiene 593 lo deja igual.
    - Si tiene + lo quita.
    """
    limpio = re.sub(r'[\s\-\(\)\+]', '', str(numero))
    if limpio.startswith('593'):
        return limpio
    if limpio.startswith('0'):
        return '593' + limpio[1:]
    # Asumir Ecuador si no tiene código de país
    return '593' + limpio


# ──────────────────────────────────────────────
# Cliente Evolution API
# ──────────────────────────────────────────────

class EvolutionAPI:
    """
    Cliente para Evolution API (WhatsApp Business).

    Documentación: https://doc.evolution-api.com/v2/api-reference
    Endpoint base:  {EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE_NAME}
    Headers:        apikey: {EVOLUTION_API_KEY}
    """

    TIMEOUT = 10  # segundos

    def __init__(self):
        self.base_url = getattr(settings, 'EVOLUTION_API_URL', '').rstrip('/')
        self.api_key = getattr(settings, 'EVOLUTION_API_KEY', '')
        self.instance = getattr(settings, 'EVOLUTION_INSTANCE_NAME', 'default')

    def _configurado(self) -> bool:
        if not self.base_url or not self.api_key:
            logger.warning(
                'EvolutionAPI no configurado. '
                'Define EVOLUTION_API_URL y EVOLUTION_API_KEY en .env'
            )
            return False
        return True

    def send_text(self, numero: str, texto: str) -> bool:
        """
        Envía un mensaje de texto plano vía WhatsApp.

        Args:
            numero: Número destino (cualquier formato, se normaliza automáticamente).
            texto:  Cuerpo del mensaje.

        Returns:
            True si Evolution API responde 200/201, False en cualquier otro caso.
            Nunca lanza excepción — los errores se loguean y retornan False.
        """
        if not self._configurado():
            return False

        numero_formateado = _normalizar_numero(numero)
        url = f'{self.base_url}/message/sendText/{self.instance}'
        payload = {'number': numero_formateado, 'text': texto}
        headers = {'apikey': self.api_key, 'Content-Type': 'application/json'}

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=self.TIMEOUT)
            if response.status_code in (200, 201):
                logger.info(f'WhatsApp enviado a {numero_formateado}')
                return True
            logger.error(
                f'Evolution API error {response.status_code} '
                f'→ {numero_formateado}: {response.text[:200]}'
            )
            return False
        except requests.exceptions.ConnectionError:
            logger.error(f'Evolution API sin conexión al enviar a {numero_formateado}')
            return False
        except requests.exceptions.Timeout:
            logger.error(f'Evolution API timeout al enviar a {numero_formateado}')
            return False
        except Exception as exc:
            logger.error(f'Evolution API error inesperado: {exc}')
            return False

    def send_template(self, numero: str, template: str, context: dict) -> bool:
        """
        Renderiza `template` con `context` usando str.format_map y llama a send_text.
        Ejemplo:
            template = "Hola {nombre}, tu nota en {materia} es {nota}."
            context  = {"nombre": "Ana", "materia": "Piano", "nota": 8.5}
        """
        try:
            texto = template.format_map(context)
        except KeyError as exc:
            logger.error(f'send_template: falta clave en context: {exc}')
            return False
        return self.send_text(numero, texto)

    # ──────────────────────────────────────────
    # Verificación de instancia
    # ──────────────────────────────────────────

    def verificar_conexion(self) -> dict:
        """
        Llama a GET /instance/connectionState/{instance}.
        Útil para el endpoint de prueba.
        Retorna dict con 'ok': bool y 'detalle': str.
        """
        if not self._configurado():
            return {'ok': False, 'detalle': 'No configurado'}
        url = f'{self.base_url}/instance/connectionState/{self.instance}'
        headers = {'apikey': self.api_key}
        try:
            response = requests.get(url, headers=headers, timeout=self.TIMEOUT)
            data = response.json() if response.content else {}
            ok = response.status_code == 200
            return {'ok': ok, 'detalle': data}
        except Exception as exc:
            return {'ok': False, 'detalle': str(exc)}


# Instancia singleton — importar desde aquí
evolution = EvolutionAPI()
