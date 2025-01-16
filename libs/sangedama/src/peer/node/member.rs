use std::net::Ipv4Addr;
use std::str::FromStr;

use futures::StreamExt;
use libp2p::multiaddr::Protocol;
use libp2p::swarm::{
    dial_opts::{DialOpts, PeerCondition},
    SwarmEvent,
};
use libp2p::{gossipsub, identity, rendezvous, Multiaddr, PeerId, Swarm};
use tokio::select;
use tokio_util::sync::CancellationToken;
use tracing::{debug, error, info};

use crate::peer::behaviour::{ClientPeerBehaviour, ClientPeerEvent};
use crate::peer::message::data::{EventType, MessageType, NodeMessage};
use crate::peer::peer_swarm::create_swarm;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::mpsc;
use tokio::sync::RwLock;
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
        rendezvous_point_public_ip: String,
    ) -> Self {
        let rendezvous_point_address = Multiaddr::empty()
            .with(Protocol::Ip4(
                Ipv4Addr::from_str(&rendezvous_point_public_ip).unwrap(),
            ))
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
    direct_channels: Arc<RwLock<HashMap<String, mpsc::Sender<Vec<u8>>>>>,
    channel_rx: Option<mpsc::Receiver<Vec<u8>>>,
    channel_tx: mpsc::Sender<Vec<u8>>,

    outside_tx: mpsc::Sender<NodeMessage>,
    inside_rx: mpsc::Receiver<Vec<u8>>,
    inside_tx: mpsc::Sender<Vec<u8>>,
}

impl MemberPeer {
    pub async fn create(
        config: MemberPeerConfig,
        key: identity::Keypair,
    ) -> (Self, tokio::sync::mpsc::Receiver<NodeMessage>) {
        let swarm = create_swarm::<ClientPeerBehaviour>(key).await;
        let (outside_tx, outside_rx) = mpsc::channel::<NodeMessage>(100);
        let (inside_tx, inside_rx) = mpsc::channel::<Vec<u8>>(100);
        let (channel_tx, channel_rx) = mpsc::channel::<Vec<u8>>(100);

        (
            Self {
                config,
                id: swarm.local_peer_id().to_string(),
                swarm,
                direct_channels: Arc::new(RwLock::new(HashMap::new())),
                channel_rx: Some(channel_rx),
                channel_tx,
                outside_tx,
                inside_rx,
                inside_tx,
            },
            outside_rx,
        )
    }

    pub fn emitter(&self) -> tokio::sync::mpsc::Sender<Vec<u8>> {
        self.inside_tx.clone()
    }

    pub fn get_sender(&self) -> mpsc::Sender<Vec<u8>> {
        self.channel_tx.clone()
    }

    // Get a direct channel to a peer
    pub async fn get_peer_channel(&self, peer_id: &str) -> Option<mpsc::Sender<Vec<u8>>> {
        let channels = self.direct_channels.read().await;
        channels.get(peer_id).cloned()
    }

    // Send a direct message to a peer
    pub async fn send_direct(
        &self,
        peer_id: &str,
        message: Vec<u8>,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        if let Some(sender) = self.get_peer_channel(peer_id).await {
            sender.send(message).await?;
            Ok(())
        } else {
            Err("Peer channel not found".into())
        }
    }

    pub async fn run(&mut self, cancellation_token: CancellationToken) {
        let name = self.config.name.clone();
        info!("Peer {:?}: {:?} Starting..", name.clone(), self.id.clone());
        let ext_address = Multiaddr::empty()
            .with(Protocol::Ip4(Ipv4Addr::UNSPECIFIED))
            .with(Protocol::Udp(0))
            .with(Protocol::QuicV1);
        self.swarm.add_external_address(ext_address.clone());
        info!(
            "Peer {:?}: {:?} External address: {:?}",
            name.clone(),
            self.id.clone(),
            ext_address.clone()
        );
        let admin_peer_id = self.config.admin_peer;
        let rendezvous_point_address = self.config.rendezvous_point_address.clone();
        info!(
            "Peer {:?}: {:?} Rendezvous point address: {:?} / admin peer: {:?}",
            name.clone(),
            self.id.clone(),
            rendezvous_point_address.clone(),
            admin_peer_id.clone()
        );

        let dial_opts = DialOpts::peer_id(admin_peer_id)
            .addresses(vec![rendezvous_point_address])
            .condition(PeerCondition::Always)
            .build();
        self.swarm.dial(dial_opts).unwrap();

        let name_copy = name.clone();

        let mut channel_rx = self.channel_rx.take().unwrap();

        loop {
            select! {
                _ = cancellation_token.cancelled() => {
                    break;
                }
                 Some(message) = channel_rx.recv() => {
                    if let Err(e) = self.outside_tx.send(NodeMessage::Message {
                        time: std::time::SystemTime::now()
                            .duration_since(std::time::UNIX_EPOCH)
                            .unwrap()
                            .as_secs_f64() as u64,
                        created_by: self.id.clone(),
                        data: message,
                        message_type: MessageType::Direct {
                            to_peer: self.id.clone()
                        },
                    }).await {
                        error!("Failed to forward direct message: {:?}", e);
                    }
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

                             let (tx, mut rx) = mpsc::channel::<Vec<u8>>(100);
                            {
                                let mut channels = self.direct_channels.write().await;
                                channels.insert(peer_id.to_string(), tx);
                            }
                        }
                        SwarmEvent::ConnectionClosed { peer_id, cause,.. } => {
                            if peer_id == self.config.admin_peer {
                                error!("Lost connection to rendezvous point {:?}", cause);
                            }
                            let mut channels = self.direct_channels.write().await;
                            channels.remove(&peer_id.to_string());
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
                            message_type: MessageType::Broadcast,
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
                gossipsub::Event::Message { message, .. } => {
                    let msg = NodeMessage::from_bytes(message.data.clone());

                    if let NodeMessage::Message {
                        message_type,
                        data,
                        created_by,
                        ..
                    } = msg
                    {
                        match message_type {
                            MessageType::Direct { to_peer } => {
                                // Only process if we're the intended recipient
                                if to_peer == self.id {
                                    match self
                                        .outside_tx
                                        .send(NodeMessage::Message {
                                            time: std::time::SystemTime::now()
                                                .duration_since(std::time::UNIX_EPOCH)
                                                .unwrap()
                                                .as_secs_f64()
                                                as u64,
                                            created_by,
                                            message_type: MessageType::Direct { to_peer },
                                            data,
                                        })
                                        .await
                                    {
                                        Ok(_) => {}
                                        Err(e) => {
                                            error!("Failed to forward direct message: {:?}", e)
                                        }
                                    }
                                }
                            }
                            MessageType::Broadcast => {
                                // Process broadcast messages as before
                                match self
                                    .outside_tx
                                    .send(NodeMessage::from_bytes(message.data))
                                    .await
                                {
                                    Ok(_) => {}
                                    Err(e) => {
                                        error!("Failed to forward broadcast message: {:?}", e)
                                    }
                                }
                            }
                        }
                    }
                }
                gossipsub::Event::Subscribed { peer_id, topic } => {
                    info!("Subscribed to topic: {:?} from peer: {:?}", topic, peer_id);
                    if peer_id.to_string() == self.config.admin_peer.to_string() {
                        info!("Member {} Subscribe with Admin", name_.clone());
                        let msg = NodeMessage::Event {
                            time: std::time::SystemTime::now()
                                .duration_since(std::time::UNIX_EPOCH)
                                .unwrap()
                                .as_secs_f64() as u64,
                            created_by: peer_id.to_string(),
                            event: EventType::Subscribe {
                                topic: topic.to_string(),
                                peer_id: peer_id.to_string(),
                            },
                        };
                        match self.outside_tx.send(msg).await {
                            Ok(_) => {}
                            Err(e) => {
                                error!("Failed to send message to outside: {:?}", e);
                            }
                        };
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
