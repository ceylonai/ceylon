use std::collections::VecDeque;
use std::sync::RwLock;
use std::time::SystemTime;

use uuid::Uuid;

use sangedama::node::node::Message;

use crate::agent::agent_base::AgentDefinition;

pub struct MessageThread {
    id: String,
    purpose: String,
    messages: RwLock<VecDeque<Message>>,
}

impl MessageThread {
    pub fn new(purpose: String) -> Self {
        let id = format!("{}-{}", SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap().as_millis(), Uuid::new_v4());
        Self {
            id,
            purpose,
            messages: RwLock::new(VecDeque::new()),
        }
    }

    pub fn add_message(&self, message: Message) {
        self.messages.write().unwrap().push_back(message);
    }
}

pub struct AgentContextManager {
    context_limit: u16,
    owner: RwLock<Option<AgentDefinition>>,
}

impl AgentContextManager {
    pub fn new(limit: u16) -> Self {
        Self {
            owner: RwLock::new(None),
            context_limit: limit,
        }
    }

    pub fn update_self_definition(&mut self, definition: AgentDefinition) {
        self.owner.write().unwrap().replace(definition);
    }

    pub fn add_message(&mut self, message: Message) -> Option<Message> {
        let message_type = message.r#type.clone();
        None
    }
}

#[cfg(test)]
mod tests {
    use sangedama::node::node::{Message, MessageType};
    use crate::agent::agent_context::MessageThread;

    #[test]
    fn it_works() {
        let t1 = MessageThread::new("Discussion about the project".to_string());

        t1.add_message(Message::data(
            "ceylon-ai-1".to_string(),
            Some("ceylon-ai-2".to_string()),
            "Hi".as_bytes().to_vec(),
        ))
    }
}