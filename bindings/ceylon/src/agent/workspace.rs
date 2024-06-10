use std::collections::HashMap;
use std::sync::Arc;
use tokio::runtime::Runtime;
use crate::AgentCore;

pub struct Workspace {
    _agents: Vec<Arc<AgentCore>>,
}

impl Workspace {
    pub fn new(agents: Vec<Arc<AgentCore>>) -> Self {
        Self {
            _agents: agents,
        }
    }

    pub async fn run_workspace(&self, inputs: HashMap<String, String>) {
        let mut rt = Runtime::new().unwrap();
        let mut tasks = vec![];
        for agent in self._agents.iter() {
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
}

