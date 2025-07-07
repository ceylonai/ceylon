use serde::{Serialize, Deserialize};
use serde_json::Value;

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct AnpMessage {
    pub version: String,
    pub msg_type: String,
    pub from: String,
    pub to: String,
    pub timestamp: String,
    pub payload: Value,
    pub signature: String,
}

impl AnpMessage {
    pub fn new(from: String, to: String, payload: Value, signature: String) -> Self {
        Self {
            version: "1.0".to_string(),
            msg_type: "request".to_string(),
            from,
            to,
            timestamp: chrono::Utc::now().to_rfc3339(),
            payload,
            signature,
        }
    }
}
