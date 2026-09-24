"""
CLI Graph Commands

Commands for querying the knowledge graph: entity search, entity details,
subgraph expansion, related documents, and graph statistics.
"""

import json
from typing import Optional

import click

from kb.commands.utils import _get_sqlite_storage


@click.group()
def graph() -> None:
    """Knowledge graph queries."""
    pass


@graph.command("search")
@click.argument("query")
@click.option("--limit", "-l", type=int, default=20, help="Max results (default: 20)")
@click.option("--json-output", "--json", "as_json", is_flag=True, help="Output as JSON")
def graph_search(query: str, limit: int, as_json: bool) -> None:
    """Search entities by name."""
    from kb.query.graph_query import GraphQuery

    storage = _get_sqlite_storage()
    try:
        gq = GraphQuery(storage=storage)
        results = gq.search_entities(q=query, limit=limit)

        if as_json:
            click.echo(json.dumps(results, ensure_ascii=False, indent=2))
            return

        if not results:
            click.echo(f"No entities matching '{query}'.")
            return

        click.echo(f"Found {len(results)} entities:\n")
        for ent in results:
            click.echo(
                f"  [{ent['id']}] {ent['display_name']}  "
                f"type={ent['type']}  mentions={ent['mention_count']}"
            )
    finally:
        storage.close()


@graph.command("show")
@click.argument("entity_id", type=int)
@click.option("--json-output", "--json", "as_json", is_flag=True, help="Output as JSON")
def graph_show(entity_id: int, as_json: bool) -> None:
    """Show entity details (mentions + relations)."""
    from kb.query.graph_query import GraphQuery

    storage = _get_sqlite_storage()
    try:
        gq = GraphQuery(storage=storage)
        entity = gq.get_entity(entity_id)

        if entity is None:
            click.echo(f"Entity {entity_id} not found.", err=True)
            raise SystemExit(1)

        if as_json:
            click.echo(json.dumps(entity, ensure_ascii=False, indent=2))
            return

        click.echo(f"{entity['display_name']}  (type={entity['type']})")
        if entity.get("description"):
            click.echo(f"  {entity['description']}")
        click.echo(f"  mentions: {entity['mention_count']}")

        mentions = entity.get("mentions", [])
        if mentions:
            click.echo(f"\nDocuments ({len(mentions)}):")
            for m in mentions:
                title = m.get("title") or m.get("knowledge_id", "")
                click.echo(f"  - {title}")
                if m.get("context"):
                    click.echo(f"    \"{m['context'][:120]}\"")

        relations = entity.get("relations", [])
        if relations:
            click.echo(f"\nRelations ({len(relations)}):")
            for r in relations:
                click.echo(
                    f"  --[{r['relation_type']}]--> "
                    f"{r['related_display_name']}  (type={r['related_type']})"
                )
    finally:
        storage.close()


@graph.command("expand")
@click.argument("entity_id", type=int)
@click.option("--depth", "-d", type=int, default=2, help="Max hops (1-5, default: 2)")
@click.option("--limit", "-l", type=int, default=50, help="Max nodes (default: 50)")
@click.option("--json-output", "--json", "as_json", is_flag=True, help="Output as JSON")
def graph_expand(entity_id: int, depth: int, limit: int, as_json: bool) -> None:
    """Expand N-hop subgraph from an entity."""
    from kb.query.graph_query import GraphQuery

    if depth < 1 or depth > 5:
        click.echo("depth must be between 1 and 5", err=True)
        raise SystemExit(1)

    storage = _get_sqlite_storage()
    try:
        gq = GraphQuery(storage=storage)
        data = gq.get_graph(entity_id=entity_id, depth=depth, limit=limit)

        if as_json:
            click.echo(json.dumps(data, ensure_ascii=False, indent=2))
            return

        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        stats = data.get("stats", {})

        if not nodes:
            click.echo(f"No subgraph found for entity {entity_id}.")
            return

        # Build adjacency for tree-style display
        node_map = {n["id"]: n for n in nodes}
        adj: dict = {}
        for e in edges:
            src, tgt = e["source_entity_id"], e["target_entity_id"]
            adj.setdefault(src, []).append((tgt, e["relation_type"]))
            adj.setdefault(tgt, []).append((src, e["relation_type"]))

        click.echo(
            f"Subgraph: {stats.get('displayed_nodes', len(nodes))} nodes, "
            f"{stats.get('displayed_edges', len(edges))} edges  "
            f"(depth={depth})\n"
        )

        # BFS tree from center
        visited = set()
        queue = [(entity_id, 0)]
        visited.add(entity_id)

        while queue:
            nid, d = queue.pop(0)
            node = node_map.get(nid)
            if node is None:
                continue
            indent = "  " * d
            click.echo(f"{indent}[{node['id']}] {node['display_name']}  type={node['type']}")
            for neighbor_id, rel_type in adj.get(nid, []):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, d + 1))
    finally:
        storage.close()


@graph.command("related")
@click.argument("knowledge_id")
@click.option("--limit", "-l", type=int, default=10, help="Max results (default: 10)")
@click.option(
    "--type", "-t", "relation_type",
    type=click.Choice(["embedding_similarity", "shared_entity"]),
    default=None, help="Filter by relation type",
)
@click.option("--json-output", "--json", "as_json", is_flag=True, help="Output as JSON")
def graph_related(knowledge_id: str, limit: int, relation_type: Optional[str], as_json: bool) -> None:
    """Show documents related to a knowledge item."""
    from kb.query.graph_query import GraphQuery

    storage = _get_sqlite_storage()
    try:
        gq = GraphQuery(storage=storage)
        results = gq.get_related_documents(
            knowledge_id=knowledge_id,
            limit=limit,
            relation_type=relation_type,
        )

        if as_json:
            click.echo(json.dumps(results, ensure_ascii=False, indent=2))
            return

        if not results:
            click.echo(f"No related documents for {knowledge_id[:12]}.")
            return

        click.echo(f"Related documents ({len(results)}):\n")
        for i, doc in enumerate(results, 1):
            click.echo(
                f"  [{i}] {doc.get('title', doc['knowledge_id'])}  "
                f"score={doc['score']:.3f}  type={doc['relation_type']}"
            )
            if doc.get("reason"):
                click.echo(f"      {doc['reason']}")
            if doc.get("shared_entities"):
                click.echo(f"      shared: {doc['shared_entities']}")
    finally:
        storage.close()


@graph.command("stats")
@click.option("--json-output", "--json", "as_json", is_flag=True, help="Output as JSON")
def graph_stats(as_json: bool) -> None:
    """Show knowledge graph statistics."""
    from kb.query.graph_query import GraphQuery

    storage = _get_sqlite_storage()
    try:
        gq = GraphQuery(storage=storage)
        stats = gq.get_graph_stats()

        if as_json:
            click.echo(json.dumps(stats, ensure_ascii=False, indent=2))
            return

        click.echo("Knowledge Graph Statistics")
        click.echo("=" * 40)
        click.echo(f"  Entities:         {stats['total_entities']}")
        click.echo(f"  Relations:        {stats['total_relations']}")
        click.echo(f"  Doc Relations:    {stats['total_doc_relations']}")
        click.echo(f"  Mentions:         {stats['total_mentions']}")

        type_dist = stats.get("type_distribution", [])
        if type_dist:
            click.echo("\n  Entity Types:")
            for td in type_dist:
                click.echo(f"    {td['type']}: {td['count']}")

        rel_dist = stats.get("relation_distribution", [])
        if rel_dist:
            click.echo("\n  Relation Types:")
            for rd in rel_dist:
                click.echo(f"    {rd['relation_type']}: {rd['count']}")

        top = stats.get("top_entities", [])
        if top:
            click.echo("\n  Top Entities:")
            for ent in top:
                click.echo(
                    f"    [{ent['id']}] {ent['display_name']}  "
                    f"type={ent['type']}  mentions={ent['mention_count']}"
                )
    finally:
        storage.close()
