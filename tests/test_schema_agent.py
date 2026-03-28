from agentic_sql.agents.schema_agent import SchemaAgent


class TestSchemaAgent:
    def test_returns_tables_key(self, engine_with_products):
        schema = SchemaAgent(engine_with_products).run()
        assert "tables" in schema

    def test_detects_all_columns(self, engine_with_products):
        tables = SchemaAgent(engine_with_products).run()["tables"]
        assert "products" in tables
        assert "id" in tables["products"]
        assert "name" in tables["products"]
        assert "price" in tables["products"]

    def test_pk_annotation_present(self, engine_with_products):
        """Primary key columns must be annotated with 'PK' for LLM context."""
        tables = SchemaAgent(engine_with_products).run()["tables"]
        assert "PK" in tables["products"]["id"]

    def test_empty_database(self, engine):
        """An engine with no tables should return an empty tables dict."""
        schema = SchemaAgent(engine).run()
        assert schema == {"tables": {}}
