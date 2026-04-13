"""
Aggregate NovelSetting structured_data into an ECharts-compatible graph.

Node format: {id, name, category, symbolSize, info}
Link format: {source, target, name, value?}

Categories: character, region, faction, plot
"""
from typing import Any

NODE_CATEGORIES = ['character', 'region', 'faction', 'plot']


def build_graph_from_settings(settings_qs) -> tuple[list[dict], list[dict]]:
    nodes_map: dict[str, dict] = {}
    links: list[dict] = []

    def add_node(name: str, category: str, info: dict | None = None):
        if not name or not isinstance(name, str):
            return
        key = f"{category}:{name}"
        if key not in nodes_map:
            nodes_map[key] = {
                'id': key,
                'name': name,
                'category': category,
                'symbolSize': 40 if category == 'character' else 30,
                'info': info or {},
            }
        elif info:
            nodes_map[key]['info'].update(info)

    def add_link(source_key: str, target_key: str, label: str = ''):
        if source_key in nodes_map and target_key in nodes_map:
            links.append({
                'source': source_key,
                'target': target_key,
                'name': label,
            })

    for setting in settings_qs:
        sd = setting.structured_data or {}
        stype = setting.setting_type

        # Initial characters
        if stype == 'characters':
            for c in sd.get('characters', []):
                add_node(c.get('name', ''), 'character', {'role': c.get('role', ''), 'brief': c.get('brief', '')})

        # Map regions
        if stype == 'map':
            for r in sd.get('regions', []):
                name = r.get('name', '')
                add_node(name, 'region', {'type': r.get('type', ''), 'description': r.get('description', '')})
                for conn in r.get('connected_to', []):
                    add_node(conn, 'region')
                    if name:
                        add_link(f'region:{name}', f'region:{conn}', '连接')

        # Opening — POV character link
        if stype == 'opening':
            pov = sd.get('pov_character', '')
            if pov:
                add_node(pov, 'character')

    nodes = list(nodes_map.values())
    return nodes, links
