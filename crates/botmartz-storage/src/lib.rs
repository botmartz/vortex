use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, HashMap};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JevSpanRecord {
    pub chunk_id: String,
    pub doc_id: String,
    pub ast_node_id: String,
    pub merkle_hash: String,
    pub doc_char_span: (usize, usize),
    pub doc_token_span: (usize, usize),
    pub parent_blend_alpha: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StorageTriadConfig {
    pub lancedb_uri: String,
    pub tantivy_index_dir: String,
    pub duckdb_path: String,
}

/// Deterministic Okapi BM25 lexical index for zero-sprawl local retrieval.
#[derive(Debug, Default, Clone)]
pub struct Bm25Index {
    docs: BTreeMap<String, Vec<String>>,
    doc_freq: HashMap<String, usize>,
    total_len: usize,
}

impl Bm25Index {
    pub fn new() -> Self {
        Self::default()
    }

    fn tokenize(text: &str) -> Vec<String> {
        text.to_lowercase()
            .split(|c: char| !c.is_alphanumeric())
            .filter(|t| t.len() >= 2)
            .map(ToString::to_string)
            .collect()
    }

    pub fn index_document(&mut self, doc_id: &str, text: &str) {
        if let Some(old_tokens) = self.docs.remove(doc_id) {
            self.total_len = self.total_len.saturating_sub(old_tokens.len());
            let unique: std::collections::HashSet<&String> = old_tokens.iter().collect();
            for term in unique {
                if let Some(cnt) = self.doc_freq.get_mut(term) {
                    *cnt = cnt.saturating_sub(1);
                }
            }
        }
        let tokens = Self::tokenize(text);
        self.total_len += tokens.len();
        let unique: std::collections::HashSet<&String> = tokens.iter().collect();
        for term in unique {
            *self.doc_freq.entry(term.clone()).or_insert(0) += 1;
        }
        self.docs.insert(doc_id.to_string(), tokens);
    }

    pub fn search(&self, query: &str, limit: usize) -> Vec<(String, f64)> {
        if self.docs.is_empty() {
            return Vec::new();
        }
        let q_tokens = Self::tokenize(query);
        let n = self.docs.len() as f64;
        let avgdl = (self.total_len as f64) / n.max(1.0);
        let k1 = 1.5;
        let b = 0.75;

        let mut scores: Vec<(String, f64)> = Vec::new();
        for (doc_id, tokens) in &self.docs {
            let dl = tokens.len() as f64;
            let mut tf_map: HashMap<&str, usize> = HashMap::new();
            for t in tokens {
                *tf_map.entry(t.as_str()).or_insert(0) += 1;
            }
            let mut score = 0.0;
            for qt in &q_tokens {
                if let Some(&tf) = tf_map.get(qt.as_str()) {
                    let df = *self.doc_freq.get(qt).unwrap_or(&0) as f64;
                    let idf = ((n - df + 0.5) / (df + 0.5) + 1.0).ln();
                    let tf_f = tf as f64;
                    let denom = tf_f + k1 * (1.0 - b + b * (dl / avgdl.max(1.0)));
                    score += idf * ((tf_f * (k1 + 1.0)) / denom.max(1e-9));
                }
            }
            if score > 0.0 {
                scores.push((doc_id.clone(), score));
            }
        }
        scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        scores.truncate(limit);
        scores
    }
}

/// Reciprocal Rank Fusion (RRF) combining lexical BM25 ranks with dense JEV vector ranks.
pub fn reciprocal_rank_fusion(
    lexical_ranks: &[String],
    vector_ranks: &[String],
    k: f64,
) -> Vec<(String, f64)> {
    let mut fused: HashMap<String, f64> = HashMap::new();
    for (idx, doc_id) in lexical_ranks.iter().enumerate() {
        *fused.entry(doc_id.clone()).or_insert(0.0) += 1.0 / (k + (idx as f64) + 1.0);
    }
    for (idx, doc_id) in vector_ranks.iter().enumerate() {
        *fused.entry(doc_id.clone()).or_insert(0.0) += 1.0 / (k + (idx as f64) + 1.0);
    }
    let mut ranked: Vec<(String, f64)> = fused.into_iter().collect();
    ranked.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    ranked
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_bm25_and_rrf() {
        let mut idx = Bm25Index::new();
        idx.index_document("n1", "RadixAttention KV cache acceleration with SGLang");
        idx.index_document("n2", "DuckDB deterministic SQL queries for KAG tables");
        let hits = idx.search("SGLang RadixAttention", 5);
        assert_eq!(hits[0].0, "n1");

        let fused = reciprocal_rank_fusion(
            &["n1".into(), "n2".into()],
            &["n2".into(), "n1".into()],
            60.0,
        );
        assert_eq!(fused.len(), 2);
    }
}
