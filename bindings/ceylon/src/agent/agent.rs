use std::any::Any;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::SystemTime;
use tokio::select;

use tokio::sync::{watch, Mutex};
use uniffi::deps::log::debug;

use sangedama::node::node::{create_node, Message, MessageType};

// The call-answer, callback interface.

#[async_trait::async_trait]
pub trait MessageHandler: Send + Sync {
    async fn on_message(&self, agent_id: String, message: Message);
}

// The call-answer, callback interface.

#[async_trait::async_trait]
pub trait Processor: Send + Sync {
    async fn run(&self, input: Vec<u8>) -> ();
}

pub struct AgentCore {
    _name: String,
    _is_leader: bool,
    _id: String,
    _workspace_id: Option<String>,
    _processor: Arc<Mutex<Option<Arc<dyn Processor>>>>,
    _on_message: Arc<Mutex<Arc<dyn MessageHandler>>>,
    rx_0: Arc<Mutex<tokio::sync::mpsc::Receiver<Message>>>,
    tx_0: tokio::sync::mpsc::Sender<Message>,
    _meta: HashMap<String, String>,
}

impl AgentCore {
    pub fn new(
        name: String,
        is_leader: bool,
        on_message: Arc<dyn MessageHandler>,
        processor: Option<Arc<dyn Processor>>,
        meta: Option<HashMap<String, String>>,
    ) -> Self {
        let (tx_0, rx_0) = tokio::sync::mpsc::channel::<Message>(100);
        let id = uuid::Uuid::new_v4().to_string();
        let mut _meta = meta.unwrap_or_default();
        _meta.insert("id".to_string(), id.clone());
        _meta.insert("name".to_string(), name.clone());
        _meta.insert("is_leader".to_string(), is_leader.to_string());
        _meta.insert(
            "created_at".to_string(),
            SystemTime::now()
                .duration_since(SystemTime::UNIX_EPOCH)
                .unwrap()
                .as_millis()
                .to_string(),
        );
        Self {
            _name: name,
            _is_leader: is_leader,
            _id: id,
            _workspace_id: None,
            _on_message: Arc::new(Mutex::new(on_message)),
            _processor: Arc::new(Mutex::new(processor)),
            rx_0: Arc::new(Mutex::new(rx_0)),
            tx_0,
            _meta,
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

    pub async fn broadcast(&self, message: Vec<u8>, to: Option<String>) {
        self.tx_0
            .send(Message::data(
                self._name.clone(),
                self._id.clone(),
                message,
                to,
            ))
            .await
            .unwrap();
    }

    pub fn meta(&self) -> HashMap<String, String> {
        self._meta.clone()
    }
}

impl AgentCore {
    pub(crate) async fn start(&self, topic: String, url: String, inputs: Vec<u8>) {
        let agent_name = self._name.clone();
        let agent_id = self._id.clone();
        let (tx_0, rx_0) = tokio::sync::mpsc::channel::<Message>(100);
        let (mut node_0, mut rx_o_0) = create_node(agent_name.clone(), true, rx_0);
        let on_message = self._on_message.clone();

        let t0 = tokio::spawn(async move {
            node_0.connect(url.as_str(), topic.as_str());
            node_0.run().await;
        });

        let rx = Arc::clone(&self.rx_0);
        let t1 = tokio::spawn(async move {
            let mut rx = rx.lock().await;
            loop {
                select! {
                        Some(message) = rx.recv() => {
                            debug!("{} Received: {:?}", agent_name.clone(), message.clone());
                            tx_0.clone().send(message).await.unwrap();
                        }
                        Some(message) = rx_o_0.recv() => {
                            let message_to_id = message.to_id.clone().unwrap_or("ALL".to_string());
                            let message_type = message.r#type;
                            if message_to_id == agent_name.clone() ||
                                message_to_id == agent_id.clone() ||
                                message_to_id == "ALL" ||
                                message_type == MessageType::Event                                {
                                on_message.lock().await.on_message(agent_name.clone(), message.clone()).await;
                        }
                    }
                }
            }
        });

        let processor = self._processor.clone();
        let t2 = tokio::spawn(async move {
            if let Some(processor) = processor.lock().await.clone() {
                processor.run(inputs).await;
            }
        });

        t0.await.unwrap();
        t1.await.unwrap();
        t2.await.unwrap();
    }
}
