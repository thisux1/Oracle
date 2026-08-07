#!/usr/bin/env python3
"""
Epic RPG Wiki Scraper — Extrai todas as páginas da wiki do Fandom via API MediaWiki
e converte para Markdown estruturado, pronto para indexação com graphify.

Uso:
    python tools/scrape_wiki.py                 # Baixa todas as páginas
    python tools/scrape_wiki.py --force          # Re-baixa tudo, ignorando cache
    python tools/scrape_wiki.py --page "Horse"   # Baixa uma página específica

Output: data/wiki_docs/<Categoria>/<Titulo>.md
"""

import os
import re
import json
import sys
import time
import argparse
import textwrap
from pathlib import Path
from urllib.parse import quote

try:
    import requests
except ImportError:
    print("Instale requests: pip install requests")
    sys.exit(1)

# ─── Config ───────────────────────────────────────────────────────────────────

WIKI_API = "https://epic-rpg.fandom.com/api.php"
WIKI_BASE = "https://epic-rpg.fandom.com/wiki/"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "wiki_docs"
MANIFEST_PATH = OUTPUT_DIR / "_manifest.json"

# Páginas traduzidas/duplicadas que devem ser ignoradas
SKIP_SUFFIXES = [
    "- Español", "- Espa\\u00f1ol", "- Italiano", "- Türkçe",
    "- Tiếng Việt", "- Ti\\u1ebfng Vi\\u1ec7t", "- German",
    "Espa\\u00f1ol", "Español",
]
SKIP_TITLES = {
    "Main Page", "EPIC RPG Wiki", "F",
    "ホーム",  # Japanese home page
}
# Prefixos de namespace que não são conteúdo do jogo
SKIP_PREFIXES = ["Template:", "File:", "Category:", "Talk:", "User:", "Blog:"]

# Mapeamento de categorias do Fandom → pastas de saída
CATEGORY_MAP = {
    "Areas": "areas",
    "Commands": "commands",
    "Dungeon": "dungeons",
    "Items": "items",
    "Mechanics": "mechanics",
    "Guides": "guides",
    "Guilds": "guilds",
    "Locations": "locations",
    "Game info": "game_info",
    "Special": "events",
    "Codes": "misc",
}

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "OracleBot-WikiScraper/1.0 (Epic RPG automation project)",
    "Accept": "application/json",
})

# Rate limiting
REQUEST_DELAY = 0.3  # segundos entre requests


# ─── API helpers ──────────────────────────────────────────────────────────────

def api_get(params: dict) -> dict:
    """Faz uma requisição GET à API do MediaWiki com rate limiting."""
    params["format"] = "json"
    time.sleep(REQUEST_DELAY)
    resp = SESSION.get(WIKI_API, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_all_page_titles() -> list[dict]:
    """Retorna lista de {pageid, title} de todas as páginas do namespace 0."""
    pages = []
    params = {
        "action": "query",
        "list": "allpages",
        "aplimit": "500",
        "apnamespace": "0",
    }
    while True:
        data = api_get(params)
        if "query" in data and "allpages" in data["query"]:
            for page in data["query"]["allpages"]:
                pages.append({"pageid": page["pageid"], "title": page["title"]})
        if "continue" in data:
            params.update(data["continue"])
        else:
            break
    return pages


def get_page_data(title: str) -> dict | None:
    """Baixa wikitext + categorias de uma página específica."""
    data = api_get({
        "action": "parse",
        "page": title,
        "prop": "wikitext|categories|links",
        "disablelimitreport": 1,
    })
    if "parse" not in data:
        return None
    parsed = data["parse"]
    return {
        "title": parsed.get("title", title),
        "pageid": parsed.get("pageid"),
        "wikitext": parsed.get("wikitext", {}).get("*", ""),
        "categories": [c["*"] for c in parsed.get("categories", [])],
        "links": [l["*"] for l in parsed.get("links", []) if l.get("ns", 0) == 0],
    }


# ─── Wikitext → Markdown converter ───────────────────────────────────────────

def wikitext_to_markdown(wikitext: str, title: str) -> str:
    """Converte wikitext do MediaWiki para Markdown estruturado."""
    text = wikitext

    # ── Limpar tags HTML irrelevantes ──
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<nowiki>(.*?)</nowiki>', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'<blockquote>(.*?)</blockquote>', r'\n> \1\n', text, flags=re.DOTALL)
    text = re.sub(r'<u>(.*?)</u>', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'<sup>(.*?)</sup>', r'^\1', text, flags=re.DOTALL)
    text = re.sub(r'<big>(.*?)</big>', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'<small>(.*?)</small>', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'</?s>', '', text)

    # ── Remover imagens e arquivos inline ──
    text = re.sub(r'\[\[File:.*?\]\]', '', text)
    text = re.sub(r'\[\[Image:.*?\]\]', '', text)

    # ── Converter links internos ──
    # [[Page|display text]] → display text (Ver: Page)
    text = re.sub(r'\[\[([^|\]]+)\|([^\]]+)\]\]', r'\2 (Ver: \1)', text)
    # [[Page]] → Page
    text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', text)

    # ── Converter links externos ──
    text = re.sub(r'\[https?://\S+\s+([^\]]+)\]', r'\1', text)
    text = re.sub(r'\[https?://\S+\]', '', text)

    # ── Converter headers ──
    text = re.sub(r'={5}(.+?)={5}', r'##### \1', text)
    text = re.sub(r'={4}(.+?)={4}', r'#### \1', text)
    text = re.sub(r'={3}(.+?)={3}', r'### \1', text)
    text = re.sub(r'={2}(.+?)={2}', r'## \1', text)

    # ── Converter formatação ──
    text = re.sub(r"'{5}(.+?)'{5}", r'***\1***', text)  # bold italic
    text = re.sub(r"'{3}(.+?)'{3}", r'**\1**', text)    # bold
    text = re.sub(r"'{2}(.+?)'{2}", r'*\1*', text)      # italic

    # ── Converter tabelas wikitext → Markdown ──
    text = convert_wiki_tables(text)

    # ── Limpar listas ──
    text = re.sub(r'^\*\*\*\s*', '      - ', text, flags=re.MULTILINE)
    text = re.sub(r'^\*\*\s*', '    - ', text, flags=re.MULTILINE)
    text = re.sub(r'^\*\s*', '- ', text, flags=re.MULTILINE)
    text = re.sub(r'^#\s*', '1. ', text, flags=re.MULTILINE)

    # ── Limpar categorias do rodapé ──
    text = re.sub(r'\[\[Category:.*?\]\]', '', text)

    # ── Limpar espaços extras ──
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    text = text.strip()

    # ── Montar header do documento ──
    header = f"# {title}\n\n"
    return header + text


def convert_wiki_tables(text: str) -> str:
    """Converte tabelas wikitext ({| ... |}) para Markdown."""
    result = []
    lines = text.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]

        # Início de tabela
        if line.strip().startswith('{|'):
            table_lines = []
            i += 1

            # Capturar caption se existir
            caption = ""
            if i < len(lines) and lines[i].strip().startswith('|+'):
                caption = clean_cell(lines[i].strip()[2:])
                i += 1

            headers = []
            rows = []
            current_row = []
            in_header = False

            while i < len(lines) and not lines[i].strip().startswith('|}'):
                stripped = lines[i].strip()

                if stripped.startswith('!'):
                    # Header cells
                    in_header = True
                    cells = re.split(r'!!', stripped[1:])
                    for cell in cells:
                        headers.append(clean_cell(cell))

                elif stripped.startswith('|-'):
                    # New row separator
                    if current_row:
                        rows.append(current_row)
                        current_row = []
                    in_header = False

                elif stripped.startswith('|'):
                    # Data cells
                    cells = re.split(r'\|\|', stripped[1:])
                    for cell in cells:
                        current_row.append(clean_cell(cell))

                i += 1

            if current_row:
                rows.append(current_row)

            # Construir tabela Markdown
            if caption:
                result.append(f"\n**{caption}**\n")

            if headers:
                # Normalizar número de colunas
                num_cols = len(headers)
                result.append('| ' + ' | '.join(headers) + ' |')
                result.append('| ' + ' | '.join(['---'] * num_cols) + ' |')
                for row in rows:
                    # Pad row to match header count
                    padded = row + [''] * (num_cols - len(row))
                    result.append('| ' + ' | '.join(padded[:num_cols]) + ' |')
            elif rows:
                # Tabela sem headers — usar primeira row como header
                num_cols = max(len(r) for r in rows) if rows else 1
                for idx, row in enumerate(rows):
                    padded = row + [''] * (num_cols - len(row))
                    result.append('| ' + ' | '.join(padded[:num_cols]) + ' |')
                    if idx == 0:
                        result.append('| ' + ' | '.join(['---'] * num_cols) + ' |')

            result.append('')
            i += 1  # skip |}
        else:
            result.append(line)
            i += 1

    return '\n'.join(result)


def clean_cell(cell: str) -> str:
    """Limpa o conteúdo de uma célula de tabela wikitext."""
    # Remove atributos de estilo (ex: style="..." ou class="...")
    cell = re.sub(r'^[^|]*\|(?!\|)', '', cell)
    # Remove formatação bold/italic residual
    cell = cell.replace("'''", "**").replace("''", "*")
    # Remove tags HTML residuais
    cell = re.sub(r'<[^>]+>', '', cell)
    # Remove imagens/arquivos
    cell = re.sub(r'\[\[File:.*?\]\]', '', cell)
    # Compacta espaços
    cell = re.sub(r'\s+', ' ', cell).strip()
    # Remove newlines para manter a tabela em uma linha
    cell = cell.replace('\n', ' ')
    return cell


# ─── File I/O ─────────────────────────────────────────────────────────────────

def should_skip(title: str) -> bool:
    """Verifica se a página deve ser ignorada (tradução, template, etc.)."""
    if title in SKIP_TITLES:
        return True
    for prefix in SKIP_PREFIXES:
        if title.startswith(prefix):
            return True
    title_lower = title.lower()
    for suffix in SKIP_SUFFIXES:
        if suffix.lower() in title_lower:
            return True
    return False


def get_output_folder(categories: list[str]) -> str:
    """Determina a pasta de saída com base nas categorias da página."""
    for cat in categories:
        if cat in CATEGORY_MAP:
            return CATEGORY_MAP[cat]
    return "general"


def sanitize_filename(title: str) -> str:
    """Converte título da página para nome de arquivo seguro."""
    name = title.replace(" ", "_")
    name = re.sub(r'[^\w\-.]', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    return name


def save_page(page_data: dict, folder: str) -> Path:
    """Salva uma página processada como arquivo Markdown."""
    out_dir = OUTPUT_DIR / folder
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = sanitize_filename(page_data["title"]) + ".md"
    filepath = out_dir / filename

    # Converter wikitext → Markdown
    markdown = wikitext_to_markdown(page_data["wikitext"], page_data["title"])

    # Adicionar metadata YAML frontmatter
    categories_str = ", ".join(page_data["categories"]) if page_data["categories"] else "Uncategorized"
    links_str = ", ".join(page_data["links"][:20]) if page_data["links"] else "None"

    frontmatter = textwrap.dedent(f"""\
    ---
    title: "{page_data['title']}"
    pageid: {page_data['pageid']}
    categories: [{categories_str}]
    source: "{WIKI_BASE}{quote(page_data['title'])}"
    related_pages: [{links_str}]
    ---

    """)

    filepath.write_text(frontmatter + markdown, encoding="utf-8")
    return filepath


# ─── Manifest ─────────────────────────────────────────────────────────────────

def load_manifest() -> dict:
    """Carrega o manifesto de páginas já baixadas."""
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {}


def save_manifest(manifest: dict):
    """Salva o manifesto atualizado."""
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

def scrape_single(title: str) -> bool:
    """Baixa e processa uma única página."""
    print(f"  📥 Baixando: {title}...", end=" ", flush=True)
    page_data = get_page_data(title)
    if not page_data or not page_data["wikitext"].strip():
        print("❌ (sem conteúdo)")
        return False

    folder = get_output_folder(page_data["categories"])
    filepath = save_page(page_data, folder)
    print(f"✅ → {filepath.relative_to(OUTPUT_DIR)}")
    return True


def scrape_all(force: bool = False):
    """Baixa todas as páginas da Wiki."""
    print("🔍 Buscando lista de páginas da Epic RPG Wiki...")
    all_pages = get_all_page_titles()
    print(f"📄 Total de páginas encontradas: {len(all_pages)}")

    # Filtrar páginas irrelevantes
    pages = [p for p in all_pages if not should_skip(p["title"])]
    print(f"📋 Páginas relevantes (após filtro): {len(pages)}")

    manifest = {} if force else load_manifest()

    downloaded = 0
    skipped = 0
    errors = 0

    for i, page in enumerate(pages, 1):
        title = page["title"]

        # Skip se já baixada (e não forçando)
        if not force and title in manifest:
            skipped += 1
            continue

        print(f"  [{i}/{len(pages)}]", end="")

        try:
            success = scrape_single(title)
            if success:
                manifest[title] = {
                    "pageid": page["pageid"],
                    "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
                downloaded += 1
            else:
                errors += 1
        except Exception as e:
            print(f"  ⚠️  Erro em '{title}': {e}")
            errors += 1

        # Salvar manifesto a cada 10 páginas
        if downloaded % 10 == 0:
            save_manifest(manifest)

    # Salvar manifesto final
    save_manifest(manifest)

    print(f"\n{'─' * 60}")
    print(f"✅ Concluído!")
    print(f"   📥 Baixadas: {downloaded}")
    print(f"   ⏭️  Já existentes (skip): {skipped}")
    print(f"   ❌ Erros: {errors}")
    print(f"   📂 Output: {OUTPUT_DIR}")


def main():
    parser = argparse.ArgumentParser(
        description="Epic RPG Wiki Scraper — Extrai dados da wiki para Markdown",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-baixa todas as páginas, ignorando cache",
    )
    parser.add_argument(
        "--page", type=str, default=None,
        help="Baixa apenas uma página específica pelo título",
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.page:
        scrape_single(args.page)
    else:
        scrape_all(force=args.force)


if __name__ == "__main__":
    main()
