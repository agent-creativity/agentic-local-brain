"""
CLI Topic Commands

Commands for managing knowledge base topic clusters.
"""

import click

from kb.commands.utils import CONFIG_FILE, _get_sqlite_storage
from kb.config import Config


@click.group()
def topics() -> None:
    """Topic cluster management."""
    pass


@topics.command("list")
def topics_list() -> None:
    """List all topic clusters."""
    storage = _get_sqlite_storage()
    try:
        from kb.query.topic_query import TopicQuery

        tq = TopicQuery(storage=storage)
        all_topics = tq.get_topics()
        stats = tq.get_topic_stats()

        if not all_topics:
            click.echo("No topic clusters found. Run 'localbrain topics rebuild' first.")
            return

        click.echo(f"Topic Clusters ({stats['total_topics']} topics, "
                    f"{stats['total_classified']}/{stats['total_documents']} docs classified)")
        click.echo("-" * 60)

        for t in all_topics:
            click.echo(
                f"  [{t['id']}] {t['label']} "
                f"({t['document_count']} docs)"
            )
            if t.get("description"):
                click.echo(f"      {t['description']}")
    finally:
        storage.close()


@topics.command("rebuild")
@click.option("--min-cluster-size", default=5, help="Minimum cluster size for HDBSCAN.")
def topics_rebuild(min_cluster_size: int) -> None:
    """Rebuild all topic clusters from scratch."""
    click.echo("Rebuilding topic clusters...")

    try:
        from kb.processors.topic_clusterer import TopicClusterer

        config = Config(CONFIG_FILE)
        clusterer = TopicClusterer.from_config(config)
        result = clusterer.cluster_all()

        click.echo(f"Done! {result['clusters']} clusters, "
                    f"{result['classified']} docs classified, "
                    f"{result['noise']} noise docs")
    except ImportError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("Install scikit-learn: pip install scikit-learn>=1.3", err=True)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@topics.command("show")
@click.argument("cluster_id", type=int)
@click.option("--limit", default=20, help="Max documents to show.")
def topics_show(cluster_id: int, limit: int) -> None:
    """Show documents in a topic cluster."""
    storage = _get_sqlite_storage()
    try:
        from kb.query.topic_query import TopicQuery

        tq = TopicQuery(storage=storage)
        topic = tq.get_topic(cluster_id)
        if topic is None:
            click.echo(f"Topic cluster {cluster_id} not found.", err=True)
            return

        docs = tq.get_topic_documents(cluster_id, limit=limit)
        click.echo(f"Topic: {topic['label']} ({topic['document_count']} docs)")
        if topic.get("description"):
            click.echo(f"  {topic['description']}")
        click.echo("-" * 60)

        for doc in docs:
            conf = f" (confidence: {doc['confidence']:.2f})" if doc.get("confidence") else ""
            click.echo(f"  [{doc['id'][:8]}] {doc['title']}{conf}")
    finally:
        storage.close()
