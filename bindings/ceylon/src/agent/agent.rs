use std::collections::HashMap;
use std::sync::Arc;

use tokio::sync::Mutex;

use sangedama::node::node::{create_node, Message};

// The call-answer, callback interface.

#[async_trait::async_trait]
pub trait MessageHandler: Send + Sync {
    async fn on_message(&self, agent_id: String, message: Message);
}

// The call-answer, callback interface.

#[async_trait::async_trait]
pub trait Processor: Send + Sync {
    async fn run(&self, message: HashMap<String, String>) -> ();
}

pub struct AgentCore {
    _name: String,
    _is_leader: bool,
    _id: String,
    _workspace_id: Option<String>,
    _processor: Arc<Mutex<Arc<dyn Processor>>>,
    _on_message: Arc<Mutex<Arc<dyn MessageHandler>>>,
    rx_0: Arc<Mutex<tokio::sync::mpsc::Receiver<Message>>>,
    tx_0: tokio::sync::mpsc::Sender<Message>,
}

impl AgentCore {
    pub fn new(name: String, is_leader: bool, on_message: Arc<dyn MessageHandler>, processor: Arc<dyn Processor>) -> Self {
        let (tx_0, rx_0) = tokio::sync::mpsc::channel::<Message>(100);
        let id = uuid::Uuid::new_v4().to_string();
        Self {
            _name: name,
            _is_leader: is_leader,
            _id: id,
            _workspace_id: None,
            _on_message: Arc::new(Mutex::new(on_message)),
            _processor: Arc::new(Mutex::new(processor)),
            rx_0: Arc::new(Mutex::new(rx_0)),
            tx_0,
        }
    }

    pub fn name(&self) -> String {
        self._name.clone()
    }

    pub fn is_leader(&self) -> bool {
        self._is_leader
    }

    pub fn id(&self) -> String {
        self._id.clone()
    }

    pub fn workspace_id(&self) -> String {
        self._workspace_id.clone().unwrap_or("".to_string())
    }

    pub fn set_workspace_id(&mut self, workspace_id: String) {
        self._workspace_id = Option::from(workspace_id);
    }

    pub async fn broadcast(&self, message: Vec<u8>) {
        self.tx_0.send(Message::data(self._name.clone(), self._id.clone(), message)).await.unwrap();
    }
}

impl AgentCore {
    pub(crate) async fn start(&self, topic: String, url: String, inputs: HashMap<String, String>) {
        let agent_name = self._name.clone();
        let (tx_0, rx_0) = tokio::sync::mpsc::channel::<Message>(100);
        let (mut node_0, mut rx_o_0) = create_node(agent_name.clone(), true, rx_0);
        let on_message = self._on_message.clone();

        tokio::spawn(async move {
            node_0.connect(url.as_str(), topic.as_str());
            node_0.run().await;
        });

        let rx = Arc::clone(&self.rx_0);
        tokio::spawn(async move {
            loop {
                if let Some(message) = rx.lock().await.recv().await {
                    tx_0.clone().send(message).await.unwrap();
                }

                if let Some(message) = rx_o_0.recv().await {
                    on_message.lock().await.on_message(agent_name.clone(), message).await;
                }
            }
        });
        let processor = self._processor.clone();
        processor.lock().await.run(inputs).await;
    }
}


