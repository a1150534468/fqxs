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

        # Deep characters — merge info and add relationships
        if stype == 'main_characters':
            for c in sd.get('characters', []):
                name = c.get('name', '')
                add_node(name, 'character', {'motivation': c.get('motivation', ''), 'growth_arc': c.get('growth_arc', '')})
                for rel in c.get('relationships', []):
                    target = rel.get('target', '')
                    add_node(target, 'character')
                    if name and target:
                        add_link(f'character:{name}', f'character:{target}', rel.get('type', ''))

        # Map regions
        if stype == 'map':
            for r in sd.get('regions', []):
                name = r.get('name', '')
                add_node(name, 'region', {'type': r.get('type', ''), 'description': r.get('description', '')})
                for conn in r.get('connected_to', []):
                    add_node(conn, 'region')
                    if name:
                        add_link(f'region:{name}', f'region:{conn}', '连接')

        # Map system — factions + base region
        if stype == 'map_system':
            for r in sd.get('regions', []):
                region_name = r.get('name', '')
                add_node(region_name, 'region', {'significance': r.get('significance', '')})
                for f in r.get('factions', []):
                    fname = f.get('name', '')
                    add_node(fname, 'faction', {'influence': f.get('influence', ''), 'base': f.get('base', '')})
                    base = f.get('base', '')
                    if base:
                        add_node(base, 'region')
                        add_link(f'faction:{fname}', f'region:{base}', '基地')

        # Sub plots — link plots to characters
        if stype == 'main_sub_plots':
            main_plot = sd.get('main_plot', {})
            main_theme = main_plot.get('theme', '主线')
            if main_theme:
                add_node(main_theme, 'plot', {'type': 'main', 'events_count': len(main_plot.get('events', []))})
                for ev in main_plot.get('events', []):
                    for ch in ev.get('characters', []):
                        add_node(ch, 'character')
                        add_link(f'plot:{main_theme}', f'character:{ch}', '参与')
            for sp in sd.get('sub_plots', []):
                sp_name = sp.get('name', '')
                if sp_name:
                    add_node(sp_name, 'plot', {'type': 'sub', 'crosses_main': sp.get('crosses_main', '')})
                    for ch in sp.get('characters', []):
                        add_node(ch, 'character')
                        add_link(f'plot:{sp_name}', f'character:{ch}', '参与')

        # Opening — POV character link
        if stype == 'opening':
            pov = sd.get('pov_character', '')
            if pov:
                add_node(pov, 'character')

    nodes = list(nodes_map.values())
    return nodes, links
