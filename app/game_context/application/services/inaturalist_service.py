import httpx
import logging
import random
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)

INATURALIST_API_BASE_URL = "https://api.inaturalist.org/v1"


class Ave(BaseModel):
    """Modelo para un ave transformada (formato Vue - compatible con JuegoImagenes.vue)"""
    id: int
    nombre: str
    nombreCientifico: str
    foto: str
    atribucion: Optional[str] = None

    class Config:
        from_attributes = True


class AvesResponse(BaseModel):
    """Modelo para la respuesta de aves formateada para el juego"""
    total: int
    aves: List[Ave]


class GameAveOption(BaseModel):
    """Opción para una pregunta del juego"""
    id: int
    nombre: str
    nombreCientifico: str


class GameAveQuestion(BaseModel):
    """Pregunta del juego con opciones"""
    id: int
    nombre: str
    nombreCientifico: str
    foto: str
    atribucion: Optional[str] = None
    opciones: List[GameAveOption]


class GameAveResponse(BaseModel):
    """Respuesta con una pregunta del juego"""
    ave: GameAveQuestion


class BirdObservation(BaseModel):
    """Modelo para una observación de ave (formato iNaturalist)"""
    id: int
    name: str
    common_name: Optional[str]
    photos: List[str]

    class Config:
        from_attributes = True


class BirdsResponse(BaseModel):
    """Modelo para la respuesta de aves (observaciones)"""
    total_results: int
    page: int
    per_page: int
    observations: List[BirdObservation]


class INaturalistService:
    """Servicio para conectar con la API de iNaturalist"""

    @staticmethod
    def _generar_opciones(ave_correcta: Ave, todas_aves: List[Ave]) -> List[GameAveOption]:
        """Genera 4 opciones: 1 correcta + 3 falsas aleatorias"""
        aves_disponibles = [a for a in todas_aves if a.id != ave_correcta.id]

        if len(aves_disponibles) < 3:
            logger.warning("No hay suficientes aves para generar 3 opciones falsas")
            aves_falsas = aves_disponibles
        else:
            aves_falsas = random.sample(aves_disponibles, 3)

        opciones = [GameAveOption(id=ave_correcta.id, nombre=ave_correcta.nombre, nombreCientifico=ave_correcta.nombreCientifico)]
        opciones.extend([GameAveOption(id=a.id, nombre=a.nombre, nombreCientifico=a.nombreCientifico) for a in aves_falsas])

        random.shuffle(opciones)
        return opciones

    @staticmethod
    async def get_birds_for_game(
        place_id: int = 10434,
        locale: str = "es-AR"
    ) -> tuple[Ave, List[Ave]]:
        """
        Obtiene especies de aves formateadas para el juego.
        Retorna todas las aves para generar opciones en el backend.

        Args:
            place_id: ID del lugar (10434 = Buenos Aires, 7190 = Argentina)
            locale: Idioma/localización (es-AR = Español Argentina)

        Returns:
            Tupla con (ave_seleccionada, todas_aves)
        """
        try:
            params = {
                "taxon_id": 3,
                "place_id": place_id,
                "native": "true",
                "quality_grade": "research",
                "locale": locale,
                "per_page": 100,
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{INATURALIST_API_BASE_URL}/observations/species_counts",
                    params=params,
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

            aves_transformadas = []
            for resultado in data.get("results", []):
                try:
                    taxon = resultado.get("taxon", {})
                    default_photo = taxon.get("default_photo", {})

                    if default_photo and taxon.get("preferred_common_name"):
                        ave = Ave(
                            id=taxon.get("id"),
                            nombre=taxon.get("preferred_common_name", "Unknown"),
                            nombreCientifico=taxon.get("name", "Unknown"),
                            foto=default_photo.get("medium_url", ""),
                            atribucion=default_photo.get("attribution")
                        )
                        aves_transformadas.append(ave)
                except Exception as e:
                    logger.warning(f"Error procesando taxón {taxon.get('id')}: {e}")
                    continue

            if not aves_transformadas:
                raise ValueError("No se obtuvieron aves de iNaturalist")

            ave_seleccionada = random.choice(aves_transformadas)
            return ave_seleccionada, aves_transformadas

        except httpx.HTTPError as e:
            logger.error(f"Error conectando con iNaturalist: {e}")
            raise
        except Exception as e:
            logger.error(f"Error procesando respuesta de iNaturalist: {e}")
            raise

    @staticmethod
    def generar_pregunta_juego(ave_correcta: Ave, todas_aves: List[Ave]) -> GameAveQuestion:
        """
        Genera una pregunta formateada para el juego.

        Args:
            ave_correcta: El ave correcta
            todas_aves: Todas las aves disponibles para generar falsas

        Returns:
            GameAveQuestion con opciones generadas
        """
        opciones = INaturalistService._generar_opciones(ave_correcta, todas_aves)

        return GameAveQuestion(
            id=ave_correcta.id,
            nombre=ave_correcta.nombre,
            nombreCientifico=ave_correcta.nombreCientifico,
            foto=ave_correcta.foto,
            atribucion=ave_correcta.atribucion,
            opciones=opciones
        )

    @staticmethod
    def validar_respuesta(ave_id: int, respuesta_usuario: str, ave_correcta_nombre: str) -> tuple[bool, int]:
        """
        Valida la respuesta del jugador.

        Args:
            ave_id: ID del ave de la pregunta
            respuesta_usuario: Respuesta del usuario
            ave_correcta_nombre: Nombre correcto del ave

        Returns:
            Tupla (es_correcta, puntos)
        """
        es_correcta = respuesta_usuario.lower().strip() == ave_correcta_nombre.lower().strip()
        puntos = 10 if es_correcta else 0

        return es_correcta, puntos

    @staticmethod
    async def get_birds_argentina(
        per_page: int = 100,
        page: int = 1,
        quality_grade: str = "research"
    ) -> BirdsResponse:
        """
        Obtiene observaciones de aves de Argentina.

        Args:
            per_page: Cantidad de resultados por página (max 100)
            page: Número de página
            quality_grade: Calidad de la observación (research, needs_id, casual)

        Returns:
            BirdsResponse con las observaciones procesadas
        """
        try:
            params = {
                "place_id": 7190,  # Argentina
                "iconic_taxa": "Aves",
                "photos": "true",
                "per_page": min(per_page, 100),
                "page": page,
                "quality_grade": quality_grade,
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{INATURALIST_API_BASE_URL}/observations",
                    params=params,
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

            # Procesar observaciones
            observations = []
            for obs in data.get("results", []):
                try:
                    taxon = obs.get("taxon", {})
                    photos = [p.get("url") for p in obs.get("photos", []) if p.get("url")]

                    if taxon and photos:  # Solo incluir si tiene taxón y fotos
                        bird = BirdObservation(
                            id=obs.get("id"),
                            name=taxon.get("name", "Unknown"),
                            common_name=taxon.get("preferred_common_name"),
                            photos=photos
                        )
                        observations.append(bird)
                except Exception as e:
                    logger.warning(f"Error procesando observación {obs.get('id')}: {e}")
                    continue

            return BirdsResponse(
                total_results=data.get("total_results", 0),
                page=page,
                per_page=min(per_page, 100),
                observations=observations
            )

        except httpx.HTTPError as e:
            logger.error(f"Error conectando con iNaturalist: {e}")
            raise
        except Exception as e:
            logger.error(f"Error procesando respuesta de iNaturalist: {e}")
            raise

    @staticmethod
    async def get_taxa_suggestions(
        q: str,
        place_id: int = 7190,
        taxon_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Obtiene sugerencias de taxa (especies) de iNaturalist.

        Args:
            q: Query de búsqueda
            place_id: ID del lugar (7190 = Argentina)
            taxon_id: ID opcional del taxón padre (Aves)

        Returns:
            Respuesta de sugerencias
        """
        try:
            params = {
                "q": q,
                "place_id": place_id,
            }

            if taxon_id:
                params["taxon_id"] = taxon_id

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{INATURALIST_API_BASE_URL}/taxa/autocomplete",
                    params=params,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error en autocomplete de iNaturalist: {e}")
            raise

    @staticmethod
    async def get_observation_by_id(observation_id: int) -> Dict[str, Any]:
        """
        Obtiene una observación específica de iNaturalist.

        Args:
            observation_id: ID de la observación

        Returns:
            Datos de la observación
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{INATURALIST_API_BASE_URL}/observations/{observation_id}",
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error obteniendo observación {observation_id}: {e}")
            raise
