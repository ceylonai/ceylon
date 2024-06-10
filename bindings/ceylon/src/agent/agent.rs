use tokio::sync::{Mutex};
use std::sync::{Arc};
use tokio::runtime::Runtime;

use sangedama::node::node::create_node;

// The call-answer, callback interface.

#[async_trait::async_trait]
pub trait MessageHandler: Send + Sync {
    async fn on_message(&self, agent_id: String, message: String);
}

// The call-answer, callback interface.

#[async_trait::async_trait]
pub trait Processor: Send + Sync {
    async fn run(&self);
}

pub struct AgentCore {
    _name: String,
    _is_leader: bool,
    _id: String,
    _workspace_id: Option<String>,
    _processor: Arc<Mutex<Arc<dyn Processor>>>,
    _on_message: Arc<Mutex<Arc<dyn MessageHandler>>>,
    rx_0: Arc<Mutex<tokio::sync::mpsc::Receiver<Vec<u8>>>>,
    tx_0: tokio::sync::mpsc::Sender<Vec<u8>>,
}

impl AgentCore {
    pub fn new(name: String, is_leader: bool, on_message: Arc<dyn MessageHandler>, processor: Arc<dyn Processor>) -> Self {
        let (tx_0, rx_0) = tokio::sync::mpsc::channel::<Vec<u8>>(100);
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

    pub async fn broadcast(&self, message: String) {
        self.tx_0.send(message.to_string().as_bytes().to_vec()).await.unwrap();
    }
}

impl AgentCore {
    pub(crate) async fn start(&self, topic: String, url: String) {
        let agent_name = self._name.clone();
        let (tx_0, rx_0) = tokio::sync::mpsc::channel::<Vec<u8>>(100);
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
                    on_message.lock().await.on_message(agent_name.clone(), String::from_utf8_lossy(&message).to_string()).await;
                }
            }
        });
        let processor = self._processor.clone();
        processor.lock().await.run().await;
    }
}


