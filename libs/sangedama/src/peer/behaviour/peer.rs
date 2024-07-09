use std::hash::Hash;

use libp2p::{gossipsub, identify, identity};
use libp2p::swarm::NetworkBehaviour;

use crate::peer::behaviour::base::create_gossip_sub_config;
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

        Self {
            gossip_sub,
            identify: identify::Behaviour::new(identify::Config::new(
                "/CEYLON-AI-IDENTITY/0.0.1".to_string(),
                local_public_key.public(),
            )),
        }
    }
}

