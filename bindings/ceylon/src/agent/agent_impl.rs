use std::collections::HashMap;
use std::sync::{Arc, RwLock};

use tokio::sync::Mutex;

use sangedama::node::node::EventType;

use crate::{AgentConfig, AgentDefinition, AgentHandler, EventHandler, MessageHandler, Processor};

pub struct AgentCore {
    _id: RwLock<Option<String>>,
    _workspace_id: RwLock<Option<String>>,
    _definition: AgentDefinition,
    config: AgentConfig,
    on_message: Arc<Mutex<Arc<dyn MessageHandler>>>,
    processor: Arc<Mutex<Option<Arc<dyn Processor>>>>,
    _meta:HashMap<String, String>,
    agent_handler: Arc<Mutex<Arc<dyn AgentHandler>>>,
    event_handlers: HashMap<EventType, Vec<Arc<dyn EventHandler>>>,
}

impl AgentCore {
    pub fn new(
        mut definition: AgentDefinition,
        config: AgentConfig,
        on_message: Arc<dyn MessageHandler>,
        processor: Option<Arc<dyn Processor>>,
        meta: Option<HashMap<String, String>>,
        agent_handler: Arc<dyn AgentHandler>,
        event_handlers: Option<HashMap<EventType, Vec<Arc<dyn EventHandler>>>>,
    ) -> Self {
        Self {
            _id: RwLock::new(None),
            _workspace_id: RwLock::new(None),
            _definition: definition,
            config,
            on_message: Arc::new(Mutex::new(on_message)),
            processor: Arc::new(Mutex::new(processor)),
            _meta: meta.unwrap_or_default(),
            agent_handler: Arc::new(Mutex::new(agent_handler)),
            event_handlers: event_handlers.unwrap_or_default(),
        }
    }

    pub fn id(&self) -> String {
        self._id.read().unwrap().clone().unwrap_or("".to_string())
    }

    pub fn workspace_id(&self) -> String {
        self._workspace_id.read().unwrap().clone().unwrap_or("".to_string())
    }

    pub fn set_workspace_id(&self, workspace_id: String) {
        self._workspace_id.write().unwrap().replace(workspace_id);
    }

    pub fn definition(&self) -> AgentDefinition {
        self._definition.clone()
    }

    pub fn meta(&self) -> HashMap<String, String> {
        self._meta.clone()
    }

    pub async fn broadcast(&self, message: Vec<u8>, to: Option<String>) {
        // Your async logic here
    }

    pub fn log(&self, message: String) {
        println!("{}", message);
    }
}

impl AgentCore {
    pub(crate) async fn start(&self, topic: String, url: String, inputs: Vec<u8>) {
        
        
        
    }
}