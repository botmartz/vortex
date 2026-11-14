use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct McpToolDescriptor {
    pub name: String,
    pub description: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct A2aCapabilities {
    pub streaming: bool,
    pub push_notifications: bool,
    pub state_transition_history: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct A2aAgentCard {
    pub name: String,
    pub description: String,
    pub url: String,
    pub version: String,
    pub capabilities: A2aCapabilities,
    pub skills: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct A2aTaskRequest {
    pub jsonrpc: String,
    pub id: Value,
    pub method: String,
    pub params: Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct A2aTaskResponse {
    pub jsonrpc: String,
    pub id: Value,
    pub result: Value,
}

pub fn registered_mcp_tools() -> Vec<McpToolDescriptor> {
    vec![
        McpToolDescriptor {
            name: "vortex_ingest_document".into(),
            description: "Parse document into H-RAG AST, compute BLAKE3 Merkle diff, extract tables into DuckDB, and index JEV Late-Chunking spans.".into(),
        },
        McpToolDescriptor {
            name: "vortex_hybrid_query".into(),
            description: "Execute hybrid H-RAG + JEV + KAG (DuckDB) + CAG (Radix KV-cache) query with Evaluation Sentinel verification.".into(),
        },
        McpToolDescriptor {
            name: "vortex_kag_sql_query".into(),
            description: "Execute deterministic read-only analytical SQL against the embedded DuckDB KAG store.".into(),
        },
        McpToolDescriptor {
            name: "vortex_inspect_ast_merkle".into(),
            description: "Inspect H-RAG DocumentAST nodes and BLAKE3 Merkle provenance hashes.".into(),
        },
        McpToolDescriptor {
            name: "vortex_a2a_delegate".into(),
            description: "Delegate a structured task across the Botmartz VORTEX A2A agent mesh.".into(),
        },
        McpToolDescriptor {
            name: "vortex_model_vault_status".into(),
            description: "Report local AI Vault models, Ollama status, and CAG KV-cache residency.".into(),
        },
    ]
}

pub fn build_vortex_a2a_card(base_url: &str) -> A2aAgentCard {
    A2aAgentCard {
        name: "Botmartz VORTEX Omni-RAG Engine".into(),
        description: "Sovereign Enterprise Omni-RAG Engine (H-RAG + JEV + CAG + KAG + BLAKE3 Merkle + Abstention Sentinel)".into(),
        url: base_url.to_string(),
        version: "0.1.0".into(),
        capabilities: A2aCapabilities {
            streaming: true,
            push_notifications: false,
            state_transition_history: true,
        },
        skills: vec![
            "hrag-ast-parsing".into(),
            "jev-late-chunking".into(),
            "cag-radix-cache".into(),
            "kag-duckdb-sql".into(),
            "sentinel-abstention".into(),
        ],
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mcp_tools_and_a2a_card() {
        let tools = registered_mcp_tools();
        assert_eq!(tools.len(), 6);
        let card = build_vortex_a2a_card("http://localhost:8420");
        assert!(card.capabilities.state_transition_history);
        let json = serde_json::to_string(&card).unwrap();
        assert!(json.contains("Botmartz VORTEX"));
    }
}
