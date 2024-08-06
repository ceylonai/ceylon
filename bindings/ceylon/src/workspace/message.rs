use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub enum AgentMessage {
    SystemMessage {
        id: u64,
        message: Vec<u8>,
    },
    NodeMessage {
        id: u64,
        message: Vec<u8>,
    },
    AgentIntroduction {
        id: String,
        role: String,
        name: String,
        topic: String,
    },
}

impl AgentMessage {
    pub fn to_bytes(&self) -> Vec<u8> {
        serde_json::to_vec(self).unwrap()
    }

    pub fn from_bytes(bytes: Vec<u8>) -> Self {
        serde_json::from_slice(&bytes).unwrap()
    }
}
