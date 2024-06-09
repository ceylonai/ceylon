use std::sync::Arc;

#[derive(Debug, Default, Clone)]
pub struct Agent {
    pub name: String,
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
        if self.agent.is_valid() || url.is_empty() {
            return Err(AgentConnectionError::InvalidDestination);
        }
        Ok(url)
    }
    pub async fn start(&self) -> Result<(), AgentStartError> {
        println!("Starting {:?}", self.agent);
        Ok(())
    }
}