from __future__ import annotations

import re

from taller.domain.enums import FormaJuridica

# El orden importa: SAS antes que SA, etc.
_PATRONES: tuple[tuple[str, FormaJuridica], ...] = (
    (r"\bs\.?\s*a\.?\s*s\.?\b", FormaJuridica.SOCIEDAD_POR_ACCIONES_SIMPLIFICADA),
    (r"\bs\.?\s*r\.?\s*l\.?\b", FormaJuridica.SOCIEDAD_RESPONSABILIDAD_LIMITADA),
    (r"\bs\.?\s*en\s*c\.?\b|sociedad\s+en\s+comandita", FormaJuridica.SOCIEDAD_EN_COMANDITA),
    (r"\bs\.?\s*a\.?\b", FormaJuridica.SOCIEDAD_ANONIMA),
    (r"sociedad\s+colectiva", FormaJuridica.SOCIEDAD_COLECTIVA),
    (r"cooperativa|\bcoop\b", FormaJuridica.COOPERATIVA),
    (r"asociaci[oó]n\s+civil|\ba\.?\s*c\.?\b", FormaJuridica.ASOCIACION_CIVIL),
    (r"fundaci[oó]n", FormaJuridica.FUNDACION),
    (r"consorcio", FormaJuridica.CONSORCIO),
    (r"unipersonal", FormaJuridica.SOCIEDAD_UNIPERSONAL),
)


def inferir_forma_juridica(razon_social: str) -> FormaJuridica | None:
    """Deduce la forma jurídica a partir de la razón social (ej. 'ACME S.A.' → SA).

    Devuelve ``None`` si no se reconoce, para que se complete a mano.
    """
    texto = razon_social.strip().lower()
    for patron, forma in _PATRONES:
        if re.search(patron, texto):
            return forma
    return None
