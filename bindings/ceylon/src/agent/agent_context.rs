use std::collections::{HashMap, VecDeque};
use std::sync::RwLock;

use sangedama::node::node::Message;

use crate::agent::agent_base::AgentDefinition;

#[derive(Default, Debug, Clone)]
pub struct AgentContext {
    pub message_list: VecDeque<Message>,
    pub definition: Option<AgentDefinition>,
}

impl AgentContext {
    fn new(context_limit: u16) -> Self {
        Self {
            message_list: VecDeque::with_capacity(context_limit as usize),
            definition: None,
        }
    }

    fn update_definition(&mut self, definition: AgentDefinition) {
        self.definition = Some(definition);
    }

    pub fn add_message(&mut self, message: Message) {
        self.message_list.push_front(message);
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
                .unwrap_or(&mut AgentContext::new(self.context_limit))
                .add_message(message);
        }
        None
    }

    pub fn get_self_context(&self) -> Vec<Message> {
        Vec::from(self._self_context.read().unwrap().message_list.clone())
    }

    pub fn get_connected_agents_context(&self) -> HashMap<String, Vec<Message>> {
        let mut map = HashMap::new();
        let _copy = self._connected_agents_context
            .read()
            .unwrap()
            .clone();
        for (k, v) in _copy.iter() {
            map.insert(k.clone(), Vec::from(v.message_list.clone()));
        }
        map
    }
}
