/*
 * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 * Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
 *
 */

// In message.rs
use serde::{Deserialize, Serialize};
use sangedama::peer::message::data::NodeMessage;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub enum MessageType {
    Broadcast,
    Direct { to_peer: String },
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub enum AgentMessage {
    SystemMessage {
        id: u64,
        message: Vec<u8>,
    },
    NodeMessage {
        id: u64,
        message: Vec<u8>,
        message_type: MessageType,
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

    pub fn create_direct_message(message: Vec<u8>, to_peer: String) -> Self {
        AgentMessage::NodeMessage {
            id: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos() as u64,
            message,
            message_type: MessageType::Direct { to_peer },
        }
    }

    pub fn create_broadcast_message(message: Vec<u8>) -> Self {
        AgentMessage::NodeMessage {
            id: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos() as u64,
            message,
            message_type: MessageType::Broadcast,
        }
    }
}