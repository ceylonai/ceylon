use std::time::Duration;

use libp2p::swarm::NetworkBehaviour;
use libp2p::{gossipsub, identify, identity, mdns, ping, rendezvous};

use crate::peer::behaviour::base::create_gossip_sub_config;
use crate::peer::behaviour::PeerBehaviour;

// We create a custom network behaviour that combines Gossipsub and Mdns.
#[derive(NetworkBehaviour)]
#[behaviour(to_swarm = "ClientPeerEvent")]
pub struct ClientPeerBehaviour {
    pub identify: identify::Behaviour,
    pub rendezvous: rendezvous::client::Behaviour,
    pub ping: ping::Behaviour,
    pub gossip_sub: gossipsub::Behaviour,
}

#[derive(Debug)]
pub enum ClientPeerEvent {
    GossipSub(gossipsub::Event),
    Mdns(mdns::Event),
    Ping(ping::Event),
    Identify(identify::Event),
    Rendezvous(rendezvous::client::Event),
}

impl From<gossipsub::Event> for ClientPeerEvent {
    fn from(event: gossipsub::Event) -> Self {
        ClientPeerEvent::GossipSub(event)
    }
}

impl From<mdns::Event> for ClientPeerEvent {
    fn from(event: mdns::Event) -> Self {
        ClientPeerEvent::Mdns(event)
    }
}

impl From<ping::Event> for ClientPeerEvent {
    fn from(event: ping::Event) -> Self {
        ClientPeerEvent::Ping(event)
    }
}

impl From<rendezvous::client::Event> for ClientPeerEvent {
    fn from(event: rendezvous::client::Event) -> Self {
        ClientPeerEvent::Rendezvous(event)
    }
}
impl From<identify::Event> for ClientPeerEvent {
    fn from(event: identify::Event) -> Self {
        ClientPeerEvent::Identify(event)
    }
}

impl PeerBehaviour for ClientPeerBehaviour {
    fn new(local_public_key: identity::Keypair) -> Self {
        // Set a custom gossip_sub_config configuration
        let gossip_sub_config = create_gossip_sub_config();
        let gossip_sub = gossipsub::Behaviour::new(
            gossipsub::MessageAuthenticity::Signed(local_public_key.clone()),
            gossip_sub_config,
        )
        .unwrap();

        Self {
            gossip_sub,
            identify: identify::Behaviour::new(identify::Config::new(
                "/CEYLON-AI-IDENTITY/0.0.1".to_string(),
                local_public_key.public(),
            )),
            rendezvous: rendezvous::client::Behaviour::new(local_public_key.clone()),
            ping: ping::Behaviour::new(ping::Config::new().with_interval(Duration::from_secs(10))),
        }
    }
}
