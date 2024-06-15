use std::collections::{HashMap, VecDeque};
use std::sync::RwLock;

use sangedama::node::node::Message;

use crate::agent::agent_base::{AgentDefinition, AgentDefinitionBuilder};

trait ThreadProcessor {
    fn process(&self, message: Message);
}

pub struct MessageThread {
    id: String,
    purpose: String,
    owner_id: String,
    participants: RwLock<HashMap<String, AgentDefinition>>,
    messages: RwLock<VecDeque<Message>>,
    _limit_participants: usize,
}

impl MessageThread {
    pub fn is_participant(&self, participant: &String) -> bool {
        let participants = self.participants.read().unwrap();
        if participants.contains_key(participant) && participant != &self.owner_id {
            return true;
        }
        false
    }
}

impl MessageThread {
    pub fn new(id: String, purpose: String, owner_id: String, limit_participants: usize) -> Self {
        Self {
            id,
            owner_id,
            purpose,
            messages: RwLock::new(VecDeque::new()),
            participants: RwLock::new(HashMap::new()),
            _limit_participants: limit_participants,
        }
    }

    pub fn add_message(&self, message: Message) {

        // Add message sender as participant
        let mut participants = self.participants.write().unwrap();
        let sender = message.sender.clone();

        // If this is the first message
        if !participants.contains_key(&message.sender) && participants.len() < self._limit_participants {
            participants.insert(sender.clone(), AgentDefinitionBuilder::new().id(sender).build());
        }

        // Is valid sender
        if participants.contains_key(&message.sender) {
            self.messages.write().unwrap().push_back(message.clone());
        }
    }

    fn len(&self) -> usize {
        self.messages.read().unwrap().len()
    }
}

pub struct AgentContextManager {
    context_limit: u16,
    owner: RwLock<Option<AgentDefinition>>,
    threads: RwLock<HashMap<String, MessageThread>>,
}

impl AgentContextManager {
    pub fn new(limit: u16) -> Self {
        Self {
            owner: RwLock::new(None),
            context_limit: limit,
            threads: RwLock::new(HashMap::new()),
        }
    }

    pub fn set_self_definition(&mut self, definition: AgentDefinition) {
        if self.owner.read().unwrap().is_some() {
            panic!("Agent Context is already set");
        }
        self.owner.write().unwrap().replace(definition);
    }


    /// We only manage 1 thread for each other agents
    /// No Group Thread implementation here
    pub fn add_message(&mut self, message: Message) {
        let message_sender = message.sender.clone();
        let message_receiver = message.receiver.clone();
        let owner_id = self.owner.read().unwrap().as_ref().unwrap().id.clone().unwrap();        
        let thread_id = format!("{}-{}", owner_id.clone(), if owner_id == message_sender { message_receiver.clone().unwrap_or("all".to_string()) } else { message_sender.clone() });
        self.add_or_update_thread(thread_id, message.clone());
    }

    fn add_or_update_thread(&self, thread_id: String, message: Message) {
        let mut threads = self.threads.write().unwrap(); // Lock for writing
        let message_sender = message.sender.clone();
        threads.entry(thread_id.clone())
            .and_modify(|thread| {
                thread.add_message(message.clone());
            })
            .or_insert_with(|| {
                let mut thread = MessageThread::new(thread_id.clone(), "".to_string(), message_sender.clone(), self.context_limit as usize);
                thread.add_message(message);
                thread
            });
    }

    fn print_threads(&self) {
        let threads = self.threads.read().unwrap();
        for thread_unique_id in threads.keys() {
            let thread = threads.get(thread_unique_id).unwrap();
            println!("thread.id={} thread.topic={} thread.len()={} thread.owner={}", thread.id, thread.purpose, thread.len(), thread.owner_id);
        }
    }
}

#[cfg(test)]
mod tests {
    use sangedama::node::node::Message;

    use crate::agent::agent_context::AgentContextManager;
    use crate::agent::message_types::{AgentMessage, AgentMessageConversions, AgentMessageTrait, AgentMessageType, HandshakeMessage, IntroduceMessage};
    use crate::AgentDefinition;

    #[test]
    fn it_works() {
        let ag_1 = AgentDefinition {
            id: Some("1".to_string()),
            name: "ceylon-ai-1".to_string(),
            is_leader: true,
            position: "LEADER".to_string(),
            responsibilities: vec![],
            instructions: vec![],
        };
        let mut context = AgentContextManager::new(10);
        context.set_self_definition(ag_1.clone());


        let ag_2 = AgentDefinition {
            id: Some("2".to_string()),
            name: "ceylon-ai-2".to_string(),
            is_leader: true,
            position: "WORKER".to_string(),
            responsibilities: vec![],
            instructions: vec![],
        };


        // Handshake messages
        let m1 = Message::data(ag_1.clone().id.unwrap().to_string(),
                               None,
                               AgentMessage::from_data(AgentMessageType::Handshake,
                                                       HandshakeMessage { message: "Hi Ag2".to_string() }).into_bytes());
        context.add_message(m1);
        context.print_threads();
        println!("\n");

        let m2 = Message::data(ag_2.clone().id.unwrap().to_string(),
                               ag_1.clone().id,
                               AgentMessage::from_data(AgentMessageType::Handshake,
                                                       HandshakeMessage { message: "Hi Ag1".to_string() }).into_bytes());
        context.add_message(m2);
        context.print_threads();
        println!("\n");

        // Introduction Messages
        let m3 = Message::data(ag_1.clone().id.unwrap().to_string(),
                               ag_2.clone().id,
                               AgentMessage::from_data(AgentMessageType::Introduce,
                                                       IntroduceMessage { agent_definition: ag_1.clone() }).into_bytes());
        context.add_message(m3);
        context.print_threads();
        println!("\n");

        let m4 = Message::data(ag_2.clone().id.unwrap().to_string(),
                               ag_1.clone().id,
                               AgentMessage::from_data(AgentMessageType::Introduce,
                                                       IntroduceMessage { agent_definition: ag_2.clone() }).into_bytes());
        context.add_message(m4);
        context.print_threads();
        println!("\n");


        let ag_3 = AgentDefinition {
            id: Some("3".to_string()),
            name: "ceylon-ai-3".to_string(),
            is_leader: true,
            position: "WORKER 2".to_string(),
            responsibilities: vec![],
            instructions: vec![],
        };


        let m5 = Message::data(ag_3.clone().id.unwrap().to_string(),
                               None,
                               AgentMessage::from_data(AgentMessageType::Introduce,
                                                       IntroduceMessage { agent_definition: ag_3.clone() }).into_bytes());
        context.add_message(m5);
        context.print_threads();
        println!("\n");
    }
}