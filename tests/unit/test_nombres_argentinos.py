from app.game_context.infrastructure.nombres_argentinos import NOMBRES_ARGENTINOS, nombre_argentino


def test_taxon_con_nombre_argentino_usa_el_nombre_local():
    assert nombre_argentino(1289601, "Corúa Neotropical") == "Biguá"


def test_taxon_sin_nombre_argentino_conserva_el_de_inaturalist():
    assert nombre_argentino(999999999, "Nombre de iNaturalist") == "Nombre de iNaturalist"


def test_nombres_argentinos_son_ids_enteros_y_nombres_no_vacios():
    for taxon_id, nombre in NOMBRES_ARGENTINOS.items():
        assert isinstance(taxon_id, int)
        assert nombre.strip() == nombre and nombre


def test_nombres_argentinos_no_se_repiten_entre_taxones():
    # Dos aves con el mismo nombre harían ambigua la validación de respuestas
    nombres = list(NOMBRES_ARGENTINOS.values())
    assert len(nombres) == len(set(nombres))
