use std::sync::Arc;

use serde::{Deserialize, Serialize};
use tokio::runtime::Runtime;
use tracing::debug;
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
    runtime: Runtime,
}


impl Workspace {
    pub fn new(agents: Vec<Arc<AgentCore>>, config: WorkspaceConfig) -> Self {
        let _name = config.name;
        let id = format!("workspace-{}", uuid::Uuid::new_v4());

        let rt = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build()
            .unwrap();

        Self {
            id,
            port: config.port,
            host: config.host,
            _name,
            _agents: agents,
            runtime: rt,
        }
    }

    pub async fn run(&self, inputs: Vec<u8>) {
        env_logger::init();
        debug!("Workspace {} running", self.id);
        let mut tasks = vec![];
        let _inputs = inputs.clone();
        for agent in self._agents.iter() {
            let _inputs = _inputs.clone();
            let url = format!("/ip4/{}/udp/{}/quic-v1", self.host, self.port);
            let topic = format!("workspace-{}", agent.workspace_id());

            let agent = agent.clone();
            let task = self.runtime.spawn(async move {
                agent.start_agent(topic, url, _inputs).await;
            });
            tasks.push(task);
        }

        for task in tasks {
            task.await.unwrap();
        }
    }
}

