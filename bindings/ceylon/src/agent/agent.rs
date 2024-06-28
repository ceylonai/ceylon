use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};
use log::{debug, error, info};
use tokio::select;
use tokio::sync::{Mutex, RwLock};

use sangedama::node::{
    node::{create_node},
    message::{NodeMessage, MessageType},
};

use crate::agent::agent_base::{AgentDefinition, MessageHandler, Processor};
use crate::agent::state::{Message, SystemMessage};

pub struct AgentCore {
    _definition: RwLock<AgentDefinition>,
    _workspace_id: Option<String>,
    _processor: Arc<Mutex<Arc<dyn Processor>>>,
    _on_message: Arc<Mutex<Arc<dyn MessageHandler>>>,
    rx_0: Arc<Mutex<tokio::sync::mpsc::Receiver<SystemMessage>>>,
    tx_0: tokio::sync::mpsc::Sender<SystemMessage>,
}

impl AgentCore {
    pub fn new(definition: AgentDefinition, on_message: Arc<dyn MessageHandler>, processor: Arc<dyn Processor>) -> Self {
        let (tx_0, rx_0) = tokio::sync::mpsc::channel::<SystemMessage>(100);
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
        let msg = SystemMessage::Content(Message {
            id: "1".to_string(),
            content: message,
            version: 1,
        });
        self.tx_0.send(msg).await.unwrap();
    }

    pub fn get_tx_0(&self) -> tokio::sync::mpsc::Sender<SystemMessage> {
        self.tx_0.clone()
    }
}

impl AgentCore {
    pub(crate) async fn start(&self, topic: String, url: String, inputs: Vec<u8>) {
        let definition = self.definition().await;
        let agent_name = definition.name.clone();
        let (tx_0, rx_0) = tokio::sync::mpsc::channel::<NodeMessage>(100);
        let (mut node_0, mut message_from_node) = create_node(agent_name.clone(), rx_0).await;
        let on_message = self._on_message.clone();

        self._definition.write().await.id = Some(node_0.id.clone());
        let definition = self.definition().await;


        let rx = Arc::clone(&self.rx_0);
        let definition_handler_process = definition.clone();
        let message_from_agent_impl_handler_process = tokio::spawn(async move {
            loop {
                if let Some(raw_message) = rx.lock().await.recv().await {
                    let name = definition_handler_process.name.clone();
                    match definition.id.clone() {
                        Some(id) => {
                            tx_0.send(NodeMessage::data(name, id, raw_message.to_bytes())).await.unwrap();
                        }
                        None => {
                            error!("Agent {} has no id", name);
                        }
                    };
                }
            }
        });
        let agent_name = definition.name.clone();
        let message_handler_process = tokio::spawn(async move {
            loop {
                if let Some(node_message) = message_from_node.recv().await {
                    if node_message.r#type == MessageType::Message {
                        debug!( "Agent {:?} received message from node {:?}", agent_name, node_message);
                        let data = SystemMessage::from_bytes(node_message.data.clone());
                        match data {
                            SystemMessage::Content(message) => {
                                on_message.lock().await.on_message(agent_name.clone(), message.content, node_message.time).await;
                            }
                            SystemMessage::SyncRequest { last_version } => {
                                // on_message.lock().await.on_sync_request(last_version).await;
                            }
                            SystemMessage::SyncResponse { messages } => {
                                // on_message.lock().await.on_sync_response(messages).await;
                            }
                            SystemMessage::Ack { message_id } => {
                                // on_message.lock().await.on_ack(message_id).await;
                            }
                            SystemMessage::Beacon { time, sender, name } => {
                                info!( "Agent {:?} received beacon {:?} from {:?} at {:?}", agent_name, sender, name, time);
                            }
                        }
                    }
                }
            }
        });

        let processor = self._processor.clone();
        let run_process = tokio::spawn(async move {
            processor.lock().await.run(inputs).await;
        });

        let node_message_sender = self.get_tx_0();
        let definition = self.definition().await;
        let run_beacon = tokio::spawn(async move {
            loop {
                match definition.clone().id {
                    Some(id) => {
                        node_message_sender.send(
                            SystemMessage::Beacon {
                                name: definition.clone().name.clone(),
                                sender: id.clone(),
                                time: SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs(),
                            }
                        ).await.expect("TODO: panic message");
                        tokio::time::sleep(tokio::time::Duration::from_secs(10)).await;
                    }
                    None => {
                        tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;
                        continue;
                    }
                }
            }
        });

        node_0.connect(url.as_str(), topic.as_str());
        node_0.run().await;

        let definition = self.definition().await;
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
            _ = run_beacon => {
                debug!("Agent {:?} run_process stopped", agent_name);
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use std::fmt::Debug;
    use std::sync::Arc;

    use log::info;
    use serde_json::json;

    use crate::{MessageHandler, Processor, Workspace, WorkspaceConfig};
    use crate::agent::agent_base::AgentDefinition;

    use super::AgentCore;

    #[derive(Debug)]
    struct AgentHandler {
        tx_0: tokio::sync::mpsc::Sender<Vec<u8>>,
    }


    #[async_trait::async_trait]
    impl MessageHandler for AgentHandler {
        async fn on_message(&self, agent_id: String, data: Vec<u8>, time: u64) {
            println!("Agent {} received message {:?}", agent_id, data);
        }
    }

    #[async_trait::async_trait]
    impl Processor for AgentHandler {
        async fn run(&self, input: Vec<u8>) -> () {
            println!("Agent received input {:?}", input);
            loop {
                println!("AgentHandler ");
                self.tx_0.send(
                    json!({
                        "data": "Hello World!",
                    }).as_str().unwrap().as_bytes().to_vec()
                ).await.unwrap();
                tokio::time::sleep(std::time::Duration::from_millis(1000)).await;
            }
        }
    }

    fn create_agent(definition: AgentDefinition) -> AgentCore {
        let (tx_0, mut rx_0) = tokio::sync::mpsc::channel::<Vec<u8>>(100);

        let ag = AgentCore::new(definition,
                                Arc::new(AgentHandler {
                                    tx_0: tx_0.clone(),
                                }),
                                Arc::new(AgentHandler {
                                    tx_0: tx_0.clone(),
                                }), );
        return ag;
    }


    #[tokio::test]
    async fn test_agent() {
        let agent = create_agent(AgentDefinition {
            id: None,
            name: "test".to_string(),
            position: "test".to_string(),
            responsibilities: vec!["test".to_string()],
            instructions: vec!["test".to_string()],
        });
        let agent2 = create_agent(AgentDefinition {
            id: None,
            name: "test2".to_string(),
            position: "test2".to_string(),
            responsibilities: vec!["test2".to_string()],
            instructions: vec!["test2".to_string()],
        });

        let workspace = Workspace::new(vec![Arc::new(agent), Arc::new(agent2)], WorkspaceConfig {
            name: "test".to_string(),
            host: "127.0.0.1".to_string(),
            port: 8080,
        });
        workspace.run(json!({"test": "test"}).to_string().as_bytes().to_vec()).await;
    }
}

