#[async_trait::async_trait]
pub trait AgentBase {
    async fn run_(&self, inputs: Vec<u8>);
}