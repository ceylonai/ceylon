use serde::{Deserialize, Serialize};
use serde::de::DeserializeOwned;
use crate::AgentDefinition;

#[derive(Deserialize, Serialize, Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum AgentMessageType {
    Handshake,
    Introduce,
    Text,
    Other,
}

pub trait AgentMessageTrait {
    fn get_type(&self) -> AgentMessageType;
    fn into_bytes(self) -> Vec<u8>;
    fn from_bytes(data: Vec<u8>) -> Self
    where
        Self: Sized;
}

pub trait AgentMessageConversions {
    fn from_data<T: Serialize>(r#type: AgentMessageType, data: T) -> Self;
    fn into_data<T: DeserializeOwned>(self) -> Option<T>;
}

#[derive(Deserialize, Serialize, Debug, Clone)]
pub struct AgentMessage {
    pub r#type: AgentMessageType,
    pub data: Vec<u8>,
}

impl AgentMessage {
    pub fn new<T: Serialize>(r#type: AgentMessageType, data: T) -> Self {
        Self {
            r#type,
            data: serde_json::to_vec(&data).unwrap(),
        }
    }
}

impl AgentMessageTrait for AgentMessage {
    fn get_type(&self) -> AgentMessageType {
        self.r#type
    }

    fn into_bytes(self) -> Vec<u8> {
        serde_json::to_vec(&self).unwrap()
    }

    fn from_bytes(data: Vec<u8>) -> Self {
        serde_json::from_slice(&data).unwrap()
    }
}

impl AgentMessageConversions for AgentMessage {
    fn from_data<T: Serialize>(r#type: AgentMessageType, data: T) -> Self {
        Self {
            r#type,
            data: serde_json::to_vec(&data).unwrap(),
        }
    }

    fn into_data<T: DeserializeOwned>(self) -> Option<T> {
        if let Ok(data) = serde_json::from_slice(&self.data) {
            Some(data)
        } else {
            None
        }
    }
}

#[derive(Deserialize, Serialize, Debug, Clone)]
pub struct HandshakeMessage {
    pub message: String,
}

#[derive(Deserialize, Serialize, Debug, Clone)]
pub struct IntroduceMessage {
    pub agent_definition: AgentDefinition,
}

#[derive(Deserialize, Serialize, Debug, Clone)]
pub struct TextMessage {
    pub text: String,
}