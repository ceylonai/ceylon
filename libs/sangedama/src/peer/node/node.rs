/*
 * Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
 * Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
 *
 */

use futures::StreamExt;
use libp2p::multiaddr::Protocol;
use libp2p::swarm::{
    dial_opts::{DialOpts, PeerCondition},
    SwarmEvent,
};
use libp2p::{gossipsub, identity, rendezvous, Multiaddr, PeerId, Swarm};
use std::collections::HashMap;
use std::net::Ipv4Addr;
use std::str::FromStr;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Duration;
use tokio::select;
use tokio_util::sync::CancellationToken;
use tracing::{debug, error, info};

use crate::peer::behaviour::peer::{
    PeerMode, RendezvousEvent, UnifiedPeerBehaviour, UnifiedPeerEvent,
};
use crate::peer::message::data::{EventType, MessageType, NodeMessage, NodeMessageTransporter};
use crate::peer::peer_swarm::create_swarm;

static CACHED_TIMESTAMP: AtomicU64 = AtomicU64::new(0);
const DEFAULT_BUFFER_SIZE: u16 = 100;

#[derive(Clone)]
pub struct UnifiedPeerConfig {
    pub name: String,
    pub workspace_id: String,
    pub mode: PeerMode,
    pub listen_port: Option<u16>,
    pub buffer_size: Option<u16>,
    pub admin_peer: Option<PeerId>,
    pub rendezvous_point_address: Option<Multiaddr>,
}

impl UnifiedPeerConfig {
    pub fn new_admin(workspace_id: String, listen_port: u16, buffer_size: Option<u16>) -> Self {
        Self {
            name: "admin".to_string(),
            workspace_id,
            mode: PeerMode::Admin,
            listen_port: Some(listen_port),
            buffer_size,
            admin_peer: None,
            rendezvous_point_address: None,
        }
    }

    pub fn new_member(
        name: String,
        workspace_id: String,
        admin_peer: String,
        rendezvous_point_admin_port: u16,
        rendezvous_point_public_ip: String,
        buffer_size: Option<u16>,
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
            mode: PeerMode::Client,
            listen_port: None,
            buffer_size,
            admin_peer: Some(PeerId::from_str(&admin_peer).unwrap()),
            rendezvous_point_address: Some(rendezvous_point_address),
        }
    }

    pub fn get_listen_address(&self) -> Multiaddr {
        Multiaddr::empty()
            .with(Protocol::Ip4(Ipv4Addr::UNSPECIFIED))
            .with(Protocol::Udp(self.listen_port.unwrap_or(0) as u16))
            .with(Protocol::QuicV1)
    }
}

pub struct UnifiedPeerImpl {
    pub id: String,
    swarm: Swarm<UnifiedPeerBehaviour>,
    pub config: UnifiedPeerConfig,
    connected_peers: HashMap<gossipsub::TopicHash, Vec<PeerId>>,
    outside_tx: tokio::sync::mpsc::Sender<NodeMessage>,
    inside_rx: tokio::sync::mpsc::Receiver<NodeMessageTransporter>,
    inside_tx: tokio::sync::mpsc::Sender<NodeMessageTransporter>,
}

impl UnifiedPeerImpl {
    pub async fn create(
        config: UnifiedPeerConfig,
        key: identity::Keypair,
    ) -> (Self, tokio::sync::mpsc::Receiver<NodeMessage>) {
        let swarm = create_swarm::<UnifiedPeerBehaviour>(key.clone()).await;

        let (outside_tx, outside_rx) = tokio::sync::mpsc::channel::<NodeMessage>(
            config.buffer_size.unwrap_or(DEFAULT_BUFFER_SIZE) as usize,
        );

        let (inside_tx, inside_rx) = tokio::sync::mpsc::channel::<NodeMessageTransporter>(
            config.buffer_size.unwrap_or(DEFAULT_BUFFER_SIZE) as usize,
        );

        (
            Self {
                config: config.clone(),
                id: swarm.local_peer_id().to_string(),
                swarm,
                connected_peers: HashMap::new(),
                outside_tx,
                inside_rx,
                inside_tx,
            },
            outside_rx,
        )
    }

    fn get_current_timestamp() -> u64 {
        CACHED_TIMESTAMP.load(Ordering::Relaxed)
    }

    pub fn emitter(&self) -> tokio::sync::mpsc::Sender<NodeMessageTransporter> {
        self.inside_tx.clone()
    }

    pub async fn run(&mut self, cancellation_token: CancellationToken) {
        info!("Peer {:?}: {:?} Starting..", self.config.name, self.id);

        match self.config.mode {
            PeerMode::Admin => {
                let listen_addr = self.config.get_listen_address();
                self.swarm.listen_on(listen_addr.clone()).unwrap();
                info!("Admin listening on: {:?}", listen_addr);
            }
            PeerMode::Client => {
                let ext_address = Multiaddr::empty()
                    .with(Protocol::Ip4(Ipv4Addr::UNSPECIFIED))
                    .with(Protocol::Udp(0))
                    .with(Protocol::QuicV1);
                self.swarm.add_external_address(ext_address.clone());

                if let (Some(admin_peer), Some(rendezvous_address)) = (
                    self.config.admin_peer,
                    self.config.rendezvous_point_address.clone(),
                ) {
                    let dial_opts = DialOpts::peer_id(admin_peer)
                        .addresses(vec![rendezvous_address.clone()])
                        .condition(PeerCondition::Always)
                        .build();
                    self.swarm.dial(dial_opts).unwrap();
                    info!("Member connecting to admin at: {:?}", rendezvous_address);
                }
            }
        }

        loop {
            select! {
                _ = cancellation_token.cancelled() => {
                    break;
                }
                event = self.swarm.select_next_some() => {
                    match event {
                        SwarmEvent::ConnectionEstablished { peer_id, .. } => {
                            match self.config.mode {
                                PeerMode::Client if Some(peer_id) == self.config.admin_peer => {
                                    if let Err(error) = self.swarm.behaviour_mut().rendezvous.client.register(
                                        rendezvous::Namespace::from_static("CEYLON-AI-PEER"),
                                        peer_id,
                                        None,
                                    ) {
                                        error!("Failed to register with admin: {error}");
                                    }
                                    info!("Connection established with admin {}", peer_id);
                                }
                                PeerMode::Admin => {
                                    info!("Admin: Connected to {}", peer_id);
                                }
                                _ => {}
                            }
                        }
                        SwarmEvent::ConnectionClosed { peer_id, .. } => {
                            info!("Disconnected from {}", peer_id);
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
                    if let Some(node_message_tr) = message {
                        let topic = gossipsub::IdentTopic::new(self.config.workspace_id.clone());
                        let (_from, message, to) = node_message_tr;

                        let distributed_message = NodeMessage::Message {
                            data: message,
                            time: std::time::SystemTime::now()
                                .duration_since(std::time::UNIX_EPOCH)
                                .unwrap()
                                .as_secs_f64() as u64,
                            created_by: self.id.clone(),
                            message_type: if to.is_none() {
                                MessageType::Broadcast
                            } else {
                                MessageType::Direct {
                                    to_peer: to.unwrap().to_string()
                                }
                            },
                        };

                        match self.swarm.behaviour_mut().gossip_sub.publish(topic, distributed_message.to_bytes()) {
                            Ok(_) => {}
                            Err(e) => {
                                error!("Failed to broadcast message: {:?}", e);
                            }
                        }
                    }
                }

                _ = tokio::time::sleep(Duration::from_nanos(1)) => {
                    CACHED_TIMESTAMP.store(0, Ordering::Relaxed);
                }
            }
        }
    }

    async fn process_event(&mut self, event: UnifiedPeerEvent) {
        match event {
            UnifiedPeerEvent::GossipSub(event) => {
                self.handle_gossipsub_event(event).await;
            }
            UnifiedPeerEvent::Rendezvous(event) => {
                self.handle_rendezvous_event(event).await;
            }
            UnifiedPeerEvent::Ping(_) => {}
            UnifiedPeerEvent::Identify(_) => {}
        }
    }

    async fn handle_gossipsub_event(&mut self, event: gossipsub::Event) {
        match event {
            gossipsub::Event::Message { message, .. } => {
                if let NodeMessage::Message {
                    message_type,
                    data,
                    created_by,
                    ..
                } = NodeMessage::from_bytes(message.data.clone())
                {
                    info!(
                        "Process Message {:?} from {}: Topic {}",
                        message_type,
                        self.config.name,
                        message.topic.to_string()
                    );

                    match message_type {
                        MessageType::Direct { to_peer } => {
                            if to_peer == self.id {
                                let current_time = Self::get_current_timestamp();
                                if let Err(e) = self
                                    .outside_tx
                                    .send(NodeMessage::Message {
                                        time: current_time,
                                        created_by,
                                        message_type: MessageType::Direct { to_peer },
                                        data,
                                    })
                                    .await
                                {
                                    error!("Failed to forward direct message: {:?}", e);
                                }
                            }
                        }
                        MessageType::Broadcast => {
                            if let Err(e) = self
                                .outside_tx
                                .send(NodeMessage::from_bytes(message.data))
                                .await
                            {
                                error!("Failed to forward broadcast message: {:?}", e);
                            }
                        }
                    }
                }
            }
            gossipsub::Event::Subscribed { topic, peer_id } => {
                info!("Subscribed to topic {:?} from peer: {:?}", topic, peer_id);
                if let PeerMode::Admin = self.config.mode {
                    self.connected_peers
                        .entry(topic.clone())
                        .or_insert_with(Vec::new)
                        .push(peer_id);
                }

                let current_time = Self::get_current_timestamp();
                if let Err(e) = self
                    .outside_tx
                    .send(NodeMessage::Event {
                        time: current_time,
                        created_by: peer_id.to_string(),
                        event: EventType::Subscribe {
                            topic: topic.to_string(),
                            peer_id: peer_id.to_string(),
                        },
                    })
                    .await
                {
                    error!("Failed to send subscribe event: {:?}", e);
                }
            }
            gossipsub::Event::Unsubscribed { topic, peer_id } => {
                info!(
                    "Unsubscribed from topic {:?} from peer: {:?}",
                    topic, peer_id
                );
                if let PeerMode::Admin = self.config.mode {
                    if let Some(peers) = self.connected_peers.get_mut(&topic) {
                        peers.retain(|p| p != &peer_id);
                    }
                }
            }
            _ => {}
        }
    }

    async fn handle_rendezvous_event(&mut self, event: RendezvousEvent) {
        let config = self.config.clone();
        match (config.mode, event) {
            (
                PeerMode::Client,
                RendezvousEvent::Client(rendezvous::client::Event::Registered {
                    namespace,
                    ttl,
                    rendezvous_node,
                }),
            ) => {
                info!(
                    "Registered for namespace '{}' at rendezvous point {} for the next {} seconds",
                    namespace, rendezvous_node, ttl
                );
                let topic = gossipsub::IdentTopic::new(self.config.workspace_id.clone());
                if let Err(e) = self.swarm.behaviour_mut().gossip_sub.subscribe(&topic) {
                    error!("Failed to subscribe to topic: {:?}", e);
                }
            }
            (
                PeerMode::Admin,
                RendezvousEvent::Server(rendezvous::server::Event::PeerRegistered { peer, .. }),
            ) => {
                info!("RendezvousServerConnected: {:?}", peer);
                let topic = gossipsub::IdentTopic::new(self.config.workspace_id.clone());
                if let Err(e) = self.swarm.behaviour_mut().gossip_sub.subscribe(&topic) {
                    error!("Failed to subscribe to topic: {:?}", e);
                }
            }
            _ => {}
        }
    }
}
