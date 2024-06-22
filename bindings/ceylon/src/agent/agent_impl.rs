use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use async_trait::async_trait;

use tokio::sync::Mutex;
use uniffi::deps::log::debug;

use sangedama::node::node::{create_node, EventType, Message};

use crate::{AgentConfig, AgentDefinition, AgentHandler, EventHandler, MessageHandler, Processor};

pub struct AgentCore {
    _id: RwLock<Option<String>>,
    _workspace_id: RwLock<Option<String>>,
    _definition: AgentDefinition,
    config: AgentConfig,
    on_message: Arc<Mutex<Arc<dyn MessageHandler>>>,
    processor: Arc<Mutex<Option<Arc<dyn Processor>>>>,
    _meta: HashMap<String, String>,
    agent_handler: Arc<Mutex<Arc<dyn AgentHandler>>>,
    event_handlers: HashMap<EventType, Vec<Arc<dyn EventHandler>>>,
}

impl AgentCore {
    pub fn new(
        definition: AgentDefinition,
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

    pub async fn broadcast(&self, message: Vec<u8>) {
        let message = Message::data(self.definition().id.clone().unwrap().clone(),message);
    }

    pub fn log(&self, message: String) {
        println!("{}", message);
    }
}

impl AgentCore {
    pub async fn start(&self, topic: String, url: String, inputs: Vec<u8>) {
        let definition = self.definition();
        let agent_name = definition.name.clone();
        let (tx_0, rx_0) = tokio::sync::mpsc::channel::<Message>(100);
        let (mut node_0, mut rx_o_0) = create_node(agent_name.clone(), self.definition().is_leader, rx_0);

        node_0.connect(url.as_str(), topic.as_str());
    }
}

#[tokio::test]
async fn test_start() {
    let workspace_id = "test".to_string();
    env_logger::init();
    debug!("Workspace {} running",workspace_id);
    struct OnAgentCoreMessage;

    #[async_trait::async_trait]
    impl MessageHandler for OnAgentCoreMessage {
        async fn on_message(&self, agent_id: String, message: Vec<u8>) {
            println!("{} Received: {:?}", agent_id, message);
        }
    }

    struct AgentEventHandler;

    #[async_trait::async_trait]
    impl AgentHandler for AgentEventHandler {
        async fn on_agent(&self, agent: AgentDefinition) {
            println!("Agent: {:?}", agent);
        }
    }

    struct AgentProcessor;

    #[async_trait::async_trait]
    impl Processor for AgentProcessor {
        async fn run(&self, input: Vec<u8>) -> () {
            todo!()
        }

        async fn on_start(&self, input: Vec<u8>) -> () {
            todo!()
        }
    }

    let event_handler: HashMap<EventType, Vec<Arc<dyn crate::agent::agent_base::EventHandler>>> = HashMap::new();
    // Create an instance of AgentCore with necessary stubs/mocks
    // mut definition: AgentDefinition,
    // config: AgentConfig,
    // on_message: Arc<dyn MessageHandler>,
    // processor: Option<Arc<dyn Processor>>,
    // meta: Option<HashMap<String, String>>,
    // agent_handler: Arc<dyn AgentHandler>,
    // event_handlers: Option<HashMap<EventType, Vec<Arc<dyn EventHandler>>>>,
    let agent_core = AgentCore::new(
        AgentDefinition::default(),
        AgentConfig {
            memory_context_size: 10
        },
        Arc::new(OnAgentCoreMessage),
        Some(Arc::new(AgentProcessor {})),
        None,
        Arc::new(AgentEventHandler {}),
        Some(event_handler),
    );
    // Set the workspace_id on the AgentCore
    agent_core.set_workspace_id(workspace_id.clone());

    let url = format!("{}/{}", "/ip4/0.0.0.0/tcp", "5000");
    let topic = format!("workspace-{}", workspace_id);
    let inputs = vec![1, 2, 3, 4];

    // Call the start method
    agent_core.start(topic.clone(), url.clone(), inputs.clone()).await;

    // Assertions to verify the behavior
    // For example, you might check if the node connected to the correct url and topic
    // This depends on the implementation details of your Node struct and connect method
}