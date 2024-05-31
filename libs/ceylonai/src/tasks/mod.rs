pub mod llm_task;

use async_trait::async_trait;
use serde_json::Value;

#[async_trait]
pub trait Task {
    async fn execute(&self, input: Value) -> Result<Value, Box<dyn std::error::Error>>;
}
