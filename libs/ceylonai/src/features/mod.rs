pub mod llm_feature;

use async_trait::async_trait;
use serde_json::Value;

#[async_trait]
pub trait Feature {
    async fn execute(&self, input: Value) -> Result<Value, Box<dyn std::error::Error>>;
}
