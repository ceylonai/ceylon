use std::collections::HashMap;
use std::sync::Arc;

use tokio::runtime::Runtime;
use serde::{Deserialize, Serialize};

use crate::AgentCore;

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct WorkspaceConfig {
    pub name: String,
    pub host: String,
    pub port: u16,
}

pub struct Workspace {
    id: String,
    port: u16,
    host: String,
    _name: String,
    _agents: Vec<Arc<AgentCore>>,
}


impl Workspace {
    pub fn new(agents: Vec<Arc<AgentCore>>, config: WorkspaceConfig) -> Self {
        let _name = config.name;
        let id = format!("workspace-{}", uuid::Uuid::new_v4());

        Self {
            id,
            port: config.port,
            host: config.host,
            _name,
            _agents: agents,
        }
    }

    pub async fn run(&self, inputs: HashMap<String, String>) {
        let mut rt = Runtime::new().unwrap();
        let mut tasks = vec![];
        for agent in self._agents.iter() {
            let url = format!("{}/{}", self.host, self.port);
            let topic = format!("workspace-{}", agent.workspace_id());
            let agent = agent.clone();
            let task = rt.spawn(async move {
                agent.start(topic, url).await;
            });
            tasks.push(task);
        }

        for task in tasks {
            task.await.unwrap();
        }
    }
}

