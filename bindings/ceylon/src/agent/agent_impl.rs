use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use log::{error, info};
use tokio::select;

use tokio::sync::Mutex;
use uniffi::deps::log::debug;

use sangedama::node::node::{create_node, EventType, Message};

use crate::{AgentConfig, AgentDefinition, AgentHandler, EventHandler, MessageHandler, Processor};
use crate::agent::memory_blockchain::Blockchain;

pub struct AgentCore {
    _id: RwLock<Option<String>>,
    _workspace_id: RwLock<Option<String>>,
    _definition: RwLock<AgentDefinition>,
    config: AgentConfig,
    on_message: Arc<Mutex<Arc<dyn MessageHandler>>>,
    processor: Arc<Mutex<Option<Arc<dyn Processor>>>>,
    _meta: HashMap<String, String>,
    agent_handler: Arc<Mutex<Arc<dyn AgentHandler>>>,
    event_handlers: HashMap<EventType, Vec<Arc<dyn EventHandler>>>,

    _out_side_message_receiver: Arc<Mutex<tokio::sync::mpsc::Receiver<Vec<u8>>>>,
    _out_side_message_sender: tokio::sync::mpsc::Sender<Vec<u8>>,

    _message_block_chain: Arc<Mutex<Blockchain>>,
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
        let (tx_0, rx_0) = tokio::sync::mpsc::channel::<Vec<u8>>(100);

        Self {
            _id: RwLock::new(None),
            _workspace_id: RwLock::new(None),
            _definition: RwLock::new(definition),
            config,
            on_message: Arc::new(Mutex::new(on_message)),
            processor: Arc::new(Mutex::new(processor)),
            _meta: meta.unwrap_or_default(),
            agent_handler: Arc::new(Mutex::new(agent_handler)),
            event_handlers: event_handlers.unwrap_or_default(),

            _out_side_message_receiver: Arc::new(Mutex::new(rx_0)),
            _out_side_message_sender: tx_0,

            _message_block_chain: Arc::new(Mutex::new(Blockchain::new())),
        }
    }

    pub fn id(&self) -> String {
        self._id.read().unwrap().clone().unwrap_or("".to_string())
    }

    pub fn workspace_id(&self) -> String {
        self._workspace_id
            .read()
            .unwrap()
            .clone()
            .unwrap_or("".to_string())
    }

    pub fn set_workspace_id(&self, workspace_id: String) {
        self._workspace_id.write().unwrap().replace(workspace_id);
    }

    pub fn definition(&self) -> AgentDefinition {
        self._definition.read().unwrap().clone()
    }

    pub fn meta(&self) -> HashMap<String, String> {
        self._meta.clone()
    }

    pub async fn broadcast(&self, _message: Vec<u8>) {
        self.get_tx().send(_message.clone()).await.unwrap();
    }

    pub fn log(&self, message: String) {
        println!("{}", message);
    }

    pub fn get_tx(&self) -> tokio::sync::mpsc::Sender<Vec<u8>> {
        self._out_side_message_sender.clone()
    }
}

impl AgentCore {
    pub async fn start(&self, topic: String, port: u16, inputs: Vec<u8>) {
        let definition = self.definition();
        let agent_name = definition.name.clone();


        


        let (mut node_0, mut msg_from_other_nodes, send_to_other_nodes) =
            create_node(agent_name.clone(), self.definition().is_leader);

        let (blockchain_tx, mut blockchain_rx) = tokio::sync::mpsc::channel::<Vec<u8>>(100);
        
        let blockchain = self._message_block_chain.clone();
        let is_leader = self.definition().is_leader;
        tokio::spawn(async move {
            let mut blockchain = blockchain.lock().await;

            if is_leader{
                blockchain.init_block();
            }
            
            while let Some(message) = blockchain_rx.recv().await {
                blockchain.add_block(message.clone());
            }
        });
        
        
        

        self._id.write().unwrap().replace(node_0.id.clone());
        self._definition.write().unwrap().id = Some(node_0.id.clone());

        let definition = self.definition();

        info!("Agent {:?} Started", definition.clone());

        let processor = self.processor.clone();
        let processor_on_start = inputs.clone();
        if let Some(processor) = processor.lock().await.clone() {
            processor.on_start(processor_on_start).await;
        }

        node_0.connect(topic.as_str(), None, port.clone());
        let node_start_handle = tokio::spawn(async move {
            debug!("Agent {} started", agent_name);
            node_0.run().await;
        });


        let mut dispatched_message_to_boradcats_rx = self._out_side_message_receiver.clone();
        let blockchain_tx_1 = blockchain_tx.clone();
        let out_side_message_broadcast_handle = tokio::spawn(async move {
            while let Some(message) = dispatched_message_to_boradcats_rx.lock().await.recv().await {
                info!("Received to dispatched: {:?} {:?}", message.clone(),definition.id);
                let agent_id = definition.id.clone().unwrap().clone();
                info!( "Agent id: {:?}", agent_id.clone());
                
                
                // Add data to blockchain
                blockchain_tx_1.send(message.clone()).await.expect("TODO: panic message");
                
                
                let data = Message::data(
                    agent_id,
                    message,
                );
                match send_to_other_nodes
                    .send(data)
                    .await {
                    Ok(_) => {
                        debug!("Sent to other nodes");
                    }
                    Err(_) => {
                        error!("Failed to send to other nodes");
                    }
                };
            }
        });

        let processor_input = inputs.clone();
        let processor = self.processor.clone();
        let processor_handle = tokio::spawn(async move {
            if let Some(processor) = processor.lock().await.clone() {
                processor.run(processor_input).await;
            }
        });

        let blockchain_tx_2 = blockchain_tx.clone();
        let message_handler = self.on_message.clone();
        let out_side_message_receiver_handle = tokio::spawn(async move {
            while let Some(msg) = msg_from_other_nodes.recv().await {
                let sender_id = msg.sender.clone();
                let data = msg.data.clone();

                info!("Message From Other Nodes: {:?}", sender_id.clone());


                // Add data to blockchain
                blockchain_tx_2.send(data.clone()).await.expect("TODO: panic message");

                message_handler
                    .lock()
                    .await
                    .on_message(sender_id.clone(), data)
                    .await;
            }
        });

        let agent_name = definition.name.clone();
        select! {
            _ = node_start_handle => {
                debug!("Agent {} node_start_handle finished", agent_name);
            },
            _ = out_side_message_broadcast_handle => {
                debug!("Agent {} out_side_message_broadcast_handle finished", agent_name);
            },
            _ = processor_handle => {
                debug!("Agent {} processor_handle finished", agent_name);
            },
            _ = out_side_message_receiver_handle => {
                debug!("Agent {} out_side_message_receiver_handle finished", agent_name);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use crate::{AgentConfig, AgentCore, AgentDefinition, AgentHandler, MessageHandler, Processor};
    use async_trait::async_trait;
    use log::info;
    use sangedama::node::node::{EventType, Message};
    use serde::{Deserialize, Serialize};
    use serde_json::json;
    use std::collections::HashMap;
    use std::sync::Arc;
    use std::thread;
    use std::time::Duration;
    use tokio::sync::Mutex;
    use uniffi::deps::log::debug;

    struct MessageHandlerImpl {
        send_message_to_broadcast_tx: tokio::sync::mpsc::Sender<Vec<u8>>,
    }

    #[async_trait]
    impl MessageHandler for MessageHandlerImpl {
        async fn on_message(&self, agent_id: String, message: Vec<u8>) {
            info!("{}  test Received: {:?}", agent_id, message);
        }
    }

    struct AgentHandlerImpl {
        send_message_to_broadcast_tx: tokio::sync::mpsc::Sender<Vec<u8>>,
    }

    #[async_trait]
    impl AgentHandler for AgentHandlerImpl {
        async fn on_agent(&self, agent: AgentDefinition) {
            println!("Agent: {:?}", agent);
        }
    }

    struct ProcessorImpl {
        send_message_to_broadcast_tx: tokio::sync::mpsc::Sender<Vec<u8>>,
        agent_definition: AgentDefinition,
    }

    #[derive(Deserialize, Serialize, Debug, Clone)]
    struct AgentMessage {
        text: String,
    }

    #[async_trait]
    impl Processor for ProcessorImpl {
        async fn run(&self, input: Vec<u8>) -> () {
            loop {
                let ran_number = rand::random::<u64>() % 10;
                tokio::time::sleep(Duration::from_millis(1000 * ran_number)).await;
                self.send_message_to_broadcast_tx
                    .send(
                        json!(AgentMessage {
                            text: format!("Hello {}", self.agent_definition.name),
                        })
                            .to_string()
                            .as_bytes()
                            .to_vec(),
                    )
                    .await
                    .unwrap();
            }
        }

        async fn on_start(&self, input: Vec<u8>) -> () {
            info!("on_start: {:?}", input);
        }
    }

    struct Agent {
        definition: AgentDefinition,
    }

    impl Agent {
        pub fn new(definition: AgentDefinition) -> Self {
            Self { definition }
        }

        pub async fn start(&self, topic: String, port: u16, inputs: Vec<u8>, workspace_id: String) {
            let event_handler: HashMap<
                EventType,
                Vec<Arc<dyn crate::agent::agent_base::EventHandler>>,
            > = HashMap::new();
            let (send_message_tx, mut send_message_rx) = tokio::sync::mpsc::channel(100);
            let event_handler: HashMap<
                EventType,
                Vec<Arc<dyn crate::agent::agent_base::EventHandler>>,
            > = HashMap::new();

            let agent_definition = self.definition.clone();

            let agent_core = AgentCore::new(
                agent_definition.clone(),
                AgentConfig {
                    memory_context_size: 10,
                },
                Arc::new(MessageHandlerImpl {
                    send_message_to_broadcast_tx: send_message_tx.clone(),
                }),
                Some(Arc::new(ProcessorImpl {
                    send_message_to_broadcast_tx: send_message_tx.clone(),
                    agent_definition: self.definition.clone(),
                })),
                None,
                Arc::new(AgentHandlerImpl {
                    send_message_to_broadcast_tx: send_message_tx.clone(),
                }),
                Some(event_handler),
            );

            let topic_clone = topic.clone();
            let port_clone = port.clone();
            let inputs_clone = inputs.clone();
            let workspace_id_clone = workspace_id.clone();

            agent_core.set_workspace_id(workspace_id_clone);

            let agent_broadcaster = agent_core.get_tx();

            let t1 = tokio::spawn(async move {
                agent_core
                    .start(topic_clone, port_clone, inputs_clone)
                    .await;
            });

            let t2 = tokio::spawn(async move {
                while let Some(message) = send_message_rx.recv().await {
                    info!("Sending: {:?}",String::from_utf8_lossy( &message).to_string());
                    agent_broadcaster.send(message).await.unwrap();
                }
            });

            let _ = tokio::join!(t1, t2);
        }
    }

    fn create_agent(agent_definition: AgentDefinition) -> Agent {
        Agent::new(agent_definition)
    }

    #[test]
    fn test_start() {
        let workspace_id = "test".to_string();
        env_logger::init();
        debug!("Workspace {} running", workspace_id);

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
        let agent_3 = create_agent(AgentDefinition {
            name: "researcher 2".to_string(),
            position: "Web Researcher".to_string(),
            is_leader: false,
            instructions: vec![],
            responsibilities: vec![],
            ..Default::default()
        });
        let agent_4 = create_agent(AgentDefinition {
            name: "researcher 3".to_string(),
            position: "Web Researcher".to_string(),
            is_leader: false,
            instructions: vec![],
            responsibilities: vec![],
            ..Default::default()
        });

        let topic = format!("workspace-{}", workspace_id);
        let inputs = vec![1, 2, 3, 4];

        let agents = vec![agent_1, agent_2, agent_3, agent_4];

        let mut agent_thread_handlers = vec![];

        for agent in agents {
            let ag1_input = inputs.clone();
            let ag1_topic = topic.clone();
            let workspace_id = workspace_id.clone();
            let ag1_thread = thread::spawn(move || {
                tokio::runtime::Builder::new_current_thread()
                    .enable_all()
                    .build()
                    .unwrap()
                    .block_on(async move {
                        agent
                            .start(
                                ag1_topic.clone(),
                                5800,
                                ag1_input.clone(),
                                workspace_id.clone(),
                            )
                            .await;
                    });
            });
            agent_thread_handlers.push(ag1_thread);
        }

        for thread in agent_thread_handlers {
            thread.join().unwrap();
        }
    }
}
