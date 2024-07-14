use std::net::Ipv4Addr;

use futures::StreamExt;
use libp2p::{gossipsub, Multiaddr, PeerId, rendezvous, Swarm};
use libp2p::multiaddr::Protocol;
use libp2p::swarm::dial_opts::{DialOpts, PeerCondition};
use libp2p::swarm::SwarmEvent;
use tokio::select;
use tracing::{info};

use crate::peer::behaviour::{ClientPeerBehaviour, ClientPeerEvent};
use crate::peer::peer_swarm::create_swarm;

pub struct MemberPeerConfig {
    pub name: String,
    pub workspace_id: String,
    pub admin_peer: PeerId,
    pub rendezvous_point_address: Multiaddr,
}

pub struct MemberPeer {
    config: MemberPeerConfig,
    pub id: String,
    swarm: Swarm<ClientPeerBehaviour>,
}


impl MemberPeer {
    pub async fn create(config: MemberPeerConfig) -> Self {
        let swarm = create_swarm::<ClientPeerBehaviour>().await;
        Self {
            config,
            id: swarm.local_peer_id().to_string(),
            swarm,
        }
    }

    pub async fn run(&mut self) {
        let name = self.config.name.clone();
        info!("Peer {:?}: {:?} Starting..", name.clone(), self.id.clone());
        let ext_address = Multiaddr::empty()
            .with(Protocol::Ip4(Ipv4Addr::UNSPECIFIED))
            .with(Protocol::Udp(0))
            .with(Protocol::QuicV1);
        self.swarm.add_external_address(ext_address.clone());

        let admin_peer_id = self.config.admin_peer.clone();
        let rendezvous_point_address = self.config.rendezvous_point_address.clone();

        let dial_opts = DialOpts::peer_id(admin_peer_id)
            .addresses(
                vec![rendezvous_point_address]
            )
            // .extend_addresses_through_behaviour()
            .condition(PeerCondition::Always)
            .build();
        self.swarm.dial(dial_opts).unwrap();


        let name_copy = name.clone();
        loop {
            select! {
                event = self.swarm.select_next_some() => {
                    self.process_event(event, admin_peer_id);
                }
            }
        }
    }


    pub(crate) fn process_event(&mut self, event: SwarmEvent<ClientPeerEvent>, rendezvous_point: PeerId) {
        match event {
            SwarmEvent::NewListenAddr { address, .. } => {
                info!("Listening on {}", address);
            }
            SwarmEvent::ConnectionClosed {
                peer_id,
                cause: Some(error),
                ..
            } if peer_id == rendezvous_point => {
                tracing::error!("Lost connection to rendezvous point {}", error);
            }
            SwarmEvent::ConnectionEstablished { peer_id, .. } if peer_id == rendezvous_point => {
                if let Err(error) = self.swarm.behaviour_mut().rendezvous.register(
                    rendezvous::Namespace::from_static("CEYLON-AI-PEER"),
                    rendezvous_point,
                    None,
                ) {
                    tracing::error!("Failed to register: {error}");
                }
                info!("Connection established with rendezvous point {}", peer_id);
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
                self.swarm.behaviour_mut().gossip_sub.subscribe(&topic).unwrap();

                info!(
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