# Plano de Integracao de Dados do Jogo (Game Data)

> Unificando Epic RPG Guide, Wiki Docs e dados do Navi em um modulo Oracle centralizado
> **Estado atual:** Nada implementado. Nenhum arquivo em `data/game_data/`.

---

## 1. Objetivo

Criar `data/game_data/` — um diretorio com dados estaticos do Epic RPG em JSON, carregados por um modulo `GameData` que o Oracle consulta para decisoes inteligentes, sem depender de fontes externas (Navi, Guide, Wiki).

## 2. Justificativa para JSON em vez de SQLite

| Aspecto | JSON | SQLite | Veredito |
|---|---|---|---|
| Simplicidade | ✅ Leitura direta | ❌ Requer driver + schema | JSON vence |
| Performance (leitura) | ✅ O(1) com dict | ✅ O(log n) com index | Empate |
| Mutabilidade | ❌ Read-only (bom para dados estaticos) | ✅ Read-write | SQLite vence para dados dinamicos |
| Portabilidade | ✅ Copia unica de arquivo | ❌ Requer dump/restore | JSON vence |
| Versionamento | ✅ Git-friendly (diff textual) | ❌ Binario, sem diff | JSON vence |
| Consumo em selfbot | ✅ 500 KB na memoria e suficiente | ❌ Overhead desnecessario | JSON vence |

**Conclusao:** JSON para dados estaticos do jogo (areas, monstros, crafting). SQLite apenas se houver necessidade de dados dinamicos do usuario (historico, configuracoes avancadas).

## 3. Arquitetura do Modulo

```
data/game_data/
├── __init__.py        # GameData singleton com lazy loading
├── monsters.json       # ~200 monstros com drops, HP, area, XP
├── areas.json          # 21+ areas com dano, gear, loot
├── dungeons.json       # 15 dungeons com mecanicas
├── crafting.json       # Receitas de crafting
├── trades.json         # Taxas de troca por area
├── professions.json    # Dados de profissoes (XP, materiais)
├── timetravel.json     # Valores de Time Jump
├── horse.json          # Racas e dados de cavalos
├── pets.json           # Dados de pets e fusao
├── cards.json          # Onde cada card dropa
├── alchemy.json        # Pocoes e efeitos
├── artifacts.json      # Bonus de artefatos
├── boosts.json         # Duracao de boosts
└── monsters_area.json  # Mobs por area (Navi)
```

Total estimado: ~500 KB de dados estaticos.

## 4. Dados por Fonte (Mapeamento Preciso)

### 4.1 Do Epic RPG Guide (content/*.py)

| Modulo Guide | Arquivo JSON | Campos | Prioridade |
|---|---|---|---|
| content/monsters.py | monsters.json | area, hp, drops, xp | 🔴 Alta |
| content/areas.py | areas.json | min_damage, max_damage, defense_needed, adventure_damage | 🔴 Alta |
| content/dungeons.py | dungeons.json | phases, min_level, mechanics, loot | 🔴 Alta |
| content/crafting.py | crafting.json | materials, tier, level | 🟡 Media |
| content/trading.py | trades.json | rates_by_area, item_modifiers | 🟡 Media |
| content/professions.py | professions.json | xp_per_level, materials_per_level | 🟢 Baixa |
| content/timetravel.py | timetravel.json | item_values, stat_weights | 🟡 Media |
| content/horse.py | horse.json | breeds, boost_values, training_costs | 🟢 Baixa |
| content/pets.py | pets.json | fusion_data, evolution_chains | 🟢 Baixa |
| content/cards.py | cards.json | drop_locations | 🟢 Baixa |
| content/alchemy.py | alchemy.json | effects, durations | 🟢 Baixa |
| content/artifacts.py | artifacts.json | bonuses, requirements | 🟢 Baixa |
| content/gambling.py | — | Probabilidades (usar direto do codigo) | 🟢 Baixa |

### 4.2 Da Wiki Docs (data/wiki_docs/)

| Fonte Wiki | Dados Uteis | Para que JSON |
|---|---|---|
| commands/Cooldowns.md | Descricoes de cooldowns | Validar BASE_COOLDOWNS |
| locations/Area_1.md .. Area_14.md | Lore e descricoes | areas.json (enriquecimento) |
| dungeons/Dungeon_11.md .. Dungeon_15.md | Mecanicas detalhadas | dungeons.json (enriquecimento) |
| general/Alchemy.md | Pocoes | alchemy.json (validacao) |
| general/Artifacts.md | Artefatos | artifacts.json (validacao) |
| general/Coins_cap.md | Limite de coins | timetravel.json (coin_cap) |
| general/World_Boost.md | World boosts | boosts.json |
| misc/Codes.md | Codigos resgataveis | — (usar direto) |
| mechanics/Pets.md | Mecanicas de pets | pets.json (enriquecimento) |
| mechanics/Professions.md | Profissoes | professions.json (enriquecimento) |

### 4.3 Do Navi (resources/ + cogs/)

| Fonte Navi | Dados Uteis | Para que JSON |
|---|---|---|
| cogs/current_area.py + resources/strings.py | MONSTERS_AREA | monsters_area.json |
| cogs/boosts.py | BOOST_DURATIONS | boosts.json |
| database/cooldowns.py | Tabela de cooldowns | Validar cooldowns |

## 5. Calculadoras Portaveis

### 5.1 Drop Chance Calculator
```python
def calculate_drop_chance(base_chance: float, luck: int,
                          area_mult: float = 1.0,
                          boost_mult: float = 1.0) -> float:
    return base_chance * (1 + luck / 100) * area_mult * boost_mult
```

### 5.2 Coin Cap Calculator
```python
def calculate_coin_cap(tt: int, ascension: int = 0) -> int:
    return tt * 100_000_000 + ascension * 50_000_000
```

### 5.3 Area Damage Calculator
```python
def calculate_area_damage(area_id: int, defense: int,
                          is_adventure: bool = False) -> int:
    area_data = AREAS.get(area_id, {})
    base = area_data.get("adventure_damage" if is_adventure else "hunt_damage", 1)
    return max(1, int(base - defense * 0.5))
```

### 5.4 Crafting Material Calculator
```python
def calculate_crafting_materials(item: str, quantity: int = 1) -> dict[str, int]:
    recipe = CRAFTING.get(item, {})
    return {mat: qty * quantity for mat, qty in recipe.items()}
```

### 5.5 Time Jump Score Calculator
```python
def calculate_tj_score(items: dict[str, int],
                       stats: dict[str, int]) -> int:
    item_score = sum(qty * TIME_TRAVEL["items"].get(item, 0) for item, qty in items.items())
    stat_score = sum(value * TIME_TRAVEL["stats"].get(stat, 0) for stat, value in stats.items())
    return item_score + stat_score
```

### 5.6 Profession XP Calculator
```python
def calculate_profession_xp(level: int) -> int:
    return int(100 * (1.5 ** (level - 1)))
```

### 5.7 Horse Boost Calculator
```python
def calculate_horse_boost(base_stat: int, level: int,
                          breed: str, item_bonus: float = 0) -> float:
    BREED_MODIFIERS = {"common": 1.0, "rare": 1.5, "epic": 2.0}
    breed_mod = BREED_MODIFIERS.get(breed, 1.0)
    return base_stat * (1 + level / 100) * breed_mod + item_bonus
```

## 6. Integracao com Oracle

### 6.1 Uso em Decisoes do Bot

| Decisao | Dados Necessarios | Fonte |
|---|---|---|
| Qual area huntar? | areas.json, monsters.json | Guide + Navi |
| Quando fazer time jump? | timetravel.json | Guide |
| Quanto crafting fazer? | crafting.json | Guide |
| Qual trade fazer? | trades.json | Guide |
| Precisa heal? | areas.json (damage), defense atual | Guide + Navi |
| Esta com boost? | boosts.json | Navi |
| Qual mob farming? | monsters.json, monsters_area.json | Guide + Navi + Wiki |

### 6.2 Pipeline de Carregamento

```python
# data/game_data/__init__.py
class GameData:
    _instance = None
    _loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self):
        if self._loaded:
            return
        import json, os
        base = os.path.dirname(__file__)
        for name in ["monsters", "areas", "dungeons", "crafting", "trades",
                      "professions", "timetravel", "horse", "pets", "cards",
                      "alchemy", "artifacts", "boosts", "monsters_area"]:
            path = os.path.join(base, f"{name}.json")
            if os.path.exists(path):
                with open(path) as f:
                    setattr(self, name.upper(), json.load(f))
            else:
                setattr(self, name.upper(), {})
        self._loaded = True
```

## 7. Script de Extracao

Criar `tools/extract_game_data.py` que:

1. Le `~/Epic-RPG-Guide/content/*.py` usando ast.literal_eval ou import direto
2. Le `~/Navi/Navi/resources/strings.py` para MONSTERS_AREA
3. Le `data/wiki_docs/**/*.md` para dados complementares (frontmatter YAML)
4. Consolida em `data/game_data/*.json`
5. Valida consistencia entre fontes
6. Reporta discrepancias

```bash
python tools/extract_game_data.py
```

## 8. Validacao de Dados

| Check | Descricao | Fontes |
|---|---|---|
| Consistencia de areas | Mesma area em Navi, Guide e Wiki | monsters_area.json vs areas.json vs wiki locations/ |
| Cooldowns corretos | BASE_COOLDOWNS vs Wiki + Navi database | Wiki Cooldowns.md + Navi database/cooldowns.py |
| Drops de monstros | Drop rates no Guide vs Wiki | monsters.json vs wiki mentions |
| Trade rates | Guia de trocas no Guide vs Wiki | trades.json vs wiki commands/Trade.md |
| Dungeon mechanics | Guide vs Wiki | dungeons.json vs wiki dungeons/ |

Discrepancias encontradas devem ser registradas em `data/game_data/discrepancies.log`.

---

## 9. Diferencas entre v1 (plans original) e v2 (esta revisao)

| Aspecto | v1 (original) | v2 (revisado) | Justificativa |
|---|---|---|---|
| Local do modulo | `bot/game_data.py` | `data/game_data/__init__.py` | Dados estaticos fora do codigo fonte |
| Formato | Hardcoded no .py | JSON files | Mais facil de extrair, versionar e editar |
| Singleton | `__new__` com `_instance` | Mesmo padrao, mas simplificado | Mantido por familiaridade |
| `MONSTERS_DATA` | Referencia indefinida | `_load_json("monsters.json")` | Corrigido — agora aponta para arquivo real |
| Script de extracao | Mencionado mas sem detalhes | Linha de comando + pipeline definidos | Clareza de implementacao |
| `data/game_data/` | 12 JSONs | 14 JSONs (adicionados boosts.json e monsters_area.json) | Cobertura completa |
