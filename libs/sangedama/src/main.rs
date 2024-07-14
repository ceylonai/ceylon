use std::net::Ipv4Addr;
use std::str::FromStr;
use libp2p::{Multiaddr, PeerId};
use libp2p::multiaddr::Protocol;
use tokio::select;
use tracing::{info};
use tracing_subscriber::fmt::format;
use uuid::Uuid;
use crate::peer::node::{AdminPeer, AdminPeerConfig, MemberPeer, MemberPeerConfig};

mod p2p;
mod peer;
#[tokio::main]
async fn main() {
    let subscriber = tracing_subscriber::FmtSubscriber::new();
    // use that subscriber to process traces emitted after this point
    tracing::subscriber::set_global_default(subscriber).unwrap();
    let workspace_id = "workspace-test".to_string();
    info!("Starting {}", workspace_id);

    let admin_port = 7845;
    let admin_config = AdminPeerConfig::new(admin_port, workspace_id.clone());

    let (mut admin_peer, mut admin_listener) = AdminPeer::create(admin_config.clone()).await;
    let admin_id = admin_peer.id.clone();
    let admin_emitter = admin_peer.emitter();
    let task_admin = tokio::task::spawn(async move {
        admin_peer.run(None).await;
    });

    let task_admin_listener = tokio::spawn(async move {
        loop {
            select! {
                event = admin_listener.recv() => {
                    info!("Admin listener {:?}", event);
                }
            }
        }
    });

    let task_run_admin = tokio::task::spawn(async move {
        loop {
            admin_emitter.send("test".to_string().as_bytes().to_vec()).await;
            tokio::time::sleep(std::time::Duration::from_millis(10000)).await;
        }
    });

    // Here we create localhost address to connect peer with admin
    let peer_dial_address = Multiaddr::empty()
        .with(Protocol::Ip4(Ipv4Addr::LOCALHOST))
        .with(Protocol::Udp(admin_port))
        .with(Protocol::QuicV1);


    let mut peer1 = MemberPeer::create(MemberPeerConfig {
        name: "peer1".to_string(),
        workspace_id: workspace_id.clone(),
        admin_peer: PeerId::from_str(&admin_id).unwrap(),
        rendezvous_point_address: peer_dial_address.clone(),
    }).await;
    let task_client = tokio::task::spawn(async move {
        peer1.run().await;
    });


    let mut peer2 = MemberPeer::create(MemberPeerConfig {
        name: "peer2".to_string(),
        workspace_id: workspace_id.clone(),
        admin_peer: PeerId::from_str(&admin_id).unwrap(),
        rendezvous_point_address: peer_dial_address.clone(),
    }).await;
    let task_client2 = tokio::task::spawn(async move {
        peer2.run().await;
    });

    task_admin.await.unwrap();
    task_admin_listener.await.unwrap();
    task_run_admin.await.unwrap();
    
    task_client.await.unwrap();
    task_client2.await.unwrap();
}