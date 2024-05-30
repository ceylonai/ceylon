use reqwest::Client;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug, PartialEq)]
pub struct Message {
    pub role: String,
    pub content: String,
}

#[derive(Serialize, Deserialize, Debug, PartialEq)]
pub struct CompletionRequest {
    pub api_key: String,
    pub model: String,
    pub messages: Vec<Message>,
    pub temperature: f64,
}


#[derive(Serialize, Deserialize, Debug, PartialEq)]
pub struct LogProbs {
    // Define the fields if you have details, for now, assuming it can be null
}

#[derive(Serialize, Deserialize, Debug, PartialEq)]
pub struct ResponseMessage {
    pub role: String,
    pub content: String,
    pub logprobs: Option<LogProbs>,
    pub finish_reason: String,
}

#[derive(Serialize, Deserialize, Debug, PartialEq)]
pub struct Choice {
    pub index: usize,
    pub message: ResponseMessage,
}

#[derive(Serialize, Deserialize, Debug, PartialEq)]
pub struct Usage {
    pub prompt_tokens: usize,
    pub completion_tokens: usize,
    pub total_tokens: usize,
}

#[derive(Serialize, Deserialize, Debug, PartialEq)]
pub struct ChatCompletion {
    pub id: String,
    pub object: String,
    pub created: u64,
    pub model: String,
    pub choices: Vec<Choice>,
    pub usage: Usage,
    pub system_fingerprint: Option<String>,
}

pub async fn open_ai_completion(request: CompletionRequest) -> Result<ChatCompletion, reqwest::Error> {
    let api_key = request.api_key.clone();  // Replace with your actual API key
    let url = "https://api.openai.com/v1/chat/completions";

    let client = Client::new();
    let request_body = request;

    let response = client.post(url)
        .header("Content-Type", "application/json")
        .header("Authorization", format!("Bearer {}", api_key))
        .json(&request_body)
        .send()
        .await?
        .json::<ChatCompletion>()
        .await?;

    Ok(response)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_chat_completion_parsing() {
        // Example JSON data
        let data = r#"
        {
            "id": "chatcmpl-9Ud2fZUpkpTJlcrjzUh5MSlvid4jg",
            "object": "chat.completion",
            "created": 1717086945,
            "model": "gpt-3.5-turbo-0125",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello! I don't have feelings, but I'm here and ready to assist you. How can I help you today?",
                        "logprobs": null,
                        "finish_reason": "stop"
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 15,
                "completion_tokens": 25,
                "total_tokens": 40
            },
            "system_fingerprint": null
        }
        "#;

        // Parse the JSON data
        let chat_completion: ChatCompletion = serde_json::from_str(data).unwrap();

        // Expected values
        let expected_chat_completion = ChatCompletion {
            id: "chatcmpl-9Ud2fZUpkpTJlcrjzUh5MSlvid4jg".to_string(),
            object: "chat.completion".to_string(),
            created: 1717086945,
            model: "gpt-3.5-turbo-0125".to_string(),
            choices: vec![Choice {
                index: 0,
                message: ResponseMessage {
                    role: "assistant".to_string(),
                    content: "Hello! I don't have feelings, but I'm here and ready to assist you. How can I help you today?".to_string(),
                    logprobs: None,
                    finish_reason: "stop".to_string(),
                },
            }],
            usage: Usage {
                prompt_tokens: 15,
                completion_tokens: 25,
                total_tokens: 40,
            },
            system_fingerprint: None,
        };

        // Assert the parsed struct matches the expected struct
        assert_eq!(chat_completion, expected_chat_completion);
    }

    #[tokio::test]
    async fn test_send_request() {
        let request = CompletionRequest {
            api_key: "sk-proj-HsGDt2gSYAZyKINNaS8iT3BlbkFJ4XE0ongb8HG2zrOS4P3i".to_string(),  // Replace with your actual API key
            model: "gpt-3.5-turbo".to_string(),
            messages: vec![Message {
                role: "user".to_string(),
                content: "Hello, AI! How are you?".to_string(),
            }],
            temperature: 0.0,
        };
        let response = open_ai_completion(request).await;
        assert!(response.is_ok());
    }
}
