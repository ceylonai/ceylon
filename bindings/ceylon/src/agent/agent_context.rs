use std::collections::HashMap;
use std::sync::RwLock;

use sangedama::node::node::Message;

use crate::agent::agent_base::AgentDefinition;

#[derive(Default, Debug, Clone)]
pub struct AgentContext {
    context_limit: u16,
    pub message_list: Vec<Message>,
    pub definition: Option<AgentDefinition>,
}

impl AgentContext {
    fn new(context_limit: u16) -> Self {
        Self {
            context_limit,
            message_list: vec![],
            definition: None,
        }
    }

    fn update_definition(&mut self, definition: AgentDefinition) {
        self.definition = Some(definition);
    }

    pub fn add_message(&mut self, message: Message) {
        self.message_list.push(message);
    }
}

pub struct AgentContextManager {
    context_limit: u16,
    owner_id: RwLock<Option<String>>,
    _self_context: RwLock<AgentContext>,
    _connected_agents_context: RwLock<HashMap<String, AgentContext>>,
}

impl AgentContextManager {
    pub fn new(limit: u16, owner_id: Option<String>) -> Self {
        Self {
            owner_id: RwLock::new(owner_id),
            context_limit: limit,
            _self_context: RwLock::new(AgentContext::default()),
            _connected_agents_context: RwLock::new(HashMap::new()),
        }
    }

    pub fn update_self_definition(&mut self, definition: AgentDefinition, id: String) {
        *self.owner_id.write().unwrap() = Some(id);
        self._self_context.write().unwrap().update_definition(definition);
    }

    pub fn add_message(&mut self, message: Message) -> Option<Message> {
        if message.originator.as_str() == self.owner_id.read().unwrap().as_ref().unwrap() {
            self._self_context.write().unwrap().add_message(message);
        } else {
            self._connected_agents_context
                .write()
                .unwrap()
                .get_mut(&message.originator)
                .unwrap_or(&mut AgentContext::default())
                .add_message(message);
        }
        None
    }
}
