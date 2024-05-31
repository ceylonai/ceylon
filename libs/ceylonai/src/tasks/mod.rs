pub mod llm_task;

use async_trait::async_trait;

#[async_trait]
pub trait Task<T: Send + Sync, R: Send + Sync>: Send + Sync {
    async fn execute(&self, input: T) -> R;
}