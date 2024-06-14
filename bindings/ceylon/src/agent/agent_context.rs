use std::collections::HashMap;
use std::sync::RwLock;
use sangedama::node::node::Message;

use crate::agent::agent_base::AgentDefinition;

#[derive(Default, Debug, Clone)]
pub struct AgentContext {
    pub message_list: Vec<Message>,
    pub definition: AgentDefinition,
}

impl AgentContext {
    fn update_definition(&mut self, definition: AgentDefinition) {
        self.definition = definition;
    }

    pub fn add_message(&mut self, message: Message) {
        self.message_list.push(message);
    }
}

pub struct AgentContextManager {
    _self_context: RwLock<AgentContext>,
    _connected_agents_context: RwLock<HashMap<String, AgentContext>>,
}

impl AgentContextManager {
    pub fn new() -> Self {
        Self {
            _self_context: RwLock::new(AgentContext::default()),
            _connected_agents_context: RwLock::new(HashMap::new()),
        }
    }

    pub fn add_message(&mut self, message: Message) {
        if message.originator == self._self_context.read().unwrap().definition.name {
            self._self_context.write().unwrap().add_message(message);
        } else {
            self._connected_agents_context
                .write()
                .unwrap()
                .get_mut(&message.originator)
                .unwrap_or(&mut AgentContext::default())
                .add_message(message);
        }
    }
}
