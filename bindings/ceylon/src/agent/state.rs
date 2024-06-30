use std::collections::{HashMap, HashSet};
use std::time::{SystemTime, UNIX_EPOCH};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Message {
    pub id: String,
    pub content: Vec<u8>,
    pub version: u128,
}

impl Message {
    pub fn new(content: Vec<u8>) -> Self {
        Self {
            id: uuid::Uuid::new_v4().to_string(),
            content,
            version: SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos(),
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub enum SystemMessage {
    Content(Message),
    SyncRequest { last_version: u64 },
    SyncResponse { messages: Vec<Message> },
    Ack { message_id: String },
    Beacon {
        name: String,
        sender: String,
        time: u64,
    },
}

impl SystemMessage {
    pub fn get_id(&self) -> String {
        match self {
            SystemMessage::Content(message) => message.id.clone(),
            SystemMessage::SyncRequest { .. } => "sync_request".to_string(),
            SystemMessage::SyncResponse { .. } => "sync_response".to_string(),
            SystemMessage::Ack { message_id } => message_id.clone(),
            SystemMessage::Beacon { .. } => "beacon".to_string(),
        }
    }

    pub fn to_bytes(&self) -> Vec<u8> {
        serde_json::to_vec(self).unwrap()
    }

    pub fn from_bytes(bytes: Vec<u8>) -> Self {
        serde_json::from_slice(&bytes).unwrap()
    }
}

pub struct AgentState {
    received_messages: HashMap<String, Message>,
    last_version: u128,
    pending_acks: HashSet<String>,
}

impl AgentState {
    fn new() -> Self {
        AgentState {
            received_messages: HashMap::new(),
            last_version: 0,
            pending_acks: HashSet::new(),
        }
    }

    fn add_message(&mut self, message: Message) -> bool {
        if message.version > self.last_version {
            let id = message.id.clone();
            self.received_messages.insert(id.clone(), message.clone());
            self.last_version = message.version;
            self.pending_acks.insert(message.id);
            true
        } else {
            false
        }
    }

    fn get_messages_after(&self, version: u128) -> Vec<Message> {
        self.received_messages.values()
            .filter(|m| m.version > version)
            .cloned()
            .collect()
    }

    fn acknowledge_message(&mut self, message_id: &String) {
        self.pending_acks.remove(message_id);
    }
}