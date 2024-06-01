use async_trait::async_trait;
use serde_json::json;

use crate::services::open_ai::{CompletionRequestData, Message, open_ai_completion, OpenAICompletionRequest};
use crate::features::Feature;

// Implement a concrete Task for AI requests
pub struct LLMTask {
    pub api_key: String,
    pub model: String,
}

impl LLMTask {
    pub(crate) fn new(api_key: String, model: String) -> Self {
        Self { api_key, model }
    }
}

#[async_trait]
impl Feature for LLMTask {
    async fn execute(&self, input: serde_json::Value) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
        let content = input["content"].as_str().unwrap().to_string();
        let request_body = OpenAICompletionRequest {
            api_key: self.api_key.to_string(),
            data: CompletionRequestData {
                model: self.model.to_string(),
                messages: vec![Message {
                    role: "user".to_string(),
                    content,
                }],
                temperature: 0.7,
            },
        };

        let response = open_ai_completion(request_body).await;
        return match response {
            Ok(response) => {
                Ok(json!({
                    "content": response.choices[0].message.content,
                    "finish_reason": response.choices[0].message.finish_reason
                }))
            }
            Err(e) => {
                Err(
                    Box::new(
                        e
                    )
                )
            }
        };
    }
}
