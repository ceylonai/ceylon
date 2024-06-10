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
    _workspace_id: String,
    _processor: Arc<Mutex<Arc<dyn Processor>>>,
    _on_message: Arc<Mutex<Arc<dyn MessageHandler>>>,
    rx_0: Arc<Mutex<tokio::sync::mpsc::Receiver<Vec<u8>>>>,
    tx_0: tokio::sync::mpsc::Sender<Vec<u8>>,
}

impl AgentCore {
    pub fn new(id: String, name: String, workspace_id: String, is_leader: bool, on_message: Arc<dyn MessageHandler>, processor: Arc<dyn Processor>) -> Self {
        let (tx_0, rx_0) = tokio::sync::mpsc::channel::<Vec<u8>>(100);
        Self {
            _name: name,
            _is_leader: is_leader,
            _id: id,
            _workspace_id: workspace_id,
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
        self._workspace_id.clone()
    }

    pub async fn broadcast(&self, message: String) {
        self.tx_0.send(message.to_string().as_bytes().to_vec()).await.unwrap();
    }
}

impl AgentCore {
    async fn start(&self) { 
        
        let port_id = 8888;
        let topic = "test_topic";

        let agent_name = self._name.clone();
        let workspace_id = self._workspace_id.clone();


        let (tx_0, mut rx_0) = tokio::sync::mpsc::channel::<Vec<u8>>(100);
        let (mut node_0, mut rx_o_0) = create_node(agent_name.clone(), true, rx_0);
        let on_message = self._on_message.clone();

        tokio::spawn(async move {
            node_0.connect(port_id, topic);
            node_0.run().await;
        });

        let processor = self._processor.clone();
        tokio::spawn(async move {
            processor.lock().await.run().await;
        });

        let rx = Arc::clone(&self.rx_0);
        loop {
            if let Some(message) = rx.lock().await.recv().await {
                tx_0.send(message).await.unwrap();
            }

            if let Some(message) = rx_o_0.recv().await {
                on_message.lock().await.on_message(agent_name.clone(), String::from_utf8_lossy(&message).to_string()).await;
            }
        }
    }
}


pub async fn run_workspace(agents: Vec<Arc<AgentCore>>) {
    let mut rt = Runtime::new().unwrap();
    let mut tasks = vec![];
    for agent in agents.iter() {
        let agent = agent.clone();
        let task = rt.spawn(async move {
            agent.start().await;
        });
        tasks.push(task);
    }

    for task in tasks {
        task.await.unwrap();
    }
}

