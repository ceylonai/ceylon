use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

use pyo3::{pyclass, pymethods, Py, PyAny};
use serde::{Deserialize, Serialize};

#[pyclass]
#[derive(Debug, Clone)]
pub struct FunctionInfo {
    #[pyo3(get, set)]
    pub handler: Py<PyAny>,
    #[pyo3(get, set)]
    pub is_async: bool,
    #[pyo3(get, set)]
    pub number_of_params: u8,
}

#[pymethods]
impl FunctionInfo {
    #[new]
    pub fn new(handler: Py<PyAny>, is_async: bool, number_of_params: u8) -> Self {
        Self {
            handler,
            is_async,
            number_of_params,
        }
    }
}

#[pyclass]
#[derive(Debug, Clone)]
pub struct EventProcessor {
    pub name: String,
    pub function: FunctionInfo,
    pub event: EventType,
}

#[pymethods]
impl EventProcessor {
    #[new]
    pub fn new(name: String, function: FunctionInfo, event: EventType) -> Self {
        Self {
            name,
            function,
            event,
        }
    }
}

#[pyclass]
#[derive(Debug, Clone)]
pub enum OriginatorType {
    System,
    Agent,
}

#[pyclass]
#[derive(Debug, Clone, PartialOrd, PartialEq)]
pub enum EventType {
    Start,
    Stop,
    Ready,
    Message,
    SystemEvent,
    Data,
    Error,
}

#[pyclass]
#[derive(Debug, Clone)]
pub struct Event {
    /// Event Data Message
    #[pyo3(get, set)]
    pub content: String,

    #[pyo3(get, set)]
    pub event_type: EventType,

    #[pyo3(get, set)]
    pub origin_type: OriginatorType,

    #[pyo3(get, set)]
    pub creator: String,

    #[pyo3(get, set)]
    pub dispatch_time: String,
}

#[pymethods]
impl Event {
    #[new]
    pub fn new(
        content: String,
        event_type: EventType,
        creator: String,
        origin_type: OriginatorType,
    ) -> Self {
        let dispatch_time = chrono::Utc::now().to_rfc3339();
        Self {
            content,
            event_type,
            creator,
            dispatch_time,
            origin_type,
        }
    }
}

pub enum TransportStatus {
    Started,
    Stopped,
    Data(String),
    Error(String),
    Info(String),
    PeerDiscovered(String),
    PeerConnected(String),
    PeerDisconnected(String),
}

#[derive(Serialize, Deserialize)]
pub struct TransportMessage {
    pub unique_id: String,
    pub data: String,
    pub dispatch_time: String,
}

impl TransportMessage {
    fn new(data: String) -> Self {
        let dispatch_time = chrono::Utc::now().to_rfc3339();
        let unique_id = calculate_hash(&format!("{dispatch_time}{data}")).to_string();
        Self {
            unique_id,
            data,
            dispatch_time,
        }
    }

    pub fn using_bytes(data: String) -> Vec<u8> {
        let server_message = TransportMessage::new(data);
        let message_str = serde_json::to_string(&server_message).unwrap();
        message_str.into_bytes()
    }
    pub fn from_bytes(data: Vec<u8>) -> Self {
        let message_str = String::from_utf8(data).unwrap();
        let server_message = serde_json::from_str(&message_str).unwrap();
        server_message
    }
}

fn calculate_hash<T: Hash>(t: &T) -> u64 {
    let mut s = DefaultHasher::new();
    t.hash(&mut s);
    s.finish()
}
