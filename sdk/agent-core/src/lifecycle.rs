#[derive(Debug, PartialEq)]
pub enum AgentState {
    Uninitialized,
    Initialized,
    Running,
    Stopped,
}

pub struct LifecycleManager {
    pub state: AgentState,
}

impl LifecycleManager {
    pub fn new() -> Self{
        Self {
            state: AgentState::Uninitialized,
        }
    }
    pub async fn initialize(&mut self) {
        self.state = AgentState::Initialized;
    }
    pub async fn start(&mut self) {
        self.state = AgentState::Running;
    }
    pub async fn stop(&mut self) {
        self.state = AgentState::Stopped;
    }
    pub async fn restart(&mut self) {
        self.stop().await;
        self.start().await;
    }
}
