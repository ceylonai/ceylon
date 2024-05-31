use async_trait::async_trait;

#[async_trait]
pub trait BaseAgent {
    fn get_role(&self) -> String;
    fn get_responsibility(&self) -> String;
    fn get_instructions(&self) -> String;
    async fn execute_task(&self, input: serde_json::Value) -> Result<serde_json::Value, Box<dyn std::error::Error>>;
} 