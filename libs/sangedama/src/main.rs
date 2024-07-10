use std::net::Ipv4Addr;
use std::str::FromStr;
use libp2p::{Multiaddr, PeerId};
use libp2p::multiaddr::Protocol;
use tracing::{info};
use crate::peer::peer::{AdminPeer, AdminPeerConfig, Peer};

mod p2p;
mod peer;
#[tokio::main]
async fn main() {
    let subscriber = tracing_subscriber::FmtSubscriber::new();
    // use that subscriber to process traces emitted after this point
    tracing::subscriber::set_global_default(subscriber).unwrap();
    info!("Starting sangedama");

    let admin_port = 7845;
    let admin_config = AdminPeerConfig::new(admin_port);

    let mut admin_peer = AdminPeer::create(admin_config.clone()).await;
    let admin_id = admin_peer.id.clone();

    let task_admin = tokio::task::spawn(async move {
        admin_peer.run(None).await;
    });

    // Here we create localhost address to connect peer with admin
    let peer_dial_address = Multiaddr::empty()
        .with(Protocol::Ip4(Ipv4Addr::LOCALHOST))
        .with(Protocol::Udp(admin_port))
        .with(Protocol::QuicV1);


    let mut peer = Peer::create("sangedama-peer1".to_string()).await;
    let peer_dial_address_p1 = peer_dial_address.clone();
    let admin_id_p1 = admin_id.clone();
    let task_client = tokio::task::spawn(async move {
        peer.run(
            peer_dial_address_p1,
            PeerId::from_str(&admin_id_p1).unwrap(),
        ).await;
    });
    let mut peer2 = Peer::create("sangedama-peer2".to_string()).await;
    let peer_dial_address_p2 = peer_dial_address.clone();
    let admin_id_p2 = admin_id.clone();
    let task_client2 = tokio::task::spawn(async move {
        peer2.run(
            peer_dial_address_p2,
            PeerId::from_str(&admin_id_p2).unwrap(),
        ).await;
    });

    task_admin.await.unwrap();
    task_client.await.unwrap();
    task_client2.await.unwrap();
}