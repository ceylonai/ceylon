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
        let message = Message::data(self.definition().id.clone().unwrap().clone(), message);
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
        node_0.run().await;
    }
}


#[cfg(test)]
mod tests {
    use std::collections::HashMap;
    use std::sync::Arc;
    use std::thread;
    use uniffi::deps::log::debug;
    use sangedama::node::node::EventType;
    use crate::{AgentConfig, AgentCore, AgentDefinition, AgentHandler, MessageHandler, Processor};


    fn create_agent(agent_definition: AgentDefinition) -> AgentCore {
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
        AgentCore::new(
            agent_definition,
            AgentConfig {
                memory_context_size: 10
            },
            Arc::new(OnAgentCoreMessage),
            Some(Arc::new(AgentProcessor {})),
            None,
            Arc::new(AgentEventHandler {}),
            Some(event_handler),
        )
    }

    #[test]
    fn test_start() {
        let workspace_id = "test".to_string();
        env_logger::init();
        debug!("Workspace {} running",workspace_id);


        let agent_1 = create_agent(AgentDefinition {
            name: "writer".to_string(),
            position: "Article Writer".to_string(),
            is_leader: true,
            instructions: vec![],
            responsibilities: vec![],
            ..Default::default()
        });
        let agent_2 = create_agent(AgentDefinition {
            name: "researcher".to_string(),
            position: "Web Researcher".to_string(),
            is_leader: false,
            instructions: vec![],
            responsibilities: vec![],
            ..Default::default()
        });

        // Set the workspace_id on the AgentCore
        agent_1.set_workspace_id(workspace_id.clone());
        agent_2.set_workspace_id(workspace_id.clone());

        let url = format!("{}/{}", "/ip4/0.0.0.0/tcp", "5000");
        let topic = format!("workspace-{}", workspace_id);
        let inputs = vec![1, 2, 3, 4];

        // Call the start method
        // agent_1.start(topic.clone(), url.clone(), inputs.clone()).await;
        // agent_2.start(topic.clone(), url.clone(), inputs.clone()).await;

        let ag1_input = inputs.clone();
        let ag1_topic = topic.clone();
        let ag1_url = url.clone();
        let ag1_thread = thread::spawn(
            move || {
                tokio::runtime::Runtime::new().unwrap().block_on(async move {
                    agent_1.start(ag1_topic.clone(), ag1_url.clone(), ag1_input.clone()).await;
                });
            }
        );


        let ag2_input = inputs.clone();
        let ag2_topic = topic.clone();
        let ag2_url = url.clone();
        let ag2_thread = thread::spawn(
            move || {
                tokio::runtime::Runtime::new().unwrap().block_on(async move {
                    agent_2.start(ag2_topic.clone(), ag2_url.clone(), ag2_input.clone()).await;
                });
                println!( "Hello, world!" );
            }
        );

        ag1_thread.join().unwrap();
        ag2_thread.join().unwrap();
    }
}