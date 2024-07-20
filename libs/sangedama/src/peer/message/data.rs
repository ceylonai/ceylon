use serde::{Deserialize, Serialize};
use serde_json::json;

#[derive(Debug, Serialize, Deserialize)]
pub enum EventType {
    Subscribe {
        topic: String,
        peer_id: String,
    },
    Unsubscribe{
        topic: String,
        peer_id: String,
    },
}

#[derive(Debug, Serialize, Deserialize)]
pub enum NodeMessage {
    Event {
        time: u64,
        created_by: String,
        event: EventType,
    },
    Message {
        time: u64,
        created_by: String,
        data: Vec<u8>,
    },
}

impl NodeMessage {
    pub fn from_bytes(bytes: Vec<u8>) -> Self {
        serde_json::from_slice(&bytes).unwrap()
    }
    pub fn to_json(&self) -> String {
        json!(self).to_string()
    }

    pub fn to_bytes(&self) -> Vec<u8> {
        serde_json::to_vec(self).unwrap()
    }
} 