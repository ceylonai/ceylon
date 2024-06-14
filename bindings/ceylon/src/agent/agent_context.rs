use std::sync::RwLock;

use sangedama::node::node::Message;

use crate::agent::agent_base::AgentDefinition;

pub struct AgentContextManager {
    context_limit: u16,
    owner_id: RwLock<Option<String>>,
}

impl AgentContextManager {
    pub fn new(limit: u16, owner_id: Option<String>) -> Self {
        Self {
            owner_id: RwLock::new(owner_id),
            context_limit: limit
        }
    }

    pub fn update_self_definition(&mut self, definition: AgentDefinition, id: String) {
        *self.owner_id.write().unwrap() = Some(id);
    }

    pub fn add_message(&mut self, message: Message) -> Option<Message> {
        let message_type = message.r#type.clone();
      
        None
    }

}
