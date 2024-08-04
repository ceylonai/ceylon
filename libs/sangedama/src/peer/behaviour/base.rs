use std::hash::{DefaultHasher, Hash, Hasher};
use std::time::Duration;

use libp2p::gossipsub::{self, Config};
use libp2p::swarm::NetworkBehaviour;
use tokio::io;

pub trait PeerBehaviour
where
    Self: NetworkBehaviour,
{
    fn new(local_public_key: libp2p::identity::Keypair) -> Self;
}

pub fn message_id_fn(message: &gossipsub::Message) -> gossipsub::MessageId {
    let mut s = DefaultHasher::new();
    message.data.hash(&mut s);
    gossipsub::MessageId::from(s.finish().to_string())
}

pub fn create_gossip_sub_config() -> Config {
    gossipsub::ConfigBuilder::default()
        .history_length(10)
        .history_gossip(10)
        .heartbeat_interval(Duration::from_secs(1)) // This is set to aid debugging by not cluttering the log space
        .validation_mode(gossipsub::ValidationMode::Strict) // This sets the kind of message validation. The default is Strict (enforce message signing)
        .message_id_fn(message_id_fn) // content-address messages. No two messages of the same content will be propagated.
        .build()
        .map_err(|msg| io::Error::new(io::ErrorKind::Other, msg))
        .unwrap()
}
