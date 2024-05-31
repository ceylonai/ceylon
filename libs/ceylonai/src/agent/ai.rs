use async_trait::async_trait;

use crate::agent::base::BaseAgent;
use crate::agent::Task;
use crate::services::open_ai::{CompletionRequest, Message, open_ai_completion};

// Implement a concrete Task for AI requests
pub struct LLMTask {
    pub api_key: String,
}

impl LLMTask {
    fn new(api_key: String) -> Self {
        Self { api_key }
    }
}

#[async_trait]
impl Task<String, String> for LLMTask {
    async fn execute(&self, input: String) -> String {
        let request_body = CompletionRequest {
            api_key: self.api_key.to_string(),
            model: "gpt-3.5-turbo".to_string(),
            messages: vec![Message {
                role: "user".to_string(),
                content: input.clone(),
            }],
            temperature: 0.7,
        };

        match open_ai_completion(request_body).await {
            Ok(response) => response.choices[0].message.content.clone(),
            Err(_) => "Error occurred during AI completion".to_string(),
        }
    }
}

pub struct LLMAgent<Tt, Rt>
    where
        Tt: Send + Sync,
        Rt: Send + Sync,
{
    base: BaseAgent<Tt, Rt>,
    pub model: String,
}

impl<Tt, Rt> LLMAgent<Tt, Rt>
    where
        Tt: Send + Sync,
        Rt: Send + Sync, LLMTask: Task<Tt, Rt>
{
    pub fn new(name: String, role: String, api_key: String) -> Self {
        Self {
            base: BaseAgent::new(name, role, Box::new(LLMTask::new(api_key))),
            model: "gpt-3.5-turbo".to_string(),
        }
    }

    pub async fn execute_task(&self, input: Tt) -> Result<Rt, Box<dyn std::error::Error>> {
        self.base.execute_task(input).await
    }
}

#[cfg(test)]
mod tests {
    use crate::common::setup_env;
    use super::*;


    #[tokio::test]
    async fn test_base_agent_with_ai_task() {
        setup_env();
        // Create a BaseAgent
        let agent: BaseAgent<String, String, > = BaseAgent::new(
            "Agent1".to_string(),
            "AI Role".to_string(),
            Box::new(LLMTask::new(std::env::var("OPENAI_API_KEY").unwrap())),
        );


        // Execute the task and notify listeners
        let result = agent.execute_task("Some input".to_string()).await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_llm_agent() {
        setup_env();
        let agent = LLMAgent::new("Agent1".to_string(), "AI Role".to_string(), std::env::var("OPENAI_API_KEY").unwrap());
        let result = agent.execute_task("Some input".to_string()).await;
        assert!(result.is_ok());
    }
}
