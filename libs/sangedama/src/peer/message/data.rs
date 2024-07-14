use libp2p::PeerId;
pub enum EventType {
    Message,
    Subscribe,
    Unsubscribe,
    Listen,
    Expired,
    Discovered,
    ConnectionClosed,
    ConnectionEstablished,
}

pub enum NodeMessage {
    Event {
        time: u64,
        created_by: PeerId,
        event: EventType,
    },
    Message {
        time: u64,
        created_by: PeerId,
        data: Vec<u8>,
    },
} 