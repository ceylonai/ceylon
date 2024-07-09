use std::hash::{DefaultHasher, Hash, Hasher};
use std::time::Duration;

use libp2p::{gossipsub, identify, identity, mdns, rendezvous};
use libp2p::swarm::NetworkBehaviour;
use libp2p_gossipsub::Config;
use tokio::io;
use crate::peer::behaviour::PeerBehaviour;

// We create a custom network behaviour that combines Gossipsub and Mdns.
#[derive(NetworkBehaviour)]
pub struct ClientPeerBehaviour {
    pub gossip_sub: gossipsub::Behaviour,
    pub identify: identify::Behaviour,
}

impl PeerBehaviour for ClientPeerBehaviour {
    fn new(local_public_key: identity::Keypair) -> Self {
        // Set a custom gossip_sub_config configuration
        let gossip_sub_config = create_gossip_sub_config();
        let gossip_sub = gossipsub::Behaviour::new(
            gossipsub::MessageAuthenticity::Signed(local_public_key.clone()),
            gossip_sub_config,
        ).unwrap();


        let mdns_config = mdns::Config {
            ttl: Duration::from_secs(60),
            query_interval: Duration::from_secs(1 * 60),
            enable_ipv6: false,
        };

        let mdns_ = mdns::tokio::Behaviour::new(mdns_config, local_public_key.public().to_peer_id())
            .unwrap();

        Self {
            gossip_sub,
            identify: identify::Behaviour::new(identify::Config::new(
                "/CEYLON-AI-IDENTITY/0.0.1".to_string(),
                local_public_key.public(),
            )),
        }
    }
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