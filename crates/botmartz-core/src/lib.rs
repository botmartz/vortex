pub use botmartz_ast as ast;
pub use botmartz_mcp as mcp;
pub use botmartz_storage as storage;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_core_end_to_end_ast_and_bm25() {
        let ast = ast::parse_markdown_ast(
            "vortex_spec",
            "# VORTEX\nRadixAttention KV caching.\n## KAG\nDuckDB SQL execution.\n",
        );
        let mut idx = storage::Bm25Index::new();
        for (id, node) in &ast.nodes {
            if !node.content.is_empty() {
                idx.index_document(id, &node.content);
            }
        }
        let hits = idx.search("DuckDB SQL", 3);
        assert_eq!(hits[0].0, "vortex_spec::para_2");
        assert_eq!(mcp::registered_mcp_tools().len(), 6);
    }
}
