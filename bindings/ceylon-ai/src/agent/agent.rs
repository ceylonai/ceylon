use std::sync::Arc;
use serde_json::json;
use tokio::runtime::Runtime;

use sangedama::node::node::create_node;

// The call-answer, callback interface.
pub trait MessageHandler {
    fn on_message(&self, agent_id: String, message: String);
}

#[derive(Debug, Default, Clone)]
pub struct AgentCore {
    _name: String,
    _is_leader: bool,
    _id: String,
    _workspace_id: String,
}

impl AgentCore {
    pub fn new( id: String,name: String, workspace_id: String,is_leader: bool) -> Self {
        Self {
            _name: name,
            _is_leader: is_leader,
            _id: id,
            _workspace_id: workspace_id,
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
}

impl AgentCore {
    async fn start(&self) {
        let port_id = 8888;
        let topic = "test_topic";

        let agent_name = self._name.clone();
        let workspace_id = self._workspace_id.clone();
        let (tx_0, mut rx_0) = tokio::sync::mpsc::channel::<Vec<u8>>(100);

        let (mut node_0, mut rx_o_0) = create_node(agent_name.clone(), true, rx_0);

        tokio::spawn(async move {
            while let Some(message) = rx_o_0.recv().await {
                println!("{:?} Received: {}", agent_name, String::from_utf8_lossy(&message));
                tx_0.send(json!({
                    "data": format!("Hi from {}", agent_name),
                }).to_string().as_bytes().to_vec()).await.unwrap();
                tokio::time::sleep(std::time::Duration::from_millis(100)).await;
            }
        });
        node_0.connect(port_id, topic);
        node_0.run().await;
    }
}


pub async fn run_workspace(agents: Vec<Arc<AgentCore>>) {
    let mut rt = Runtime::new().unwrap();
    let mut tasks = vec![];
    for agent in agents.iter() {
        let mut agent = agent.clone();
        let task = rt.spawn(async move {
            agent.start().await;
        });
        tasks.push(task);
    }

    for task in tasks {
        task.await.unwrap();
    }
}

