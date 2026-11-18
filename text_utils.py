"""Funcoes simples para padronizar textos cadastrados no estoque."""
import unicodedata


def normalize_text(value):
    """Converte para minusculas, remove acentos e normaliza espacos."""
    text = str(value or "").strip()
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(
        character for character in decomposed
        if not unicodedata.combining(character)
    )
    return " ".join(without_accents.lower().split())
