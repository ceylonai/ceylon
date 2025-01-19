/*
 * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 * Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
 *
 */

// In data.rs
use serde::{Deserialize, Serialize};
use serde_json::json;

#[derive(Debug, Serialize, Deserialize)]
pub enum MessageType {
    Broadcast,
    Direct { to_peer: String },
}

#[derive(Debug, Serialize, Deserialize)]
pub enum EventType {
    Subscribe { topic: String, peer_id: String },
    Unsubscribe { topic: String, peer_id: String },
    PeerDiscovered { peer_id: String },
    PeerDisconnected { peer_id: String },
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
        message_type: MessageType,
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

    pub fn create_direct_message(from: String, to: String, data: Vec<u8>) -> Self {
        NodeMessage::Message {
            time: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs_f64() as u64,
            created_by: from,
            message_type: MessageType::Direct { to_peer: to },
            data,
        }
    }

    pub fn create_broadcast_message(from: String, data: Vec<u8>) -> Self {
        NodeMessage::Message {
            time: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs_f64() as u64,
            created_by: from,
            message_type: MessageType::Broadcast,
            data,
        }
    }
}
// (from, data, to)
pub type NodeMessageTransporter = (String, Vec<u8>, Option<String>);
