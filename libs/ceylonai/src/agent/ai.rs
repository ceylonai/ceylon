use std::error::Error;
use async_trait::async_trait;
use serde_json::Value;
use crate::agent::base::BaseAgent;
use crate::features::llm_feature::LLMTask;
use crate::features::Feature;

pub struct LLMAgent {
    pub role: String,
    pub responsibility: String,
    pub instructions: String,
    task: LLMTask,
}

impl LLMAgent {
    pub fn new(role: String, responsibility: String, api_key: String, model: String) -> Self {
        Self {
            role,
            responsibility,
            instructions: "Respond to the following user input.".to_string(),
            task: LLMTask::new(api_key, model),
        }
    }
}

#[async_trait]
impl BaseAgent for LLMAgent {
    fn get_role(&self) -> String {
        self.role.clone()
    }

    fn get_responsibility(&self) -> String {
        self.responsibility.clone()
    }

    fn get_instructions(&self) -> String {
        self.instructions.clone()
    }

    async fn execute_task(&self, input: Value) -> Result<Value, Box<dyn Error>> {
        self.task.execute(input).await
    }
}

#[cfg(test)]
mod tests {
    use serde_json::json;
    use crate::common::setup_env;

    use super::*;

    #[tokio::test]
    async fn test_llm_agent() {
        setup_env();
        let agent = LLMAgent::new(
            "Agent1".to_string(),
            "AI Role".to_string(),
            std::env::var("OPENAI_API_KEY").unwrap(),
            "gpt-3.5-turbo".to_string());
        // Execute the task and notify listeners
        let result = agent.execute_task(json!({
            "content": "Hello, AI! How are you?"
        })).await;
        match result {
            Ok(result) => assert_eq!(result["content"].to_string().is_empty(), false),
            Err(e) => {
                panic!("Error: {}", e);
            }
        }
    }
}
