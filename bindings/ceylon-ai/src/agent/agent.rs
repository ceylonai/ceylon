use std::sync::Arc;
use serde_json::json;
use sangedama::node::node::{create_node, Node};

#[derive(Debug, Default, Clone)]
pub struct Agent {
    pub name: String,
    pub is_leader: bool,
    pub id: Option<String>,
    pub workspace_id: Option<String>,
}

impl Agent {
    fn is_valid(&self) -> bool {
        self.id.is_some() && self.workspace_id.is_some() && !self.name.is_empty()
    }
}

#[derive(Debug, thiserror::Error)]
pub enum AgentConnectionError {
    #[error("InvalidDestination")]
    InvalidDestination
}

#[derive(Debug, thiserror::Error)]
pub enum AgentStartError {
    #[error("InternalError")]
    InternalError
}

pub struct AgentRunner {
    agent: Arc<Agent>,
}

impl AgentRunner {
    pub fn new(agent: Agent, workspace_id: String) -> Self {
        let id = uuid::Uuid::new_v4().to_string();
        let mut agent = agent.clone();
        agent.id = Some(id);
        agent.workspace_id = Some(workspace_id);
        Self {
            agent: Arc::new(agent),
        }
    }

    pub async fn connect(&self, url: String) -> Result<String, AgentConnectionError> {
        // if self.agent.is_valid() || url.is_empty() {
        //     return Err(AgentConnectionError::InvalidDestination);
        // }
        Ok(url)
    }
    pub async fn start(&self) -> Result<(), AgentStartError> {
        println!("Starting {:?}", self.agent);

        let agent_name = self.agent.name.clone();
        let workspace_id = self.agent.workspace_id.clone().unwrap();
        let (tx_0, mut rx_0) = tokio::sync::mpsc::channel::<Vec<u8>>(100);
        let (mut node, mut rx_o_0) = create_node(agent_name, self.agent.is_leader, rx_0);

        let runtime = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap();

        runtime.spawn(async move {
            node.connect(8888, workspace_id.as_str());
            node.run().await;
        });

        let t1 = runtime.spawn(async move {
            while let Some(message) = rx_o_0.recv().await {
                println!("Node_0 Received: {}", String::from_utf8_lossy(&message));
                tx_0.send(json!({
                    "data": "Hi from Node_1",
                }).to_string().as_bytes().to_vec()).await.unwrap();
                tokio::time::sleep(std::time::Duration::from_millis(100)).await;
            }
        });

        runtime.block_on(async move {
            t1.await.expect("Error");
        });

        Ok(())
    }
}