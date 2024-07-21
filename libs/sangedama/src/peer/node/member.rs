use futures::StreamExt;
use libp2p::multiaddr::Protocol;
use libp2p::swarm::dial_opts::{DialOpts, PeerCondition};
use libp2p::swarm::SwarmEvent;
use libp2p::{gossipsub, identity, rendezvous, Multiaddr, PeerId, Swarm};
use std::net::Ipv4Addr;
use std::str::FromStr;
use tokio::select;
use tokio_util::sync::CancellationToken;
use tracing::{debug, error, info};

use crate::peer::behaviour::{ClientPeerBehaviour, ClientPeerEvent};
use crate::peer::message::data::NodeMessage;
use crate::peer::peer_swarm::create_swarm;

#[derive(Debug, Clone)]
pub struct MemberPeerConfig {
    pub name: String,
    pub workspace_id: String,
    pub admin_peer: PeerId,
    pub rendezvous_point_address: Multiaddr,
}

impl MemberPeerConfig {
    pub fn new(
        name: String,
        workspace_id: String,
        admin_peer: String,
        rendezvous_point_admin_port: u16,
    ) -> Self {
        let rendezvous_point_address = Multiaddr::empty()
            .with(Protocol::Ip4(Ipv4Addr::LOCALHOST))
            .with(Protocol::Udp(rendezvous_point_admin_port))
            .with(Protocol::QuicV1);

        Self {
            name,
            workspace_id,
            admin_peer: PeerId::from_str(&admin_peer).unwrap(),
            rendezvous_point_address,
        }
    }
}

pub struct MemberPeer {
    config: MemberPeerConfig,
    pub id: String,
    swarm: Swarm<ClientPeerBehaviour>,

    outside_tx: tokio::sync::mpsc::Sender<NodeMessage>,

    inside_rx: tokio::sync::mpsc::Receiver<Vec<u8>>,
    inside_tx: tokio::sync::mpsc::Sender<Vec<u8>>,
}

impl MemberPeer {
    pub async fn create(
        config: MemberPeerConfig,
        key: identity::Keypair,
    ) -> (Self, tokio::sync::mpsc::Receiver<NodeMessage>) {
        let swarm = create_swarm::<ClientPeerBehaviour>(key).await;

        let (outside_tx, outside_rx) = tokio::sync::mpsc::channel::<NodeMessage>(100);

        let (inside_tx, inside_rx) = tokio::sync::mpsc::channel::<Vec<u8>>(100);

        (
            Self {
                config,
                id: swarm.local_peer_id().to_string(),
                swarm,

                outside_tx,

                inside_tx,
                inside_rx,
            },
            outside_rx,
        )
    }

    pub fn emitter(&self) -> tokio::sync::mpsc::Sender<Vec<u8>> {
        self.inside_tx.clone()
    }
    pub async fn run(&mut self, cancellation_token: CancellationToken) {
        let name = self.config.name.clone();
        info!("Peer {:?}: {:?} Starting..", name.clone(), self.id.clone());
        let ext_address = Multiaddr::empty()
            .with(Protocol::Ip4(Ipv4Addr::UNSPECIFIED))
            .with(Protocol::Udp(0))
            .with(Protocol::QuicV1);
        self.swarm.add_external_address(ext_address.clone());

        let admin_peer_id = self.config.admin_peer;
        let rendezvous_point_address = self.config.rendezvous_point_address.clone();

        let dial_opts = DialOpts::peer_id(admin_peer_id)
            .addresses(vec![rendezvous_point_address])
            .condition(PeerCondition::Always)
            .build();
        self.swarm.dial(dial_opts).unwrap();

        let name_copy = name.clone();
        loop {
            select! {
                _ = cancellation_token.cancelled() => {
                    break;
                }
                event = self.swarm.select_next_some() => {
                    match event {
                       SwarmEvent::ConnectionEstablished { peer_id, .. } => {
                            if peer_id ==  self.config.admin_peer {
                                if let Err(error) = self.swarm.behaviour_mut().rendezvous.register(
                                    rendezvous::Namespace::from_static("CEYLON-AI-PEER"),
                                     self.config.admin_peer,
                                    None,
                                ) {
                                    error!("Failed to register: {error}");
                                }
                                info!("Connection established with rendezvous point {}", peer_id);
                            }
                        }
                        SwarmEvent::ConnectionClosed { peer_id, cause,.. } => {
                            if peer_id == self.config.admin_peer {
                                error!("Lost connection to rendezvous point {:?}", cause);
                            }
                        }
                        SwarmEvent::Behaviour(event) => {
                            self.process_event(event).await;
                        }
                        other => {
                            debug!("Unhandled {:?}", other);
                        }
                    }
                }

                message = self.inside_rx.recv() => {
                    if let Some(message) = message {
                        let topic = gossipsub::IdentTopic::new(self.config.workspace_id.clone());

                        let distributed_message = NodeMessage::Message {
                            data: message,
                            time: std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() as u64,
                            created_by: self.id.clone(),
                        };
                        match self.swarm.behaviour_mut().gossip_sub.publish(topic.clone(),distributed_message.to_bytes()){
                            Ok(_) => {}
                            Err(e) => {
                                error!("Failed to broadcast message from {}: {:?} Topic {:?}",name_copy, e, topic.to_string());
                            }
                        }
                    }
                }
            }
        }
    }

    async fn process_event(&mut self, event: ClientPeerEvent) {
        let name_ = self.config.name.clone();
        match event {
            ClientPeerEvent::Rendezvous(event) => match event {
                rendezvous::client::Event::Registered {
                    namespace,
                    ttl,
                    rendezvous_node,
                } => {
                    info!(
                            "Registered for namespace '{}' at rendezvous point {} for the next {} seconds",
                            namespace, rendezvous_node, ttl
                        );
                    let topic = gossipsub::IdentTopic::new(self.config.workspace_id.clone());
                    self.swarm
                        .behaviour_mut()
                        .gossip_sub
                        .subscribe(&topic)
                        .unwrap();
                }
                _ => {
                    info!("Rendezvous: {:?}", event);
                }
            },

            ClientPeerEvent::GossipSub(event) => match event {
                gossipsub::Event::Subscribed { peer_id, topic } => {
                    info!("Subscribed to topic: {:?} from peer: {:?}", topic, peer_id);
                    if peer_id.to_string() == self.config.admin_peer.to_string() {
                        info!("Member {} Subscribe with Admin", name_.clone());
                    }
                }

                gossipsub::Event::Unsubscribed { peer_id, topic } => {
                    info!(
                        "Unsubscribed from topic: {:?} from peer: {:?}",
                        topic, peer_id
                    );
                    if peer_id.to_string() == self.config.admin_peer.to_string() {
                        info!("Member {} Unsubscribe with Admin", name_.clone());
                    }
                }

                gossipsub::Event::Message { message, .. } => {
                    let msg = NodeMessage::from_bytes(message.data);
                    match self.outside_tx.send(msg).await {
                        Ok(_) => {}
                        Err(e) => {
                            error!("Failed to send message to outside: {:?}", e);
                        }
                    };
                }

                _ => {
                    info!("GossipSub: {:?}", event);
                }
            },

            _ => {
                // tracing::info!("Unhandled {:?}", other);
            }
        }
    }
}
