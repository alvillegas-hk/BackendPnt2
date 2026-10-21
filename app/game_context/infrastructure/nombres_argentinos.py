import json
from pathlib import Path

# Nombres comunes usados en Argentina, indexados por taxon_id de iNaturalist.
# Se indexa por id y no por nombre: el nombre de iNaturalist puede cambiar, el id no.
# Los taxones que no estén en el archivo conservan el nombre que devuelve iNaturalist.
_RUTA = Path(__file__).parent / "nombres_argentinos.json"


def _cargar_nombres() -> dict[int, str]:
    with _RUTA.open(encoding="utf-8") as archivo:
        return {int(taxon_id): nombre for taxon_id, nombre in json.load(archivo).items()}


NOMBRES_ARGENTINOS = _cargar_nombres()


def nombre_argentino(taxon_id: int, nombre_inaturalist: str) -> str:
    """Devuelve el nombre argentino del taxón, o el de iNaturalist si no hay uno cargado."""
    return NOMBRES_ARGENTINOS.get(taxon_id, nombre_inaturalist)
