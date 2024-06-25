use std::sync::{Arc, RwLock};
use std::thread;

use log::error;
use serde::{Deserialize, Serialize};
use uniffi::deps::log::debug;

use crate::AgentCore;

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct WorkspaceConfig {
    pub name: String,
    pub port: u16,
}

pub struct Workspace {
    id: String,
    port: u16,
    _name: String,
    _agents: RwLock<Vec<Arc<AgentCore>>>,
}


impl Workspace {
    pub fn new(agents: Vec<Arc<AgentCore>>, config: WorkspaceConfig) -> Self {
        env_logger::init();
        let _name = config.name;
        let id = format!("workspace-{}", uuid::Uuid::new_v4());

        // Set agent workspace_id
        for agent in agents.iter() {
            agent.set_workspace_id(id.clone());
        }

        // Validate: agent name,id must be unique
        let mut names = vec![];
        let mut ids = vec![];
        for agent in agents.iter() {
            let name = agent.definition().name.clone();
            if names.contains(&name) {
                panic!("Agent name {} is not unique", name);
            }
            names.push(name.clone());
            ids.push(agent.id());
        }


        Self {
            id,
            port: config.port,
            _name,
            _agents: RwLock::new(agents),
        }
    }

    pub async fn run(&self, input: Vec<u8>) {
        debug!("Workspace {} running", self.id);
        let rt = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build().unwrap();
        let mut tasks = vec![];
        let _input = input.clone();
        for agent in self._agents.read().unwrap().iter() {
            let _inputs = _input.clone();
            let url = self.port;
            let topic = format!("workspace-{}", agent.workspace_id());

            let agent = agent.clone();
            let task = rt.spawn(async move {
                agent.start(topic, url, _inputs).await;
            });
            tasks.push(task);
        }

        for task in tasks {
            match task.await {
                Ok(_) => {}
                Err(e) => {
                    error!("Error: {:?}", e);
                }
            };
        }
    }
}

pub async fn agent_runner_multi_thread(agents: Vec<Arc<AgentCore>>, topic: String, inputs: Vec<u8>, workspace_id: String) {
    env_logger::init();
    let mut agent_thread_handlers = vec![];

    for agent in agents {
        let ag1_input = inputs.clone();
        let ag1_topic = topic.clone();
        let workspace_id = workspace_id.clone();
        let ag1_thread = thread::spawn(move || {
            tokio::runtime::Builder::new_current_thread()
                .enable_all()
                .build()
                .unwrap()
                .block_on(async move {
                    agent.set_workspace_id(workspace_id.clone());
                    agent
                        .start(ag1_topic.clone(), 8445, ag1_input.clone()).await
                });
        });
        agent_thread_handlers.push(ag1_thread);
    }

    for thread in agent_thread_handlers {
        thread.join().unwrap();
    }
}

pub async fn agent_run_single(agent: Arc<AgentCore>, topic: String, inputs: Vec<u8>, workspace_id: String) {
    match env_logger::try_init(){        
        Ok(_) => {},
        Err(e) => {
            error!("Error: {:?}", e);
        }
    }
    let ag1_input = inputs.clone();
    let ag1_topic = topic.clone();
    let workspace_id = workspace_id.clone();
    tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .unwrap()
        .block_on(async move {
            agent.set_workspace_id(workspace_id.clone());
            agent
                .start(ag1_topic.clone(), 8445, ag1_input.clone()).await
        });
}
