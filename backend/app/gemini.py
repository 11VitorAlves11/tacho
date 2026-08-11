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


def is_available(settings: Settings) -> bool:
    return bool(settings.gemini_api_key)


def _extract(settings: Settings, contents: list) -> schemas.RecipeExtraction | None:
    if not is_available(settings):
        return None
    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schemas.RecipeExtraction,
            ),
        )
        parsed = response.parsed
        if not isinstance(parsed, schemas.RecipeExtraction) or not parsed.title.strip():
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
    return _extract(settings, [_EXTRACTION_PROMPT, truncated])


def extract_from_images(settings: Settings, images: list[tuple[bytes, str]]) -> schemas.RecipeExtraction | None:
    """`images`: lista de (bytes, content_type), 1-3 fotos — página de
    livro ou receita manuscrita. Resultado só alimenta o formulário manual
    para revisão, nunca grava direto (ver schemas.RecipeExtraction)."""
    if not images or len(images) > 3:
        return None
    parts = [types.Part.from_bytes(data=data, mime_type=content_type) for data, content_type in images]
    return _extract(settings, [_EXTRACTION_PROMPT, *parts])
