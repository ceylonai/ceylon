/*
 * Copyright (c) 2023-2025 SYIGEN LTD.
 * Author: Dewmal - dewmal@syigen.com
 * Created: 2025-01-19
 * Ceylon Project - https://github.com/ceylonai/ceylon
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * This file is part of Ceylon Project.
 * Original authors: Dewmal - dewmal@syigen.com
 * For questions and support: https://github.com/ceylonai/ceylon/issues
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
