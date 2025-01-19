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