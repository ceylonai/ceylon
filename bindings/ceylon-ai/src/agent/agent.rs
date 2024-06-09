use serde_json::json;
use tokio::runtime::Runtime;

use sangedama::node::node::create_node;

// The call-answer, callback interface.
pub trait MessageHandler {
    fn on_message(&self, agent_id: String, message: String);
}

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

    async fn start(&self) {
        let port_id = 8888;
        let topic = "test_topic";

        let agent_name = self.name.clone();
        let workspace_id = self.workspace_id.clone().unwrap();
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



pub async fn run_workspace(agents: Vec<Agent>, workspace_id: String) {
    let mut rt = Runtime::new().unwrap();
    let mut tasks = vec![];
    for agent in agents.iter() {
        let mut agent = agent.clone();
        agent.workspace_id = Some(workspace_id.clone());
        if agent.is_valid() {
            let task = rt.spawn(async move {
                agent.start().await;
            });
            tasks.push(task);
        }
    }

    for task in tasks {
        task.await.unwrap();
    }
}

