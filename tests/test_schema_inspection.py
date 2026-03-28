from agentic_sql.db.schema import inspect_schema


class TestInspectSchema:
    def test_detects_tables_and_columns(self, engine_with_users):
        schema = inspect_schema(engine_with_users)
        assert "users" in schema
        assert "id" in schema["users"]
        assert "name" in schema["users"]

    def test_pk_annotation(self, engine_with_users):
        schema = inspect_schema(engine_with_users)
        assert "PK" in schema["users"]["id"]

    def test_no_tables_returns_empty(self, engine):
        schema = inspect_schema(engine)
        assert schema == {}
