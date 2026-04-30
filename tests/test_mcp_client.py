"""Tests for the MCP client module."""

from types import SimpleNamespace

from src.mcp_client import _strip_titles, mcp_tool_to_openai_function


class TestStripTitles:
    def test_removes_top_level_title(self):
        schema = {"title": "MyModel", "type": "object", "properties": {}}
        result = _strip_titles(schema)
        assert "title" not in result
        assert result["type"] == "object"

    def test_removes_nested_titles(self):
        schema = {
            "title": "Outer",
            "type": "object",
            "properties": {
                "name": {"title": "Name", "type": "string"},
                "age": {"title": "Age", "type": "integer"},
            },
        }
        result = _strip_titles(schema)
        assert "title" not in result
        assert "title" not in result["properties"]["name"]
        assert "title" not in result["properties"]["age"]
        assert result["properties"]["name"]["type"] == "string"

    def test_removes_titles_in_arrays(self):
        schema = {
            "title": "Root",
            "anyOf": [
                {"title": "Option1", "type": "string"},
                {"title": "Option2", "type": "integer"},
            ],
        }
        result = _strip_titles(schema)
        assert "title" not in result
        for item in result["anyOf"]:
            assert "title" not in item

    def test_preserves_non_title_fields(self):
        schema = {
            "title": "X",
            "type": "object",
            "description": "A thing",
            "required": ["a"],
        }
        result = _strip_titles(schema)
        assert result == {
            "type": "object",
            "description": "A thing",
            "required": ["a"],
        }

    def test_empty_schema(self):
        assert _strip_titles({}) == {}


class TestMcpToolToOpenaiFunction:
    def test_basic_conversion(self):
        tool = SimpleNamespace(
            name="list_products",
            description="List all products",
            inputSchema={
                "title": "ListProductsInput",
                "type": "object",
                "properties": {
                    "category": {"title": "Category", "type": "string"},
                },
            },
        )
        result = mcp_tool_to_openai_function(tool)

        assert result["type"] == "function"
        assert result["function"]["name"] == "list_products"
        assert result["function"]["description"] == "List all products"
        assert "title" not in result["function"]["parameters"]
        assert "title" not in result["function"]["parameters"]["properties"]["category"]

    def test_no_input_schema(self):
        tool = SimpleNamespace(
            name="ping",
            description="Health check",
            inputSchema=None,
        )
        result = mcp_tool_to_openai_function(tool)
        assert result["function"]["parameters"] == {"type": "object", "properties": {}}

    def test_no_description(self):
        tool = SimpleNamespace(
            name="noop",
            description=None,
            inputSchema={"type": "object", "properties": {}},
        )
        result = mcp_tool_to_openai_function(tool)
        assert result["function"]["description"] == ""
