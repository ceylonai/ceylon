use std::sync::{Arc, Mutex};

use crate::agent::base::BaseAgent;

// Struct to represent a team of agents
pub struct Team {
    agents: Vec<Arc<Mutex<dyn BaseAgent + Send + Sync>>>,
}

impl Team {
    pub fn new() -> Self {
        Team {
            agents: Vec::new(),
        }
    }

    pub fn add_agent(&mut self, agent: Arc<Mutex<dyn BaseAgent + Send + Sync>>) {
        self.agents.push(agent);
    }

    pub fn get_agents(&self) -> Vec<Arc<Mutex<dyn BaseAgent + Send + Sync>>> {
        self.agents.clone()
    }
}

