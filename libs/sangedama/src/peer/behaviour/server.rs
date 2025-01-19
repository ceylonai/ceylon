/*
 * Copyright (c) 2023-2025 SYIGEN LTD.
 * Author: Dewmal - dewmal@syigen.com
 * Created: 2025-01-19
 * Ceylon Project - https://github.com/ceylonai/ceylon
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * This file is part of Ceylon Project.
 * Original authors: Dewmal - dewmal@syigen.com
 * For questions and support: https://github.com/ceylonai/ceylon/issues
 */

use std::time::Duration;

use libp2p::swarm::NetworkBehaviour;
use libp2p::{gossipsub, identify, ping, rendezvous};

use crate::peer::behaviour::{base::create_gossip_sub_config, PeerBehaviour};

// We create a custom network behaviour that combines Gossipsub and Mdns.
#[derive(NetworkBehaviour)]
#[behaviour(to_swarm = "PeerAdminEvent")]
pub struct PeerAdminBehaviour {
    pub rendezvous: rendezvous::server::Behaviour,
    pub ping: ping::Behaviour,
    pub identify: identify::Behaviour,
    pub gossip_sub: gossipsub::Behaviour,
}

#[derive(Debug)]
pub enum PeerAdminEvent {
    Rendezvous(rendezvous::server::Event),
    Ping(ping::Event),
    Identify(identify::Event),
    GossipSub(gossipsub::Event),
}

impl From<gossipsub::Event> for PeerAdminEvent {
    fn from(event: gossipsub::Event) -> Self {
        PeerAdminEvent::GossipSub(event)
    }
}

impl From<ping::Event> for PeerAdminEvent {
    fn from(event: ping::Event) -> Self {
        PeerAdminEvent::Ping(event)
    }
}

impl From<rendezvous::server::Event> for PeerAdminEvent {
    fn from(event: rendezvous::server::Event) -> Self {
        PeerAdminEvent::Rendezvous(event)
    }
}
impl From<identify::Event> for PeerAdminEvent {
    fn from(event: identify::Event) -> Self {
        PeerAdminEvent::Identify(event)
    }
}

impl PeerBehaviour for PeerAdminBehaviour {
    fn new(local_public_key: libp2p::identity::Keypair) -> Self {
        let rendezvous_server =
            rendezvous::server::Behaviour::new(rendezvous::server::Config::default());
        let gossip_sub_config = create_gossip_sub_config();
        let gossip_sub = gossipsub::Behaviour::new(
            gossipsub::MessageAuthenticity::Signed(local_public_key.clone()),
            gossip_sub_config,
        )
        .unwrap();

        Self {
            gossip_sub,
            rendezvous: rendezvous_server,
            ping: ping::Behaviour::new(ping::Config::new().with_interval(Duration::from_secs(10))),
            identify: identify::Behaviour::new(identify::Config::new(
                "/CEYLON-AI-IDENTITY/0.0.1".to_string(),
                local_public_key.public(),
            )),
        }
    }
}
