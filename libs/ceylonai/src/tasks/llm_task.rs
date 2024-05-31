use async_trait::async_trait;
use crate::services::open_ai::{CompletionRequest, Message, open_ai_completion};
use crate::tasks::Task;

// Implement a concrete Task for AI requests
pub struct LLMTask {
    pub api_key: String,
}

impl LLMTask {
    pub(crate) fn new(api_key: String) -> Self {
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
