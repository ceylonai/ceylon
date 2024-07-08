use std::collections::VecDeque;
use std::time::{Duration, Instant};

#[derive(Clone, Debug)]
pub struct CachedMessage {
    topic: String,
    data: Vec<u8>,
    id: u64,
    timestamp: Instant,
}

pub struct MessageCache {
    messages: VecDeque<CachedMessage>,
    max_size: usize,
    max_age: Duration,
}

impl MessageCache {
    fn new(max_size: usize, max_age: Duration) -> Self {
        MessageCache {
            messages: VecDeque::new(),
            max_size,
            max_age,
        }
    }

    fn add_message(&mut self, topic: String, data: Vec<u8>, id: u64) {
        let message = CachedMessage {
            topic,
            data,
            id,
            timestamp: Instant::now(),
        };

        self.messages.push_back(message);

        // Remove old messages
        self.clean();
    }

    fn clean(&mut self) {
        let now = Instant::now();
        while self.messages.len() > self.max_size ||
            (self.messages.front().map_or(false, |m| now.duration_since(m.timestamp) > self.max_age)) {
            self.messages.pop_front();
        }
    }

    fn get_recent_messages(&self, since: Instant) -> Vec<CachedMessage> {
        self.messages.iter()
            .filter(|m| m.timestamp > since)
            .cloned()
            .collect()
    }
}