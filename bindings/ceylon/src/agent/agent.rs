use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};
use log::{debug, error, info};
use tokio::{select, signal};
use tokio::sync::{mpsc, Mutex, oneshot, RwLock};

use sangedama::node::{
    node::{create_node},
    message::{NodeMessage, MessageType},
};

use crate::agent::agent_base::{AgentDefinition, MessageHandler, Processor};
use crate::agent::state::{AgentState, Message, SystemMessage};

pub struct AgentCore {
    _definition: RwLock<AgentDefinition>,
    _workspace_id: Option<String>,
    _processor: Arc<Mutex<Arc<dyn Processor>>>,
    _on_message: Arc<Mutex<Arc<dyn MessageHandler>>>,
    receiver_from_outside_rx: Arc<Mutex<tokio::sync::mpsc::Receiver<SystemMessage>>>,
    sender_from_outside_tx: tokio::sync::mpsc::Sender<SystemMessage>,

    shutdown_tx: Arc<mpsc::Sender<()>>,
    shutdown_rx: Arc<Mutex<mpsc::Receiver<()>>>,
}

impl AgentCore {
    pub fn new(definition: AgentDefinition, on_message: Arc<dyn MessageHandler>, processor: Arc<dyn Processor>) -> Self {
        let (tx_0, rx_0) = tokio::sync::mpsc::channel::<SystemMessage>(100);
        let (shutdown_tx, shutdown_rx) = mpsc::channel::<()>(1);

        Self {
            _definition: RwLock::new(definition),
            _workspace_id: None,
            _on_message: Arc::new(Mutex::new(on_message)),
            _processor: Arc::new(Mutex::new(processor)),
            receiver_from_outside_rx: Arc::new(Mutex::new(rx_0)),
            sender_from_outside_tx: tx_0,

            shutdown_tx: Arc::new(shutdown_tx),
            shutdown_rx: Arc::new(Mutex::new(shutdown_rx)),
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
        let name = self.definition().await.name.clone();
        let id = self.id().await;
        let msg = SystemMessage::Content(Message::new(message, Some(id), name));
        self.sender_from_outside_tx.send(msg).await.unwrap();
    }

    pub fn get_tx_0(&self) -> tokio::sync::mpsc::Sender<SystemMessage> {
        self.sender_from_outside_tx.clone()
    }

    pub async fn stop(&self) {
        info!( "Agent {} stop", self.definition().await.name);
        self.shutdown_tx.clone().send(()).await.unwrap();
    }
}

impl AgentCore {
    pub async fn start(&self, topic: String, url: String, inputs: Vec<u8>) {
        let definition = self.definition().await;
        let agent_name = definition.name.clone();
        let (tx_0, rx_0) = tokio::sync::mpsc::channel::<NodeMessage>(100);
        let (mut node_0, mut message_from_node) = create_node(agent_name.clone(), rx_0).await;
        let on_message = self._on_message.clone();

        self._definition.write().await.id = Some(node_0.id.clone());
        let definition = self.definition().await;

        let (agent_state_message_sender_tx, mut agent_state_message_receiver) = tokio::sync::mpsc::channel::<Message>(100);

        let agent_state = Arc::new(Mutex::new(AgentState::new()));

        let mut is_requst_to_shutdown = false;

        // State Message Handle here
        let agent_state_clone = Arc::clone(&agent_state);
        let agent_state_message_processor = tokio::spawn(async move {
            loop {
                if is_requst_to_shutdown {
                    break;
                }
                if let Some(message) = agent_state_message_receiver.recv().await {
                    debug!( "Message: {:?}", message);
                    {
                        agent_state_clone.lock().await.add_message(message).await;
                        debug!("AgentState updated");
                    }
                    {
                        let snapshot = agent_state_clone.lock().await.request_snapshot().await;
                        debug!("Snapshot: {:?}", snapshot);
                    }
                }
            }
        });


        // Message distributed to other nodes
        let receiver_from_outside_rx = Arc::clone(&self.receiver_from_outside_rx);
        let definition_handler_process = definition.clone();
        let agent_state_message_sender_tx_c1 = agent_state_message_sender_tx.clone();
        let agent_id = definition.id.clone().unwrap_or("".to_string());
        let message_from_agent_impl_handler_process = tokio::spawn(async move {
            loop {
                if is_requst_to_shutdown {
                    break;
                }
                if tx_0.is_closed() {
                    break;
                }
                if let Some(raw_message) = receiver_from_outside_rx.lock().await.recv().await {
                    let name = definition_handler_process.name.clone();
                    match definition.id.clone() {
                        Some(id) => {
                            let msg = NodeMessage::data(name, id, raw_message.to_bytes());
                            tx_0.send(msg).await.unwrap();

                            if let SystemMessage::Content(message) = raw_message {
                                let mut msg = message.clone();
                                if msg.sender_id.is_none() {
                                    msg.sender_id = Some(agent_id.clone());
                                }
                                agent_state_message_sender_tx_c1.send(msg).await.unwrap();
                            }
                        }
                        None => {
                            error!("Agent {} has no id", name);
                        }
                    };
                }
            }
        });

        // Agent receive message from other nodes
        let agent_name = definition.name.clone();
        let agent_state_message_sender_tx_c1 = agent_state_message_sender_tx.clone();
        let agent_state_clone_handle_process = Arc::clone(&agent_state);
        let node_message_sender = self.get_tx_0();
        let message_handler_process = tokio::spawn(async move {
            loop {
                if is_requst_to_shutdown {
                    break;
                }
                if let Some(node_message) = message_from_node.recv().await {
                    if node_message.r#type == MessageType::Message {
                        debug!( "Agent {:?} received message from node {:?}", agent_name, node_message);
                        let sender_id = node_message.originator_id;
                        let sender_name = node_message.originator;
                        let data = SystemMessage::from_bytes(node_message.data.clone());
                        let snapshot = agent_state_clone_handle_process.lock().await.request_snapshot().await;
                        match data {
                            SystemMessage::Content(message) => {
                                agent_state_message_sender_tx_c1.send(message.clone()).await.unwrap();
                                on_message.lock().await.on_message(sender_id, message.content, node_message.time).await;
                            }
                            SystemMessage::SyncRequest { versions } => {
                                debug!( "Agent {:?} received sync request from node {:?}", sender_name, versions);
                                let mut missing_versions = vec![];

                                // If requested list miss something in snapshot
                                let snapshot_versions = snapshot.versions();
                                for snapshot_version in snapshot_versions {
                                    if !versions.contains(&snapshot_version) {
                                        missing_versions.push(snapshot_version);
                                    }
                                }

                                if !missing_versions.is_empty() {
                                    let missing_messages = snapshot.get_messages(missing_versions.clone());
                                    let sync_request = SystemMessage::SyncResponse {
                                        messages: missing_messages,
                                    };
                                    node_message_sender.send(sync_request).await.expect("TODO: panic message");
                                }
                            }
                            SystemMessage::SyncResponse { messages } => {
                                debug!( "Agent {:?} received sync response from node {:?}", agent_name, messages);

                                for message in messages {
                                    agent_state_message_sender_tx_c1.send(message.clone()).await.unwrap();
                                }
                            }
                            SystemMessage::Beacon { time, sender, name, sync_hash } => {
                                debug!( "Agent {:?} received beacon {:?} from {:?} at {:?}", agent_name, sender, name, time);

                                if sync_hash != snapshot.sync_hash() {
                                    debug!("Sync Hash: {:?} from {:?} not equal to snapshot hash: {:?}", sync_hash, sender, snapshot.sync_hash());

                                    let sync_request = SystemMessage::SyncRequest {
                                        versions: snapshot.versions(),
                                    };
                                    node_message_sender.send(sync_request).await.expect("TODO: panic message");
                                }
                            }
                        }
                    }
                }
            }
        });

        // Handle run process 
        let processor = self._processor.clone();
        let run_process = tokio::spawn(async move {
            processor.lock().await.run(inputs).await;
        });

        // Handle sync process
        let node_message_sender = self.get_tx_0();
        let definition = self.definition().await;
        let agent_state_clone_sync_process = Arc::clone(&agent_state);
        let run_sync_request = tokio::spawn(async move {
            loop {
                match definition.clone().id {
                    Some(id) => {
                        let snapshot = agent_state_clone_sync_process.lock().await.request_snapshot().await;
                        let beacon_message = SystemMessage::Beacon {
                            time: SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs_f64(),
                            sender: id.clone(),
                            name: definition.name.clone(),
                            sync_hash: snapshot.sync_hash(),
                        };
                        node_message_sender.send(beacon_message).await.unwrap();
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

        let shutdown_rx_ = Arc::clone(&self.shutdown_rx);

        let agent_name_clone = definition.name.clone();
        let task_shutdown = tokio::spawn(async move {
            loop {
                if let Some(_) = shutdown_rx_.lock().await.recv().await {
                    debug!("Agent {:?} received shutdown signal", agent_name_clone);
                    is_requst_to_shutdown = true;
                    break;
                }
            }
        });

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
            _ = run_sync_request => {
                debug!("Agent {:?} run_sync_request stopped", agent_name);
            },
            _ = agent_state_message_processor => {
                debug!("Agent {:?} agent_state_message_processor stopped", agent_name);
            },
            _ = task_shutdown => {
                debug!("Agent {:?} agent_state_message_processor stopped", agent_name);
            },
             _ = signal::ctrl_c() => {
                println!("Agent {:?} received exit signal", agent_name);
                // Perform any necessary cleanup here
                is_requst_to_shutdown = true;
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
            host: "0.0.0.0".to_string(),
            port: 0,
        });
        workspace.run(json!({"test": "test"}).to_string().as_bytes().to_vec()).await;
    }
}

