
"""Identificacao de historicos por responsavel, malha e parametros."""

from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
DIRETORIO_HISTORICOS = RAIZ_PROJETO / "historicos"


def _texto(valor, campo):
    if valor is None:
        raise ValueError(f"{campo} e obrigatorio.")

    resultado = unicodedata.normalize("NFC", str(valor).strip())

    if not resultado:
        raise ValueError(f"{campo} nao pode ser vazio.")

    return resultado


def _numero(valor, campo):
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{campo} deve ser numerico.") from exc

    if not numero.is_finite():
        raise ValueError(f"{campo} deve ser finito.")

    if numero == 0:
        numero = Decimal(0)

    return format(numero.normalize(), "f")


def _slug(valor):
    texto = unicodedata.normalize("NFKD", valor)
    texto = texto.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "_", texto).strip("_")[:28] or "sem_nome"


def caminho_historico(responsavel, nome_malha, K, tau, T):
    responsavel = _texto(responsavel, "Responsavel")
    nome_malha = _texto(nome_malha, "Nome da malha")

    chave = [
        responsavel,
        nome_malha,
        _numero(K, "K"),
        _numero(tau, "tau"),
        _numero(T, "T")
    ]

    resumo = sha256(
        json.dumps(chave, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:20]

    nome_arquivo = (
        f"historico_{_slug(nome_malha)}__"
        f"{_slug(responsavel)}__{resumo}.xlsx"
    )

    return DIRETORIO_HISTORICOS / nome_arquivo
