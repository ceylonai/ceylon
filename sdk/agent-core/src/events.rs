use tokio::sync::broadcast;

#[derive(Clone)]
pub struct EventBus {
    sender: broadcast::Sender<Event>,
}

impl EventBus {
    pub fn new() -> Self {
        let (sender, _) = broadcast::channel(100);
        Self { sender }
    }
    pub fn subscribe(&self) -> broadcast::Receiver<Event> {
        self.sender.subscribe()
    }
    pub fn publish(&self, event: Event) {
        self.sender.send(event).unwrap();
    }
}

#[derive(Debug, Clone)]
pub enum Event {
    TaskCompleted(String),
    TaskFailed(String),
    AgentStarted,
    AgentStopped,
}
