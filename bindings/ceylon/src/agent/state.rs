use std::time::{SystemTime, UNIX_EPOCH};

use log::info;
use serde::{Deserialize, Serialize};
use tokio::sync::RwLock;

pub static SYSTEM_MESSAGE_CONTENT_TYPE: &str = "ceylon.system.message.content";
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Message {
    pub sender: String,
    pub sender_id: Option<String>,
    pub id: String,
    pub content: Vec<u8>,
    pub version: u128,
}

impl Message {
    pub fn new(content: Vec<u8>, sender_id: Option<String>, sender: String) -> Self {
        Self {
            id: uuid::Uuid::new_v4().to_string(),
            content,
            version: SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos(),
            sender_id,
            sender,
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub enum SystemMessage {
    Content(Message),
    SyncRequest { versions: Vec<u128> },
    SyncResponse { messages: Vec<Message> },
    Beacon {
        name: String,
        sender: String,
        time: u128,
        sync_hash: u128,
    },
}

impl SystemMessage {
    pub fn get_id(&self) -> String {
        match self {
            SystemMessage::Content(message) => message.id.clone(),
            SystemMessage::SyncRequest { .. } => "sync_request".to_string(),
            SystemMessage::SyncResponse { .. } => "sync_response".to_string(),
            SystemMessage::Beacon { .. } => "beacon".to_string(),
        }
    }
    pub fn get_type(&self) -> String {
        match self {
            SystemMessage::Content(..) => SYSTEM_MESSAGE_CONTENT_TYPE.to_string(),
            SystemMessage::SyncRequest { .. } => "sync_request".to_string(),
            SystemMessage::SyncResponse { .. } => "sync_response".to_string(),
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

pub type AgentStateMessageList = Vec<Message>;

#[derive(Debug)]
pub struct AgentStateSnap {
    pub messages: AgentStateMessageList,
    pub last_version: u128,
}

impl AgentStateSnap {
    pub fn versions(&self) -> Vec<u128> {
        self.messages
            .iter()
            .map(|message| message.version)
            .collect()
    }

    pub fn sync_hash(&self) -> u128 {
        let mut hash = 0u128;
        for message in &self.messages {
            hash ^= message.version;
        }
        hash
    }

    pub fn missing_versions(&self, versions: Vec<u128>) -> Vec<u128> {
        let mut missing_versions = Vec::new();
        for version in versions {
            if !self.versions().contains(&version) {
                missing_versions.push(version);
            }
        }
        missing_versions
    }
    
    pub fn get_messages(&self, versions: Vec<u128>) -> Vec<Message> {
        let mut messages = Vec::new();
        for version in versions {
            if let Some(message) = self.messages.iter().find(|message| message.version == version) {
                messages.push(message.clone());
            }
        }
        messages
    }
}

#[derive(Default)]
pub struct AgentState {
    messages: RwLock<AgentStateMessageList>,
    last_version: RwLock<u128>,
}

impl AgentState {
    pub fn new() -> Self {
        Self {
            messages: RwLock::new(Vec::new()),
            last_version: RwLock::new(0),
        }
    }

    pub async fn add_message(&self, message: Message) {
        info!("Started add_message ordered by version");
        self.messages.write().await.push(message);
        self.order_by_version().await;
        let last_message = self.get_last_message().await;
        let last_version = self.last_version.read().await.clone();
        info!( "Last version: {}, Last message version: {}", last_version, last_message.version);
        if last_message.version > last_version {
            let mut last_version = self.last_version.write().await;
            *last_version = last_message.version;
        }
        info!("Finished add_message ordered by version");
    }

    pub async fn get_last_message(&self) -> Message {
        let messages = self.messages.read().await.clone();
        messages.last().unwrap().clone()
    }

    pub async fn order_by_version(&self) {
        info!("Started updating ordered by version");
        let mut messages = self.messages.read().await.clone();
        let mut ordered_messages = Vec::new();
        messages.sort_by(|a, b| a.version.cmp(&b.version));
        for message in messages {
            ordered_messages.push(message);
        }
        let mut update_messages = self.messages.write().await;
        update_messages.clear();
        update_messages.extend(ordered_messages);
        info!("Finished updating ordered by version");
    }

    pub async fn request_snapshot(&self) -> AgentStateSnap {
        let messages = self.messages.read().await.clone();
        let last_version = self.last_version.read().await.clone();
        AgentStateSnap { messages, last_version }
    }
}