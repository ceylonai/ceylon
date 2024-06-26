use std::sync::Arc;

use log::{debug, error};
use tokio::select;
use tokio::sync::{Mutex, RwLock};

use sangedama::node::node::{create_node, Message, MessageType};

use crate::agent::agent_base::{AgentDefinition, MessageHandler, Processor};

pub struct AgentCore {
    _definition: RwLock<AgentDefinition>,
    _workspace_id: Option<String>,
    _processor: Arc<Mutex<Arc<dyn Processor>>>,
    _on_message: Arc<Mutex<Arc<dyn MessageHandler>>>,
    rx_0: Arc<Mutex<tokio::sync::mpsc::Receiver<Message>>>,
    tx_0: tokio::sync::mpsc::Sender<Message>,
}

impl AgentCore {
    pub fn new(definition: AgentDefinition, on_message: Arc<dyn MessageHandler>, processor: Arc<dyn Processor>) -> Self {
        let (tx_0, rx_0) = tokio::sync::mpsc::channel::<Message>(100);
        Self {
            _definition: RwLock::new(definition),
            _workspace_id: None,
            _on_message: Arc::new(Mutex::new(on_message)),
            _processor: Arc::new(Mutex::new(processor)),
            rx_0: Arc::new(Mutex::new(rx_0)),
            tx_0,
        }
    }

    pub async fn definition(&self) -> AgentDefinition {
        self._definition.read().await.clone()
    }

    pub async fn id(&self) -> String {
        self._definition.read().await.id.clone().unwrap_or("".to_string())
    }

    pub fn workspace_id(&self) -> String {
        self._workspace_id.clone().unwrap_or("".to_string())
    }

    pub fn set_workspace_id(&mut self, workspace_id: String) {
        self._workspace_id = Option::from(workspace_id);
    }

    pub async fn broadcast(&self, message: Vec<u8>) {
        let definition = self.definition().await;
        let name = definition.name.clone();
        match definition.id.clone() {
            Some(id) => {
                self.tx_0.send(Message::data(name, id, message)).await.unwrap();
            }
            None => {
                error!("Agent {} has no id", name);
            }
        };
    }
}

impl AgentCore {
    pub(crate) async fn start(&self, topic: String, url: String, inputs: Vec<u8>) {
        let definition = self.definition().await;
        let agent_name = definition.name.clone();
        let (tx_0, rx_0) = tokio::sync::mpsc::channel::<Message>(100);
        let (mut node_0, mut message_from_node) = create_node(agent_name.clone(), true, rx_0);
        let on_message = self._on_message.clone();

        self._definition.write().await.id = Some(node_0.id.clone());
        let definition = self.definition().await;


        let rx = Arc::clone(&self.rx_0);
        let message_from_agent_impl_handler_process = tokio::spawn(async move {
            loop {
                if let Some(message) = rx.lock().await.recv().await {
                    debug!( "Agent {:?}  message to dispatch {:?}", agent_name, message);
                    tx_0.clone().send(message).await.unwrap();
                }
            }
        });
        let agent_name = definition.name.clone();
        let message_handler_process = tokio::spawn(async move {
            loop {
                if let Some(message) = message_from_node.recv().await {
                    if message.r#type == MessageType::Message {
                        debug!( "Agent {:?} received message from node {:?}", agent_name, message);
                        on_message.lock().await.on_message(agent_name.clone(), message).await;
                    }
                }
            }
        });

        let processor = self._processor.clone();
        let run_process = tokio::spawn(async move {
            processor.lock().await.run(inputs).await;
        });

        node_0.connect(url.as_str(), topic.as_str());
        node_0.run().await;

        let agent_name = definition.name.clone();
        debug!( "Agent {:?} started", agent_name);


        select! {
            _ = message_from_agent_impl_handler_process => {
                debug!("Agent {:?} message_from_agent_impl_handler_process stopped", agent_name);
            },
            _ = message_handler_process => {
                debug!("Agent {:?} message_handler_process stopped", agent_name);
            },
            _ = run_process => {
                debug!("Agent {:?} run_process stopped", agent_name);
            },
        }
    }
}


