use std::time::SystemTime;
use serde::{Deserialize, Serialize};
use serde_json::json;

pub enum EventType {
    OnMessage,
    OnSubscribe,
    OnUnsubscribe,
    OnListen,
    OnExpired,
    OnDiscovered,
    OnConnectionClosed,
    OnConnectionEstablished,
}

impl EventType {
    fn as_str(&self) -> &'static str {
        match self {
            EventType::OnMessage => "OnMessage",
            EventType::OnSubscribe => "OnSubscribe",
            EventType::OnUnsubscribe => "OnUnsubscribe",
            EventType::OnListen => "OnListen",
            EventType::OnExpired => "OnExpired",
            EventType::OnDiscovered => "OnDiscovered",
            EventType::OnConnectionClosed => "OnConnectionClosed",
            EventType::OnConnectionEstablished => "OnConnectionEstablished",
        }
    }
}

#[derive(Deserialize, Serialize, Debug, PartialEq, Eq)]
pub enum MessageType {
    Message,
    Event,
}

#[derive(Deserialize, Serialize, Debug)]
pub struct NodeMessage {
    pub data: Vec<u8>,
    pub message: String,
    pub time: u64,
    pub originator: String,
    pub originator_id: String,
    pub r#type: MessageType,
}

impl NodeMessage {
    fn new(
        originator: String,
        originator_id: String,
        message: String,
        data: Vec<u8>,
        message_type: MessageType,
    ) -> Self {
        Self {
            data,
            time: SystemTime::now()
                .duration_since(SystemTime::UNIX_EPOCH)
                .unwrap()
                .as_millis() as u64,
            originator,
            originator_id,
            r#type: message_type,
            message,
        }
    }
    pub(crate) fn event(originator: String, event: EventType) -> Self {
        Self::new(
            originator,
            "SELF".to_string(),
            event.as_str().to_string(),
            vec![],
            MessageType::Event,
        )
    }

    pub fn data(from: String, originator_id: String, data: Vec<u8>) -> Self {
        Self::new(
            from,
            originator_id,
            "DATA-MESSAGE".to_string(),
            data,
            MessageType::Message,
        )
    }

    pub(crate) fn to_json(&self) -> String {
        json!(self).to_string()
    }
}