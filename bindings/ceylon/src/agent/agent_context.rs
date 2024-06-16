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
    _message_limit: usize,
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
    pub fn new(id: String, purpose: String, owner_id: String, limit_participants: usize, message_limit: usize) -> Self {
        Self {
            id,
            owner_id,
            purpose,
            messages: RwLock::new(VecDeque::with_capacity(message_limit)),
            participants: RwLock::new(HashMap::new()),
            _limit_participants: limit_participants,
            _message_limit: message_limit,
        }
    }

    pub fn new_with_participants(id: String, purpose: String, owner_id: String, participants: HashMap<String, AgentDefinition>, limit_participants: usize, message_limit: usize) -> Self {
        Self {
            id,
            owner_id,
            purpose,
            messages: RwLock::new(VecDeque::with_capacity(message_limit)),
            participants: RwLock::new(participants),
            _limit_participants: limit_participants,
            _message_limit: message_limit,
        }
    }

    pub fn new_for_only_one_agent(id: String, purpose: String, owner_id: String, participant: AgentDefinition, message_limit: usize) -> Self {
        Self {
            id,
            owner_id,
            purpose,
            messages: RwLock::new(VecDeque::with_capacity(message_limit)),
            participants: RwLock::new(HashMap::from([(participant.id.clone().unwrap(), participant)])),
            _limit_participants: 1,
            _message_limit: message_limit,
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
            self.messages.write().unwrap().push_front(message.clone());

            if self.messages.read().unwrap().len() > self._message_limit {
                self.messages.write().unwrap().pop_back();
            }
        }
    }

    fn len(&self) -> usize {
        self.messages.read().unwrap().len()
    }

    fn get_messages(&self) -> Vec<Message> {
        self.messages.read().unwrap().clone().into_iter().collect()
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
        self.add_to_existing_thread(thread_id, message.clone());
    }

    fn add_to_existing_thread(&self, thread_id: String, message: Message) {
        let mut threads = self.threads.write().unwrap(); // Lock for writing
        threads.entry(thread_id.clone())
            .and_modify(|thread| {
                thread.add_message(message.clone());
            });
    }


    fn add_or_update_thread(&self, thread_id: String, message: Message) {
        let mut threads = self.threads.write().unwrap(); // Lock for writing
        let message_sender = message.sender.clone();
        let id = message.sender.clone();
        threads.entry(id.clone())
            .and_modify(|thread| {
                thread.add_message(message.clone());
            })
            .or_insert_with(|| {
                let mut thread = MessageThread::new(thread_id.clone(), "".to_string(), message_sender.clone(), 1, self.context_limit as usize);
                thread.add_message(message);
                thread
            });
    }

    pub fn create_context(&self, agent_definition: AgentDefinition) {
        let id = agent_definition.id.clone().unwrap();
        let topic = format!("{}-{}", agent_definition.position, id.clone());
        let agent_context = MessageThread::new_for_only_one_agent(
            topic.clone(),
            format!("Discussion with {}", agent_definition.position),
            agent_definition.id.clone().unwrap(),
            agent_definition,
            self.context_limit as usize,
        );
        self.threads.write().unwrap().insert(id, agent_context);
    }

    pub fn get_owner(&self) -> AgentDefinition {
        self.owner.read().unwrap().as_ref().unwrap().clone()
    }

    pub fn has_thread(&self, agent_id: String) -> bool {
        self.threads.read().unwrap().contains_key(&agent_id)
    }

    fn print_threads(&self) {
        let threads = self.threads.read().unwrap();
        for thread_unique_id in threads.keys() {
            let thread = threads.get(thread_unique_id).unwrap();
            println!("thread.id={} thread.topic={} thread.len()={} thread.owner={}", thread.id, thread.purpose, thread.len(), thread.owner_id);
        }
    }

    fn print_threads_messages(&self) {
        let threads = self.threads.read().unwrap();
        for thread_unique_id in threads.keys() {
            let thread = threads.get(thread_unique_id).unwrap();
            println!("thread.id={} thread.topic={} thread.len()={} thread.owner={}", thread.id, thread.purpose, thread.len(), thread.owner_id);
            for message in thread.get_messages() {
                println!("thread.id={:?} thread.topic={:?} message.sender={:?} message.receiver={:?} message.content={:?}", thread.id, thread.purpose, message.sender, message.receiver, message.message);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use rand::Rng;

    use sangedama::node::node::Message;

    use crate::agent::agent_context::AgentContextManager;
    use crate::agent::message_types::{AgentMessage, AgentMessageConversions, AgentMessageTrait, AgentMessageType, HandshakeMessage, IntroduceMessage, TextMessage};
    use crate::AgentDefinition;

    #[test]
    fn it_works() {
        let ag_1 = AgentDefinition {
            id: Some("MAIN".to_string()),
            name: "ceylon-ai-MAIN".to_string(),
            is_leader: true,
            position: "LEADER".to_string(),
            responsibilities: vec![],
            instructions: vec![],
        };
        let mut context = AgentContextManager::new(1000);
        context.set_self_definition(ag_1.clone());


        for random_ag_idx in 0..10 {
            // let random_ag_idx = rand::thread_rng().gen_range(0..10);

            let ag_2 = AgentDefinition {
                id: Some(format!("{}", random_ag_idx + 1)),
                name: format!("ceylon-ai-{}", random_ag_idx + 1),
                is_leader: true,
                position: format!("WORKER-{}", random_ag_idx + 1),
                responsibilities: vec![],
                instructions: vec![],
            };


            // Handshake messages
            let m1 = Message::data(ag_1.clone().id.unwrap().to_string(),
                                   None,
                                   AgentMessage::from_data(AgentMessageType::Handshake,
                                                           HandshakeMessage { message: "Hi".to_string() }).into_bytes());
            context.add_message(m1);
            context.print_threads();
            println!("\n");

            // Handshake messages
            let m2 = Message::data(ag_1.clone().id.unwrap().to_string(),
                                   ag_2.clone().id,
                                   AgentMessage::from_data(AgentMessageType::Handshake,
                                                           IntroduceMessage {
                                                               agent_definition: ag_2
                                                           }).into_bytes());
            context.add_message(m2);
            context.print_threads();
            println!("\n");
        }


        for i in 0..1000 {
            let random_ag_idx = rand::thread_rng().gen_range(0..10);

            let ag_2 = AgentDefinition {
                id: Some(format!("{}", random_ag_idx + 1)),
                name: format!("ceylon-ai-{}", random_ag_idx + 1),
                is_leader: true,
                position: format!("WORKER-{}", random_ag_idx + 1),
                responsibilities: vec![],
                instructions: vec![],
            };


            // Handshake messages
            let m2 = Message::data(ag_1.clone().id.unwrap().to_string(),
                                   ag_2.clone().id,
                                   AgentMessage::from_data(AgentMessageType::Other,
                                                           TextMessage {
                                                               text: format!("Hi My count is {}", i)
                                                           }).into_bytes());
            context.add_message(m2);
            context.print_threads();
            println!("\n");
        }

        println!("\n\n");
        context.print_threads_messages();
    }
}