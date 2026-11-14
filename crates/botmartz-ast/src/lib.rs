use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum AstNodeType {
    Document,
    Section,
    Subsection,
    Paragraph,
    Table,
    CodeBlock,
    Equation,
    Figure,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AstNode {
    pub node_id: String,
    pub doc_id: String,
    pub node_type: AstNodeType,
    pub title: Option<String>,
    pub content: String,
    pub depth: u32,
    pub structural_path: Vec<String>,
    pub parent_id: Option<String>,
    pub children_ids: Vec<String>,
    pub prev_sibling_id: Option<String>,
    pub next_sibling_id: Option<String>,
    pub char_span: (usize, usize),
    pub merkle_hash: Option<String>,
}

impl AstNode {
    pub fn content_hash(&self) -> String {
        let mut hasher = blake3::Hasher::new();
        hasher.update(
            format!(
                "{:?}|{}|{}",
                self.node_type,
                self.title.as_deref().unwrap_or(""),
                self.content.trim()
            )
            .as_bytes(),
        );
        hasher.finalize().to_hex().to_string()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum MerkleChangeType {
    Added,
    Modified,
    Deleted,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct MerkleDelta {
    pub node_id: String,
    pub change_type: MerkleChangeType,
    pub old_merkle_hash: Option<String>,
    pub new_merkle_hash: Option<String>,
    pub structural_path: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DocumentAst {
    pub doc_id: String,
    pub root_id: String,
    pub nodes: BTreeMap<String, AstNode>,
}

impl DocumentAst {
    pub fn compute_merkle_root(&mut self) -> Option<String> {
        let root_id = self.root_id.clone();
        self.compute_node_merkle(&root_id)
    }

    fn compute_node_merkle(&mut self, node_id: &str) -> Option<String> {
        let (content_hash, children) = {
            let node = self.nodes.get(node_id)?;
            (node.content_hash(), node.children_ids.clone())
        };
        let mut child_hashes = Vec::with_capacity(children.len());
        for cid in children {
            if let Some(ch) = self.compute_node_merkle(&cid) {
                child_hashes.push(ch);
            }
        }
        let mut hasher = blake3::Hasher::new();
        hasher.update(content_hash.as_bytes());
        for ch in child_hashes {
            hasher.update(ch.as_bytes());
        }
        let final_hash = hasher.finalize().to_hex().to_string();
        if let Some(node) = self.nodes.get_mut(node_id) {
            node.merkle_hash = Some(final_hash.clone());
        }
        Some(final_hash)
    }
}

/// Parse Markdown into a hierarchical H-RAG `DocumentAst` and compute its BLAKE3 Merkle tree.
pub fn parse_markdown_ast(doc_id: &str, markdown: &str) -> DocumentAst {
    let root_id = format!("{doc_id}::root");
    let root_node = AstNode {
        node_id: root_id.clone(),
        doc_id: doc_id.to_string(),
        node_type: AstNodeType::Document,
        title: Some(doc_id.to_string()),
        content: String::new(),
        depth: 0,
        structural_path: vec![doc_id.to_string()],
        parent_id: None,
        children_ids: Vec::new(),
        prev_sibling_id: None,
        next_sibling_id: None,
        char_span: (0, markdown.len()),
        merkle_hash: None,
    };

    let mut nodes: BTreeMap<String, AstNode> = BTreeMap::new();
    nodes.insert(root_id.clone(), root_node);
    let mut section_stack: Vec<String> = vec![root_id.clone()];

    let mut offset = 0usize;
    let mut sec_idx = 0usize;
    let mut para_idx = 0usize;
    let mut table_idx = 0usize;
    let mut code_idx = 0usize;

    let mut in_code_block = false;
    let mut code_buf = String::new();
    let mut code_start = 0usize;

    let mut in_table = false;
    let mut table_buf = String::new();
    let mut table_start = 0usize;

    let attach_node = |nodes: &mut BTreeMap<String, AstNode>, parent_id: &str, mut node: AstNode| {
        let node_id = node.node_id.clone();
        let prev_id = nodes
            .get_mut(parent_id)
            .and_then(|parent| {
                let prev = parent.children_ids.last().cloned();
                parent.children_ids.push(node_id.clone());
                prev
            });
        if let Some(prev_id) = prev_id {
            node.prev_sibling_id = Some(prev_id.clone());
            if let Some(prev) = nodes.get_mut(&prev_id) {
                prev.next_sibling_id = Some(node_id.clone());
            }
        }
        nodes.insert(node_id, node);
    };

    for segment in markdown.split_inclusive('\n') {
        let start_char = offset;
        let end_char = offset + segment.len();
        offset = end_char;
        let trimmed = segment.trim();

        if trimmed.starts_with("```") {
            if in_table {
                table_idx += 1;
                let parent_id = section_stack.last().cloned().unwrap_or_else(|| root_id.clone());
                let (p_depth, p_path) = {
                    let p = &nodes[&parent_id];
                    (p.depth, p.structural_path.clone())
                };
                let node = AstNode {
                    node_id: format!("{doc_id}::table_{table_idx}"),
                    doc_id: doc_id.to_string(),
                    node_type: AstNodeType::Table,
                    title: None,
                    content: table_buf.trim().to_string(),
                    depth: p_depth + 1,
                    structural_path: p_path,
                    parent_id: Some(parent_id.clone()),
                    children_ids: Vec::new(),
                    prev_sibling_id: None,
                    next_sibling_id: None,
                    char_span: (table_start, start_char),
                    merkle_hash: None,
                };
                attach_node(&mut nodes, &parent_id, node);
                in_table = false;
                table_buf.clear();
            }

            if !in_code_block {
                in_code_block = true;
                code_start = start_char;
                code_buf.clear();
                code_buf.push_str(segment);
            } else {
                code_buf.push_str(segment);
                code_idx += 1;
                let parent_id = section_stack.last().cloned().unwrap_or_else(|| root_id.clone());
                let (p_depth, p_path) = {
                    let p = &nodes[&parent_id];
                    (p.depth, p.structural_path.clone())
                };
                let node = AstNode {
                    node_id: format!("{doc_id}::code_{code_idx}"),
                    doc_id: doc_id.to_string(),
                    node_type: AstNodeType::CodeBlock,
                    title: None,
                    content: code_buf.trim().to_string(),
                    depth: p_depth + 1,
                    structural_path: p_path,
                    parent_id: Some(parent_id.clone()),
                    children_ids: Vec::new(),
                    prev_sibling_id: None,
                    next_sibling_id: None,
                    char_span: (code_start, end_char),
                    merkle_hash: None,
                };
                attach_node(&mut nodes, &parent_id, node);
                in_code_block = false;
                code_buf.clear();
            }
            continue;
        }

        if in_code_block {
            code_buf.push_str(segment);
            continue;
        }

        if trimmed.starts_with('|') && trimmed.ends_with('|') {
            if !in_table {
                in_table = true;
                table_start = start_char;
                table_buf.clear();
            }
            table_buf.push_str(segment);
            continue;
        } else if in_table {
            table_idx += 1;
            let parent_id = section_stack.last().cloned().unwrap_or_else(|| root_id.clone());
            let (p_depth, p_path) = {
                let p = &nodes[&parent_id];
                (p.depth, p.structural_path.clone())
            };
            let node = AstNode {
                node_id: format!("{doc_id}::table_{table_idx}"),
                doc_id: doc_id.to_string(),
                node_type: AstNodeType::Table,
                title: None,
                content: table_buf.trim().to_string(),
                depth: p_depth + 1,
                structural_path: p_path,
                parent_id: Some(parent_id.clone()),
                children_ids: Vec::new(),
                prev_sibling_id: None,
                next_sibling_id: None,
                char_span: (table_start, start_char),
                merkle_hash: None,
            };
            attach_node(&mut nodes, &parent_id, node);
            in_table = false;
            table_buf.clear();
        }

        if trimmed.is_empty() {
            continue;
        }

        let hash_count = trimmed.chars().take_while(|c| *c == '#').count();
        if (1..=6).contains(&hash_count) && trimmed.chars().nth(hash_count) == Some(' ') {
            sec_idx += 1;
            let level = hash_count as u32;
            let title = trimmed[hash_count + 1..].trim().to_string();
            while section_stack.len() > 1 {
                let top_id = section_stack.last().unwrap();
                if nodes[top_id].depth >= level {
                    section_stack.pop();
                } else {
                    break;
                }
            }
            let parent_id = section_stack.last().cloned().unwrap_or_else(|| root_id.clone());
            let mut path = nodes[&parent_id].structural_path.clone();
            path.push(title.clone());
            let node_id = format!("{doc_id}::sec_{sec_idx}");
            let node = AstNode {
                node_id: node_id.clone(),
                doc_id: doc_id.to_string(),
                node_type: if level <= 2 {
                    AstNodeType::Section
                } else {
                    AstNodeType::Subsection
                },
                title: Some(title),
                content: trimmed.to_string(),
                depth: level,
                structural_path: path,
                parent_id: Some(parent_id.clone()),
                children_ids: Vec::new(),
                prev_sibling_id: None,
                next_sibling_id: None,
                char_span: (start_char, end_char),
                merkle_hash: None,
            };
            attach_node(&mut nodes, &parent_id, node);
            section_stack.push(node_id);
        } else {
            para_idx += 1;
            let parent_id = section_stack.last().cloned().unwrap_or_else(|| root_id.clone());
            let (p_depth, p_path) = {
                let p = &nodes[&parent_id];
                (p.depth, p.structural_path.clone())
            };
            let node = AstNode {
                node_id: format!("{doc_id}::para_{para_idx}"),
                doc_id: doc_id.to_string(),
                node_type: AstNodeType::Paragraph,
                title: None,
                content: trimmed.to_string(),
                depth: p_depth + 1,
                structural_path: p_path,
                parent_id: Some(parent_id.clone()),
                children_ids: Vec::new(),
                prev_sibling_id: None,
                next_sibling_id: None,
                char_span: (start_char, end_char),
                merkle_hash: None,
            };
            attach_node(&mut nodes, &parent_id, node);
        }
    }

    if in_table {
        table_idx += 1;
        let parent_id = section_stack.last().cloned().unwrap_or_else(|| root_id.clone());
        let (p_depth, p_path) = {
            let p = &nodes[&parent_id];
            (p.depth, p.structural_path.clone())
        };
        let node = AstNode {
            node_id: format!("{doc_id}::table_{table_idx}"),
            doc_id: doc_id.to_string(),
            node_type: AstNodeType::Table,
            title: None,
            content: table_buf.trim().to_string(),
            depth: p_depth + 1,
            structural_path: p_path,
            parent_id: Some(parent_id.clone()),
            children_ids: Vec::new(),
            prev_sibling_id: None,
            next_sibling_id: None,
            char_span: (table_start, offset),
            merkle_hash: None,
        };
        attach_node(&mut nodes, &parent_id, node);
    }

    let mut ast = DocumentAst {
        doc_id: doc_id.to_string(),
        root_id,
        nodes,
    };
    ast.compute_merkle_root();
    ast
}

/// Top-down O(k log N) subtree-pruning Merkle diff between an older and newer `DocumentAst`.
pub fn diff_trees(old_ast: &DocumentAst, new_ast: &DocumentAst) -> Vec<MerkleDelta> {
    let mut deltas = Vec::new();
    let old_root = old_ast.nodes.get(&old_ast.root_id);
    let new_root = new_ast.nodes.get(&new_ast.root_id);

    if let (Some(o_r), Some(n_r)) = (old_root, new_root) {
        if o_r.merkle_hash.is_some() && o_r.merkle_hash == n_r.merkle_hash {
            return deltas;
        }
    }

    let mut visited = BTreeSet::new();
    diff_subtree(old_ast, new_ast, &old_ast.root_id, &new_ast.root_id, &mut deltas, &mut visited);

    // Handle structural moves or detached IDs not visited via root traversal
    let old_ids: BTreeSet<&String> = old_ast.nodes.keys().collect();
    let new_ids: BTreeSet<&String> = new_ast.nodes.keys().collect();

    for nid in new_ids.difference(&old_ids) {
        if !visited.contains(*nid) {
            let n_node = &new_ast.nodes[*nid];
            deltas.push(MerkleDelta {
                node_id: (*nid).clone(),
                change_type: MerkleChangeType::Added,
                old_merkle_hash: None,
                new_merkle_hash: n_node.merkle_hash.clone(),
                structural_path: n_node.structural_path.clone(),
            });
        }
    }
    for nid in old_ids.difference(&new_ids) {
        if !visited.contains(*nid) {
            let o_node = &old_ast.nodes[*nid];
            deltas.push(MerkleDelta {
                node_id: (*nid).clone(),
                change_type: MerkleChangeType::Deleted,
                old_merkle_hash: o_node.merkle_hash.clone(),
                new_merkle_hash: None,
                structural_path: o_node.structural_path.clone(),
            });
        }
    }

    deltas
}

fn collect_subtree_deltas(
    ast: &DocumentAst,
    node_id: &str,
    change_type: MerkleChangeType,
    deltas: &mut Vec<MerkleDelta>,
    visited: &mut BTreeSet<String>,
) {
    if let Some(node) = ast.nodes.get(node_id) {
        visited.insert(node_id.to_string());
        let (old_h, new_h) = match change_type {
            MerkleChangeType::Added => (None, node.merkle_hash.clone()),
            MerkleChangeType::Deleted => (node.merkle_hash.clone(), None),
            MerkleChangeType::Modified => (None, node.merkle_hash.clone()),
        };
        deltas.push(MerkleDelta {
            node_id: node.node_id.clone(),
            change_type: change_type.clone(),
            old_merkle_hash: old_h,
            new_merkle_hash: new_h,
            structural_path: node.structural_path.clone(),
        });
        for cid in &node.children_ids {
            collect_subtree_deltas(ast, cid, change_type.clone(), deltas, visited);
        }
    }
}

fn diff_subtree(
    old_ast: &DocumentAst,
    new_ast: &DocumentAst,
    old_id: &str,
    new_id: &str,
    deltas: &mut Vec<MerkleDelta>,
    visited: &mut BTreeSet<String>,
) {
    let o_node = match old_ast.nodes.get(old_id) {
        Some(n) => n,
        None => return,
    };
    let n_node = match new_ast.nodes.get(new_id) {
        Some(n) => n,
        None => return,
    };
    visited.insert(old_id.to_string());
    visited.insert(new_id.to_string());

    // Prune entire unchanged subtree in O(1)
    if o_node.merkle_hash.is_some() && o_node.merkle_hash == n_node.merkle_hash {
        return;
    }

    if o_node.content_hash() != n_node.content_hash() {
        deltas.push(MerkleDelta {
            node_id: n_node.node_id.clone(),
            change_type: MerkleChangeType::Modified,
            old_merkle_hash: o_node.merkle_hash.clone(),
            new_merkle_hash: n_node.merkle_hash.clone(),
            structural_path: n_node.structural_path.clone(),
        });
    }

    let old_children: BTreeSet<&String> = o_node.children_ids.iter().collect();
    let new_children: BTreeSet<&String> = n_node.children_ids.iter().collect();

    for cid in old_children.intersection(&new_children) {
        diff_subtree(old_ast, new_ast, cid, cid, deltas, visited);
    }
    for cid in new_children.difference(&old_children) {
        collect_subtree_deltas(new_ast, cid, MerkleChangeType::Added, deltas, visited);
    }
    for cid in old_children.difference(&new_children) {
        collect_subtree_deltas(old_ast, cid, MerkleChangeType::Deleted, deltas, visited);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_markdown_ast_and_merkle_diff() {
        let md_v1 = "# Architecture\nVORTEX uses Rust.\n## Storage\n| Engine | Role |\n| --- | --- |\n| DuckDB | KAG |\n";
        let md_v2 = "# Architecture\nVORTEX uses Rust and BLAKE3.\n## Storage\n| Engine | Role |\n| --- | --- |\n| DuckDB | KAG |\n";

        let ast_v1 = parse_markdown_ast("doc1", md_v1);
        let ast_v2 = parse_markdown_ast("doc1", md_v2);

        assert!(ast_v1.nodes[&ast_v1.root_id].merkle_hash.is_some());
        assert_ne!(
            ast_v1.nodes[&ast_v1.root_id].merkle_hash,
            ast_v2.nodes[&ast_v2.root_id].merkle_hash
        );

        let deltas = diff_trees(&ast_v1, &ast_v2);
        assert_eq!(deltas.len(), 1);
        assert_eq!(deltas[0].node_id, "doc1::para_1");
        assert_eq!(deltas[0].change_type, MerkleChangeType::Modified);
        assert_eq!(
            ast_v1.nodes["doc1::table_1"].merkle_hash,
            ast_v2.nodes["doc1::table_1"].merkle_hash
        );
    }
}
