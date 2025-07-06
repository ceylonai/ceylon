pub enum AgentState {
    Uninitialized,
    Initialized,
    Running,
    Stopped,
}

pub struct LifecycleManager {
    state: AgentState,
}

impl LifecycleManager {
    pub fn new() -> Self{
        Self {
            state: AgentState::Uninitialized,
        }
    }
    pub async fn initialize(&mut self) {}
    pub async fn start(&mut self) {}
    pub async fn stop(&mut self) {}
    pub async fn restart(&mut self) {}
}
