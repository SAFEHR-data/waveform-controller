from importlib import resources

def get_sql_query_text(query_rel_path: str) -> str:
    return (resources.files("sql") / query_rel_path).read_text()
