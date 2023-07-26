use pyo3::{prelude::*, Py, PyAny, pyclass, pymethods};

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
    pub function: FunctionInfo,
    pub event: EventType,
}

#[pymethods]
impl EventProcessor {
    #[new]
    pub fn new(function: FunctionInfo, event: EventType) -> Self {
        Self {
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
    START,
    STOP,
    READY,
    MESSAGE,
    SYSTEM_EVENT,
    DATA,
    ERROR,
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
    pub fn new(content: String,
               event_type: EventType,
               creator: String,
               origin_type: OriginatorType) -> Self {
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