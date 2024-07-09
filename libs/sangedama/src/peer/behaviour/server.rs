use std::time::Duration;

use libp2p::{identify, ping, rendezvous};
use libp2p::swarm::NetworkBehaviour;
use tracing::info;
use crate::peer::behaviour::PeerBehaviour;

// We create a custom network behaviour that combines Gossipsub and Mdns.
#[derive(NetworkBehaviour)]
pub struct PeerAdminBehaviour {
    pub rendezvous: rendezvous::server::Behaviour,
    pub ping: ping::Behaviour,
    pub identify: identify::Behaviour,
}

impl PeerBehaviour for PeerAdminBehaviour {
    fn new(local_public_key: libp2p::identity::Keypair) -> Self {
        let rendezvous_server = rendezvous::server::Behaviour::new(rendezvous::server::Config::default());
        Self {
            rendezvous: rendezvous_server,
            ping: ping::Behaviour::new(ping::Config::new().with_interval(Duration::from_secs(1))),
            identify: identify::Behaviour::new(identify::Config::new(
                "/CEYLON-AI-IDENTITY/0.0.1".to_string(),
                local_public_key.public(),
            )),
        }
    }
}

impl PeerAdminBehaviour {
    pub fn process_event(&mut self, event: PeerAdminBehaviourEvent) {
        match event {
            PeerAdminBehaviourEvent::Rendezvous(event) => {
                info!( "Rendezvous event: {:?}", event);
            }
            PeerAdminBehaviourEvent::Ping(event) => {
                info!( "Rendezvous Ping: {:?}", event);
            }
            PeerAdminBehaviourEvent::Identify(event) => {
                info!( "Rendezvous Identify: {:?}", event);
            }
        }
    }
} 
