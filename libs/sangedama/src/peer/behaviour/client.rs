use std::time::Duration;

use libp2p::{gossipsub, identify, identity, mdns, PeerId, ping, rendezvous};
use libp2p::swarm::{NetworkBehaviour, SwarmEvent};
use tracing::info;
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
        ).unwrap();

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


impl ClientPeerBehaviour {
    pub(crate) fn process_event(&mut self, event: SwarmEvent<ClientPeerEvent>, rendezvous_point: PeerId) {
        match event {
            SwarmEvent::NewListenAddr { address, .. } => {
                tracing::info!("Listening on {}", address);
            }
            SwarmEvent::ConnectionClosed {
                peer_id,
                cause: Some(error),
                ..
            } if peer_id == rendezvous_point => {
                tracing::error!("Lost connection to rendezvous point {}", error);
            }
            SwarmEvent::ConnectionEstablished { peer_id, .. } if peer_id == rendezvous_point => {
                if let Err(error) = self.rendezvous.register(
                    rendezvous::Namespace::from_static("CEYLON-AI-PEER"),
                    rendezvous_point,
                    None,
                ) {
                    tracing::error!("Failed to register: {error}");
                }
                tracing::info!("Connection established with rendezvous point {}", peer_id);
            }
            // once `/identify` did its job, we know our external address and can register
            SwarmEvent::Behaviour(ClientPeerEvent::Rendezvous(
                                      rendezvous::client::Event::Registered {
                                          namespace,
                                          ttl,
                                          rendezvous_node,
                                      },
                                  )) => {
                let topic = gossipsub::IdentTopic::new("test_topic");
                self.gossip_sub.subscribe(&topic).unwrap();

                tracing::info!(
                    "Registered for namespace '{}' at rendezvous point {} for the next {} seconds",
                    namespace,
                    rendezvous_node,
                    ttl
                );
            }
            SwarmEvent::Behaviour(ClientPeerEvent::Rendezvous(
                                      rendezvous::client::Event::RegisterFailed {
                                          rendezvous_node,
                                          namespace,
                                          error,
                                      },
                                  )) => {
                tracing::error!(
                    "Failed to register: rendezvous_node={}, namespace={}, error_code={:?}",
                    rendezvous_node,
                    namespace,
                    error
                );
            }

            SwarmEvent::Behaviour(ClientPeerEvent::GossipSub(gossipsub::Event::Message {
                                                                          propagation_source: peer_id,
                                                                          message_id,
                                                                          message,
                                                                      })) => {
                info!("Received message '{:?}' from {:?} on {:?}", String::from_utf8_lossy(&message.data), peer_id, message_id);
            }

            SwarmEvent::Behaviour(ClientPeerEvent::GossipSub(gossipsub::Event::Subscribed { peer_id, topic })) => {
                info!("Subscribed to  {:?} from {:?}", topic, peer_id);
            }
            // SwarmEvent::Behaviour(ClientPeerBehaviourEvent::Ping(ping::Event {
            //                                                          peer,
            //                                                          result: Ok(rtt),
            //                                                          ..
            //                                                      })) if peer != rendezvous_point => {
            //     tracing::info!("Ping to {} is {}ms", peer, rtt.as_millis())
            // }
            other => {
                // tracing::info!("Unhandled {:?}", other);
            }
        }
    }
}
