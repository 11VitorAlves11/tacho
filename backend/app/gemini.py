"""Importação inteligente via Gemini (TODO.md): (a) fallback de extração
quando o `recipe-scrapers` falha ou devolve resultado incompleto; (b)
importação por foto (Vision). Opcional — sem `Settings.gemini_api_key`,
`is_available()` devolve False e quem chamar isto tem de tratar isso como
"sem sugestão", nunca como erro.

⚠️ NÃO TESTADO CONTRA A API REAL nesta sessão de desenvolvimento — sem
chave disponível. TODO.md tem o aviso completo; validar cedo com casos
reais (URLs que o recipe-scrapers falha, fotos de livros PT) antes de
confiar nisto em produção. Mesmo risco já identificado no PRD para dados
de saúde (nutrição): um LLM pode "corrigir" quantidades/texto
silenciosamente — por isso isto nunca grava sozinho, só alimenta um
rascunho para revisão manual (ver schemas.RecipeExtraction)."""

from google import genai
from google.genai import types

from app import schemas
from app.config import Settings

_MODEL = "gemini-flash-latest"

_EXTRACTION_PROMPT = (
    "Extrai esta receita de cozinha para JSON estruturado, em português "
    "europeu. Campos: title (obrigatório), description (opcional, 1-2 "
    "frases), servings (número de porções, inteiro, se indicado), "
    "prep_minutes/cook_minutes (inteiros, minutos, se indicados), "
    "ingredients (lista de {name, quantity, unit, is_header} — quantity "
    "é número decimal, ex. 0.5 para meia unidade; is_header=true só para "
    "linhas que são título de secção, ex. 'Para o recheio', sem quantity/"
    "unit nesse caso), steps (lista de {instruction, duration_minutes} — "
    "duration_minutes só se o passo mencionar um tempo explícito de "
    "espera/cozedura). Não inventes valores que não estão no texto/imagem "
    "— deixa os campos a null/vazio em vez de adivinhar."
)


_RECEIPT_PROMPT = (
    "Esta é uma foto de uma fatura/talão de supermercado em português. "
    "Extrai só os artigos alimentares ou de despensa comprados (o que "
    "faria sentido guardar como ingrediente de cozinha), como uma lista "
    "de nomes genéricos, em português europeu, em minúsculas e no "
    "singular (ex. 'iogurte natural', 'arroz', 'azeite', 'peito de "
    "frango' — nunca o nome exato/abreviado da linha da fatura, ex. "
    "'IOG NAT MIMOSA 4X125G' devia sair como 'iogurte natural'). Ignora "
    "por completo linhas que não são artigos comprados: total, "
    "subtotal, IVA, NIF, morada, forma de pagamento, cartão, troco, "
    "número de talão/fatura, desconto, cartão de cliente, e artigos "
    "não alimentares (sacos, jornais, produtos de higiene, limpeza, "
    "etc.). Não repitas o mesmo artigo duas vezes. Não inventes artigos "
    "que não estão na imagem — se não conseguires ler a fatura, devolve "
    "uma lista vazia."
)


def is_available(settings: Settings) -> bool:
    return bool(settings.gemini_api_key)


def _extract(settings: Settings, contents: list, response_schema: type, is_valid):
    if not is_available(settings):
        return None
    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
            ),
        )
        parsed = response.parsed
        if not isinstance(parsed, response_schema) or not is_valid(parsed):
            return None
        return parsed
    except Exception:
        # Best-effort, mesmo padrão de save_recipe_image_from_url — uma
        # falha aqui nunca deve rebentar a importação em si, só significa
        # "sem sugestão desta vez" (rede em baixo, chave inválida, resposta
        # que não bate com o schema, quota esgotada, etc.).
        return None


def extract_from_html(settings: Settings, html: str) -> schemas.RecipeExtraction | None:
    """Fallback quando o recipe-scrapers não trouxe ingredientes nem passos
    nenhuns (ver app/tasks.py) — nunca chamado para "melhorar" um resultado
    que já veio preenchido, só para tentar salvar um que veio vazio."""
    # HTML bruto de uma página de receita pode ser grande; corta a um
    # tamanho razoável para não estourar o limite de contexto/custo por
    # pedido — o essencial de uma receita está tipicamente nos primeiros
    # blocos do documento.
    truncated = html[:60_000]
    return _extract(
        settings, [_EXTRACTION_PROMPT, truncated], schemas.RecipeExtraction, lambda r: bool(r.title.strip())
    )


def extract_from_images(settings: Settings, images: list[tuple[bytes, str]]) -> schemas.RecipeExtraction | None:
    """`images`: lista de (bytes, content_type), 1-3 fotos — página de
    livro ou receita manuscrita. Resultado só alimenta o formulário manual
    para revisão, nunca grava direto (ver schemas.RecipeExtraction)."""
    if not images or len(images) > 3:
        return None
    parts = [types.Part.from_bytes(data=data, mime_type=content_type) for data, content_type in images]
    return _extract(settings, [_EXTRACTION_PROMPT, *parts], schemas.RecipeExtraction, lambda r: bool(r.title.strip()))


def extract_pantry_items_from_image(settings: Settings, image: tuple[bytes, str]) -> schemas.PantryExtraction | None:
    """`image`: (bytes, content_type) de uma foto de fatura/talão de
    supermercado. Resultado só alimenta uma lista pré-marcada no frontend
    para confirmação num toque (`POST /pantry/bulk`), nunca grava direto —
    mesmo princípio de `extract_from_images` (ver `schemas.PantryExtraction`)."""
    data, content_type = image
    part = types.Part.from_bytes(data=data, mime_type=content_type)
    return _extract(settings, [_RECEIPT_PROMPT, part], schemas.PantryExtraction, lambda _r: True)
