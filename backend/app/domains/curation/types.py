"""Pure functions for the curation domain — no FastAPI, no SQLAlchemy imports."""


def build_fork_lineage(parent_lineage: list[str], parent_id: str) -> list[str]:
    """Return the fork lineage list for a child collection.

    parent_lineage: the ancestor list of the board being forked (root first)
    parent_id:      the id of the board being forked
    Returns:        a new list with parent_id appended — does not mutate input
    """
    return list(parent_lineage) + [parent_id]
