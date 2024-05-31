use crate::agent::base::BaseAgent;
use crate::tasks::llm_task::LLMTask;
use crate::tasks::Task;

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
